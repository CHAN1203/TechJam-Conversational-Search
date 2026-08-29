from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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
