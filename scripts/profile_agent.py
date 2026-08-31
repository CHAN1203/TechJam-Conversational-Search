from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


class _Timed:
    """Records per-turn wall time and peak RSS without altering behaviour."""

    def __init__(self, agent: object, sample_rss) -> None:
        self.agent = agent
        self._sample_rss = sample_rss
        self.latencies_ms: list[float] = []
        self.peak_rss_mb = sample_rss()

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.agent.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        start = time.perf_counter()
        response = self.agent.respond(session_id, user_message, turn, top_k)
        self.latencies_ms.append((time.perf_counter() - start) * 1000.0)
        self.peak_rss_mb = max(self.peak_rss_mb, self._sample_rss())
        return response


def _rss_sampler():
    """Return a callable giving current RSS in MB, or None if unavailable.

    psutil is a development convenience, not a submission dependency, so its
    absence degrades the report rather than failing the run.
    """
    try:
        import psutil
    except ImportError:
        return None
    process = psutil.Process(os.getpid())
    return lambda: process.memory_info().rss / (1024 * 1024)


def profile(catalog_path: str | Path, dataset_path: str | Path) -> dict:
    """Measure construction cost, per-turn latency and peak memory.

    These are the feasibility figures `docs/submission_rules.md` requires the
    submission to disclose.

    Args:
        catalog_path: Frozen catalog to index.
        dataset_path: Public-set sessions to replay.

    Returns:
        A JSON-serialisable report. Memory fields are `None` without psutil.
    """
    sample_rss = _rss_sampler()
    if sample_rss is None:
        sample_rss = lambda: 0.0
        memory_available = False
    else:
        memory_available = True

    baseline_rss = sample_rss()
    samples = load_jsonl(dataset_path)
    catalog_ids, categories, products = catalog_index(catalog_path)

    start = time.perf_counter()
    agent = Agent(catalog_path)
    construction_seconds = time.perf_counter() - start

    timed = _Timed(agent, sample_rss)
    start = time.perf_counter()
    result = evaluate(timed, samples, catalog_ids, categories, products)
    evaluation_seconds = time.perf_counter() - start

    latencies = sorted(timed.latencies_ms)

    def percentile(fraction: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * fraction))]

    return {
        "python_version": ".".join(str(part) for part in os.sys.version_info[:3]),
        "sessions": len(samples),
        "turns_measured": len(latencies),
        "construction_seconds": round(construction_seconds, 2),
        "evaluation_seconds": round(evaluation_seconds, 1),
        "projected_800_session_seconds": round(evaluation_seconds * 4 + construction_seconds, 1),
        "latency_ms": {
            "mean": round(statistics.fmean(latencies), 1),
            "median": round(statistics.median(latencies), 1),
            "p95": round(percentile(0.95), 1),
            "p99": round(percentile(0.99), 1),
            "max": round(latencies[-1], 1),
        },
        "memory_mb": {
            "baseline_rss": round(baseline_rss, 1),
            "peak_rss": round(timed.peak_rss_mb, 1),
            "agent_attributable": round(timed.peak_rss_mb - baseline_rss, 1),
        } if memory_available else None,
        "reported_token_usage": result["reported_token_usage"],
        "technical_score": result["recommended_technical_score"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Latency and memory profile of the agent")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="reports/experiments/resource-profile.json")
    args = parser.parse_args()

    report = profile(args.catalog, args.dataset)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
