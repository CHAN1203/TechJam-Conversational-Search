from __future__ import annotations

from collections.abc import Mapping

from analysis.gazetteer import normalize_term


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
