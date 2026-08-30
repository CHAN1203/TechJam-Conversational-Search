# Coverage-Stress Dual Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic no-imputation coverage-stress catalog and make every evaluator-facing experiment run official and stress catalog variants by default.

**Architecture:** Pure functions in `analysis/coverage_stress.py` calculate and apply target-only masks, while `analysis/catalog_variants.py` verifies or rebuilds the generated artifact and exposes official/stress paths to experiment scripts. The official evaluator remains unchanged; a new default runner plus the existing clarification and popularity scripts execute each experiment independently on both variants and report separate metrics and stress-minus-official deltas.

**Tech Stack:** Python 3.10+, standard library only (`argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `tempfile`, `unittest`), SQLite FTS5 through the existing Agent.

**Spec:** `docs/designs/2026-08-29-coverage-stress-dual-evaluation-design.md`

## Global Constraints

- Never modify `evaluator/`, `data/public_set.jsonl`, or `data/catalog.jsonl`.
- Never fill, copy, impute, or synthesize a missing field.
- Modify only the 200 public target records in the generated catalog; keep all non-target parsed JSON values and the ordered 50,000-ASIN sequence unchanged.
- Use `techjam-coverage-stress-v1` as the default seed and `coverage-stress-v1` as the initial algorithm version.
- Treat official metrics as the primary result and stress metrics only as a public-target-aware sensitivity diagnostic; never combine them into one score.
- Store the generated catalog under ignored `data/generated/`; track only aggregate manifests, results, and reports.
- Preserve the legacy single-catalog payload when `--catalog-mode official` is selected.
- The current working tree already contains a user-requested, uncommitted `docs/experiment_history.md` coverage section. Preserve it and incorporate it in Task 7; never discard or overwrite it when creating an execution worktree.
- Before execution, use `superpowers:using-git-worktrees` to isolate implementation and carry the existing `docs/experiment_history.md` change safely.

---

### Task 1: Deterministic field-mask planning

**Files:**
- Create: `analysis/coverage_stress.py`
- Create: `tests/test_coverage_stress.py`

**Interfaces:**
- Consumes: product dictionaries with unique `parent_asin` values and a sequence of distinct public target IDs.
- Produces: `FieldMaskPlan`, `plan_field_masks(...)`, and `apply_masks_to_product(...)` for Task 2.

- [ ] **Step 1: Write failing tests for exact marginal counts and no-imputation behavior**

Create `tests/test_coverage_stress.py` with this fixture and assertions:

```python
from __future__ import annotations

import unittest

from analysis.coverage_stress import apply_masks_to_product, plan_field_masks


class CoverageStressPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            {
                "parent_asin": "A",
                "price": 10.0,
                "features": ["cotton"],
                "description": ["alpha"],
                "details": {"color": "red"},
                "store": "one",
            },
            {
                "parent_asin": "B",
                "price": 20.0,
                "features": ["wool"],
                "description": [],
                "details": {"color": "blue"},
                "store": "two",
            },
            {
                "parent_asin": "C",
                "price": None,
                "features": ["silk"],
                "description": ["charlie"],
                "details": {},
                "store": None,
            },
            {
                "parent_asin": "D",
                "price": None,
                "features": [],
                "description": ["delta"],
                "details": {"color": "black"},
                "store": "four",
            },
        ]

    def test_plan_masks_only_overcovered_target_fields(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "features", "description", "details", "store"),
            seed="fixed",
        )

        self.assertEqual(1, plans["price"].desired_target_present)
        self.assertEqual(2, plans["price"].original_target_present)
        self.assertEqual(1, len(plans["price"].masked_ids))
        self.assertEqual(2, plans["description"].desired_target_present)
        self.assertEqual(1, plans["description"].original_target_present)
        self.assertEqual(0, len(plans["description"].masked_ids))
        self.assertEqual(1, plans["description"].unfillable_shortfall)

    def test_apply_masks_never_fills_a_missing_field(self) -> None:
        plans = plan_field_masks(
            self.products,
            target_ids=("A", "B"),
            fields=("price", "description"),
            seed="fixed",
        )
        masked = [apply_masks_to_product(product, plans) for product in self.products]

        self.assertEqual([], masked[1]["description"])
        self.assertEqual(["charlie"], masked[2]["description"])
        self.assertEqual(["delta"], masked[3]["description"])
        self.assertEqual(1, sum(row["price"] is not None for row in masked[:2]))

    def test_same_seed_produces_the_same_mask_ids(self) -> None:
        first = plan_field_masks(self.products, ("A", "B"), ("price",), "fixed")
        second = plan_field_masks(self.products, ("B", "A"), ("price",), "fixed")
        self.assertEqual(first["price"].masked_ids, second["price"].masked_ids)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm the import failure**

