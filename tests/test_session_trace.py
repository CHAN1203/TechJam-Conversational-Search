from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.session_trace import (
    DURABLE_SLOT,
    LEARNED_AFTER_OPENING,
    REPLACED_BY_MESSAGE,
    VOLUNTEERED_ON_OPENING,
    TurnTrace,
    is_dead_turn,
    lost_terms,
    override_disposition,
    summarize,
)
from evaluator.local_evaluator import catalog_index
from scripts.trace_session import trace_session
from starter.agent import Agent


class OverrideDispositionTest(unittest.TestCase):
    def _reasons(self, dispositions) -> dict[str, tuple[bool, str]]:
        return {
            f"{item.slot}.{item.term}": (item.kept, item.reason)
            for item in dispositions
        }

    def test_each_override_rule_is_reported_separately(self) -> None:
        accumulated = {
            "category": {"belt": 1},
            "material": {"leather": 1},
            "color": {"black": 1},
            "style": {"casual": 3},
        }

        reasons = self._reasons(
            override_disposition(accumulated, {"material": ["suede"]})
        )

        self.assertEqual((True, DURABLE_SLOT), reasons["category.belt"])
        self.assertEqual((False, REPLACED_BY_MESSAGE), reasons["material.leather"])
        self.assertEqual((False, VOLUNTEERED_ON_OPENING), reasons["color.black"])
        self.assertEqual((True, LEARNED_AFTER_OPENING), reasons["style.casual"])

    def test_a_named_slot_loses_even_its_durable_terms(self) -> None:
        # The customer replaced the thing they are shopping for, so durability
        # must not outrank an explicit replacement in the same message.
        reasons = self._reasons(
            override_disposition({"category": {"belt": 1}}, {"category": ["wallet"]})
        )

        self.assertEqual((False, REPLACED_BY_MESSAGE), reasons["category.belt"])

    def test_no_accumulated_state_yields_no_dispositions(self) -> None:
        self.assertEqual([], override_disposition({}, {"material": ["leather"]}))


class LostTermsTest(unittest.TestCase):
    def test_monotonic_accumulation_loses_nothing(self) -> None:
        self.assertEqual([], lost_terms(["belts", "buckle"], ["belts", "buckle", "leather"]))

    def test_override_rebuild_reports_dropped_surface_forms(self) -> None:
        # "belts" is replaced by the gazetteer's normalized "belt", which FTS5
        # treats as a different token because it does not stem.
        self.assertEqual(
            ["belts", "closure"],
            lost_terms(["belts", "buckle", "closure"], ["belt", "buckle", "leather"]),
        )


class DeadTurnTest(unittest.TestCase):
    def test_first_turn_is_never_dead(self) -> None:
        self.assertFalse(is_dead_turn(None, ["shoes"], None))

    def test_unchanged_terms_without_a_hit_are_dead(self) -> None:
        self.assertTrue(is_dead_turn(["shoes"], ["shoes"], None))

    def test_unchanged_terms_are_not_dead_when_the_target_is_ranked(self) -> None:
        self.assertFalse(is_dead_turn(["shoes"], ["shoes"], 4))

    def test_changed_terms_are_not_dead(self) -> None:
        self.assertFalse(is_dead_turn(["shoes"], ["shoes", "leather"], None))


