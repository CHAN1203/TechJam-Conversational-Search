from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path

from starter.clarification import select_attribute
from starter.dense import DenseIndex
from starter.slots import extract_slots
from starter.reranker import rerank_candidates


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}
CANDIDATE_POOL_SIZE = 100
# An intent override replaces a preference, not the thing being shopped for.
# These slots describe the item itself, so they survive the override unless the
# customer names a replacement for them in the same message.
DURABLE_SLOTS = ("category", "department")
# Constraints volunteered on the opening turn are what an override revokes.
OPENING_TURN = 1
# The hidden target is a real purchase record and purchased items are reviewed
# items: the median target carries 6,846 ratings against a catalog median of 12.
# Kept small enough that a better constraint match still outranks mere
# popularity; it separates candidates that would otherwise tie.
POPULARITY_WEIGHT = 1.2
# Reasoned choice from a 3-point triangulation (0.5, 1.0, 2.0), not a full
# validation-split sweep -- see reports/experiments/semantic-reranking.md.
# 1.0 improved TechnicalScore with zero sessions flipping hit/miss; 2.0
# regressed. A fuller sweep is a reasonable next step, not done here.
SEMANTIC_WEIGHT = 1.0
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


# One title-weight unit (FIELD_WEIGHTS["title"] in starter/reranker.py). Large
# enough to outweigh a handful of cheap, single-field matches elsewhere, small
# enough that a candidate missing several field-weighted terms cannot win on
# completeness alone.
COMPLETENESS_BONUS = 4.0


def _classify_route(message_slots: dict[str, list[str]]) -> str:
    """Buying discloses a concrete constraint on the opening turn; Browsing
    starts vague (docs/competition_specification.md). Category/department
    describe the item itself, not a preference, so they don't count."""
    if any(slot not in DURABLE_SLOTS for slot in message_slots):
        return "buying"
    return "browsing"


