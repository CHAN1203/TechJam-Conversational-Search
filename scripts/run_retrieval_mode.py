from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the evaluator with a chosen retrieval_mode")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--retrieval-mode", default="bm25")
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)

    started = time.perf_counter()
    agent = Agent(args.catalog, retrieval_mode=args.retrieval_mode)
    build_seconds = round(time.perf_counter() - started, 3)

    started = time.perf_counter()
    result = evaluate(agent, samples, catalog_ids, categories, products)
    eval_seconds = round(time.perf_counter() - started, 3)

    result["retrieval_mode"] = args.retrieval_mode
    result["build_seconds"] = build_seconds
    result["eval_seconds"] = eval_seconds

    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "sessions"}, indent=2))


if __name__ == "__main__":
    main()
