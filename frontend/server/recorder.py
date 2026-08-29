from __future__ import annotations

import copy
import sqlite3
from collections.abc import Mapping, Sequence

from evaluator.local_evaluator import normalize_recommendations


def snapshot_agent_state(agent: object, session_id: str) -> dict:
    """Read the agent's per-session state for display.

    These attributes are private. The viewer reads them because they hold the
    state that explains a session, and exposing them on `Agent` would add
    scoring-path code that only a development tool needs. Every lookup degrades
    to empty rather than raising, so refactoring `Agent` blanks the panel
    instead of breaking the viewer.
    """
    slots = getattr(agent, "_session_slots", {}).get(session_id, {})
    terms = getattr(agent, "_session_terms", {}).get(session_id, [])
    asked = getattr(agent, "_session_asked_attributes", {}).get(session_id, set())
    return {
        # The agent mutates this dict in place across turns, so a reference here
        # would show the final state at every step of the replay.
        "slots": copy.deepcopy(slots),
        "query_terms": list(terms),
        "asked_attributes": sorted(asked),
    }


def fts_match_count(agent: object, query_terms: Sequence[str]) -> int | None:
    """Count catalog rows matching the agent's current query.

    The agent does not keep the expression it searched with -- it is a local in
    `respond` -- so this rebuilds it from the recorded terms using the same
    join. Display only: if the two ever drift, the count is wrong and nothing
    else is affected.
    """
    if not query_terms:
        return 0
    connection = getattr(agent, "connection", None)
    if connection is None:
        return None
    expression = " OR ".join(f'"{term}"' for term in query_terms)
    try:
        row = connection.execute(
            "SELECT count(*) FROM products WHERE products MATCH ?", (expression,)
        ).fetchone()
    except sqlite3.Error:
        return None
    return int(row[0])


class RecordingAgent:
    """Transparent proxy that records every turn the evaluator drives.

    The official `evaluate()` calls only `reset` and `respond`, so wrapping the
    agent lets the unmodified evaluator produce the transcript. The turns that
    come out are the turns a scoring run produces -- there is no reimplemented
    loop that can drift from the evaluator.
    """

    def __init__(
        self,
        agent: object,
        products: Mapping[str, Mapping],
        catalog_ids: set[str],
        target: str,
    ) -> None:
        self.agent = agent
        self.turns: list[dict] = []
        self.session_id: str | None = None
        self._products = products
        self._catalog_ids = catalog_ids
        self._target = str(target)

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.session_id = session_id
        self.turns = []
        self.agent.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        try:
            response = self.agent.respond(session_id, user_message, turn, top_k)
        except Exception as error:
            # Record the failure, then let the evaluator's own handler take it.
            # A crashed turn stays visible instead of looking like an empty one.
            self.turns.append(self._record(session_id, user_message, turn, None, error))
            raise
        self.turns.append(self._record(session_id, user_message, turn, response, None))
        return response

    def _record(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        response: object,
        error: Exception | None,
    ) -> dict:
        payload = response.get("recommendations") if isinstance(response, dict) else None
        ranked = normalize_recommendations(payload, self._catalog_ids)
        state = snapshot_agent_state(self.agent, session_id)
        return {
            "turn": turn,
            "user_message": user_message,
            "agent_message": response.get("message") if isinstance(response, dict) else "",
            "ask_attribute": response.get("ask_attribute") if isinstance(response, dict) else None,
            "recommendations": [
                {
                    "rank": rank,
                    "parent_asin": parent_asin,
                    "title": str(self._products.get(parent_asin, {}).get("title") or ""),
                    "is_target": parent_asin == self._target,
                }
                for rank, parent_asin in enumerate(ranked, 1)
            ],
            "target_rank": ranked.index(self._target) + 1 if self._target in ranked else None,
            "fts_match_count": fts_match_count(self.agent, state["query_terms"]),
            "error": f"{type(error).__name__}: {error}" if error is not None else None,
            **state,
        }
