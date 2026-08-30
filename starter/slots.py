from __future__ import annotations

from collections.abc import Mapping

from analysis.gazetteer import normalize_term


# Customer surface forms for the synthetic material, mined from `details.Material`
# seed values only as "faux leather" or "polyurethane" -- "PU" and "pleather"
# never appear there, so the mined vocabulary alone never learns them. "pu leather"
# must resolve to the synthetic term before slot matching runs, or the "leather"
# it contains would tag the constraint as genuine leather instead.
_MATERIAL_ALIASES = {
    "pu leather": "faux leather",
    "pleather": "faux leather",
    "pu": "faux leather",
}


def _apply_material_aliases(haystack: str, material_terms: Mapping[str, int]) -> str:
    if "faux leather" not in material_terms:
        return haystack
    for alias in sorted(_MATERIAL_ALIASES, key=len, reverse=True):
        haystack = haystack.replace(f" {alias} ", f" {_MATERIAL_ALIASES[alias]} ")
    return haystack


def extract_slots(
    text: str,
    gazetteer: Mapping[str, Mapping[str, int]],
) -> dict[str, list[str]]:
    """Assign the terms present in `text` to their catalog slots.

    Matching is whole-word over the same normalization used to mine the
    gazetteer, so "dresses" reaches the "dress" entry. Longer matches win:
    "running shoe" suppresses the "shoe" it contains, keeping the most specific
    constraint the customer actually stated.
    """
    haystack = f" {normalize_term(text)} "
    haystack = _apply_material_aliases(haystack, gazetteer.get("material", {}))
    matched: dict[str, list[str]] = {}
    for slot, terms in gazetteer.items():
        hits = [term for term in terms if f" {term} " in haystack]
        if not hits:
            continue
        hits.sort(key=len, reverse=True)
        kept: list[str] = []
        for term in hits:
            if not any(f" {term} " in f" {longer} " for longer in kept):
                kept.append(term)
        matched[slot] = kept
    return matched
