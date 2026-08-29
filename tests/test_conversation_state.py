from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starter.agent import Agent


class ConversationStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def build_agent(
        self,
        products: list[dict],
        profile: dict | None = None,
        clarification_policy: str | None = None,
        gazetteer: dict | None = None,
    ) -> Agent:
        base = Path(self.temporary_directory.name)
        catalog_path = base / "catalog.jsonl"
        catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in products),
            encoding="utf-8",
        )
        gazetteer_path = base / "gazetteer.json"
        gazetteer_path.write_text(json.dumps(gazetteer or {}), encoding="utf-8")
        if clarification_policy is None:
            agent = Agent(catalog_path, gazetteer_path=gazetteer_path)
        else:
            agent = Agent(
                catalog_path,
                clarification_policy=clarification_policy,
                gazetteer_path=gazetteer_path,
            )
        agent.reset("session", profile or {})
        return agent

    def test_respond_accumulates_constraints_across_turns(self) -> None:
        agent = self.build_agent([
            {
                "parent_asin": "RED-COTTON",
                "title": "Red Shirt",
                "categories": ["Shirts"],
                "features": ["Cotton"],
                "details": {},
                "store": "Example",
                "description": [],
            },
            {
                "parent_asin": "COTTON-ONLY",
                "title": "Cotton Shirt",
                "categories": ["Shirts"],
                "features": ["Everyday wear"],
                "details": {},
                "store": "Example",
                "description": [],
            },
        ])

        agent.respond("session", "I want a red shirt", 1, 1)
        response = agent.respond(
            "session",
            "For that, what matters is: cotton.",
            2,
            1,
        )

        self.assertEqual(
            [{"parent_asin": "RED-COTTON"}],
            response["recommendations"],
        )

    def test_negative_preference_reply_does_not_pollute_constraints(self) -> None:
        agent = self.build_agent([
            {
                "parent_asin": "BLUE-SHIRT",
                "title": "Blue Shirt",
                "categories": ["Shirts"],
                "features": ["Everyday wear"],
                "details": {},
                "store": "Example",
                "description": [],
            },
            {
                "parent_asin": "NEGATIVE-WORDS",
                "title": "Material Preference Judgment",
                "categories": ["Accessories"],
                "features": ["Novelty item"],
                "details": {},
                "store": "Example",
                "description": [],
            },
        ])

        agent.respond("session", "I want a blue shirt", 1, 1)
        response = agent.respond(
            "session",
            "I don't have a preference for material; please use your judgment.",
            2,
            1,
        )

        self.assertEqual(
            [{"parent_asin": "BLUE-SHIRT"}],
            response["recommendations"],
        )

    def test_intent_override_drops_the_revoked_value_but_keeps_the_product_type(self) -> None:
        # An override replaces a preference, not the thing being shopped for.
        # Forgetting "shirt" as well would send the customer a jacket.
        agent = self.build_agent(
            [
                {
                    "parent_asin": "RED-SHIRT",
                    "title": "Red Shirt",
                    "categories": ["Shirts"],
                    "features": ["Everyday wear"],
                    "details": {}, "store": "Example", "description": [],
                },
                {
                    # Deliberately the weaker match on "blue" alone, so this
                    # test can only pass if "shirt" survives the override.
                    "parent_asin": "BLUE-SHIRT",
                    "title": "Classic Everyday Button Down Collared Shirt In Blue",
                    "categories": ["Shirts"],
                    "features": ["Everyday wear"],
                    "details": {}, "store": "Example", "description": [],
                },
                {
                    "parent_asin": "BLUE-JACKET",
                    "title": "Blue Jacket",
                    "categories": ["Jackets"],
                    "features": ["Everyday wear"],
                    "details": {}, "store": "Example", "description": [],
                },
            ],
            gazetteer={
                "category": {"shirt": 2, "jacket": 1},
                "color": {"red": 1, "blue": 2},
            },
        )

        agent.respond("session", "I want a red shirt", 1, 1)
        response = agent.respond(
            "session",
            "Actually, ignore my earlier preference. What I need is: blue.",
            2,
            1,
        )

        self.assertEqual(
            [{"parent_asin": "BLUE-SHIRT"}],
            response["recommendations"],
        )

    def test_ask_attribute_follows_profile_tags_without_repeating(self) -> None:
        agent = self.build_agent(
            [{
                "parent_asin": "SHIRT",
                "title": "Everyday Shirt",
                "categories": ["Shirts"],
                "features": ["Comfortable"],
                "details": {},
                "store": "Example",
                "description": [],
            }],
            profile={"preference_tags": ["material", "fit"]},
            clarification_policy="profile",
        )

        first = agent.respond("session", "I want a shirt", 1, 1)
        second = agent.respond(
            "session",
            "I don't have a preference for material.",
            2,
            1,
        )

        self.assertEqual("material", first["ask_attribute"])
        self.assertEqual("size", second["ask_attribute"])

    def test_agent_uses_selected_clarification_policy(self) -> None:
        agent = self.build_agent(
            [{
                "parent_asin": "SHIRT",
                "title": "Everyday Shirt",
                "categories": ["Shirts"],
                "features": ["Comfortable"],
                "details": {},
                "store": "Example",
                "description": [],
            }],
            profile={"preference_tags": ["style"]},
            clarification_policy="fixed",
        )

        response = agent.respond("session", "I want a shirt", 1, 1)

        self.assertEqual("material", response["ask_attribute"])

    def test_default_policy_uses_candidate_variation(self) -> None:
        agent = self.build_agent(
            [
                {
                    "parent_asin": "RED-SHIRT",
                    "title": "Red Cotton Shirt",
                    "categories": ["Shirts"],
                    "features": ["Cotton"],
                    "details": {},
                    "store": "Example",
                    "description": [],
                },
                {
                    "parent_asin": "BLUE-SHIRT",
                    "title": "Blue Cotton Shirt",
                    "categories": ["Shirts"],
                    "features": ["Cotton"],
                    "details": {},
                    "store": "Example",
                    "description": [],
                },
            ],
            profile={"preference_tags": ["style"]},
        )

        response = agent.respond("session", "I want a shirt", 1, 1)

        self.assertEqual("color", response["ask_attribute"])


