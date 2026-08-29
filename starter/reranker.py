from __future__ import annotations

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


def _match_score(query_terms: Sequence[str], candidate: Mapping[str, object]) -> float:
    best_weight_by_term = {term: 0.0 for term in query_terms}
    for field, weight in FIELD_WEIGHTS.items():
        tokens = _field_tokens(candidate.get(field, ""))
        for term in best_weight_by_term.keys() & tokens:
            best_weight_by_term[term] = max(best_weight_by_term[term], weight)
    return sum(best_weight_by_term.values())


def rerank_candidates(
    query_terms: Sequence[str],
    candidates: Sequence[Mapping[str, object]],
    top_k: int,
) -> list[str]:
    scored = [
        (_match_score(query_terms, candidate), rank, str(candidate["parent_asin"]))
        for rank, candidate in enumerate(candidates)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [parent_asin for _, _, parent_asin in scored[:top_k]]
