# Baseline Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, read-only diagnostics that measure first-turn BM25 candidate recall and catalog field coverage before selecting the dense retrieval and clarification designs.

**Architecture:** Add small pure analysis functions with unit tests, then wrap them in a CLI that imports the official starter and evaluator without modifying either. The CLI runs against the frozen public set and catalog and writes a compact JSON report plus a human-readable Markdown summary.

**Tech Stack:** Python 3.10+, standard library, SQLite FTS5 through the official starter, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md`

## Global Constraints

- Preserve the official `Agent.reset` and `Agent.respond` interfaces.
- Never modify `evaluator/`, `data/public_set.jsonl`, or catalog records.
- Keep diagnostics deterministic and functional without network access.
- Use the official `starter.Agent` for real BM25 measurements.
- Report overall and per-scenario results.
- Introduce production behavior only after its test fails for the expected reason.
- Do not add embedding, reranking, state, or clarification dependencies in this plan.

---

### Task 1: Candidate-rank aggregation

**Files:**
- Create: `analysis/__init__.py`
- Create: `analysis/bm25_diagnostics.py`
- Create: `tests/test_bm25_diagnostics.py`

**Interfaces:**
- Consumes: ranked `parent_asin` strings produced by the official Agent.
- Produces: `rank_of(target_id, ranked_ids) -> int | None` and `summarize_ranks(records, cutoffs) -> dict`.

- [ ] **Step 1: Write failing rank and aggregation tests**

```python
from __future__ import annotations

import unittest

from analysis.bm25_diagnostics import rank_of, summarize_ranks


class Bm25DiagnosticsTest(unittest.TestCase):
    def test_rank_of_returns_one_based_rank_or_none(self) -> None:
        self.assertEqual(rank_of("B", ["A", "B", "C"]), 2)
        self.assertIsNone(rank_of("Z", ["A", "B", "C"]))

    def test_summarize_ranks_reports_literal_cutoff_rates_by_scenario(self) -> None:
        records = [
            {"scenario_type": "buying", "rank": 1},
            {"scenario_type": "buying", "rank": 25},
            {"scenario_type": "browsing", "rank": None},
            {"scenario_type": "browsing", "rank": 75},
        ]
        self.assertEqual(summarize_ranks(records, (10, 50, 100)), {
            "sample_count": 4,
            "recall": {"10": 0.25, "50": 0.5, "100": 0.75},
            "scenario_recall": {
                "browsing": {
                    "sample_count": 2,
                    "recall": {"10": 0.0, "50": 0.0, "100": 0.5},
                },
                "buying": {
                    "sample_count": 2,
                    "recall": {"10": 0.5, "50": 1.0, "100": 1.0},
                },
            },
        })
```

- [ ] **Step 2: Run the tests and confirm RED**

Run:

```powershell
python -m unittest tests.test_bm25_diagnostics -v
```

Expected: import failure because `analysis.bm25_diagnostics` does not exist.

- [ ] **Step 3: Implement the minimal pure functions**

```python
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence


def rank_of(target_id: str, ranked_ids: Sequence[str]) -> int | None:
    try:
        return ranked_ids.index(target_id) + 1
    except ValueError:
        return None


def _recall(ranks: Sequence[int | None], cutoffs: tuple[int, ...]) -> dict[str, float]:
    if not ranks:
        return {str(cutoff): 0.0 for cutoff in cutoffs}
    return {
        str(cutoff): round(
            sum(rank is not None and rank <= cutoff for rank in ranks) / len(ranks),
            6,
        )
        for cutoff in cutoffs
    }


def summarize_ranks(records: Iterable[dict], cutoffs: tuple[int, ...]) -> dict:
    materialized = list(records)
    grouped: dict[str, list[int | None]] = defaultdict(list)
    for record in materialized:
        grouped[str(record["scenario_type"])].append(record.get("rank"))
    return {
        "sample_count": len(materialized),
        "recall": _recall([record.get("rank") for record in materialized], cutoffs),
        "scenario_recall": {
            name: {"sample_count": len(ranks), "recall": _recall(ranks, cutoffs)}
            for name, ranks in sorted(grouped.items())
        },
    }
```

- [ ] **Step 4: Run focused and complete tests and confirm GREEN**

```powershell
python -m unittest tests.test_bm25_diagnostics -v
python -m unittest discover -s tests -v
```

Expected: 5 tests pass with no failures.

- [ ] **Step 5: Commit the aggregation unit**

```powershell
git add analysis/__init__.py analysis/bm25_diagnostics.py tests/test_bm25_diagnostics.py
git commit -m "feat: add candidate recall diagnostics"
```

---

### Task 2: Real first-turn BM25 measurement

**Files:**
- Modify: `analysis/bm25_diagnostics.py`
- Create: `scripts/__init__.py`
- Create: `scripts/analyze_bm25_recall.py`
- Modify: `tests/test_bm25_diagnostics.py`

**Interfaces:**
- Consumes: official `Agent`, public samples, catalog IDs, categories, and product records.
- Produces: `measure_first_turn(agent, samples, categories, products, cutoff) -> list[dict]` and a CLI JSON document on stdout or at `--output`.

- [ ] **Step 1: Write a failing integration-shaped unit test**

Add a real interface double that returns deterministic IDs; assertions target the
measurement record rather than calls made to the double.

```python
class RankedAgent:
    def reset(self, session_id: str, user_profile: dict) -> None:
        self.session_id = session_id

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        return {
            "message": "matches",
            "ask_attribute": None,
            "recommendations": [
                {"parent_asin": value} for value in ["A", "TARGET", "C"][:top_k]
            ],
        }