Run:

```powershell
python -m unittest tests.test_coverage_stress.CoverageStressPlanTest -v
```

Expected: `ERROR` with `ModuleNotFoundError` or missing exported symbols from `analysis.coverage_stress`.

- [ ] **Step 3: Implement the mask-plan data type and deterministic selection**

Create `analysis/coverage_stress.py` with these definitions and the minimal helpers they call:

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from collections.abc import Mapping, Sequence

from analysis.catalog_profile import _present


ALGORITHM_VERSION = "coverage-stress-v1"
DEFAULT_SEED = "techjam-coverage-stress-v1"
DEFAULT_FIELDS = (
    "title", "features", "description", "price", "categories",
    "details", "average_rating", "rating_number", "store",
)


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
```

- [ ] **Step 4: Add explicit failure tests for duplicate and missing IDs**

Append tests that call `plan_field_masks` with duplicate target IDs, a missing target, and duplicate catalog rows, asserting the exact `ValueError` message fragments `must be distinct`, `missing from catalog`, and `duplicate catalog parent_asin`.

- [ ] **Step 5: Run the component and complete suites**

Run:

```powershell
python -m unittest tests.test_coverage_stress -v
python -m unittest discover -s tests -v
```

Expected: all coverage-stress tests pass and the existing suite has zero failures.

- [ ] **Step 6: Commit Task 1**

```powershell
git add analysis/coverage_stress.py tests/test_coverage_stress.py
git commit -m "feat: plan deterministic coverage masks"
```

---

### Task 2: Atomic catalog generation and aggregate manifest

**Files:**
- Modify: `analysis/coverage_stress.py`
- Modify: `tests/test_coverage_stress.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `plan_field_masks(...)` and `apply_masks_to_product(...)` from Task 1.
- Produces: `build_coverage_stress_catalog(...) -> dict`, `manifest_is_current(...) -> bool`, and an ignored generated JSONL artifact for Task 3.

- [ ] **Step 1: Write a failing end-to-end generator test**

Add a temporary-directory test that writes the four-product Task 1 fixture and two public samples, then calls:

```python
manifest = build_coverage_stress_catalog(
    source_catalog=catalog_path,
    dataset_path=dataset_path,
    output_catalog=output_path,
    manifest_path=manifest_path,
    fields=("price", "features", "description", "details", "store"),
    seed="fixed",
)
```

Assert all of the following:

```python
self.assertEqual(4, manifest["catalog_row_count"])
self.assertEqual(2, manifest["session_count"])
self.assertEqual(2, manifest["distinct_target_count"])
self.assertEqual(1, manifest["fields"]["price"]["stress_target_present"])
self.assertEqual(1, manifest["fields"]["description"]["unfillable_shortfall"])
self.assertTrue(output_path.exists())
self.assertTrue(manifest_path.exists())
self.assertTrue(manifest_is_current(
    source_catalog=catalog_path,
    dataset_path=dataset_path,
    output_catalog=output_path,
    manifest_path=manifest_path,
    seed="fixed",
    fields=("price", "features", "description", "details", "store"),
))
```

Reload both catalogs and assert ordered ASIN equality, parsed equality for `C` and `D`, and that only target fields named in the plans changed.

- [ ] **Step 2: Run the test and confirm the missing builder failure**

Run:

```powershell
python -m unittest tests.test_coverage_stress.CoverageStressBuildTest -v
```

Expected: import or attribute failure for `build_coverage_stress_catalog`.

- [ ] **Step 3: Implement hashing, JSONL loading, validation, and atomic replacement**

Add these public functions to `analysis/coverage_stress.py`. Keep file loading,
atomic writing, and post-write validation in private helpers named
`_load_jsonl`, `_atomic_write_jsonl`, `_validate_generated_catalog`, and
`_atomic_write_json`; use `_build_manifest` for aggregate serialization. Extend
the Task 1 imports with `json`, `os`, `tempfile`, and `Path` from `pathlib`:

