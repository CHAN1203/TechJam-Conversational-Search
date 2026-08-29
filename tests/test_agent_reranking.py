from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starter.agent import Agent


class AgentRerankingTest(unittest.TestCase):
    def test_respond_reranks_a_larger_bm25_candidate_pool(self) -> None:
        products = [
            {
                "parent_asin": "PARTIAL",
                "title": "Men Hiking",
                "categories": ["Footwear"],
                "features": ["Everyday shoes"],
                "details": {},
                "store": "Example",
                "description": [],
            },
            {
                "parent_asin": "COMPLETE",
                "title": "Trail Footwear",
                "categories": ["Men", "Hiking"],
                "features": ["Full grain leather"],
                "details": {},
                "store": "Example",
                "description": ["Boots"],
            },
            *[
                {
                    "parent_asin": f"FILLER-{index}",
                    "title": f"Accessory {index}",
                    "categories": ["Accessories"],
                    "features": ["Leather"],
                    "details": {},
                    "store": "Example",
                    "description": ["Boots"],
                }
                for index in range(20)
            ],
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            agent = Agent(catalog_path)
            agent.reset("session", {})

            response = agent.respond("session", "men leather hiking boots", 1, 1)

        self.assertEqual(
            [{"parent_asin": "COMPLETE"}],
            response["recommendations"],
        )


if __name__ == "__main__":
    unittest.main()


class AgentPopularityPriorTest(unittest.TestCase):
    def test_prefers_the_heavily_reviewed_item_when_constraints_tie(self) -> None:
        # The hidden target is a real purchase record, so it is far more likely
        # to be a heavily reviewed item than an obscure one that matches the
        # same words.
        products = [
            {
                "parent_asin": "OBSCURE",
                "title": "Genuine Leather Belt with Buckle",
                "categories": ["Accessories", "Belts"],
                "features": ["Buckle closure"], "details": {},
                "store": "Example", "description": [],
                "average_rating": 4.7, "rating_number": 18,
            },
            {
                "parent_asin": "POPULAR",
                "title": "Genuine Leather Belt with Buckle",
                "categories": ["Accessories", "Belts"],
                "features": ["Buckle closure"], "details": {},
                "store": "Example", "description": [],
                "average_rating": 4.3, "rating_number": 6614,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            gazetteer_path = Path(directory) / "gazetteer.json"
            gazetteer_path.write_text("{}", encoding="utf-8")
            agent = Agent(catalog_path, gazetteer_path=gazetteer_path)
            agent.reset("session", {})
            response = agent.respond("session", "leather belt buckle closure", 1, 2)

        self.assertEqual("POPULAR", response["recommendations"][0]["parent_asin"])

    def test_missing_rating_number_does_not_break_ranking(self) -> None:
        products = [
            {
                "parent_asin": "NO-RATINGS",
                "title": "Leather Belt",
                "categories": ["Belts"], "features": [], "details": {},
                "store": "Example", "description": [],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            gazetteer_path = Path(directory) / "gazetteer.json"
            gazetteer_path.write_text("{}", encoding="utf-8")
            agent = Agent(catalog_path, gazetteer_path=gazetteer_path)
            agent.reset("session", {})
            response = agent.respond("session", "leather belt", 1, 1)

        self.assertEqual(
            [{"parent_asin": "NO-RATINGS"}], response["recommendations"]
        )
