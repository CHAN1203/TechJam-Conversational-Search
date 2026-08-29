from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_popularity_sweep import run_popularity_sweep, run_popularity_variants


class PopularitySweepTest(unittest.TestCase):
    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )

    def _samples(self) -> list[dict]:
        return [
            {
                "sample_id": "easy",
                "difficulty_bucket": "easy",
                "scenario_type": "buying",
                "user_profile": {},
                "ground_truth": {"parent_asin": "A"},
                "intent_card": {"target_category": "blue shoe", "hard_constraints": [], "soft_preferences": []},
                "behavior": {},
            },
            {
                "sample_id": "hard",
                "difficulty_bucket": "hard",
                "scenario_type": "buying",
                "user_profile": {},
                "ground_truth": {"parent_asin": "B"},
                "intent_card": {"target_category": "red boot", "hard_constraints": [], "soft_preferences": []},
                "behavior": {},
            },
        ]

    def _catalog(self, directory: str, name: str, stress: bool = False) -> Path:
        path = Path(directory) / name
        products = [
            {"parent_asin": "A", "title": "blue shoe", "categories": ["Shoes"]},
            {"parent_asin": "B", "title": "red boot", "categories": ["Shoes"]},
        ]
        if stress:
            products[0]["title"] = "shoe"
        self._write_jsonl(path, products)
        return path

    def test_single_catalog_returns_weight_split_and_difficulty_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_popularity_sweep(
                self._catalog(directory, "catalog.jsonl"),
                self._samples(),
                weights=(0.0, 1.2),
                validation_size=1,
                seed="fixed",
            )

            self.assertEqual({"0", "1.2"}, set(result["weights"]))
            for row in result["weights"].values():
                self.assertEqual({"full", "development", "validation", "difficulty"}, set(row))
                self.assertEqual({"easy", "hard"}, set(row["difficulty"]))

    def test_dual_catalog_returns_deltas_by_weight_split_and_difficulty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            variants = {
                "official": self._catalog(directory, "official.jsonl"),
                "coverage_stress": self._catalog(directory, "stress.jsonl", stress=True),
            }
            payload = run_popularity_variants(
                variants, self._samples(), weights=(0.0, 1.2), validation_size=1, seed="fixed"
            )

            self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
            self.assertEqual("coverage_stress_minus_official", payload["delta_direction"])
            self.assertIn("1.2", payload["deltas"])
            self.assertIn("validation", payload["deltas"]["1.2"])
            self.assertIn("difficulty", payload["deltas"]["1.2"])


if __name__ == "__main__":
    unittest.main()
