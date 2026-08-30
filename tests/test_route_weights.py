"""Tests for per-route reranking weights (E31, rejected).

The experiment is rejected -- see
`reports/experiments/route-conditional-weights.md` -- so these tests exist to
preserve the implementation for review, and to pin the one property that would
matter if it were ever retained: with no per-route weight configured, the agent
must behave exactly as it did before the parameter existed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starter.agent import Agent, _classify_route


# OBSCURE is the better *field* match: the query term "shirts" lands in its
# title (weight 4.0) but only in POPULAR's description (weight 1.0). POPULAR
# wins anyway, because the popularity prior outweighs that 3.0 gap. Zeroing
# popularity is therefore the one change that can flip the pair, which is what
# makes the route-scoping assertion meaningful rather than vacuous.
CATALOG = [
    {
        "parent_asin": "POPULAR",
        "title": "Cotton garment",
        "categories": ["Clothing"],
        "features": ["cotton"],
        "details": {"department": "womens"},
        "store": "Example",
        "description": ["shirts for everyday wear"],
        "price": 25.0,
        "rating_number": 50000,
    },
    {
        "parent_asin": "OBSCURE",
        "title": "Shirts cotton",
        "categories": ["Clothing"],
        "features": ["cotton"],
        "details": {"department": "womens"},
        "store": "Example",
        "description": ["everyday wear"],
        "price": 25.0,
        "rating_number": 1,
    },
]
GAZETTEER = {
    "category": {"shirt": 4},
    "material": {"cotton": 5},
    "color": {"blue": 3},
}

# Opens with a concrete non-durable constraint -> Buying.
BUYING_OPENER = "I'm looking for shirts. A key requirement is: cotton."
# Opens with only the item type -> Browsing.
BROWSING_OPENER = "I'm looking for shirts, but I'm still exploring."


class RouteClassifierTest(unittest.TestCase):
    """`_classify_route` reads only the opening turn's slots."""

    def test_a_non_durable_slot_marks_the_session_as_buying(self) -> None:
        self.assertEqual("buying", _classify_route({"material": ["cotton"]}))

    def test_durable_slots_alone_mark_the_session_as_browsing(self) -> None:
        self.assertEqual(
            "browsing", _classify_route({"category": ["shirt"], "department": ["womens"]})
        )

    def test_no_slots_at_all_marks_the_session_as_browsing(self) -> None:
        self.assertEqual("browsing", _classify_route({}))


class RouteWeightTest(unittest.TestCase):
    """Per-route weights apply to their own route and nothing else."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.catalog_path = base / "catalog.jsonl"
        self.catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in CATALOG), encoding="utf-8"
        )
        self.gazetteer_path = base / "gazetteer.json"
        self.gazetteer_path.write_text(json.dumps(GAZETTEER), encoding="utf-8")

    def build(self, **kwargs) -> Agent:
        """Construct an agent over the fixture catalog with semantic scoring off.

        Args:
            **kwargs: Overrides forwarded to `Agent`.

        Returns:
            An agent whose ranking depends only on the weights under test.
        """
        options = {
            "gazetteer_path": self.gazetteer_path,
            # Semantic and phrase scoring off so the popularity prior and the
            # field weights are the only things ordering the pair.
            "semantic_weight": 0.0,
            "phrase_weight": 0.0,
            "retrieval_mode": "bm25",
        }
        options.update(kwargs)
        return Agent(self.catalog_path, **options)

    def first_recommendation(self, agent: Agent, opener: str) -> str:
        agent.reset("session", {})
        response = agent.respond("session", opener, 1, 2)
        return response["recommendations"][0]["parent_asin"]

    def test_unset_route_weights_leave_ranking_unchanged(self) -> None:
        """The regression guard: the default must be the pre-E31 behaviour."""
        default = self.build()
        explicit_empty = self.build(
            route_semantic_weights={}, route_popularity_weights={}
        )
        for opener in (BUYING_OPENER, BROWSING_OPENER):
            with self.subTest(opener=opener):
                self.assertEqual(
                    self.first_recommendation(default, opener),
                    self.first_recommendation(explicit_empty, opener),
                )

    def test_a_route_weight_changes_only_its_own_route(self) -> None:
        """Zeroing popularity on Browsing must not disturb Buying.

        The two catalog rows are identical apart from `rating_number`, so the
        popularity prior is the only thing that can order them.
        """
        baseline = self.build()
        self.assertEqual("POPULAR", self.first_recommendation(baseline, BROWSING_OPENER))

        routed = self.build(route_popularity_weights={"browsing": 0.0})
        self.assertNotEqual(
            self.first_recommendation(baseline, BROWSING_OPENER),
            self.first_recommendation(routed, BROWSING_OPENER),
        )
        self.assertEqual(
            self.first_recommendation(baseline, BUYING_OPENER),
            self.first_recommendation(routed, BUYING_OPENER),
        )

    def test_route_is_frozen_at_the_opening_turn(self) -> None:
        """A constraint disclosed on turn 2 must not reclassify the session."""
        agent = self.build()
        agent.reset("session", {})
        agent.respond("session", BROWSING_OPENER, 1, 2)
        agent.respond("session", "For that, what matters is: cotton.", 2, 2)
        self.assertEqual("browsing", agent._session_route["session"])

    def test_a_route_only_semantic_weight_still_builds_the_dense_index(self) -> None:
        """`_needs_dense_index` must consult the per-route weights, not just the global one."""
        agent = self.build(semantic_weight=0.0, route_semantic_weights={"buying": 1.0})
        self.assertTrue(agent._needs_dense_index)
        self.assertIsNotNone(agent.dense_index)


if __name__ == "__main__":
    unittest.main()
