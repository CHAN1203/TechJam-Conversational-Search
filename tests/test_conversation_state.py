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
    ) -> Agent:
        catalog_path = Path(self.temporary_directory.name) / "catalog.jsonl"
        catalog_path.write_text(
            "".join(json.dumps(product) + "\n" for product in products),
            encoding="utf-8",
        )
        if clarification_policy is None:
            agent = Agent(catalog_path)
        else:
            agent = Agent(catalog_path, clarification_policy=clarification_policy)
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

    def test_intent_override_replaces_earlier_constraints(self) -> None:
        agent = self.build_agent([
            {
                "parent_asin": "OLD-MIXED",
                "title": "Red Shirt",
                "categories": ["Shirts"],
                "features": ["Blue accent"],
                "details": {},
                "store": "Example",
                "description": [],
            },
            {
                "parent_asin": "NEW-BLUE",
                "title": "Blue Jacket",
                "categories": ["Jackets"],
                "features": ["Everyday wear"],
                "details": {},
                "store": "Example",
                "description": [],
            },
        ])

        agent.respond("session", "I want a red shirt", 1, 1)
        response = agent.respond(
            "session",
            "Actually, ignore my earlier preference. What I need is: blue.",
            2,
            1,
        )

        self.assertEqual(
            [{"parent_asin": "NEW-BLUE"}],
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
