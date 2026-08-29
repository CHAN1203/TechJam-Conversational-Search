"""Prove the submission bundle is complete and contract-compliant in isolation.

`docs/submission_rules.md` requires an entry file exporting `Agent` plus every
local helper module it needs. Nothing verified that list, and it was wrong: a
bundle of `starter/` alone raises `ModuleNotFoundError: No module named
'analysis'`, because `starter/slots.py` imports `normalize_term` from the
diagnostics package.

`SUBMISSION_PATHS` below is that list, and this test is what keeps it honest.
The bundle is copied to a temporary directory and exercised in a **subprocess**
with `PYTHONPATH` cleared and the working directory set to the bundle root. The
subprocess is load-bearing: an in-process import would resolve against this
repository and prove nothing about what the organizer receives.

While isolated, the bundle is also checked against
`docs/agent_api_contract.json` and driven with hostile input. Those properties
hold today only because `TOKEN_RE` is `[a-z0-9]+`, which keeps FTS5 syntax out
of the `MATCH` expression. Widening it would produce `sqlite3.OperationalError`,
which the evaluator catches and scores as a miss -- a silent loss that no other
test would surface.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

# Everything the scored agent needs, and nothing else. The rest of `analysis/`
# must stay out: `bm25_diagnostics.py` and `experiment_results.py` import
# `evaluator.local_evaluator`, which does not belong in a participant bundle.
# `analysis/__init__.py` holds only a docstring, so importing
# `analysis.gazetteer` does not pull those modules in.
SUBMISSION_PATHS = (
    "starter/__init__.py",
    "starter/agent.py",
    "starter/clarification.py",
    "starter/reranker.py",
    "starter/slots.py",
    "analysis/__init__.py",
    "analysis/gazetteer.py",
    "data/gazetteer.json",
)

# Modules the bundle must never need. Shipping them, or importing them from the
# scored path, would break the organizer's run or violate the submission rules.
FORBIDDEN_MODULES = ("evaluator", "frontend", "scripts")

EXPECTED_GAZETTEER_SLOTS = {
    "category", "color", "department", "material", "size", "style",
}

ALLOWED_ATTRIBUTES = {
    "category", "material", "color", "size", "style", "brand",
    "budget", "feature", "use_case", "other",
}

# Hostile and degenerate customer messages. The specification permits the
# organizer to paraphrase simulator output, so the agent must not assume the
# templated public-set phrasing.
ADVERSARIAL_MESSAGES = {
    "empty": "",
    "whitespace": "   \t\n  ",
    "fts5_metachars": 'shirt AND NOT "quoted" OR (nested) * ^ - :',
    "sql_quote": "shirt'; DROP TABLE products; --",
    "unicode": "chemise bleue 靴 \U0001f45f café",
    "very_long": "cotton shirt " * 5000,
    "only_stopwords": "the a an and of to",
    "numeric": "12345 67890",
}

# Runs inside the bundle, so it may import only what the bundle ships. Its
# configuration arrives in a file rather than argv: the 60k-character
# adversarial message exceeds the Windows command-line limit.
BUNDLE_RUNNER = '''
import json, sys, tempfile
from pathlib import Path

from starter.agent import Agent

CONFIG = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ALLOWED = set(CONFIG["allowed_attributes"])
MESSAGES = CONFIG["messages"]
FORBIDDEN = CONFIG["forbidden_modules"]

CATALOG = [
    {"parent_asin": "SHIRT", "title": "Blue cotton shirt",
     "categories": ["Clothing", "Shirts"], "features": ["cotton", "breathable"],
     "details": {"department": "womens"}, "store": "Example",
     "description": ["a light shirt"], "price": 25.0, "rating_number": 120},
    {"parent_asin": "JACKET", "title": "Black nylon jacket",
     "categories": ["Clothing", "Jackets"], "features": ["nylon", "waterproof"],
     "details": {"department": "mens"}, "store": "Example",
     "description": ["a rain jacket"], "price": 80.0, "rating_number": 8},
]

violations = []


def check(response, top_k, label):
    """Assert one turn response against the published Agent contract."""
    if not isinstance(response.get("message"), str):
        violations.append([label, "message is not a string"])
    attribute = response.get("ask_attribute")
    if attribute is not None and attribute not in ALLOWED:
        violations.append([label, "ask_attribute %r not allowed" % (attribute,)])
    recommendations = response.get("recommendations")
    if not isinstance(recommendations, list):
        violations.append([label, "recommendations is not a list"])
        return
    if len(recommendations) > top_k:
        violations.append([label, "returned %d > top_k %d" % (len(recommendations), top_k)])
    identifiers = [item.get("parent_asin") for item in recommendations]
    if any(not isinstance(value, str) or not value for value in identifiers):
        violations.append([label, "recommendation missing a string parent_asin"])
    if len(set(identifiers)) != len(identifiers):
        violations.append([label, "duplicate parent_asin"])
    usage = response.get("usage")
    if usage is not None:
        for field in ("prompt_tokens", "completion_tokens"):
            value = usage.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                violations.append([label, "usage.%s is %r" % (field, value)])


directory = Path(tempfile.mkdtemp())
catalog_path = directory / "catalog.jsonl"
catalog_path.write_text(
    "".join(json.dumps(product) + "\\n" for product in CATALOG), encoding="utf-8"
)

# Default gazetteer path: resolved relative to the bundle working directory.
agent = Agent(catalog_path)
gazetteer_slots = sorted(agent.gazetteer)

agent.reset("multi", {"preference_tags": ["material"], "summary": "likes cotton"})
conversation = [
    "I'm looking for shirts. A key requirement is: cotton.",
    "For that, what matters is: blue.",
    "I don't have a preference for size; please use your judgment.",
    "Actually, ignore my earlier preference. What I need is: nylon.",
]
for turn, message in enumerate(conversation, 1):
    check(agent.respond("multi", message, turn, 10), 10, "turn%d" % turn)

adversarial = {}
for name, message in MESSAGES.items():
    agent.reset("probe_" + name, {})
    try:
        response = agent.respond("probe_" + name, message, 1, 10)
    except Exception as error:
        adversarial[name] = "RAISED %s: %s" % (type(error).__name__, error)
        continue
    check(response, 10, "adversarial:" + name)
    adversarial[name] = "ok"

reset_guard = "did not raise"
try:
    agent.respond("never_reset", "shirt", 1, 10)
except RuntimeError:
    reset_guard = "RuntimeError"
except Exception as error:
    reset_guard = type(error).__name__

print(json.dumps({
    "violations": violations,
    "adversarial": adversarial,
    "gazetteer_slots": gazetteer_slots,
    "reset_guard": reset_guard,
    "leaked_modules": sorted(name for name in FORBIDDEN if name in sys.modules),
}))
'''


def build_bundle(destination: Path) -> None:
    """Copy exactly the declared submission files into `destination`.

    Args:
        destination: Empty directory that becomes the bundle root.

    Raises:
        FileNotFoundError: If a declared submission path is missing from the
            repository, which means `SUBMISSION_PATHS` has gone stale.
    """
    for relative in SUBMISSION_PATHS:
        source = REPOSITORY_ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(f"declared submission file is missing: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_in_bundle(bundle: Path) -> dict:
    """Execute the bundle runner isolated from this repository.

    `PYTHONPATH` is cleared and the working directory is the bundle root, so
    imports resolve only against copied files. Any reach back into the
    repository surfaces as `ModuleNotFoundError`.

    Args:
        bundle: Directory produced by `build_bundle`.

    Returns:
        The runner's decoded JSON report.

    Raises:
        AssertionError: If the subprocess fails, carrying its stderr.
    """
    runner = bundle / "_bundle_runner.py"
    runner.write_text(BUNDLE_RUNNER, encoding="utf-8")
    config = bundle / "_bundle_config.json"
    config.write_text(
        json.dumps(
            {
                "allowed_attributes": sorted(ALLOWED_ATTRIBUTES),
                "messages": ADVERSARIAL_MESSAGES,
                "forbidden_modules": list(FORBIDDEN_MODULES),
            }
        ),
        encoding="utf-8",
    )
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    completed = subprocess.run(
        [sys.executable, str(runner), str(config)],
        cwd=bundle,
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"bundle failed to run in isolation:\n{completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


class SubmissionBundleTest(unittest.TestCase):
    """Run the declared bundle in isolation and hold it to the published contract."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        bundle = Path(cls._directory.name) / "bundle"
        bundle.mkdir()
        build_bundle(bundle)
        cls.bundle = bundle
        cls.report = run_in_bundle(bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_every_declared_file_exists_in_the_repository(self) -> None:
        for relative in SUBMISSION_PATHS:
            with self.subTest(path=relative):
                self.assertTrue((REPOSITORY_ROOT / relative).is_file())

    def test_bundle_imports_and_runs_without_the_repository(self) -> None:
        """The load-bearing assertion: nothing outside the bundle is reachable.

        `setUpClass` already ran the bundle, so reaching this test at all means
        the isolated import succeeded. Kept explicit so the failure reads as a
        packaging problem rather than an unrelated error.
        """
        self.assertIn("adversarial", self.report)

    def test_scored_path_does_not_pull_in_repository_only_packages(self) -> None:
        self.assertEqual([], self.report["leaked_modules"])

    def test_turn_responses_satisfy_the_agent_contract(self) -> None:
        self.assertEqual([], self.report["violations"])

    def test_hostile_and_degenerate_input_does_not_raise(self) -> None:
        for name in ADVERSARIAL_MESSAGES:
            with self.subTest(message=name):
                self.assertEqual("ok", self.report["adversarial"][name])

    def test_respond_before_reset_is_rejected(self) -> None:
        self.assertEqual("RuntimeError", self.report["reset_guard"])

    def test_gazetteer_asset_ships_and_loads(self) -> None:
        """A missing gazetteer costs 0.033455 TechnicalScore and raises nothing.

        `_load_gazetteer` degrades to an empty mapping by design, so omitting
        the asset from a bundle is silent. This makes the omission loud.
        """
        self.assertTrue((self.bundle / "data" / "gazetteer.json").is_file())
        self.assertEqual(EXPECTED_GAZETTEER_SLOTS, set(self.report["gazetteer_slots"]))

    def test_bundle_carries_no_python_dependencies_beyond_the_standard_library(self) -> None:
        """The agent must run offline with no third-party install.

        `docs/submission_rules.md` requires the submission to state whether it
        needs network access. Pinning the import surface keeps that claim true.
        """
        third_party = {
            "numpy", "scipy", "pandas", "sklearn", "torch", "transformers",
            "openai", "anthropic", "requests", "httpx", "faiss",
        }
        for relative in SUBMISSION_PATHS:
            if not relative.endswith(".py"):
                continue
            source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            for package in third_party:
                with self.subTest(path=relative, package=package):
                    self.assertNotIn(f"import {package}", source)


if __name__ == "__main__":
    unittest.main()
