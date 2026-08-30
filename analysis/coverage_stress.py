from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from analysis.catalog_profile import _present


ALGORITHM_VERSION = "coverage-stress-v1"
DEFAULT_SEED = "techjam-coverage-stress-v1"
DEFAULT_FIELDS = (
    "title", "features", "description", "price", "categories",
    "details", "average_rating", "rating_number", "store",
)
REQUIRED_INVARIANTS = {
    "ordered_identifiers_preserved": True,
    "non_targets_preserved": True,
    "no_fields_filled": True,
    "planned_counts_matched": True,
}


@dataclass(frozen=True)
class FieldMaskPlan:
    field: str
    catalog_present: int
    catalog_coverage: float
    desired_target_present: int
    original_target_present: int
    masked_ids: frozenset[str]
    unfillable_shortfall: int


def _mask_digest(seed: str, field: str, parent_asin: str) -> bytes:
    value = "\0".join((ALGORITHM_VERSION, seed, field, parent_asin))
    return hashlib.sha256(value.encode("utf-8")).digest()


def _index_products(products: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    indexed: dict[str, Mapping[str, object]] = {}
    for product in products:
        parent_asin = str(product.get("parent_asin", ""))
        if not parent_asin:
            raise ValueError("catalog product is missing parent_asin")
        if parent_asin in indexed:
            raise ValueError(f"duplicate catalog parent_asin: {parent_asin}")
        indexed[parent_asin] = product
    return indexed


def plan_field_masks(
    products: Sequence[Mapping[str, object]],
    target_ids: Sequence[str],
    fields: Sequence[str] = DEFAULT_FIELDS,
    seed: str = DEFAULT_SEED,
) -> dict[str, FieldMaskPlan]:
    indexed = _index_products(products)
    normalized_targets = tuple(str(value) for value in target_ids)
    if len(set(normalized_targets)) != len(normalized_targets):
        raise ValueError("public target parent_asin values must be distinct")
    missing = sorted(set(normalized_targets) - indexed.keys())
    if missing:
        raise ValueError(f"public targets missing from catalog: {', '.join(missing)}")

    plans: dict[str, FieldMaskPlan] = {}
    for field in fields:
        catalog_present = sum(_present(product.get(field)) for product in products)
        catalog_coverage = 0.0 if not products else catalog_present / len(products)
        present_targets = [
            parent_asin for parent_asin in normalized_targets
            if _present(indexed[parent_asin].get(field))
        ]
        desired = round(catalog_coverage * len(normalized_targets))
        mask_count = max(0, len(present_targets) - desired)
        ranked = sorted(present_targets, key=lambda value: _mask_digest(seed, field, value))
        plans[field] = FieldMaskPlan(
            field=field,
            catalog_present=catalog_present,
            catalog_coverage=round(catalog_coverage, 6),
            desired_target_present=desired,
            original_target_present=len(present_targets),
            masked_ids=frozenset(ranked[:mask_count]),
            unfillable_shortfall=max(0, desired - len(present_targets)),
        )
    return plans


def apply_masks_to_product(
    product: Mapping[str, object],
    plans: Mapping[str, FieldMaskPlan],
) -> dict:
    result = dict(product)
    parent_asin = str(result["parent_asin"])
    for field, plan in plans.items():
        if parent_asin not in plan.masked_ids:
            continue
        value = result.get(field)
        if isinstance(value, list):
            result[field] = []
        elif isinstance(value, dict):
            result[field] = {}
        else:
            result[field] = None
    return result


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _resolve_distinct_paths(
    source_catalog: str | Path,
    dataset_path: str | Path,
    output_catalog: str | Path,
    manifest_path: str | Path,
) -> tuple[Path, Path, Path, Path]:
    paths = {
        "source_catalog": Path(source_catalog).resolve(),
        "dataset_path": Path(dataset_path).resolve(),
        "output_catalog": Path(output_catalog).resolve(),
        "manifest_path": Path(manifest_path).resolve(),
    }
    normalized = {
        name: os.path.normcase(os.path.normpath(str(path)))
        for name, path in paths.items()
    }
    names = tuple(paths)
    for index, name in enumerate(names):
        for other_name in names[index + 1:]:
            if normalized[name] == normalized[other_name]:
                raise ValueError(
                    f"coverage-stress paths must be distinct: {name} and {other_name} "
                    f"resolve to {paths[name]}"
                )
    return (
        paths["source_catalog"],
        paths["dataset_path"],
        paths["output_catalog"],
        paths["manifest_path"],
    )


def _atomic_write_jsonl(path: Path, rows: Sequence[Mapping[str, object]], validate) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        validate(temporary)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    try:
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _validate_generated_catalog(
    source_path: Path,
    generated_path: Path,
    target_ids: Sequence[str],
    plans: Mapping[str, FieldMaskPlan],
) -> None:
    source = _load_jsonl(source_path)
    generated = _load_jsonl(generated_path)
    if len(source) != len(generated):
        raise ValueError("generated catalog row count differs from source")
    source_ids = [str(row.get("parent_asin", "")) for row in source]
    generated_ids = [str(row.get("parent_asin", "")) for row in generated]
    if source_ids != generated_ids:
        raise ValueError("generated catalog identifiers differ from source")

    target_set = set(target_ids)
    for original, result in zip(source, generated):
        parent_asin = str(original["parent_asin"])
        if parent_asin not in target_set and result != original:
            raise ValueError("generated catalog changed a non-target product")
        for field in set(original) | set(result):
            if _present(result.get(field)) and not _present(original.get(field)):
                raise ValueError(f"generated catalog filled missing field: {field}")
            if parent_asin in target_set and field not in plans and result.get(field) != original.get(field):
                raise ValueError(f"generated catalog changed unplanned field: {field}")

    generated_by_id = _index_products(generated)
    source_by_id = _index_products(source)
    for field, plan in plans.items():
        for parent_asin in target_ids:
            original = source_by_id[parent_asin]
            expected = apply_masks_to_product(original, {field: plan}).get(field)
            if generated_by_id[parent_asin].get(field) != expected:
                raise ValueError(f"generated catalog mask membership mismatch for field: {field}")
        final_count = sum(
            _present(generated_by_id[parent_asin].get(field))
            for parent_asin in target_ids
        )
        expected_count = plan.original_target_present - len(plan.masked_ids)
        if final_count != expected_count:
            raise ValueError(f"generated catalog mask count mismatch for field: {field}")


def _build_manifest(
    source_path: Path,
    dataset: Path,
    output: Path,
    target_ids: Sequence[str],
    products: Sequence[Mapping[str, object]],
    plans: Mapping[str, FieldMaskPlan],
    seed: str,
) -> dict:
    field_manifest = {
        field: {
            "catalog_present": plan.catalog_present,
            "catalog_coverage": plan.catalog_coverage,
            "desired_target_present": plan.desired_target_present,
            "original_target_present": plan.original_target_present,
            "masked_count": len(plan.masked_ids),
            "stress_target_present": plan.original_target_present - len(plan.masked_ids),
            "unfillable_shortfall": plan.unfillable_shortfall,
        }
        for field, plan in plans.items()
    }
    return {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "seed": seed,
        "field_order": list(plans),
        "source_catalog": Path(os.path.relpath(source_path.resolve(), Path.cwd())).as_posix(),
        "dataset": Path(os.path.relpath(dataset.resolve(), Path.cwd())).as_posix(),
        "output_catalog": Path(os.path.relpath(output.resolve(), Path.cwd())).as_posix(),
        "source_catalog_sha256": file_sha256(source_path),
        "dataset_sha256": file_sha256(dataset),
        "output_catalog_sha256": file_sha256(output),
        "catalog_row_count": len(products),
        "session_count": len(target_ids),
        "distinct_target_count": len(set(target_ids)),
        "matched_target_count": len(set(target_ids)),
        "fields": field_manifest,
        "invariants": dict(REQUIRED_INVARIANTS),
    }


def build_coverage_stress_catalog(
    source_catalog: str | Path,
    dataset_path: str | Path,
    output_catalog: str | Path,
    manifest_path: str | Path,
    fields: Sequence[str] = DEFAULT_FIELDS,
    seed: str = DEFAULT_SEED,
) -> dict:
    source_path, dataset, output, manifest_file = _resolve_distinct_paths(
        source_catalog, dataset_path, output_catalog, manifest_path
    )
    products = _load_jsonl(source_path)
    samples = _load_jsonl(dataset)
    target_ids = [str(row["ground_truth"]["parent_asin"]) for row in samples]
    plans = plan_field_masks(products, target_ids, fields, seed)
    generated = [apply_masks_to_product(product, plans) for product in products]
    _atomic_write_jsonl(
        output,
        generated,
        validate=lambda temporary: _validate_generated_catalog(
            source_path, temporary, target_ids, plans
        ),
    )
    manifest = _build_manifest(
        source_path, dataset, output, target_ids, products, plans, seed
    )
    _atomic_write_json(manifest_file, manifest)
    return manifest


def manifest_is_current(
    source_catalog: str | Path,
    dataset_path: str | Path,
    output_catalog: str | Path,
    manifest_path: str | Path,
    seed: str = DEFAULT_SEED,
    fields: Sequence[str] = DEFAULT_FIELDS,
) -> bool:
    source = Path(source_catalog)
    dataset = Path(dataset_path)
    output = Path(output_catalog)
    manifest_file = Path(manifest_path)
    if not output.is_file() or not manifest_file.is_file():
        return False
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        return (
            manifest["schema_version"] == 1
            and manifest["algorithm_version"] == ALGORITHM_VERSION
            and manifest["seed"] == seed
            and manifest["field_order"] == list(fields)
            and manifest["source_catalog_sha256"] == file_sha256(source)
            and manifest["dataset_sha256"] == file_sha256(dataset)
            and manifest["output_catalog_sha256"] == file_sha256(output)
            and manifest["invariants"] == REQUIRED_INVARIANTS
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False
