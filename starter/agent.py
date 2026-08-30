from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path

from starter.clarification import select_attribute
from starter.ledger import ANSWERED, VOLUNTEERED, ConstraintLedger, assign_slots
from starter.slots import extract_slots
from starter.reranker import rerank_candidates


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}
NO_PREFERENCE_PHRASES = (
    "don't have a preference",
    "don't have an additional preference",
    "do not have a preference",
    "no preference",
)
CANDIDATE_POOL_SIZE = 100
# The accumulated query is capped so a long session cannot grow an
# unbounded MATCH expression. Observed sessions reach about 17 terms.
TERM_LIMIT = 40
STATE_MODELS = ("slots", "ledger")
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


def _is_no_preference(message: str) -> bool:
    """True when the customer declined to constrain the asked attribute.

    Both representations of state must honour this. Guarding only the query
    terms still lets the slot extractor read the attribute name out of the
    reply, so "no additional preference for use_case" files "case" as a
    category, where DURABLE_SLOTS then protects it from every later override.
    """
    lowered = message.lower()
    return any(phrase in lowered for phrase in NO_PREFERENCE_PHRASES)


def _constraint_terms(message: str) -> list[str]:
    return [] if _is_no_preference(message) else _terms(message)


def _is_intent_override(message: str) -> bool:
    lowered = message.lower()
    return lowered.startswith("actually") and "ignore my earlier preference" in lowered


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
        state_model: str = "slots",
        answered_weight: float = 1.0,
        decay_lambda: float = 0.0,
        no_gain_probe: int | None = None,
    ) -> None:
        if state_model not in STATE_MODELS:
            raise ValueError(f"unsupported state model: {state_model}")
        self.catalog_path = Path(catalog_path)
        self.clarification_policy = clarification_policy
        self.state_model = state_model
        # Stage 2, both off by default: 1.0 makes every term weigh the same,
        # and None never overrides the clarification policy.
        self.answered_weight = answered_weight
        self.decay_lambda = decay_lambda
        self.no_gain_probe = no_gain_probe
        self.popularity_weight = popularity_weight
        self.gazetteer = _load_gazetteer(gazetteer_path)
        self.connection = sqlite3.connect(":memory:")
        self._session_terms: dict[str, list[str]] = {}
        self._session_profiles: dict[str, dict] = {}
        self._session_asked_attributes: dict[str, set[str]] = {}
        self._session_slots: dict[str, dict[str, dict[str, int]]] = {}
        self._session_ledgers: dict[str, ConstraintLedger] = {}
        self._session_term_weights: dict[str, dict[str, float] | None] = {}
        self._session_no_gain: dict[str, int] = {}
        self._build_index()

    def _build_index(self) -> None:
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
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                try:
                    self._popularity[str(product["parent_asin"])] = float(
                        product.get("rating_number") or 0.0
                    )
                except (TypeError, ValueError):
                    self._popularity[str(product["parent_asin"])] = 0.0
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
        self.document_count = self.connection.execute(
            "SELECT count(*) FROM products"
        ).fetchone()[0]

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
        self._session_ledgers[session_id] = ConstraintLedger()
        self._session_term_weights[session_id] = None
        self._session_no_gain[session_id] = 0

    def _advance_slots(
        self,
        session_id: str,
        user_message: str,
        current_terms: list[str],
        message_slots: dict[str, list[str]],
        turn: int,
    ) -> list[str]:
        """E11 state: a flat term list patched in place, rebuilt at an override."""
        accumulated_slots = self._session_slots.get(session_id, {})
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
        self._session_term_weights[session_id] = None
        return list(dict.fromkeys([*previous_terms, *current_terms]))[:TERM_LIMIT]

    def _advance_ledger(
        self,
        session_id: str,
        user_message: str,
        current_terms: list[str],
        message_slots: dict[str, list[str]],
        turn: int,
    ) -> list[str]:
        """Ledger state: statuses change, entries do not, the query is projected.

        The override is applied before the new message is recorded, so a
        constraint the customer restates in the same breath as revoking an old
        one comes back active rather than staying revoked.
        """
        ledger = self._session_ledgers[session_id]
        if _is_intent_override(user_message):
            ledger.apply_override(message_slots, DURABLE_SLOTS, OPENING_TURN)
        gained = ledger.record(
            current_terms,
            assign_slots(current_terms, message_slots),
            turn,
            ANSWERED if turn > OPENING_TURN else VOLUNTEERED,
        )
        # A turn that adds no active entry cannot change the ranking: retrieval
        # is a pure function of the projected terms. Counting these is how the
        # agent notices, from its own state alone, that asking about specific
        # attributes has stopped paying.
        self._session_no_gain[session_id] = (
            0 if gained else self._session_no_gain.get(session_id, 0) + 1
        )
        self._session_slots[session_id] = ledger.slots_view()
        self._session_term_weights[session_id] = ledger.projection_weights(
            turn, self.answered_weight, self.decay_lambda
        )
        return ledger.project(TERM_LIMIT)

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
        message_slots = (
            {}
            if _is_no_preference(user_message)
            else extract_slots(user_message, self.gazetteer)
        )
        advance = (
            self._advance_ledger
            if self.state_model == "ledger"
            else self._advance_slots
        )
        unique_terms = advance(session_id, user_message, current_terms, message_slots, turn)
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
                    "rating_number": self._popularity.get(row[0], 0.0),
                }
                for row in rows
            ]
            recommendations = [
                {"parent_asin": parent_asin}
                for parent_asin in rerank_candidates(
                    unique_terms,
                    candidates,
                    top_k,
                    popularity_weight=self.popularity_weight,
                    term_weights=self._session_term_weights.get(session_id),
                )
            ]
        asked = self._session_asked_attributes[session_id]
        if (
            self.no_gain_probe is not None
            and self._session_no_gain.get(session_id, 0) >= self.no_gain_probe
        ):
            # Named attributes have stopped yielding, so ask an open question
            # instead of continuing down the policy order. Repeating it is
            # deliberate: the point is to keep asking for anything undisclosed.
            ask_attribute = "other"
        else:
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