if __name__ == "__main__":
    unittest.main()


class IntentOverrideMemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    CATALOG = [
        {
            "parent_asin": "SHOE-CANVAS",
            "title": "Running Shoe Built With Durable Canvas Upper Material",
            "categories": ["Shoes"],
            "features": ["Breathable everyday trainer"],
            "details": {}, "store": "Example", "description": [],
        },
        {
            "parent_asin": "SHOE-LEATHER",
            "title": "Running Shoe Built With Durable Leather Upper Material",
            "categories": ["Shoes"],
            "features": ["Breathable everyday trainer"],
            "details": {}, "store": "Example", "description": [],
        },
        {
            "parent_asin": "BAG-CANVAS",
            "title": "Canvas Bag",
            "categories": ["Bags"],
            "features": ["Tote"],
            "details": {}, "store": "Example", "description": [],
        },
    ]
    GAZETTEER = {
        "category": {"shoe": 2, "bag": 1},
        "material": {"canvas": 2, "leather": 1},
    }

    def build_agent(self) -> Agent:
        base = Path(self.temporary_directory.name)
        catalog_path = base / "catalog.jsonl"
        catalog_path.write_text(
            "".join(json.dumps(p) + "\n" for p in self.CATALOG), encoding="utf-8"
        )
        gazetteer_path = base / "gazetteer.json"
        gazetteer_path.write_text(json.dumps(self.GAZETTEER), encoding="utf-8")
        agent = Agent(catalog_path, gazetteer_path=gazetteer_path)
        agent.reset("session", {})
        return agent

    def test_missing_gazetteer_file_leaves_the_agent_usable(self) -> None:
        base = Path(self.temporary_directory.name)
        catalog_path = base / "catalog.jsonl"
        catalog_path.write_text(
            "".join(json.dumps(p) + "\n" for p in self.CATALOG), encoding="utf-8"
        )
        agent = Agent(catalog_path, gazetteer_path=base / "absent.json")
        agent.reset("session", {})
        response = agent.respond("session", "I want a canvas shoe", 1, 3)
        self.assertIsInstance(response["recommendations"], list)