```python
def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build_coverage_stress_catalog(
    source_catalog: str | Path,
    dataset_path: str | Path,
    output_catalog: str | Path,
    manifest_path: str | Path,
    fields: Sequence[str] = DEFAULT_FIELDS,
    seed: str = DEFAULT_SEED,
) -> dict:
    source_path = Path(source_catalog)
    dataset = Path(dataset_path)
    output = Path(output_catalog)
    manifest_file = Path(manifest_path)
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
            and all(manifest["invariants"].values())
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False
```

Use `Path.open(encoding="utf-8")` to load JSONL. Extract target IDs only from
`sample["ground_truth"]["parent_asin"]`; do not import evaluator behavior. Build
the manifest field rows from each `FieldMaskPlan`:

```python
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
```

Write the output to a `tempfile.NamedTemporaryFile` in `output_catalog.parent`,
close it, validate the temporary JSONL, then replace the destination with
`Path.replace`. Validate before replacement:

- output row count and ordered ASINs equal the source;
- every non-target parsed row equals the source row;
- no field changes from missing to present;
- final target counts equal `original_target_present - masked_count`.

Write the manifest atomically after the output replacement. Include:

```python
manifest = {
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
    "invariants": {
        "ordered_identifiers_preserved": True,
        "non_targets_preserved": True,
        "no_fields_filled": True,
        "planned_counts_matched": True,
    },
}
```

`manifest_is_current` returns `False` for missing/unreadable files and otherwise
requires matching schema, algorithm, seed, all three current SHA-256 hashes, and
the four `True` invariants.

- [ ] **Step 4: Add staleness and determinism tests**

Build twice with the same seed and assert the output SHA-256 is identical. Then
change one dataset byte through a valid JSON field, assert `manifest_is_current`
is `False`, rebuild, and assert it returns `True`. Also simulate a failing
validation and assert an already valid output file remains unchanged.

- [ ] **Step 5: Ignore only generated catalog artifacts**

Append to `.gitignore`:

```gitignore
# Local deterministic coverage-stress catalog artifacts.
data/generated/
```

- [ ] **Step 6: Run tests and verify ignore behavior**

```powershell
python -m unittest tests.test_coverage_stress -v
python -m unittest discover -s tests -v
git check-ignore -v data/generated/catalog-coverage-stress.jsonl
```

Expected: all tests pass and `git check-ignore` identifies the new `.gitignore` rule.

- [ ] **Step 7: Commit Task 2**

```powershell
git add .gitignore analysis/coverage_stress.py tests/test_coverage_stress.py
git commit -m "feat: build coverage stress catalog"
```

---

### Task 3: Catalog variant resolver and build CLI

**Files:**
- Create: `analysis/catalog_variants.py`
- Create: `scripts/build_coverage_stress_catalog.py`
- Create: `tests/test_catalog_variants.py`
- Modify: `tests/test_coverage_stress.py`

**Interfaces:**
- Consumes: `build_coverage_stress_catalog(...)` and `manifest_is_current(...)` from Task 2.
- Produces: `add_catalog_variant_arguments(...)` and `resolve_catalog_variants(...)` for Tasks 4–6, plus a human-runnable catalog build command.

- [ ] **Step 1: Write failing resolver tests**

Use temporary source and dataset fixtures. Verify:

```python
official, manifest = resolve_catalog_variants(
    catalog_path=catalog_path,
    dataset_path=dataset_path,
    mode="official",
    stress_catalog_path=stress_path,
    manifest_path=manifest_path,
    seed="fixed",
)
self.assertEqual({"official": catalog_path}, official)
self.assertIsNone(manifest)
self.assertFalse(stress_path.exists())

dual, manifest = resolve_catalog_variants(
    catalog_path=catalog_path,
    dataset_path=dataset_path,
    mode="dual",
    stress_catalog_path=stress_path,
    manifest_path=manifest_path,
    seed="fixed",
)
self.assertEqual({"official", "coverage_stress"}, set(dual))
self.assertEqual(stress_path, dual["coverage_stress"])
self.assertIsNotNone(manifest)
```

Call `stress` mode separately and assert only `coverage_stress` is returned.

- [ ] **Step 2: Run the resolver test and confirm the import failure**