def _load_gazetteer(path: str | Path) -> dict[str, dict[str, int]]:
    """Load the mined slot vocabularies, degrading to lexical-only behaviour.

    The scored path must never fail because a derived asset is absent, so a
    missing or unreadable file yields an empty gazetteer and the agent keeps
    working exactly as it did before slots existed.
    """
    try:
        with Path(path).open(encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {
        str(slot): {str(term): int(count) for term, count in terms.items()}
        for slot, terms in loaded.items()
        if isinstance(terms, dict)
    }


class Agent:
    """Offline multi-turn retrieval agent with no LLM dependency."""

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
        clarification_policy: str = "candidate",
        gazetteer_path: str | Path = "data/gazetteer.json",
        popularity_weight: float = POPULARITY_WEIGHT,
        retrieval_mode: str = "bm25",
        semantic_weight: float = SEMANTIC_WEIGHT,
    ) -> None:
        self.catalog_path = Path(catalog_path)
        self.clarification_policy = clarification_policy
        self.popularity_weight = popularity_weight
        self.retrieval_mode = retrieval_mode
        self.semantic_weight = semantic_weight
        self.gazetteer = _load_gazetteer(gazetteer_path)
        self.connection = sqlite3.connect(":memory:")
        self._session_terms: dict[str, list[str]] = {}
        self._session_profiles: dict[str, dict] = {}
        self._session_asked_attributes: dict[str, set[str]] = {}
        self._session_slots: dict[str, dict[str, dict[str, int]]] = {}
        self._session_route: dict[str, str] = {}
        self._build_index()

    def _build_index(self) -> None:
        # Needed either as a retrieval route (E16/E17) or purely to score
        # candidates that BM25 already retrieved (semantic reranking).
        self._needs_dense_index = self.retrieval_mode in ("dense", "rrf") or self.semantic_weight != 0.0
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        cursor.execute(
            "CREATE VIRTUAL TABLE product_vocab USING fts5vocab(products, 'row')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        self._popularity: dict[str, float] = {}
        self._products: dict[str, dict] = {}
        dense_asins: list[str] = []
        dense_texts: list[str] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                parent_asin = str(product["parent_asin"])
                try:
                    self._popularity[parent_asin] = float(product.get("rating_number") or 0.0)
                except (TypeError, ValueError):
                    self._popularity[parent_asin] = 0.0
                fields = (
                    _text(product.get("title")),
                    _text(product.get("categories")),
                    _text(product.get("features")),
                    _text(product.get("details")),
                    _text(product.get("store")),
                    _text(product.get("description")),
                )
                batch.append((parent_asin, *fields))
                self._products[parent_asin] = {
                    "parent_asin": parent_asin,
                    "title": fields[0],
                    "categories": fields[1],
                    "features": fields[2],
                    "details": fields[3],
                    "store": fields[4],
                    "description": fields[5],
                    "rating_number": self._popularity[parent_asin],
                }
                if self._needs_dense_index:
                    dense_asins.append(parent_asin)
                    dense_texts.append(" ".join(fields))
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()
        self.document_count = self.connection.execute(
            "SELECT count(*) FROM products"
        ).fetchone()[0]
        self.dense_index = DenseIndex(dense_asins, dense_texts) if self._needs_dense_index else None

    def _catalog_idf(self, terms: list[str]) -> dict[str, float]:
        """Weight each query term by how rare it is across the whole catalog.

        Document frequency comes from the FTS5 vocabulary table, so it is the
        real catalog-wide count and costs no extra pass over the data. It must
        not be derived from the retrieved candidates: those are the documents
        the query already matched, so its most important term would look
        ubiquitous there and be penalised.
        """
        if not terms:
            return {}
        placeholders = ", ".join("?" for _ in terms)
        rows = self.connection.execute(
            f"SELECT term, doc FROM product_vocab WHERE term IN ({placeholders})",
            terms,
        ).fetchall()
        frequencies = {str(term): int(doc) for term, doc in rows}
        total = self.document_count or 1
        return {
            term: math.log(1.0 + total / (1.0 + frequencies.get(term, 0)))
            for term in terms
        }

    def reset(self, session_id: str, user_profile: dict) -> None:
        # The profile is anonymized and may be used for personalization.
        self._session_terms[session_id] = []
        self._session_profiles[session_id] = user_profile
        self._session_asked_attributes[session_id] = set()
        self._session_slots[session_id] = {}
        self._session_route.pop(session_id, None)

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
        message_slots = extract_slots(user_message, self.gazetteer)
        accumulated_slots = self._session_slots.get(session_id, {})
        if session_id not in self._session_route:
            self._session_route[session_id] = _classify_route(message_slots)
        if _is_intent_override(user_message):
            # "Ignore my earlier preference" revokes what the customer
            # volunteered on the opening turn. It does not revoke the answers
            # they gave when the agent asked, and it does not revoke the item
            # they are shopping for. Slots this message replaces are dropped.
            accumulated_slots = {
                slot: {
                    term: arrived
                    for term, arrived in terms.items()
                    if slot in DURABLE_SLOTS or arrived > OPENING_TURN
                }
                for slot, terms in accumulated_slots.items()
                if slot not in message_slots
            }
            accumulated_slots = {
                slot: terms for slot, terms in accumulated_slots.items() if terms
            }
            previous_terms = [
                token
                for terms in accumulated_slots.values()
                for term in terms
                for token in _terms(term)
            ]
        else:
            previous_terms = self._session_terms[session_id]
        for slot, terms in message_slots.items():
            retained = accumulated_slots.setdefault(slot, {})
            for term in terms:
                retained.setdefault(term, turn)
        self._session_slots[session_id] = accumulated_slots
        unique_terms = list(dict.fromkeys([*previous_terms, *current_terms]))[:40]
        self._session_terms[session_id] = unique_terms
        required_terms: set[str] = set()
        if self._session_route[session_id] == "buying":
            # Read off the same slot memory the override logic already
            # maintains; intersect with this turn's actual query terms so a
            # normalization difference (e.g. gazetteer singularization) can
            # never ask the reranker to require a term that isn't there.
            slot_terms = {
                token
                for slot, terms in accumulated_slots.items()
                if slot not in DURABLE_SLOTS
                for term in terms
                for token in _terms(term)
            }
            required_terms = slot_terms & set(unique_terms)
        expression = " OR ".join(f'"{term}"' for term in unique_terms)
        query_text = " ".join(unique_terms)
        if self.retrieval_mode == "dense":
            # Isolated comparison only: replaces BM25 candidates entirely so
            # dense retrieval's own recall can be measured on its own,
            # before any fusion with BM25 (see reports/experiments/dense-retrieval.md).
            pool_size = max(top_k, CANDIDATE_POOL_SIZE)
            dense_hits = self.dense_index.search(query_text, pool_size) if self.dense_index else []
            candidates = [self._products[asin] for asin in dense_hits if asin in self._products]
        elif not expression:
            candidates = []
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
                    "rating_number": self._popularity.get(row[0], 0.0),
                }
                for row in rows
            ]
        if not candidates:
            recommendations: list[dict] = []
        else:
            semantic_scores: dict[str, float] = {}
            if self.semantic_weight != 0.0 and self.dense_index is not None:
                query_vector = self.dense_index.project(query_text)
                if query_vector is not None:
                    for candidate in candidates:
                        asin = str(candidate["parent_asin"])
                        doc_vector = self.dense_index.vector_for(asin)
                        if doc_vector is not None:
                            semantic_scores[asin] = float(query_vector @ doc_vector)
            recommendations = [
                {"parent_asin": parent_asin}
                for parent_asin in rerank_candidates(
                    unique_terms,
                    candidates,
                    top_k,
                    popularity_weight=self.popularity_weight,
                    required_terms=required_terms,
                    completeness_bonus=COMPLETENESS_BONUS,
                    semantic_scores=semantic_scores,
                    semantic_weight=self.semantic_weight,
                )
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
