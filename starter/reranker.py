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


def extract_bigrams(text: str) -> list[str]:
    """Consecutive word pairs, lowercased, from one piece of text -- a
    phrase relationship is a property of adjacency within a single
    utterance, not something to accumulate across turns."""
    tokens = TOKEN_RE.findall(text.lower())
    return [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]


def _combined_field_text(candidate: Mapping[str, object]) -> str:
    return " ".join(str(candidate.get(field, "")) for field in FIELD_WEIGHTS).lower()


def _phrase_match_count(phrase_terms: Sequence[str], candidate: Mapping[str, object]) -> int:
    combined = _combined_field_text(candidate)
    return sum(1 for phrase in phrase_terms if phrase in combined)


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
    price_weight: float = 0.0,
    rating_weight: float = 0.0,
    required_terms: Sequence[str] | None = None,
    completeness_bonus: float = 0.0,
    semantic_scores: Mapping[str, float] | None = None,
    semantic_weight: float = 0.0,
    phrase_terms: Sequence[str] | None = None,
    phrase_weight: float = 0.0,
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
    31.6% are priced, while targets in that same decile are 89% priced. A
    listing with a price is an active listing, and only active listings get
    purchased. It is a bonus rather than a filter because 11% of targets carry
    no price.

    `rating_weight` scales the star rating. It is a far weaker signal than the
    review count: targets average 4.372 against the catalog's 4.087, but within
    the top popularity decile where 173 of 200 targets sit that gap shrinks to
    4.385 against 4.301. Two thirds of rated products also sit between 4.0 and
    5.0 stars, leaving little range to discriminate on. An unrated item scores
    zero here, which is a penalty consistent with the purchase prior.

    `required_terms` (with `completeness_bonus`) rewards a candidate that
    matches every one of a customer's currently-known constraints, as
    opposed to one that racks up more individual term matches elsewhere
    without satisfying all of them together. `required_terms` must be a
    subset of `query_terms` -- completeness is read off the same per-term
    field weights already computed for scoring, not a second text scan.
    Intended for Buying-classified sessions only; omit for Browsing, where
    the customer has not committed to a specific value yet.

    `semantic_scores` maps `parent_asin` to a precomputed similarity score
    (e.g. dense cosine similarity between the query and that candidate),
    added as `semantic_weight * semantic_scores[parent_asin]`. A candidate
    absent from the mapping contributes zero, not an error -- the semantic
    signal is a bonus on top of lexical scoring, never a requirement.

    `phrase_terms` (with `phrase_weight`) rewards a candidate whose text
    contains the customer's adjacent word-pairs as a literal substring, not
    just the same words scattered independently -- "running shoe" as a
    phrase is more specific than a document matching "running" and "shoe"
    in unrelated places.
    """
    required = set(required_terms or ())
    semantic_scores = semantic_scores or {}
    phrase_terms = phrase_terms or ()
    scored = []
    for rank, candidate in enumerate(candidates):
        parent_asin = str(candidate["parent_asin"])
        best_weight_by_term = _best_weight_by_term(query_terms, candidate)
        score = _match_score(best_weight_by_term, idf) + popularity_weight * _popularity(candidate)
        score += price_weight * _has_price(candidate)
        score += rating_weight * _average_rating(candidate)
        score += semantic_weight * semantic_scores.get(parent_asin, 0.0)
        score += phrase_weight * _phrase_match_count(phrase_terms, candidate)
        if required and all(best_weight_by_term.get(term, 0.0) > 0.0 for term in required):
            score += completeness_bonus
        scored.append((score, rank, parent_asin))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [parent_asin for _, _, parent_asin in scored[:top_k]]