```powershell
python -m unittest tests.test_catalog_variants -v
```

Expected: `ModuleNotFoundError: analysis.catalog_variants`.

- [ ] **Step 3: Implement the shared resolver**

Create `analysis/catalog_variants.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from analysis.coverage_stress import (
    DEFAULT_SEED,
    build_coverage_stress_catalog,
    manifest_is_current,
)


CATALOG_MODES = ("dual", "official", "stress")


def add_catalog_variant_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog-mode", choices=CATALOG_MODES, default="dual")
    parser.add_argument(
        "--stress-catalog",
        default="data/generated/catalog-coverage-stress.jsonl",
    )
    parser.add_argument(
        "--stress-manifest",
        default="reports/experiments/coverage-stress-catalog.json",
    )
    parser.add_argument("--stress-seed", default=DEFAULT_SEED)


def resolve_catalog_variants(
    catalog_path: str | Path,
    dataset_path: str | Path,
    mode: str,
    stress_catalog_path: str | Path,
    manifest_path: str | Path,
    seed: str = DEFAULT_SEED,
) -> tuple[dict[str, Path], dict | None]:
    if mode not in CATALOG_MODES:
        raise ValueError(f"unsupported catalog mode: {mode}")
    official = Path(catalog_path)
    dataset = Path(dataset_path)
    if mode == "official":
        return {"official": official}, None

    stress = Path(stress_catalog_path)
    manifest_file = Path(manifest_path)
    if not manifest_is_current(
        official, dataset, stress, manifest_file, seed=seed
    ):
        manifest = build_coverage_stress_catalog(
            official, dataset, stress, manifest_file, seed=seed
        )
    else:
        import json
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    if mode == "stress":
        return {"coverage_stress": stress}, manifest
    return {"official": official, "coverage_stress": stress}, manifest
```

- [ ] **Step 4: Implement the build CLI and compact field table**

Create `scripts/build_coverage_stress_catalog.py` with `--catalog`, `--dataset`,
`--output`, `--manifest`, and `--seed`. Call the Task 2 builder and print one row
per field in this format:

```python
print("field\toriginal\tdesired\tmasked\tstress\tshortfall")
for field, row in manifest["fields"].items():
    print(
        f"{field}\t{row['original_target_present']}\t"
        f"{row['desired_target_present']}\t{row['masked_count']}\t"
        f"{row['stress_target_present']}\t{row['unfillable_shortfall']}"
    )
```

- [ ] **Step 5: Test CLI help and resolver reuse**

```powershell
python -m unittest tests.test_catalog_variants tests.test_coverage_stress -v
python -m scripts.build_coverage_stress_catalog --help
python -m unittest discover -s tests -v
```

Expected: tests pass and help lists all five build arguments.

- [ ] **Step 6: Commit Task 3**

```powershell
git add analysis/catalog_variants.py scripts/build_coverage_stress_catalog.py tests/test_catalog_variants.py tests/test_coverage_stress.py
git commit -m "feat: resolve official and stress catalogs"
```

---

### Task 4: Default dual-catalog evaluator runner

**Files:**
- Modify: `analysis/experiment_results.py`
- Modify: `tests/test_experiment_results.py`
- Create: `scripts/run_dual_catalog_evaluation.py`
- Create: `tests/test_dual_catalog_evaluation.py`

**Interfaces:**
- Consumes: catalog paths from `resolve_catalog_variants(...)`, existing `evaluate(...)`, `catalog_index(...)`, and `Agent`.
- Produces: `summary_delta(...)`, `run_catalog_evaluation(...)`, and aggregate dual-run JSON used by Task 7.

- [ ] **Step 1: Write a failing summary-delta unit test**

Add to `tests/test_experiment_results.py`:

```python
from analysis.experiment_results import summary_delta

def test_summary_delta_reports_only_core_metrics(self) -> None:
    official = {
        "sample_count": 2,
        "hit_rate_at_10": 0.5,
        "mrr": 0.25,
        "mttc": 7.0,
        "efficiency": 0.4,
        "recommended_technical_score": 0.405,
    }
    stress = {
        "sample_count": 2,
        "hit_rate_at_10": 0.25,
        "mrr": 0.125,
        "mttc": 9.0,
        "efficiency": 0.2,
        "recommended_technical_score": 0.2025,
    }
    self.assertEqual(
        {
            "hit_rate_at_10": -0.25,
            "mrr": -0.125,
            "mttc": 2.0,
            "efficiency": -0.2,
            "recommended_technical_score": -0.2025,
        },
        summary_delta(official, stress),
    )
```