def test_measure_first_turn_records_target_rank(self) -> None:
    samples = [{
        "sample_id": "sample-1",
        "scenario_type": "buying",
        "user_profile": {"summary": "fixture"},
        "ground_truth": {"parent_asin": "TARGET"},
        "intent_card": {
            "target_category": "shoe",
            "hard_constraints": ["leather"],
            "soft_preferences": ["walking"],
        },
        "behavior": {"scenario_type": "buying"},
    }]
    records = measure_first_turn(
        RankedAgent(), samples, {"TARGET": ["Clothing", "Shoes"]}, {}, cutoff=100
    )
    self.assertEqual(records, [{
        "sample_id": "sample-1",
        "scenario_type": "buying",
        "rank": 2,
    }])
```

- [ ] **Step 2: Run the focused test and confirm RED**

```powershell
python -m unittest tests.test_bm25_diagnostics.Bm25DiagnosticsTest.test_measure_first_turn_records_target_rank -v
```

Expected: import failure because `measure_first_turn` is missing.

- [ ] **Step 3: Implement measurement using official simulator helpers**

`measure_first_turn` must call `materialize_hidden_fields`, `coarse_category`, and
`initial_message` from `evaluator.local_evaluator`, reset each session, request
the maximum cutoff, extract recommendation IDs, and record the target rank. It
must not copy or modify evaluator logic.

```python
from evaluator.local_evaluator import coarse_category, initial_message, materialize_hidden_fields


def measure_first_turn(
    agent: object,
    samples: list[dict],
    categories: dict[str, list[str]],
    products: dict[str, dict],
    cutoff: int,
) -> list[dict]:
    records: list[dict] = []
    for sample in samples:
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        message = initial_message(
            effective,
            coarse_category(categories.get(target, [])),
            set(),
        )
        session_id = f"diagnostic_{sample['sample_id']}"
        agent.reset(session_id, sample["user_profile"])
        response = agent.respond(session_id, message, 1, cutoff)
        ranked_ids = [
            str(item["parent_asin"])
            for item in response.get("recommendations", [])
            if isinstance(item, dict) and item.get("parent_asin")
        ]
        records.append({
            "sample_id": str(sample["sample_id"]),
            "scenario_type": str(sample["scenario_type"]),
            "rank": rank_of(target, ranked_ids),
        })
    return records
```

- [ ] **Step 4: Add the CLI wrapper**

The CLI must accept these exact arguments:

```text
--catalog data/catalog.jsonl
--dataset data/public_set.jsonl
--output reports/baseline/bm25-first-turn-recall.json
--cutoffs 10 50 100 500
```

It must load official artifacts, instantiate `starter.Agent`, run the
measurement once at cutoff 500, call `summarize_ranks`, and write indented JSON.

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.bm25_diagnostics import measure_first_turn, summarize_ranks
from evaluator.local_evaluator import catalog_index, load_jsonl
from starter.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="reports/baseline/bm25-first-turn-recall.json")
    parser.add_argument("--cutoffs", nargs="+", type=int, default=[10, 50, 100, 500])
    args = parser.parse_args()
    cutoffs = tuple(sorted(set(args.cutoffs)))
    _, categories, products = catalog_index(args.catalog)
    records = measure_first_turn(
        Agent(args.catalog),
        load_jsonl(args.dataset),
        categories,
        products,
        max(cutoffs),
    )
    report = summarize_ranks(records, cutoffs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run focused and complete tests**

```powershell
python -m unittest tests.test_bm25_diagnostics -v
python -m unittest discover -s tests -v
```

Expected: 6 tests pass with no failures.

- [ ] **Step 6: Commit the real measurement path**

```powershell
git add analysis/bm25_diagnostics.py scripts/__init__.py scripts/analyze_bm25_recall.py tests/test_bm25_diagnostics.py
git commit -m "feat: measure first-turn BM25 recall"
```

---

### Task 3: Catalog field coverage

**Files:**
- Create: `analysis/catalog_profile.py`
- Create: `scripts/analyze_catalog.py`
- Create: `tests/test_catalog_profile.py`

**Interfaces:**
- Consumes: iterable catalog product dictionaries.
- Produces: `profile_catalog(products, fields) -> dict` with row count and per-field present, missing, and coverage values.

- [ ] **Step 1: Write a failing literal-fixture test**

```python
from __future__ import annotations

import unittest

from analysis.catalog_profile import profile_catalog


