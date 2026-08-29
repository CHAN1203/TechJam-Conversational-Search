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
