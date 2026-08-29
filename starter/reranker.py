from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
FIELD_WEIGHTS = {
    "title": 4.0,
    "categories": 3.0,
    "features": 2.0,
    "details": 2.0,
    "store": 1.5,
    "description": 1.0,
}


def _field_tokens(value: object) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(str(value))}


def _popularity(candidate: Mapping[str, object]) -> float:
    try:
        count = float(candidate.get("rating_number") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return math.log1p(max(count, 0.0))


def _best_weight_by_term(query_terms: Sequence[str], candidate: Mapping[str, object]) -> dict[str, float]:
    best_weight_by_term = {term: 0.0 for term in query_terms}
    for field, weight in FIELD_WEIGHTS.items():
        tokens = _field_tokens(candidate.get(field, ""))
        for term in best_weight_by_term.keys() & tokens:
            best_weight_by_term[term] = max(best_weight_by_term[term], weight)
    return best_weight_by_term


def _match_score(
    best_weight_by_term: Mapping[str, float],
    idf: Mapping[str, float] | None = None,
) -> float:
    if idf is None:
        return sum(best_weight_by_term.values())
    return sum(
        weight * idf.get(term, 1.0)
        for term, weight in best_weight_by_term.items()
    )


def rerank_candidates(
    query_terms: Sequence[str],
    candidates: Sequence[Mapping[str, object]],
    top_k: int,
    idf: Mapping[str, float] | None = None,
    popularity_weight: float = 0.0,
    required_terms: Sequence[str] | None = None,
    completeness_bonus: float = 0.0,
) -> list[str]:
    """Order candidates by field-weighted term matches.

    `idf` optionally weights each term by how rare it is in the whole catalog,
    so a distinctive word counts for more than a ubiquitous one. Frequency must
    come from the full catalog, never from the candidate pool: the pool is the
    set of documents the query already matched, so the query's most important
    term appears in nearly all of them and pool frequency would penalise it.

    `popularity_weight` scales a `log1p(rating_number)` prior. The hidden target
    is a real purchase record, and purchased items are reviewed items: the
    median target carries 6,846 ratings against a catalog median of 12. The
    weight is kept small enough that a better constraint match still wins, so
    the prior separates candidates that are otherwise tied.

    `required_terms` (with `completeness_bonus`) rewards a candidate that
    matches every one of a customer's currently-known constraints, as
    opposed to one that racks up more individual term matches elsewhere
    without satisfying all of them together. `required_terms` must be a
    subset of `query_terms` -- completeness is read off the same per-term
    field weights already computed for scoring, not a second text scan.
    Intended for Buying-classified sessions only; omit for Browsing, where
    the customer has not committed to a specific value yet.
    """
    required = set(required_terms or ())
    scored = []
    for rank, candidate in enumerate(candidates):
        best_weight_by_term = _best_weight_by_term(query_terms, candidate)
        score = _match_score(best_weight_by_term, idf) + popularity_weight * _popularity(candidate)
        if required and all(best_weight_by_term.get(term, 0.0) > 0.0 for term in required):
            score += completeness_bonus
        scored.append((score, rank, str(candidate["parent_asin"])))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [parent_asin for _, _, parent_asin in scored[:top_k]]