class CatalogProfileTest(unittest.TestCase):
    def test_profile_catalog_counts_empty_collections_as_missing(self) -> None:
        products = [
            {"title": "Shoe", "features": ["leather"], "details": {}},
            {"title": "Boot", "features": [], "details": {"color": "black"}},
            {"title": "", "features": None, "details": None},
        ]
        self.assertEqual(profile_catalog(products, ("title", "features", "details")), {
            "row_count": 3,
            "fields": {
                "details": {"present": 1, "missing": 2, "coverage": 0.333333},
                "features": {"present": 1, "missing": 2, "coverage": 0.333333},
                "title": {"present": 2, "missing": 1, "coverage": 0.666667},
            },
        })
```

- [ ] **Step 2: Run the test and confirm RED**

```powershell
python -m unittest tests.test_catalog_profile -v
```

Expected: import failure because `analysis.catalog_profile` does not exist.

- [ ] **Step 3: Implement exact presence rules**

A value is present unless it is `None`, an empty string after stripping, or an
empty list/dictionary. Materialize the iterable once, sort field keys, and round
coverage to six decimals.

```python
from __future__ import annotations

from collections.abc import Iterable


def _present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def profile_catalog(products: Iterable[dict], fields: tuple[str, ...]) -> dict:
    rows = list(products)
    result: dict[str, dict] = {}
    for field in sorted(fields):
        present = sum(_present(row.get(field)) for row in rows)
        result[field] = {
            "present": present,
            "missing": len(rows) - present,
            "coverage": 0.0 if not rows else round(present / len(rows), 6),
        }
    return {"row_count": len(rows), "fields": result}
```

- [ ] **Step 4: Add a catalog JSONL CLI**

The CLI accepts `--catalog`, `--output`, and repeatable `--field`; default fields
are `title`, `features`, `description`, `price`, `categories`, `details`,
`average_rating`, `rating_number`, and `store`.

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.catalog_profile import profile_catalog
from evaluator.local_evaluator import load_jsonl


DEFAULT_FIELDS = (
    "title", "features", "description", "price", "categories", "details",
    "average_rating", "rating_number", "store",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--output", default="reports/baseline/catalog-profile.json")
    parser.add_argument("--field", action="append", dest="fields")
    args = parser.parse_args()
    report = profile_catalog(load_jsonl(args.catalog), tuple(args.fields or DEFAULT_FIELDS))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run focused and complete tests**

```powershell
python -m unittest tests.test_catalog_profile -v
python -m unittest discover -s tests -v
```

Expected: 7 tests pass with no failures.

- [ ] **Step 6: Commit catalog profiling**

```powershell
git add analysis/catalog_profile.py scripts/analyze_catalog.py tests/test_catalog_profile.py
git commit -m "feat: profile catalog field coverage"
```

---

### Task 4: Generate and document the verified diagnostic report

**Files:**
- Create: `reports/baseline/bm25-first-turn-recall.json`
- Create: `reports/baseline/catalog-profile.json`
- Create: `reports/baseline/diagnostic-summary.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the two verified analysis CLIs.
- Produces: committed, reproducible evidence and exact rerun commands.

- [ ] **Step 1: Run both diagnostics against official artifacts**

```powershell
python -m scripts.analyze_bm25_recall --output reports/baseline/bm25-first-turn-recall.json
python -m scripts.analyze_catalog --output reports/baseline/catalog-profile.json
```

Expected: both commands exit zero and write valid JSON.

- [ ] **Step 2: Inspect the reports before interpreting them**

```powershell
python -m json.tool reports/baseline/bm25-first-turn-recall.json
python -m json.tool reports/baseline/catalog-profile.json
```

Expected: 200 measured samples, cutoffs 10/50/100/500, four scenarios, and
50,000 catalog rows.

- [ ] **Step 3: Write a concise evidence summary**

`diagnostic-summary.md` must state the measured values, distinguish first-turn
candidate recall from evaluator HitRate@10, and make exactly one evidence-backed
recommendation for the next implementation plan:

- If target recall rises substantially between 10 and 500, prioritize reranking.
- If target recall remains low at 500, prioritize semantic retrieval.
- If clarification fields have low coverage, restrict entropy calculations to
  grounded fields and retain `other` as fallback.

- [ ] **Step 4: Add README commands**

Document the two diagnostic commands under a `Baseline Diagnostics` heading.
Do not copy generated metric values into the README; link to the committed
summary so there is one source of truth.

- [ ] **Step 5: Run final verification**

```powershell
python -m unittest discover -s tests -v
python -m evaluator.local_evaluator
python -m json.tool reports/baseline/bm25-first-turn-recall.json
python -m json.tool reports/baseline/catalog-profile.json
git diff --check
```

Expected: all tests pass, official baseline metrics remain exactly 0.125
HitRate@10, 0.068034 MRR, 9.81 MTTC, and 0.10671 TechnicalScore, JSON is valid,
and `git diff --check` reports no whitespace errors.

- [ ] **Step 6: Commit the verified evidence**

```powershell
git add README.md reports/baseline
git commit -m "docs: record baseline retrieval diagnostics"
```
