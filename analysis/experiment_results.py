from __future__ import annotations

from collections import defaultdict

from evaluator.local_evaluator import metric_summary


CORE_METRICS = (
    "hit_rate_at_10", "mrr", "mttc", "efficiency",
    "recommended_technical_score",
)


def summary_delta(official: dict, stress: dict) -> dict[str, float]:
    return {
        metric: round(float(stress[metric]) - float(official[metric]), 6)
        for metric in CORE_METRICS
        if metric in official and metric in stress
        and official[metric] is not None and stress[metric] is not None
    }


def summarize_sessions(sessions: list[dict]) -> dict:
    overall = metric_summary(sessions)
    mttc = overall["mttc"]
    efficiency = 0.0 if mttc is None else max(0.0, min(1.0, (11.0 - float(mttc)) / 10.0))
    technical_score = (
        0.50 * overall["hit_rate_at_10"]
        + 0.30 * overall["mrr"]
        + 0.20 * efficiency
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for session in sessions:
        grouped[str(session["scenario_type"])].append(session)
    return {
        **overall,
        "efficiency": round(efficiency, 6),
        "recommended_technical_score": round(technical_score, 6),
        "scenario_metrics": {
            name: metric_summary(grouped[name])
            for name in sorted(grouped)
        },
    }
