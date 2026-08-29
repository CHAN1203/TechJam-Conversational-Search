from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from starter.clarification import select_attribute
from starter.reranker import rerank_candidates


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}
CANDIDATE_POOL_SIZE = 100
ATTRIBUTE_QUESTIONS = {
    "material": "Do you have a material preference?",
    "size": "Do you have any sizing or fit requirements?",
    "style": "What style or fit do you prefer?",
    "feature": "Which product feature matters most to you?",
    "use_case": "What will you mainly use it for?",
    "color": "Do you have a color preference?",
    "brand": "Do you have a preferred brand?",
    "budget": "What budget range should I use?",
    "other": "Is there another requirement I should prioritize?",
}


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _terms(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


def _constraint_terms(message: str) -> list[str]:
    lowered = message.lower()
    if any(phrase in lowered for phrase in (
        "don't have a preference",
        "don't have an additional preference",
        "do not have a preference",
        "no preference",
    )):
        return []
    return _terms(message)


def _is_intent_override(message: str) -> bool:
    lowered = message.lower()
    return lowered.startswith("actually") and "ignore my earlier preference" in lowered


class Agent:
    """Offline multi-turn retrieval agent with no LLM dependency."""

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
        clarification_policy: str = "candidate",
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.clarification_policy = clarification_policy
        self.connection = sqlite3.connect(":memory:")
        self._session_terms: dict[str, list[str]] = {}
        self._session_profiles: dict[str, dict] = {}
        self._session_asked_attributes: dict[str, set[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                batch.append(
                    (
                        str(product["parent_asin"]),
                        _text(product.get("title")),
                        _text(product.get("categories")),
                        _text(product.get("features")),
                        _text(product.get("details")),
                        _text(product.get("store")),
                        _text(product.get("description")),
                    )
                )
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

    def reset(self, session_id: str, user_profile: dict) -> None:
        # The profile is anonymized and may be used for personalization.
        self._session_terms[session_id] = []
        self._session_profiles[session_id] = user_profile
        self._session_asked_attributes[session_id] = set()

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        if session_id not in self._session_terms:
            raise RuntimeError("reset must be called before respond")
        current_terms = _constraint_terms(user_message)
        previous_terms = [] if _is_intent_override(user_message) else self._session_terms[session_id]
        unique_terms = list(dict.fromkeys([*previous_terms, *current_terms]))[:40]
        self._session_terms[session_id] = unique_terms
        expression = " OR ".join(f'"{term}"' for term in unique_terms)
        if not expression:
            candidates: list[dict] = []
            recommendations: list[dict] = []
        else:
            rows = self.connection.execute(
                "SELECT parent_asin, title, categories, features, details, store, description "
                "FROM products WHERE products MATCH ? "
                "ORDER BY bm25(products, 0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0) LIMIT ?",
                (expression, max(top_k, CANDIDATE_POOL_SIZE)),
            ).fetchall()
            candidates = [
                {
                    "parent_asin": row[0],
                    "title": row[1],
                    "categories": row[2],
                    "features": row[3],
                    "details": row[4],
                    "store": row[5],
                    "description": row[6],
                }
                for row in rows
            ]
            recommendations = [
                {"parent_asin": parent_asin}
                for parent_asin in rerank_candidates(unique_terms, candidates, top_k)
            ]
        asked = self._session_asked_attributes[session_id]
        ask_attribute = select_attribute(
            self.clarification_policy,
            self._session_profiles[session_id],
            asked,
            candidates,
        )
        if ask_attribute is not None:
            asked.add(ask_attribute)
        return {
            "message": ATTRIBUTE_QUESTIONS.get(
                ask_attribute,
                "Here are the closest matches I found.",
            ),
            "ask_attribute": ask_attribute,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