class OverrideRetainsAnsweredConstraintsTest(ConversationStateTest):
    def test_override_keeps_answers_given_to_questions_but_drops_the_volunteered_preference(self) -> None:
        # "Ignore my earlier preference" revokes what the customer volunteered
        # on turn 1, not the answers they gave when the agent asked. Dropping
        # those answers throws away constraints that were never withdrawn.
        agent = self.build_agent(
            [
                {
                    # Weaker on {shirt, blue} alone, so this can only win if
                    # "cotton" survives the override.
                    "parent_asin": "BLUE-COTTON",
                    "title": "Blue Cotton Button Down Collared Shirt",
                    "categories": ["Shirts"],
                    "features": ["Everyday wear"],
                    "details": {}, "store": "Example", "description": [],
                },
                {
                    "parent_asin": "BLUE-LINEN",
                    "title": "Blue Shirt",
                    "categories": ["Shirts"],
                    "features": ["Linen"],
                    "details": {}, "store": "Example", "description": [],
                },
                {
                    "parent_asin": "RED-COTTON",
                    "title": "Red Cotton Shirt",
                    "categories": ["Shirts"],
                    "features": ["Everyday wear"],
                    "details": {}, "store": "Example", "description": [],
                },
            ],
            gazetteer={
                "category": {"shirt": 3},
                "color": {"red": 1, "blue": 2},
                "material": {"cotton": 2, "linen": 1},
            },
        )

        agent.respond("session", "I want a red shirt", 1, 1)
        agent.respond("session", "For that, what matters is: cotton.", 2, 1)
        response = agent.respond(
            "session",
            "Actually, ignore my earlier preference. What I need is: blue.",
            3,
            1,
        )

        self.assertEqual(
            [{"parent_asin": "BLUE-COTTON"}],
            response["recommendations"],
        )


class BuyingBrowsingRoutingTest(ConversationStateTest):
    """A Buying customer discloses a concrete constraint on the opening turn
    (docs/competition_specification.md); a Browsing customer starts vague.
    The session is classified once, from the opening message only, and that
    classification is used for the rest of the conversation.
    """

    def test_opening_constraint_routes_the_session_as_buying(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={"category": {"shirt": 1}, "color": {"black": 1}},
        )
        agent.respond("session", "I want a black shirt", 1, 1)
        self.assertEqual("buying", agent._session_route["session"])

    def test_vague_opening_message_routes_the_session_as_browsing(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={"category": {"shirt": 1}, "color": {"black": 1}},
        )
        agent.respond("session", "I want a shirt, still exploring", 1, 1)
        self.assertEqual("browsing", agent._session_route["session"])

    def test_route_is_frozen_after_the_opening_turn(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={"category": {"shirt": 1}, "color": {"black": 1}},
        )
        agent.respond("session", "I want a shirt, still exploring", 1, 1)
        agent.respond("session", "black please", 2, 1)
        self.assertEqual("browsing", agent._session_route["session"])

    def test_buying_route_prefers_the_candidate_matching_every_constraint(self) -> None:
        # MORE-HITS turns up via extra, unrelated feature words but is missing
        # the color the customer actually asked for; ALL-MATCH satisfies every
        # disclosed constraint. Only the Buying route should reward that.
        agent = self.build_agent(
            [
                {
                    "parent_asin": "ALL-MATCH",
                    "title": "Black Leather Belt",
                    "categories": "Belts", "features": "", "details": {},
                    "store": "Example", "description": [],
                },
                {
                    "parent_asin": "MORE-HITS",
                    "title": "Leather Belt",
                    "categories": "Belts",
                    "features": "everyday casual outdoor accessory gift",
                    "details": {}, "store": "Example", "description": [],
                },
            ],
            gazetteer={"category": {"belt": 2}, "color": {"black": 1}, "material": {"leather": 1}},
        )

        response = agent.respond(
            "session",
            "I want a black leather belt, something everyday casual outdoor",
            1,
            2,
        )

        self.assertEqual(
            [{"parent_asin": "ALL-MATCH"}, {"parent_asin": "MORE-HITS"}],
            response["recommendations"],
        )


