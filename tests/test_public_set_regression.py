"""Guard the retained public-set result against silent regression.

`docs/experiment_history.md` names one method as current best, but until now no
test asserted its score. A refactor could drop TechnicalScore and leave the
whole suite green -- measured: a build scoring `0.808383` instead of `0.841838`
passes every other test in this repository.

Expected values are read from `docs/current_best_results.json`, never hard-coded
here. That mirrors `docs/baseline_results.json` and honours the workflow rule
against typing remembered scores into evidence: regenerate the JSON from a real
evaluator run when a method is intentionally retained.

The run needs the untracked 50,000-item catalog and takes about a minute, so it
is opt-in via `TECHJAM_RUN_PUBLIC_SET=1`. It skips with a stated reason
otherwise, keeping `python -m unittest discover -s tests` fast on a fresh clone.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PATH = REPOSITORY_ROOT / "docs" / "current_best_results.json"
CATALOG_PATH = REPOSITORY_ROOT / "data" / "catalog.jsonl"
DATASET_PATH = REPOSITORY_ROOT / "data" / "public_set.jsonl"
RUN_FLAG = "TECHJAM_RUN_PUBLIC_SET"

# The evaluator rounds every reported metric to six decimals, so the retained
# result is reproducible exactly rather than approximately. The agent holds no
# randomness and the simulator seeds its own from `sample_id`.
PLACES = 6


def _should_run() -> tuple[bool, str]:
    """Report whether the full public-set run can execute, and why not if it cannot.

    Returns:
        A pair of (runnable, reason). `reason` is empty when runnable is True
        and otherwise carries the skip message shown in test output.
    """
    if os.environ.get(RUN_FLAG) != "1":
        return False, f"set {RUN_FLAG}=1 to run the full public-set regression"
    if not CATALOG_PATH.exists():
        return False, f"missing {CATALOG_PATH}; download it from the GitHub Release"
    return True, ""


RUNNABLE, SKIP_REASON = _should_run()


@unittest.skipUnless(RUNNABLE, SKIP_REASON)
class PublicSetRegressionTest(unittest.TestCase):
    """Assert the committed retained result still reproduces exactly."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
        samples = load_jsonl(DATASET_PATH)
        catalog_ids, categories, products = catalog_index(CATALOG_PATH)
        # No constructor overrides: this must score whatever the shipped
        # defaults score, which is what the organizer will run.
        cls.result = evaluate(
            Agent(CATALOG_PATH), samples, catalog_ids, categories, products
        )

    def test_sample_count_matches_the_released_public_set(self) -> None:
        self.assertEqual(self.expected["sample_count"], self.result["sample_count"])

    def test_overall_metrics_match_the_retained_result(self) -> None:
        for key, actual_key in (
            ("hit_rate_at_10", "hit_rate_at_10"),
            ("mrr", "mrr"),
            ("mttc", "mttc"),
            ("efficiency", "efficiency"),
            ("technical_score", "recommended_technical_score"),
        ):
            with self.subTest(metric=key):
                self.assertAlmostEqual(
                    self.expected[key],
                    self.result[actual_key],
                    places=PLACES,
                    msg=(
                        f"{key} moved; if this change is intended, regenerate "
                        f"{EXPECTED_PATH.name} and update docs/experiment_history.md"
                    ),
                )

    def test_every_scenario_matches_the_retained_result(self) -> None:
        """Catch a regression hidden inside an unchanged aggregate.

        Section 2 of the experiment ledger exists for this: E4-B collapsed
        Intent Override from 0.633333 to 0.333333 while overall TechnicalScore
        moved only -0.006019. An aggregate-only assertion would miss that.
        """
        expected_scenarios = self.expected["scenario_metrics"]
        actual_scenarios = self.result["scenario_metrics"]
        self.assertEqual(sorted(expected_scenarios), sorted(actual_scenarios))
        for scenario, expected in expected_scenarios.items():
            actual = actual_scenarios[scenario]
            for metric in ("hit_rate_at_10", "mrr", "mttc"):
                with self.subTest(scenario=scenario, metric=metric):
                    self.assertAlmostEqual(
                        expected[metric],
                        actual[metric],
                        places=PLACES,
                        msg=f"{scenario} {metric} regressed",
                    )
            with self.subTest(scenario=scenario, metric="sample_count"):
                self.assertEqual(expected["sample_count"], actual["sample_count"])

    def test_reported_token_usage_stays_zero_for_the_offline_agent(self) -> None:
        """The retained agent uses no model, so a non-zero count means one crept in."""
        self.assertEqual(
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            self.result["reported_token_usage"],
        )


if __name__ == "__main__":
    unittest.main()
