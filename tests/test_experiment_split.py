from __future__ import annotations

import unittest
from collections import Counter

from analysis.experiment_split import stratified_split


class ExperimentSplitTest(unittest.TestCase):
    def test_split_has_exact_size_and_balanced_strata(self) -> None:
        samples = [
            {
                "sample_id": f"a-{index}",
                "scenario_type": "buying",
                "difficulty_bucket": "easy",
            }
            for index in range(5)
        ] + [
            {
                "sample_id": f"b-{index}",
                "scenario_type": "browsing",
                "difficulty_bucket": "medium",
            }
            for index in range(3)
        ] + [
            {
                "sample_id": f"c-{index}",
                "scenario_type": "intent_override",
                "difficulty_bucket": "hard",
            }
            for index in range(2)
        ]

        development, validation = stratified_split(samples, validation_size=4)

        self.assertEqual(6, len(development))
        self.assertEqual(4, len(validation))
        self.assertEqual(
            Counter({("buying", "easy"): 2, ("browsing", "medium"): 1, ("intent_override", "hard"): 1}),
            Counter(
                (sample["scenario_type"], sample["difficulty_bucket"])
                for sample in validation
            ),
        )
        self.assertTrue(
            {sample["sample_id"] for sample in development}.isdisjoint(
                sample["sample_id"] for sample in validation
            )
        )


if __name__ == "__main__":
    unittest.main()
