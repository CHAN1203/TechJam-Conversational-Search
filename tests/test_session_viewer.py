from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate
from frontend.server.recorder import RecordingAgent
from frontend.server.transcript import SessionRunner, derive_disclosed
from starter.agent import Agent


PRODUCTS = [
    {
        "parent_asin": "SHIRT",
        "title": "Blue cotton shirt",
        "categories": ["Clothing", "Shirts"],
        "features": ["cotton", "breathable"],
        "details": {"department": "womens"},
        "store": "Example",
        "description": ["a light shirt"],
        "price": 25.0,
    },
    {
        "parent_asin": "JACKET",
        "title": "Black nylon jacket",
        "categories": ["Clothing", "Jackets"],
        "features": ["nylon", "waterproof"],
        "details": {"department": "mens"},
        "store": "Example",
        "description": ["a rain jacket"],
        "price": 80.0,
    },
]
GAZETTEER = {
    "category": {"shirt": 4, "jacket": 3},
    "material": {"cotton": 5, "nylon": 4},
    "color": {"blue": 3, "black": 2},
}
SAMPLES = [
    {
        "sample_id": "public_0001",
        "scenario_type": "buying",
        "category_bucket": "clothing",
        "difficulty_bucket": "easy",
        "ground_truth": {"parent_asin": "SHIRT"},
        "user_profile": {"preference_tags": ["material"], "summary": "likes cotton"},
    },
    {
        "sample_id": "public_0002",
        "scenario_type": "intent_override",
        "category_bucket": "clothing",
        "difficulty_bucket": "hard",
        "ground_truth": {"parent_asin": "JACKET"},
        "user_profile": {"preference_tags": ["style"], "summary": "critical"},
    },
]


def write_fixture(directory: str) -> tuple[Path, Path, Path]:
    root = Path(directory)
    catalog_path = root / "catalog.jsonl"
    dataset_path = root / "public_set.jsonl"
    gazetteer_path = root / "gazetteer.json"
    catalog_path.write_text(
        "".join(json.dumps(product) + "\n" for product in PRODUCTS), encoding="utf-8"
    )
    dataset_path.write_text(
        "".join(json.dumps(sample) + "\n" for sample in SAMPLES), encoding="utf-8"
    )
    gazetteer_path.write_text(json.dumps(GAZETTEER), encoding="utf-8")
    return catalog_path, dataset_path, gazetteer_path


class MutatingStubAgent:
    """Mutates its per-session slot state in place, exactly as Agent does."""

    def __init__(self) -> None:
        self._session_slots: dict[str, dict[str, dict[str, int]]] = {}
        self._session_terms: dict[str, list[str]] = {}
        self._session_asked_attributes: dict[str, set[str]] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._session_slots[session_id] = {}
        self._session_terms[session_id] = []
        self._session_asked_attributes[session_id] = set()

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        self._session_slots[session_id].setdefault("material", {})[f"term{turn}"] = turn
        self._session_terms[session_id].append(f"term{turn}")
        return {
            "message": "ok",
            "ask_attribute": "material",
            "recommendations": [{"parent_asin": "SHIRT"}],
        }


class RaisingStubAgent:
    def reset(self, session_id: str, user_profile: dict) -> None:
        pass

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        raise RuntimeError("agent exploded")