- [ ] **Step 2: Run the test and verify the missing function failure**

```powershell
python -m unittest tests.test_experiment_results -v
```

Expected: import failure for `summary_delta`.

- [ ] **Step 3: Implement explicit core metric deltas**

Append to `analysis/experiment_results.py`:

```python
CORE_METRICS = (
    "hit_rate_at_10", "mrr", "mttc", "efficiency",
    "recommended_technical_score",
)


def summary_delta(official: dict, stress: dict) -> dict[str, float]:
    return {
        metric: round(float(stress[metric]) - float(official[metric]), 6)
        for metric in CORE_METRICS
        if metric in official and metric in stress
        and official[metric] is not None and stress[metric] is not None
    }
```

Do not subtract `sample_count`, elapsed time, token counts, or arbitrary numeric fields.

- [ ] **Step 4: Write a failing dual-run payload test**

In `tests/test_dual_catalog_evaluation.py`, create two two-product catalogs and
one public sample. Make the stress catalog mask the target's searchable term so
the official and stress results differ. Call:

```python
payload = run_catalog_evaluation(
    variants={"official": official_path, "coverage_stress": stress_path},
    samples=samples,
)
```

Assert `payload["catalogs"]` contains both variants, neither result contains
`sessions`, and `payload["deltas"]["overall"]` equals
`summary_delta(official_summary, stress_summary)`. Assert scenario deltas are
keyed by the shared scenario names.

- [ ] **Step 5: Implement the new runner without modifying the evaluator**

Create `scripts/run_dual_catalog_evaluation.py` with:

```python
def _evaluate_catalog(catalog_path: str | Path, samples: list[dict]) -> dict:
    catalog_ids, categories, products = catalog_index(catalog_path)
    result = evaluate(
        Agent(catalog_path), samples, catalog_ids, categories, products
    )
    return {key: value for key, value in result.items() if key != "sessions"}


def run_catalog_evaluation(
    variants: dict[str, Path],
    samples: list[dict],
) -> dict:
    results = {
        name: _evaluate_catalog(path, samples)
        for name, path in variants.items()
    }
    if set(results) != {"official", "coverage_stress"}:
        return next(iter(results.values()))
    official = results["official"]
    stress = results["coverage_stress"]
    shared_scenarios = sorted(
        set(official["scenario_metrics"]) & set(stress["scenario_metrics"])
    )
    return {
        "schema_version": 1,
        "catalogs": results,
        "deltas": {
            "direction": "coverage_stress_minus_official",
            "overall": summary_delta(official, stress),
            "scenario_metrics": {
                scenario: summary_delta(
                    official["scenario_metrics"][scenario],
                    stress["scenario_metrics"][scenario],
                )
                for scenario in shared_scenarios
            },
        },
    }
```

The CLI keeps `--catalog`, `--dataset`, and `--output`, adds shared variant
arguments, resolves variants, runs the payload function, writes JSON, and prints
aggregate results. Default output is
`reports/experiments/coverage-stress-baseline.json`.

- [ ] **Step 6: Verify dual and official-only modes**

```powershell
python -m unittest tests.test_experiment_results tests.test_dual_catalog_evaluation -v
python -m scripts.run_dual_catalog_evaluation --help
python -m unittest discover -s tests -v
```

Expected: tests pass; CLI help shows `dual`, `official`, and `stress`; the
official-only unit fixture returns the legacy aggregate summary rather than a
nested `catalogs` object.

- [ ] **Step 7: Commit Task 4**

```powershell
git add analysis/experiment_results.py tests/test_experiment_results.py scripts/run_dual_catalog_evaluation.py tests/test_dual_catalog_evaluation.py
git commit -m "feat: run default dual catalog evaluation"
```

---

### Task 5: Dual-catalog clarification ablation

**Files:**
- Modify: `scripts/run_clarification_ablation.py`
- Modify: `tests/test_clarification_ablation.py`

