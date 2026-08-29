from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from evaluator.local_evaluator import (
    coarse_category,
    initial_message,
    materialize_hidden_fields,
)


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
        "recall": _recall(
            [record.get("rank") for record in materialized],
            cutoffs,
        ),
        "scenario_recall": {
            name: {
                "sample_count": len(ranks),
                "recall": _recall(ranks, cutoffs),
            }
            for name, ranks in sorted(grouped.items())
        },
    }


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
