"""Replay one public session and print what conversation state did each turn.

This is a diagnostic tool, not an agent method and not part of a submission
bundle. It drives the real `Agent` through the official evaluator's own
simulation functions, so the transcript it prints is the transcript the scorer
would have produced. Nothing here is imported by `starter/`.

    python -m scripts.trace_session --sample public_0052
    python -m scripts.trace_session --sample public_0002 --output trace.json

Read the output as three stacked layers per turn: what the customer said, what
the agent extracted from it, and what survived into state. On an override turn
the keep/drop table names the rule that decided each term.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from analysis.session_trace import (
    TurnTrace,
    is_dead_turn,
    lost_terms,
    override_disposition,
    summarize,
)
from evaluator.local_evaluator import (
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from starter.agent import Agent, _constraint_terms, _is_intent_override
from starter.slots import extract_slots


def trace_session(agent: Agent, sample: dict, catalog_ids: set[str],
                  categories: dict[str, list[str]], products: dict[str, dict]) -> dict:
    """Run one session to completion, capturing state before and after each turn.

    The loop mirrors `evaluator.local_evaluator.evaluate` for a single sample,
    including the rule that a hit before the override turn does not count in an
    intent-override session. Diverging from that loop would make the trace
    disagree with `results.json`, which is the whole point of the tool.
    """
    session_id = str(sample["sample_id"])
    agent.reset(session_id, sample["user_profile"])
    target = str(sample["ground_truth"]["parent_asin"])
    card, behavior = materialize_hidden_fields(sample, products)
    effective = {**sample, "intent_card": card, "behavior": behavior}

    disclosed: set[str] = set()
    boundary_used = False
    override_applied = sample["scenario_type"] != "intent_override"
    message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)

    traces: list[TurnTrace] = []
    previous_terms: list[str] | None = None
    first_hit_turn: int | None = None

    for turn in range(1, MAX_TURNS + 1):
        before_terms = list(agent._session_terms[session_id])
        before_slots = copy.deepcopy(agent._session_slots[session_id])
        is_override = _is_intent_override(message)
        message_slots = extract_slots(message, agent.gazetteer)

        response = agent.respond(session_id, message, turn, TOP_K)

        after_terms = list(agent._session_terms[session_id])
        ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
        target_rank = ranked.index(target) + 1 if target in ranked else None

        record = TurnTrace(
            turn=turn,
            user_message=message,
            is_override=is_override,
            constraint_terms=_constraint_terms(message),
            message_slots={slot: list(terms) for slot, terms in message_slots.items()},
            slots_after=copy.deepcopy(agent._session_slots[session_id]),
            terms_after=after_terms,
            terms_lost=lost_terms(before_terms, after_terms),
            dispositions=(
                override_disposition(before_slots, message_slots) if is_override else []
            ),
            ask_attribute=response.get("ask_attribute"),
            asked_after=sorted(agent._session_asked_attributes[session_id]),
            top_ids=ranked[:5],
            target_rank=target_rank,
            dead=is_dead_turn(previous_terms, after_terms, target_rank),
        )
        traces.append(record)
        previous_terms = after_terms

        if override_applied and target in ranked:
            first_hit_turn = turn
            break
        if turn == MAX_TURNS:
            break

        override = effective.get("behavior", {}).get("override") or {}
        if not override_applied and turn + 1 == int(override.get("turn", 3)):
            override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                disclosed.add(new_value)
            message = str(override.get("message", "Actually, please ignore my earlier preference."))
        else:
            message, boundary_used = customer_reply(
                effective, response.get("ask_attribute"), disclosed, boundary_used
            )

    return {
        "sample_id": sample["sample_id"],
        "scenario_type": sample["scenario_type"],
        "difficulty_bucket": sample.get("difficulty_bucket"),
        "target": target,
        "intent_card": card,
        "behavior": behavior,
        "hit": first_hit_turn is not None,
        "first_hit_turn": first_hit_turn,
        "turns": [record.to_dict() for record in traces],
        "summary": summarize(traces),
    }


def render(trace: dict, products: dict[str, dict]) -> str:
    """Format one trace for a terminal. The JSON payload stays authoritative."""
    target = trace["target"]
    product = products.get(target, {})
    lines = [
        f"SAMPLE   {trace['sample_id']}  |  {trace['scenario_type']}  |  {trace['difficulty_bucket']}",
        f"TARGET   {target}  {str(product.get('title') or '')[:64]}",
        f"         rating_number={product.get('rating_number')}",
        f"CARD     {json.dumps(trace['intent_card'], ensure_ascii=False)}",
    ]
    override = trace["behavior"].get("override")
    if override:
        lines.append(f"OVERRIDE {json.dumps(override, ensure_ascii=False)}")
    lines.append("=" * 96)

    for record in trace["turns"]:
        flag = "  [INTENT OVERRIDE]" if record["is_override"] else ""
        dead = "  [DEAD TURN]" if record["dead"] else ""
        lines.append(f"\n--- TURN {record['turn']}{flag}{dead} " + "-" * 52)
        lines.append(f"USER   {record['user_message']}")
        lines.append(f"  constraint_terms  {record['constraint_terms']}")
        lines.append(f"  message_slots     {json.dumps(record['message_slots'], ensure_ascii=False)}")
        if record["dispositions"]:
            for item in record["dispositions"]:
                verb = "keep" if item["kept"] else "DROP"
                lines.append(
                    f"    {verb}  {item['slot']}.{item['term']} "
                    f"(arrived@{item['arrived']})  {item['reason']}"
                )
        if record["terms_lost"]:
            lines.append(f"  QUERY TERMS LOST  {record['terms_lost']}")
        lines.append("  slots:")
        for slot, terms in sorted(record["slots_after"].items()):
            lines.append(f"      {slot:<12}{json.dumps(terms, ensure_ascii=False)}")
        lines.append(f"  terms ({len(record['terms_after'])}/40)  {record['terms_after']}")
        lines.append(f"  asked             {record['asked_after']}")
        lines.append(f"AGENT  ask_attribute={record['ask_attribute']!r}")
        lines.append(f"  top5              {record['top_ids']}")
        lines.append(f"  TARGET RANK       {record['target_rank']}")

    summary = trace["summary"]
    lines.append("\n" + "=" * 96)
    lines.append(
        f"hit={trace['hit']}  first_hit_turn={trace['first_hit_turn']}  "
        f"best_rank={summary['best_rank']}  dead_turns={summary['dead_turns']}/{summary['turns']}"
    )
    if summary["override_turn"] is not None:
        lines.append(
            f"override turn {summary['override_turn']}: "
            f"rank {summary['rank_before_override']} -> {summary['rank_after_override']}, "
            f"{len(summary['terms_lost_at_override'])} query terms lost"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trace conversation state turn by turn for one public session"
    )
    parser.add_argument("--sample", required=True, help="sample_id, for example public_0052")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--gazetteer", default="data/gazetteer.json")
    parser.add_argument("--output", help="optional path for the JSON trace")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    sample = next(
        (item for item in samples if str(item["sample_id"]) == args.sample), None
    )
    if sample is None:
        raise SystemExit(f"sample_id not found in {args.dataset}: {args.sample}")

    catalog_ids, categories, products = catalog_index(args.catalog)
    agent = Agent(args.catalog, gazetteer_path=args.gazetteer)
    trace = trace_session(agent, sample, catalog_ids, categories, products)
    print(render(trace, products))

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
