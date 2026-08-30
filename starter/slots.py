from __future__ import annotations

from collections.abc import Mapping

from analysis.gazetteer import normalize_term


# Customer abbreviations for materials the mined gazetteer only ever learns
# under their full chemical name from `details.Material` seed values -- the
# abbreviation itself never appears there, so the mined vocabulary alone never
# learns it. "pu leather" must resolve to the synthetic term before slot
# matching runs, or the "leather" it contains would tag the constraint as
# genuine leather instead. Each alias is hand-verified against its own real
# usage (unlike deriving one from initials, which is unsafe: "polyvinyl
# chloride" naively initializes to "PC", a different, real material --
# polycarbonate -- so that path is not used here).
_MATERIAL_ALIASES = {
    "pu leather": "faux leather",
    "pleather": "faux leather",
    "pu": "faux leather",
    "pvc": "polyvinyl chloride",
    "eva": "ethylene vinyl acetate",
}


def _apply_material_aliases(haystack: str, material_terms: Mapping[str, int]) -> str:
    for alias in sorted(_MATERIAL_ALIASES, key=len, reverse=True):
        canonical = _MATERIAL_ALIASES[alias]
        if canonical not in material_terms:
            continue
        haystack = haystack.replace(f" {alias} ", f" {canonical} ")
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