**Interfaces:**
- Consumes: unchanged `run_ablation(...)`, `resolve_catalog_variants(...)`, and `summary_delta(...)`.
- Produces: `run_ablation_variants(...)` and dual payload deltas by policy and split.

- [ ] **Step 1: Write the failing dual-ablation test**

Reuse the existing tiny catalog/sample fixture, create a second catalog path,
and call:

```python
payload = run_ablation_variants(
    variants={"official": official_path, "coverage_stress": stress_path},
    samples=samples,
    policies=("fixed", "profile"),
    validation_size=1,
    seed="techjam-clarification-v1",
)
```

Assert:

```python
self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
self.assertEqual({"fixed", "profile"}, set(payload["deltas"]))
self.assertEqual(
    "coverage_stress_minus_official",
    payload["delta_direction"],
)
self.assertIn("full", payload["deltas"]["fixed"])
self.assertIn("validation", payload["deltas"]["profile"])
```

Keep the existing `run_ablation` test unchanged to protect the legacy function.

- [ ] **Step 2: Run the focused test and confirm the missing wrapper failure**

```powershell
python -m unittest tests.test_clarification_ablation -v
```

Expected: import failure for `run_ablation_variants`.

- [ ] **Step 3: Implement variant execution and explicit deltas**

Add:

```python
def run_ablation_variants(
    variants: dict[str, Path],
    samples: list[dict],
    policies: tuple[str, ...] = DEFAULT_POLICIES,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
    results = {
        name: run_ablation(path, samples, policies, validation_size, seed)
        for name, path in variants.items()
    }
    if set(results) != {"official", "coverage_stress"}:
        return next(iter(results.values()))
    official = results["official"]["policies"]
    stress = results["coverage_stress"]["policies"]
    return {
        "schema_version": 1,
        "catalogs": results,
        "delta_direction": "coverage_stress_minus_official",
        "deltas": {
            policy: {
                split: summary_delta(official[policy][split], stress[policy][split])
                for split in ("full", "development", "validation")
            }
            for policy in policies
        },
    }
```

Update `main()` to add variant arguments, resolve paths once, call the wrapper,
and write the result. Do not alter policy defaults, split seed, validation size,
or `run_ablation` behavior.

- [ ] **Step 4: Verify both schemas and all tests**

```powershell
python -m unittest tests.test_clarification_ablation -v
python -m scripts.run_clarification_ablation --help
python -m unittest discover -s tests -v
```

Expected: dual is the CLI default; `--catalog-mode official` is accepted; all
legacy and dual tests pass.

- [ ] **Step 5: Commit Task 5**

```powershell
git add scripts/run_clarification_ablation.py tests/test_clarification_ablation.py
git commit -m "feat: compare clarification on both catalogs"
```

---

### Task 6: Dual-catalog popularity sweep

**Files:**
- Modify: `scripts/run_popularity_sweep.py`
- Create: `tests/test_popularity_sweep.py`

**Interfaces:**
- Consumes: `resolve_catalog_variants(...)`, `summary_delta(...)`, and existing evaluator/split helpers.
- Produces: testable `run_popularity_sweep(...)`, `run_popularity_variants(...)`, and dual deltas by weight, split, and difficulty.

- [ ] **Step 1: Extract behavior expectations into a failing unit test**

Create a two-product catalog and two public samples with different difficulty
buckets. Call the new single-catalog function:

```python
result = run_popularity_sweep(
    catalog_path=catalog_path,
    samples=samples,
    weights=(0.0, 1.2),
    validation_size=1,
    seed="fixed",
)
```

Assert keys `0` and `1.2` exist under `weights`, and each contains `full`,
`development`, `validation`, and both difficulty buckets. This extraction must
preserve the existing main-loop calculations exactly.

- [ ] **Step 2: Run the test and verify the missing function failure**

```powershell
python -m unittest tests.test_popularity_sweep -v
```

Expected: import failure for `run_popularity_sweep`.

- [ ] **Step 3: Extract the current single-catalog implementation**

Move the body currently in `main()` into:

```python
def run_popularity_sweep(
    catalog_path: str | Path,
    samples: list[dict],
    weights: tuple[float, ...] = DEFAULT_WEIGHTS,
    validation_size: int = 80,
    seed: str = DEFAULT_SEED,
) -> dict:
```

Return the existing payload shape:

```python
{
    "seed": seed,
    "validation_size": validation_size,
    "weights": results,
}
```

