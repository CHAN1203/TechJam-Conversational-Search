from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.query_stress import STRESS_LEVELS, StressAgent
from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


def run_query_stress(
    catalog_path: str | Path,
    samples: list[dict],
    modes: tuple[str, ...] = ("bm25",),
) -> dict:
    """Score every retrieval mode under every query-stress level.

    One agent is built per mode-set and its `retrieval_mode` mutated between
    runs; neither the FTS5 index nor the dense index depends on it.

    Args:
        catalog_path: Frozen catalog to index.
        samples: Public-set sessions.
        modes: Retrieval modes to compare.

    Returns:
        `{level: {mode: metrics}}`, metrics excluding per-session detail.
    """
    catalog_ids, categories, products = catalog_index(catalog_path)
    # "union" builds the dense index, so one agent serves every mode.
    agent = Agent(catalog_path, retrieval_mode="union")
    results: dict[str, dict] = {}
    for level, transform in STRESS_LEVELS.items():
        results[level] = {}
        for mode in modes:
            agent.retrieval_mode = mode
            result = evaluate(
                StressAgent(agent, transform), samples, catalog_ids, categories, products
            )
            results[level][mode] = {
                key: value for key, value in result.items() if key != "sessions"
            }
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Query-side paraphrase stress diagnostic")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--modes", default="bm25,union,dense")
    parser.add_argument("--output", default="reports/experiments/query-stress.json")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    modes = tuple(mode.strip() for mode in args.modes.split(",") if mode.strip())
    results = run_query_stress(args.catalog, samples, modes)
    Path(args.output).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for level, by_mode in results.items():
        for mode, metrics in by_mode.items():
            print(
                f"{level:18s} {mode:6s} "
                f"score={metrics['recommended_technical_score']:.6f} "
                f"hit={metrics['hit_rate_at_10']:.3f} mrr={metrics['mrr']:.6f}"
            )


if __name__ == "__main__":
    main()
