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


def _average_rating(candidate: Mapping[str, object]) -> float:
    try:
        return float(candidate.get("average_rating") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _has_price(candidate: Mapping[str, object]) -> float:
    return 1.0 if candidate.get("has_price") else 0.0


def _match_score(
    query_terms: Sequence[str],
    candidate: Mapping[str, object],
    idf: Mapping[str, float] | None = None,
) -> float:
    best_weight_by_term = {term: 0.0 for term in query_terms}
    for field, weight in FIELD_WEIGHTS.items():
        tokens = _field_tokens(candidate.get(field, ""))
        for term in best_weight_by_term.keys() & tokens:
            best_weight_by_term[term] = max(best_weight_by_term[term], weight)
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
    price_weight: float = 0.0,
    rating_weight: float = 0.0,
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

    `price_weight` scales a flat bonus for carrying a price at all. 89% of
    public targets have one against 21% of the catalog, and the gap survives
    controlling for popularity: within the catalog's top popularity decile only
    31.7% are priced, while targets in that same decile are 89% priced. A
    listing with a price is an active listing, and only active listings get
    purchased. It is a bonus rather than a filter because 11% of targets carry
    no price.

    `rating_weight` scales the star rating. It is a far weaker signal than the
    review count: targets average 4.372 against the catalog's 4.087, but within
    the top popularity decile where 173 of 200 targets sit that gap shrinks to
    4.385 against 4.301. Three quarters of the catalog also sits between 4.0 and
    5.0 stars, leaving little range to discriminate on. An unrated item scores
    zero here, which is a penalty consistent with the purchase prior.
    """
    scored = [
        (
            _match_score(query_terms, candidate, idf)
            + popularity_weight * _popularity(candidate)
            + price_weight * _has_price(candidate)
            + rating_weight * _average_rating(candidate),
            rank,
            str(candidate["parent_asin"]),
        )
        for rank, candidate in enumerate(candidates)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [parent_asin for _, _, parent_asin in scored[:top_k]]