Keep progress printing in `main()` or a small callback; the pure function must
not be required to parse CLI arguments.

- [ ] **Step 4: Write the failing variant and delta test**

Call `run_popularity_variants` with official and stress fixture paths. Assert:

```python
self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
self.assertEqual("coverage_stress_minus_official", payload["delta_direction"])
self.assertIn("1.2", payload["deltas"])
self.assertIn("validation", payload["deltas"]["1.2"])
self.assertIn("difficulty", payload["deltas"]["1.2"])
```

- [ ] **Step 5: Implement variant execution without changing weight selection**

Add `run_popularity_variants(...)` that calls the single-catalog function for
each variant. For dual mode, loop over the requested string weight keys and use
`summary_delta` for `full`, `development`, and `validation`, plus every shared
difficulty bucket:

```python
weight_deltas[key] = {
    "full": summary_delta(official_row["full"], stress_row["full"]),
    "development": summary_delta(
        official_row["development"], stress_row["development"]
    ),
    "validation": summary_delta(
        official_row["validation"], stress_row["validation"]
    ),
    "difficulty": {
        bucket: summary_delta(
            official_row["difficulty"][bucket],
            stress_row["difficulty"][bucket],
        )
        for bucket in sorted(
            set(official_row["difficulty"]) & set(stress_row["difficulty"])
        )
    },
}
```

Update the CLI to default to dual mode while leaving `DEFAULT_WEIGHTS`, split
seed, and validation size unchanged.

- [ ] **Step 6: Verify legacy and dual behavior**

```powershell
python -m unittest tests.test_popularity_sweep -v
python -m scripts.run_popularity_sweep --help
python -m unittest discover -s tests -v
```

Expected: all tests pass; official-only mode returns the pre-change payload
shape; dual mode nests both catalogs and deltas.

- [ ] **Step 7: Commit Task 6**

```powershell
git add scripts/run_popularity_sweep.py tests/test_popularity_sweep.py
git commit -m "feat: sweep popularity on both catalogs"
```

---

### Task 7: Real-data verification, aggregate evidence, and workflow documentation

**Files:**
- Modify: `data/README.md`
- Modify: `docs/EXPERIMENT_WORKFLOW.md`
- Modify: `docs/experiment_history.md`
- Create: `reports/experiments/coverage-stress-catalog.json`
- Create: `reports/experiments/coverage-stress-baseline.json`
- Create: `reports/experiments/coverage-stress-dual-evaluation.md`
- Generated and ignored: `data/generated/catalog-coverage-stress.jsonl`

**Interfaces:**
- Consumes: all implemented CLIs and the current best default `Agent`.
- Produces: reproducible real-data evidence, documented commands, and the final user-facing interpretation.

- [ ] **Step 1: Run the full suite before real-data generation**

```powershell
python -m unittest discover -s tests -v
```

Expected: zero failures and zero errors. Record the exact test count in the report.

- [ ] **Step 2: Build the real stress catalog**

```powershell
python -m scripts.build_coverage_stress_catalog
```

Expected manifest counts:

```text
details:     original 200, desired 193, masked 7,   stress 193, shortfall 0
store:       original 200, desired 199, masked 1,   stress 199, shortfall 0
features:    original 200, desired 179, masked 21,  stress 179, shortfall 0
description: original 89,  desired 104, masked 0,   stress 89,  shortfall 15
price:       original 178, desired 42,  masked 136, stress 42,  shortfall 0
```

Also confirm title, categories, average rating, and rating count remain 200/200.

- [ ] **Step 3: Prove deterministic regeneration**

Record the generated catalog SHA-256 from the manifest, run the build command a
second time, and confirm the SHA-256 remains identical. Run:

```powershell
git check-ignore -v data/generated/catalog-coverage-stress.jsonl
```

Expected: `.gitignore` identifies `data/generated/`, and the generated catalog
does not appear in `git status --short`.

- [ ] **Step 4: Run the current best Agent on both variants**

```powershell
python -m scripts.run_dual_catalog_evaluation --output reports\experiments\coverage-stress-baseline.json
```

Expected: output contains `catalogs.official`, `catalogs.coverage_stress`, and
`deltas`; official results reproduce the current retained metrics within exact
deterministic equality. If official metrics differ from the current documented
`0.965` HitRate and `0.841838` TechnicalScore, stop and investigate before
documenting the stress comparison.

