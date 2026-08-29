from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from evaluator.local_evaluator import (
    catalog_index,
    coarse_category,
    evaluate,
    load_jsonl,
    materialize_hidden_fields,
)
from frontend.server.recorder import RecordingAgent
from starter.agent import CANDIDATE_POOL_SIZE, Agent


DEFAULT_CATALOG = "data/catalog.jsonl"
DEFAULT_DATASET = "data/public_set.jsonl"
DEFAULT_GAZETTEER = "data/gazetteer.json"
SESSION_STATE_ATTRIBUTES = (
    "_session_terms",
    "_session_profiles",
    "_session_asked_attributes",
    "_session_slots",
)


def derive_disclosed(card: Mapping[str, object], turns: Sequence[Mapping]) -> list[list[str]]:
    """Reconstruct, per turn, which intent-card constraints the customer has revealed.

    The evaluator's `disclosed` set is a local inside `evaluate()` and cannot be
    read from outside. But `initial_message` and `customer_reply` emit
    constraint strings verbatim into the message text, so a constraint counts as
    disclosed at turn N once it appears in a message up to and including N.

    This is a reconstruction, not an observation, and the UI labels it as such.
    """
    constraints = [
        str(value)
        for value in [
            *(card.get("hard_constraints") or []),
            *(card.get("soft_preferences") or []),
        ]
    ]
    seen = ""
    per_turn: list[list[str]] = []
    for turn in turns:
        seen = f"{seen} {turn.get('user_message', '')}"
        per_turn.append([value for value in constraints if value in seen])
    return per_turn


def target_summary(product: Mapping[str, object]) -> dict:
    return {
        "parent_asin": str(product.get("parent_asin") or ""),
        "title": str(product.get("title") or ""),
        "store": str(product.get("store") or ""),
        "price": product.get("price"),
        "categories": [str(value) for value in product.get("categories") or []],
        "features": [str(value) for value in product.get("features") or []],
        "details": {
            str(key): str(value) for key, value in (product.get("details") or {}).items()
        },
    }


class SessionRunner:
    """Runs one public-set sample and returns everything needed to replay it.

    The agent and the catalog index are built once. Indexing 50,000 products
    takes about five seconds; a session after that costs milliseconds.
    """

    def __init__(
        self,
        catalog_path: str | Path = DEFAULT_CATALOG,
        dataset_path: str | Path = DEFAULT_DATASET,
        gazetteer_path: str | Path = DEFAULT_GAZETTEER,
    ) -> None:
        self.samples = load_jsonl(dataset_path)
        self.catalog_ids, self.categories, self.products = catalog_index(catalog_path)
        # No overrides: the viewer runs whatever the current best defaults are.
        self.agent = Agent(catalog_path, gazetteer_path=gazetteer_path)

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    def agent_config(self) -> dict:
        return {
            "clarification_policy": self.agent.clarification_policy,
            "candidate_pool_size": CANDIDATE_POOL_SIZE,
            "gazetteer_slots": sorted(self.agent.gazetteer),
            "catalog_size": len(self.catalog_ids),
        }

    def listing(self) -> list[dict]:
        return [
            {
                "index": index,
                "sample_id": str(sample.get("sample_id") or ""),
                "scenario_type": str(sample.get("scenario_type") or ""),
                "difficulty_bucket": str(sample.get("difficulty_bucket") or ""),
            }
            for index, sample in enumerate(self.samples, 1)
        ]

    def run(self, number: object) -> dict:
        sample = self.samples[self._checked_index(number) - 1]
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, self.products)
        recorder = RecordingAgent(self.agent, self.products, self.catalog_ids, target)

        # The unmodified official evaluator drives the proxy, so these are the
        # turns a scoring run produces.
        result = evaluate(recorder, [sample], self.catalog_ids, self.categories, self.products)

        turns = recorder.turns
        for turn, disclosed in zip(turns, derive_disclosed(card, turns)):
            turn["disclosed"] = disclosed
        self._forget(recorder.session_id)

        return {
            "sample": {
                "index": int(number),
                "sample_id": str(sample.get("sample_id") or ""),
                "scenario_type": str(sample.get("scenario_type") or ""),
                "difficulty_bucket": str(sample.get("difficulty_bucket") or ""),
                "category_bucket": str(sample.get("category_bucket") or ""),
                "user_profile": sample.get("user_profile") or {},
            },
            "metrics": result["sessions"][0],
            "turns": turns,
            "hidden": {
                "target": target_summary(self.products.get(target, {"parent_asin": target})),
                "intent_card": card,
                "behavior": behavior,
                "coarse_category": coarse_category(self.categories.get(target, [])),
            },
            "agent": self.agent_config(),
        }

    def _checked_index(self, number: object) -> int:
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError(f"sample must be an integer, got {number!r}")
        if not 1 <= number <= self.sample_count:
            raise ValueError(f"sample must be between 1 and {self.sample_count}, got {number}")
        return number

    def _forget(self, session_id: str | None) -> None:
        """Drop the finished session so a long-lived server does not accumulate state."""
        if session_id is None:
            return
        for attribute in SESSION_STATE_ATTRIBUTES:
            getattr(self.agent, attribute, {}).pop(session_id, None)