class SummarizeTest(unittest.TestCase):
    def _turn(self, turn: int, **overrides) -> TurnTrace:
        defaults = dict(
            turn=turn, user_message="", is_override=False, constraint_terms=[],
            message_slots={}, slots_after={}, terms_after=[], terms_lost=[],
        )
        defaults.update(overrides)
        return TurnTrace(**defaults)

    def test_reports_the_rank_on_each_side_of_the_override(self) -> None:
        turns = [
            self._turn(1, target_rank=None),
            self._turn(2, target_rank=6),
            self._turn(3, is_override=True, target_rank=None, terms_lost=["tees", "blouses"]),
        ]

        summary = summarize(turns)

        self.assertEqual(3, summary["override_turn"])
        self.assertEqual(6, summary["rank_before_override"])
        self.assertIsNone(summary["rank_after_override"])
        self.assertEqual(["tees", "blouses"], summary["terms_lost_at_override"])
        self.assertEqual(6, summary["best_rank"])

    def test_a_session_without_an_override_reports_no_override_turn(self) -> None:
        summary = summarize([self._turn(1, target_rank=2), self._turn(2, dead=True)])

        self.assertIsNone(summary["override_turn"])
        self.assertIsNone(summary["rank_before_override"])
        self.assertEqual(1, summary["dead_turns"])


class TraceSessionIntegrationTest(unittest.TestCase):
    """Drive the real Agent and evaluator loop over a two-product catalog."""

    def _fixture(self, directory: str) -> tuple[Path, Path]:
        catalog = Path(directory) / "catalog.jsonl"
        catalog.write_text(
            "".join(
                json.dumps(row) + "\n"
                for row in (
                    {
                        "parent_asin": "A", "title": "leather belt",
                        "categories": ["Accessories", "Belts"],
                        "features": ["buckle closure"], "details": {"material": "leather"},
                        "store": "Example", "description": "", "rating_number": 1000,
                    },
                    {
                        "parent_asin": "B", "title": "canvas belt",
                        "categories": ["Accessories", "Belts"],
                        "features": ["clip closure"], "details": {"material": "canvas"},
                        "store": "Example", "description": "", "rating_number": 5,
                    },
                )
            ),
            encoding="utf-8",
        )
        gazetteer = Path(directory) / "gazetteer.json"
        gazetteer.write_text(
            json.dumps({"category": {"belt": 2}, "material": {"leather": 1, "canvas": 1}}),
            encoding="utf-8",
        )
        return catalog, gazetteer

    def _sample(self) -> dict:
        return {
            "sample_id": "trace_0001",
            "scenario_type": "intent_override",
            "difficulty_bucket": "easy",
            "user_profile": {"preference_tags": ["material"]},
            "ground_truth": {"parent_asin": "A"},
            "intent_card": {
                "target_category": "leather belt",
                "hard_constraints": ["leather"],
                "soft_preferences": ["Buckle closure"],
            },
            "behavior": {
                "scenario_type": "intent_override",
                "override": {
                    "turn": 3,
                    "old_value": "Buckle closure",
                    "new_value": "leather",
                    "message": "Actually, ignore my earlier preference. What I need is: leather.",
                },
            },
        }

    def test_trace_marks_the_override_turn_and_matches_the_evaluator_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog, gazetteer = self._fixture(directory)
            catalog_ids, categories, products = catalog_index(catalog)
            agent = Agent(catalog, gazetteer_path=gazetteer)

            trace = trace_session(agent, self._sample(), catalog_ids, categories, products)

            override_turns = [row for row in trace["turns"] if row["is_override"]]
            self.assertEqual(1, len(override_turns))
            self.assertEqual(3, override_turns[0]["turn"])
            self.assertEqual(3, trace["summary"]["override_turn"])
            # A hit before the override turn does not count, so no session can
            # report a first_hit_turn earlier than the override.
            if trace["first_hit_turn"] is not None:
                self.assertGreaterEqual(trace["first_hit_turn"], 3)

    def test_every_turn_records_both_state_representations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog, gazetteer = self._fixture(directory)
            catalog_ids, categories, products = catalog_index(catalog)
            agent = Agent(catalog, gazetteer_path=gazetteer)

            trace = trace_session(agent, self._sample(), catalog_ids, categories, products)

            self.assertTrue(trace["turns"])
            for row in trace["turns"]:
                self.assertIn("terms_after", row)
                self.assertIn("slots_after", row)
                self.assertIn("terms_lost", row)
                self.assertIsInstance(row["dead"], bool)


if __name__ == "__main__":
    unittest.main()
