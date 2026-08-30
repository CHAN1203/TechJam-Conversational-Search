"""Per-turn conversation-state trace for one public session.

The agent keeps two parallel representations of what the customer has said: the
flat ``_session_terms`` list that builds the FTS5 query, and the structured
``_session_slots`` mapping. They are only reconciled at an intent override, and
that reconciliation is destructive. This module records what each turn did to
both so the two can be compared before and after a state-machine change.

Everything here is pure. It reads a snapshot of agent state that the caller
supplies; it never constructs an Agent, opens the catalog, or touches the
evaluator. `scripts/trace_session.py` is the CLI that drives it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field

from starter.agent import DURABLE_SLOTS, OPENING_TURN


# Why an accumulated slot term survived or did not survive an intent override.
# The four reasons mirror the branches in `Agent.respond` exactly; if that logic
# changes, these strings must change with it or the trace becomes a lie.
REPLACED_BY_MESSAGE = "slot_replaced_by_message"
DURABLE_SLOT = "durable_slot"
LEARNED_AFTER_OPENING = "learned_after_opening_turn"
VOLUNTEERED_ON_OPENING = "volunteered_on_opening_turn"


@dataclass(frozen=True)
class SlotDisposition:
    """One accumulated slot term and the override rule that decided its fate."""

    slot: str
    term: str
    arrived: int
    kept: bool
    reason: str


@dataclass
class TurnTrace:
    """Everything one turn did to conversation state."""

    turn: int
    user_message: str
    is_override: bool
    constraint_terms: list[str]
    message_slots: dict[str, list[str]]
    slots_after: dict[str, dict[str, int]]
    terms_after: list[str]
    terms_lost: list[str]
    dispositions: list[SlotDisposition] = field(default_factory=list)
    ask_attribute: str | None = None
    asked_after: list[str] = field(default_factory=list)
    top_ids: list[str] = field(default_factory=list)
    target_rank: int | None = None
    dead: bool = False

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["dispositions"] = [asdict(item) for item in self.dispositions]
        return payload


def override_disposition(
    accumulated_slots: Mapping[str, Mapping[str, int]],
    message_slots: Mapping[str, Sequence[str]],
    durable_slots: Sequence[str] = DURABLE_SLOTS,
    opening_turn: int = OPENING_TURN,
) -> list[SlotDisposition]:
    """Explain, per term, what the override branch keeps and what it drops.

    The rules are checked in the same order the agent checks them. A slot named
    by the override message loses every term it holds, including durable ones,
    because the customer just replaced that slot. Only after that test does
    durability, and then arrival turn, get a chance to save a term.
    """
    durable = set(durable_slots)
    dispositions: list[SlotDisposition] = []
    for slot in sorted(accumulated_slots):
        for term, arrived in accumulated_slots[slot].items():
            if slot in message_slots:
                kept, reason = False, REPLACED_BY_MESSAGE
            elif slot in durable:
                kept, reason = True, DURABLE_SLOT
            elif arrived > opening_turn:
                kept, reason = True, LEARNED_AFTER_OPENING
            else:
                kept, reason = False, VOLUNTEERED_ON_OPENING
            dispositions.append(SlotDisposition(slot, term, arrived, kept, reason))
    return dispositions


def lost_terms(before: Sequence[str], after: Sequence[str]) -> list[str]:
    """Query terms present before the turn and absent after it.

    On a normal turn this is always empty: accumulation is monotonic. A
    non-empty result means the override rebuilt the term list from the slot
    dictionary, so any term the gazetteer could not classify was discarded and
    any surviving term was replaced by its normalized form.
    """
    remaining = set(after)
    return [term for term in before if term not in remaining]


def is_dead_turn(
    previous_terms: Sequence[str] | None,
    terms: Sequence[str],
    target_rank: int | None,
) -> bool:
    """True when the turn could not have changed the ranking.

    Retrieval is a pure function of the accumulated term list, so an unchanged
    list produces an unchanged candidate order. If the target is not already in
    the returned list, the turn spent a question and bought nothing. The first
    turn is never dead because it has no predecessor.
    """
    if previous_terms is None:
        return False
    return list(previous_terms) == list(terms) and target_rank is None


def summarize(turns: Iterable[TurnTrace]) -> dict:
    """Aggregate one session's turns into the numbers worth comparing."""
    ordered = list(turns)
    override_turns = [turn.turn for turn in ordered if turn.is_override]
    ranks = [turn.target_rank for turn in ordered if turn.target_rank is not None]
    override_turn = override_turns[0] if override_turns else None
    rank_before_override = None
    rank_after_override = None
    if override_turn is not None:
        before = [
            turn.target_rank for turn in ordered
            if turn.turn < override_turn and turn.target_rank is not None
        ]
        rank_before_override = before[-1] if before else None
        after = [turn.target_rank for turn in ordered if turn.turn == override_turn]
        rank_after_override = after[0] if after else None
    return {
        "turns": len(ordered),
        "dead_turns": sum(1 for turn in ordered if turn.dead),
        "best_rank": min(ranks) if ranks else None,
        "override_turn": override_turn,
        "rank_before_override": rank_before_override,
        "rank_after_override": rank_after_override,
        "terms_lost_at_override": next(
            (turn.terms_lost for turn in ordered if turn.is_override), []
        ),
    }