class NarrowPhraseIndependentOverrideTest(ConversationStateTest):
    """A change of mind is a conflict with an established, on-topic value --
    not any word that happens to land in the same gazetteer slot. A term
    that arrived answering a *different* question (e.g. "synthetic"
    answering a "feature" question, but lexically matching the "material"
    slot) is not something a later, real answer to that slot's own question
    can "override": it was never a legitimate value for that question in
    the first place.
    """

    def test_off_topic_contamination_does_not_block_a_later_real_answer(self) -> None:
        # Reproduces reports/experiments/phrase-independent-override.md's
        # exact regression in miniature: "synthetic" arrives answering a
        # "feature" question (profile order asks feature before material)
        # but lexically matches "material". The later, genuine material
        # answer ("cotton") must not be treated as overriding it.
        agent = self.build_agent(
            [],
            profile={"preference_tags": ["comfort"]},
            clarification_policy="profile",
            gazetteer={"category": {"shoe": 1}, "material": {"synthetic": 1, "cotton": 1}},
        )
        first = agent.respond("session", "I want a shoe", 1, 1)
        self.assertEqual("feature", first["ask_attribute"])

        second = agent.respond("session", "For that, what matters is: synthetic sole.", 2, 1)
        self.assertEqual("material", second["ask_attribute"])

        agent.respond("session", "cotton please", 3, 1)

        slots = agent._session_slots["session"]
        self.assertIn("synthetic", slots.get("material", {}))
        self.assertIn("cotton", slots.get("material", {}))

    def test_unprompted_paraphrase_still_overrides_a_legitimate_value(self) -> None:
        # "red" is established on the opening turn -- a legitimate value.
        # No literal phrase here; this is the core capability the rejected
        # broad attempt was trying to recover.
        agent = self.build_agent(
            [],
            gazetteer={"category": {"shirt": 1}, "color": {"red": 1, "blue": 1}},
        )
        agent.respond("session", "I want a red shirt", 1, 1)
        agent.respond("session", "I've changed my mind, blue please.", 2, 1)

        slots = agent._session_slots["session"]
        self.assertNotIn("red", slots.get("color", {}))
        self.assertIn("blue", slots.get("color", {}))

    def test_repeating_the_same_value_is_not_a_false_override(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={
                "category": {"shirt": 1},
                "color": {"red": 1, "blue": 1},
                "style": {"casual": 1, "formal": 1},
            },
        )
        agent.respond("session", "I want a casual red shirt", 1, 1)
        agent.respond("session", "I definitely want red.", 2, 1)

        self.assertIn("casual", agent._session_slots["session"].get("style", {}))

    def test_a_brand_new_slot_is_not_a_false_override(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={
                "category": {"shirt": 1},
                "color": {"red": 1},
                "material": {"cotton": 1},
            },
        )
        agent.respond("session", "I want a red shirt", 1, 1)
        agent.respond("session", "cotton please", 2, 1)

        slots = agent._session_slots["session"]
        self.assertIn("red", slots.get("color", {}))
        self.assertIn("cotton", slots.get("material", {}))

    def test_literal_override_phrase_still_works(self) -> None:
        agent = self.build_agent(
            [],
            gazetteer={"category": {"shirt": 1}, "color": {"red": 1, "blue": 1}},
        )
        agent.respond("session", "I want a red shirt", 1, 1)
        agent.respond(
            "session",
            "Actually, ignore my earlier preference. What I need is: blue.",
            2,
            1,
        )

        slots = agent._session_slots["session"]
        self.assertNotIn("red", slots.get("color", {}))
        self.assertIn("blue", slots.get("color", {}))
