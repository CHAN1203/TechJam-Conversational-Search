from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.run_popularity_sweep as popularity_sweep
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

            metrics = {
                "hit_rate_at_10": 0.1,
                "mrr": 0.2,
                "mttc": 0.3,
                "efficiency": 0.4,
                "recommended_technical_score": 0.5,
            }

            def summary(stress: bool) -> dict:
                return {
                    metric: value + (0.01 if stress else 0.0)
                    for metric, value in metrics.items()
                }

            def fake_sweep(catalog_path: str | Path, *args, **kwargs) -> dict:
                stress = Path(catalog_path).name == "stress.jsonl"
                row = {
                    split: summary(stress)
                    for split in ("full", "development", "validation")
                }
                row["difficulty"] = {
                    bucket: summary(stress) for bucket in ("easy", "hard")
                }
                return {
                    "seed": "fixed",
                    "validation_size": 1,
                    "weights": {"0": row, "1.2": row},
                }

            with patch.object(popularity_sweep, "run_popularity_sweep", side_effect=fake_sweep):
                payload = run_popularity_variants(
                    variants, self._samples(), weights=(0.0, 1.2), validation_size=1, seed="fixed"
                )

            self.assertEqual({"official", "coverage_stress"}, set(payload["catalogs"]))
            self.assertEqual("coverage_stress_minus_official", payload["delta_direction"])
            expected_delta = {metric: 0.01 for metric in metrics}
            expected_row = {
                split: expected_delta
                for split in ("full", "development", "validation")
            }
            expected_row["difficulty"] = {
                bucket: expected_delta for bucket in ("easy", "hard")
            }
            self.assertEqual(
                {"0": expected_row, "1.2": expected_row}, payload["deltas"]
            )


if __name__ == "__main__":
    unittest.main()