- [ ] **Step 5: Smoke-test both updated experiment entry points**

Run one focused setting per script to control runtime while exercising both variants:

```powershell
python -m scripts.run_clarification_ablation --policies candidate --output reports\experiments\coverage-stress-candidate.json
python -m scripts.run_popularity_sweep --weights 1.2 --output reports\experiments\coverage-stress-popularity.json
```

Expected: each output contains official and coverage-stress results plus deltas.
Use these files for verification only; do not track them unless their aggregate
evidence is referenced in the final report. If not tracked, remove them by exact
filename after extracting the verified aggregate numbers.

- [ ] **Step 6: Update data and experiment workflow documentation**

Add to `data/README.md`:

```markdown
## Generated coverage-stress catalog

`data/generated/catalog-coverage-stress.jsonl` is a local diagnostic artifact.
Build it with `python -m scripts.build_coverage_stress_catalog`. It preserves all
catalog identifiers and masks only over-covered fields on the 200 public targets;
it is not an official catalog or submission artifact.
```

Add the default dual commands and historical reproduction mode to
`docs/EXPERIMENT_WORKFLOW.md`:

```powershell
python -m scripts.run_dual_catalog_evaluation
python -m scripts.run_clarification_ablation --policies candidate
python -m scripts.run_popularity_sweep --weights 1.2
python -m scripts.run_dual_catalog_evaluation --catalog-mode official
```

State that official metrics select methods, stress metrics reveal metadata
sensitivity, and no combined score is valid.

- [ ] **Step 7: Write the aggregate experiment report**

Create `reports/experiments/coverage-stress-dual-evaluation.md` with these exact sections:

```markdown
# Coverage-Stress Dual Evaluation

## Question
## Construction
## Verified invariants
## Target coverage before and after
## Official versus coverage-stress result
## Scenario result
## Interpretation
## Limitations
## Reproduction commands
```

Populate every table from the generated JSON files. Explicitly state that the
stress run changes both retrieval-visible metadata and evaluator-materialized
customer disclosures, matches only marginal presence, leaves description at
89/200, does not correct popularity bias, and cannot forecast private results.

- [ ] **Step 8: Integrate the existing history edit without losing it**

Preserve the already-written `3.3 Public-session target field coverage` section
in `docs/experiment_history.md`. Add a diagnostic entry after the current latest
chronological record that includes:

- exact build and dual-run commands;
- manifest coverage counts;
- official and stress overall/scenario metrics;
- test count;
- decision: keep as a diagnostic evaluation environment, not an Agent method;
- limitations and links to the manifest, result JSON, report, design, and plan.

Do not renumber or rewrite historical E0–E11 method results because the stress
catalog is not a competing retrieval strategy.

- [ ] **Step 9: Run final verification**

```powershell
python -m unittest discover -s tests -v
python -m scripts.build_coverage_stress_catalog
python -m scripts.run_dual_catalog_evaluation --catalog-mode official --output results_official_reproduction.json
git diff --check
git status --short --ignored
git ls-files data/generated
```

Expected:

- all tests pass;
- manifest remains current and deterministic;
- official-only metrics match the dual payload's official metrics;
- `git diff --check` prints no errors;
- `git ls-files data/generated` prints nothing;
- only intended code, tests, tracked aggregate evidence, and English docs are staged.

- [ ] **Step 10: Review the exact staged files and commit Task 7**

```powershell
git add data/README.md docs/EXPERIMENT_WORKFLOW.md docs/experiment_history.md reports/experiments/coverage-stress-catalog.json reports/experiments/coverage-stress-baseline.json reports/experiments/coverage-stress-dual-evaluation.md
git diff --cached --stat
git diff --cached
git commit -m "docs: record dual catalog evaluation"
```

Do not stage `data/generated/`, local smoke outputs, `results_*.json`, Chinese
mirrors, credentials, or any unrelated working-tree file.

---

## Completion Gate

Before reporting implementation complete, verify every task commit exists, run
the final Task 7 commands again on the exact final tree, and use
`superpowers:verification-before-completion`. Report official and stress metrics
separately, the generated artifact hash, exact test count, remaining limitations,
and any uncommitted files that were intentionally preserved.
