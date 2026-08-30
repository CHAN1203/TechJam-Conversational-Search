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
    # None (the default) means "use Agent's own default weight" -- a fixed
    # numeric default here would silently go stale and override Agent's
    # real default the moment that default changes, as happened once
    # already when E18 changed it from 0.0 to 1.0.
    parser.add_argument("--semantic-weight", type=float, default=None)
    parser.add_argument("--phrase-weight", type=float, default=None)
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)

    agent_kwargs: dict[str, object] = {"retrieval_mode": args.retrieval_mode}
    if args.semantic_weight is not None:
        agent_kwargs["semantic_weight"] = args.semantic_weight
    if args.phrase_weight is not None:
        agent_kwargs["phrase_weight"] = args.phrase_weight

    started = time.perf_counter()
    agent = Agent(args.catalog, **agent_kwargs)
    build_seconds = round(time.perf_counter() - started, 3)

    started = time.perf_counter()
    result = evaluate(agent, samples, catalog_ids, categories, products)
    eval_seconds = round(time.perf_counter() - started, 3)

    result["retrieval_mode"] = args.retrieval_mode
    result["semantic_weight"] = agent.semantic_weight
    result["phrase_weight"] = agent.phrase_weight
    result["build_seconds"] = build_seconds
    result["eval_seconds"] = eval_seconds

    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "sessions"}, indent=2))


if __name__ == "__main__":
    main()
