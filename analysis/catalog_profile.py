from __future__ import annotations

from collections.abc import Iterable


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def profile_catalog(products: Iterable[dict], fields: tuple[str, ...]) -> dict:
    rows = list(products)
    result: dict[str, dict] = {}
    for field in sorted(fields):
        present = sum(_present(row.get(field)) for row in rows)
        result[field] = {
            "present": present,
            "missing": len(rows) - present,
            "coverage": 0.0 if not rows else round(present / len(rows), 6),
        }
    return {"row_count": len(rows), "fields": result}
