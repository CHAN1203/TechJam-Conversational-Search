from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_clarification_ablation import run_ablation


class ClarificationAblationTest(unittest.TestCase):
    def test_run_ablation_reports_each_policy_and_split(self) -> None:
        products = [
            {
                "parent_asin": "RED",
                "title": "Red Shirt",
                "categories": ["Shirts"],
                "features": ["Cotton"],
                "details": {},
                "store": "Example",
                "description": [],
            },
            {
                "parent_asin": "BLUE",
                "title": "Blue Jacket",
                "categories": ["Jackets"],
                "features": ["Nylon"],
                "details": {},
                "store": "Example",
                "description": [],
            },
        ]
        samples = [
            {
                "sample_id": "sample-red",
                "scenario_type": "buying",
                "difficulty_bucket": "easy",
                "ground_truth": {"parent_asin": "RED"},
                "user_profile": {"preference_tags": ["material"]},
                "intent_card": {
                    "target_category": "shirt",
                    "hard_constraints": ["red"],
                    "soft_preferences": ["cotton"],
                },
                "behavior": {"scenario_type": "buying"},
            },
            {
                "sample_id": "sample-blue",
                "scenario_type": "buying",
                "difficulty_bucket": "easy",
                "ground_truth": {"parent_asin": "BLUE"},
                "user_profile": {"preference_tags": ["style"]},
                "intent_card": {
                    "target_category": "jacket",
                    "hard_constraints": ["blue"],
                    "soft_preferences": ["nylon"],
                },
                "behavior": {"scenario_type": "buying"},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.jsonl"
            catalog_path.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )

            result = run_ablation(
                catalog_path,
                samples,
                policies=("fixed", "profile"),
                validation_size=1,
            )

        self.assertEqual(1, result["split"]["development_count"])
        self.assertEqual(1, result["split"]["validation_count"])
        self.assertEqual({"fixed", "profile"}, set(result["policies"]))
        self.assertEqual(2, result["policies"]["fixed"]["full"]["sample_count"])
        self.assertEqual(1, result["policies"]["profile"]["validation"]["sample_count"])


if __name__ == "__main__":
    unittest.main()