class RecordingAgentTest(unittest.TestCase):
    def test_recording_does_not_change_evaluator_metrics(self) -> None:
        """The load-bearing test: observing a session must not alter it."""
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, _, gazetteer_path = write_fixture(directory)
            catalog_ids, categories, products = catalog_index(catalog_path)
            agent = Agent(catalog_path, gazetteer_path=gazetteer_path)

            plain = evaluate(agent, SAMPLES, catalog_ids, categories, products)
            recorded = [
                evaluate(
                    RecordingAgent(agent, products, catalog_ids, sample["ground_truth"]["parent_asin"]),
                    [sample],
                    catalog_ids,
                    categories,
                    products,
                )["sessions"][0]
                for sample in SAMPLES
            ]

        self.assertEqual(plain["sessions"], recorded)

    def test_recorded_turn_count_matches_first_hit_turn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, _, gazetteer_path = write_fixture(directory)
            catalog_ids, categories, products = catalog_index(catalog_path)
            agent = Agent(catalog_path, gazetteer_path=gazetteer_path)
            sample = SAMPLES[0]
            recorder = RecordingAgent(agent, products, catalog_ids, "SHIRT")

            session = evaluate(recorder, [sample], catalog_ids, categories, products)["sessions"][0]

        self.assertTrue(session["hit"])
        self.assertEqual(session["first_hit_turn"], len(recorder.turns))
        self.assertEqual(session["best_rank"], recorder.turns[-1]["target_rank"])

    def test_slot_snapshots_are_independent_across_turns(self) -> None:
        recorder = RecordingAgent(MutatingStubAgent(), {}, {"SHIRT"}, "SHIRT")
        recorder.reset("s1", {})
        recorder.respond("s1", "first", 1, 10)
        recorder.respond("s1", "second", 2, 10)

        self.assertEqual({"term1": 1}, recorder.turns[0]["slots"]["material"])
        self.assertEqual({"term1": 1, "term2": 2}, recorder.turns[1]["slots"]["material"])
        self.assertEqual(["term1"], recorder.turns[0]["query_terms"])

    def test_agent_error_is_recorded_and_reraised(self) -> None:
        recorder = RecordingAgent(RaisingStubAgent(), {}, {"SHIRT"}, "SHIRT")
        recorder.reset("s1", {})

        with self.assertRaises(RuntimeError):
            recorder.respond("s1", "hello", 1, 10)

        self.assertEqual(1, len(recorder.turns))
        self.assertIn("agent exploded", recorder.turns[0]["error"])
        self.assertEqual([], recorder.turns[0]["recommendations"])


class DerivedDisclosureTest(unittest.TestCase):
    def test_constraint_counts_as_disclosed_once_it_appears_in_a_message(self) -> None:
        card = {"hard_constraints": ["cotton"], "soft_preferences": ["blue"]}
        turns = [
            {"user_message": "I'm looking for shirts. A key requirement is: cotton."},
            {"user_message": "I don't have an additional preference for size."},
            {"user_message": "For that, what matters is: blue."},
        ]

        disclosed = derive_disclosed(card, turns)

        self.assertEqual([["cotton"], ["cotton"], ["cotton", "blue"]], disclosed)


class SessionRunnerTest(unittest.TestCase):
    def test_rejects_sample_numbers_outside_the_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, gazetteer_path = write_fixture(directory)
            runner = SessionRunner(catalog_path, dataset_path, gazetteer_path)

            for number in (0, 3, -1, "2"):
                with self.assertRaises(ValueError):
                    runner.run(number)

    def test_run_returns_turns_metrics_and_hidden_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, gazetteer_path = write_fixture(directory)
            runner = SessionRunner(catalog_path, dataset_path, gazetteer_path)

            transcript = runner.run(1)

        self.assertEqual("public_0001", transcript["sample"]["sample_id"])
        self.assertEqual(1, transcript["sample"]["index"])
        self.assertEqual("buying", transcript["sample"]["scenario_type"])
        self.assertTrue(transcript["turns"])
        self.assertEqual(1, transcript["turns"][0]["turn"])
        self.assertIn("disclosed", transcript["turns"][0])
        self.assertEqual("SHIRT", transcript["hidden"]["target"]["parent_asin"])
        self.assertEqual("Blue cotton shirt", transcript["hidden"]["target"]["title"])
        self.assertIn("hard_constraints", transcript["hidden"]["intent_card"])
        self.assertIn("hit", transcript["metrics"])

    def test_run_does_not_leak_session_state_into_the_shared_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, gazetteer_path = write_fixture(directory)
            runner = SessionRunner(catalog_path, dataset_path, gazetteer_path)

            runner.run(1)
            runner.run(2)

        self.assertEqual({}, runner.agent._session_slots)
        self.assertEqual({}, runner.agent._session_terms)

    def test_sample_index_lists_every_sample(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog_path, dataset_path, gazetteer_path = write_fixture(directory)
            runner = SessionRunner(catalog_path, dataset_path, gazetteer_path)

            listing = runner.listing()

        self.assertEqual(2, runner.sample_count)
        self.assertEqual([1, 2], [item["index"] for item in listing])
        self.assertEqual("intent_override", listing[1]["scenario_type"])


if __name__ == "__main__":
    unittest.main()
