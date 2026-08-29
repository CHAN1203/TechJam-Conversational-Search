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
    parser.add_argument(
        "--output",
        default="reports/baseline/bm25-first-turn-recall.json",
    )
    parser.add_argument(
        "--cutoffs",
        nargs="+",
        type=int,
        default=[10, 50, 100, 500],
    )
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
