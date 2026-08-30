"""Append-only constraint ledger and the query projected from it.

E11 keeps two representations of what the customer has said: the flat term list
that builds the FTS5 query, and a slot dictionary. They are reconciled only at
an intent override, destructively, by rebuilding the term list from the slot
dictionary. Terms the gazetteer never classified are lost in that rebuild, and
the terms that survive come back in the gazetteer's singular form, which the
FTS5 tokenizer treats as different words.

The ledger removes the second representation. Every token the customer supplies
becomes an entry, classified or not. An override changes an entry's status; it
never deletes one, so the query never has to be rebuilt and no wording is lost.
The query is projected from the active entries on every turn.

Stage 0 measured that removing unclassified tokens from the query costs two
intent_override sessions, because those tokens widen the FTS5 MATCH expression
and change which candidates enter the pool. Entries with `slot=None` are
therefore first-class here: they carry no slot semantics but they are projected
like any other active entry.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from analysis.gazetteer import normalize_term


ACTIVE = "active"
REVOKED = "revoked"
SUPERSEDED = "superseded"

# Where the constraint came from. This is the only honest basis for weighting
# entries differently: extraction itself is deterministic gazetteer matching,
# so a per-term confidence would be 1.0 for every entry.
VOLUNTEERED = "volunteered"
ANSWERED = "answered"

# How firmly the customer stated a constraint, when they said so explicitly.
# UNKNOWN is the default and the safe one: a ledger where nothing is marked
# HARD behaves exactly as it did before this field existed.
HARD = "hard"
UNKNOWN = "unknown"
# Recorded but not scored. Weighting entries by source was measured and
# rejected (E13-C1: the validation optimum was the off position), and the
# weighting hook was dropped when the reranker was restructured upstream.
# The field stays because it is the one honest basis for such a weighting if
# a later experiment finds a use for it.

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass
class Entry:
    """One thing the customer said, and what has happened to it since."""

    surface: str
    normalized: str
    slot: str | None
    status: str = ACTIVE
    source: str = VOLUNTEERED
    strength: str = UNKNOWN
    first_turn: int = 1
    last_turn: int = 1


def assign_slots(
    tokens: Sequence[str],
    message_slots: Mapping[str, Sequence[str]],
) -> dict[str, str]:
    """Map each message token to the slot whose matched term contains it.

    `extract_slots` reports slots as normalized, sometimes multi-word terms
    ("belt buckle"). The ledger stores one entry per token, so each slot term is
    split back into tokens and matched against the customer's own wording
    through the same normalization.
    """
    assigned: dict[str, str] = {}
    for slot, terms in message_slots.items():
        wanted = {
            piece
            for term in terms
            for piece in TOKEN_RE.findall(str(term).lower())
        }
        for token in tokens:
            if normalize_term(token) in wanted:
                assigned.setdefault(token, slot)
    return assigned


class ConstraintLedger:
    """Insertion-ordered entries keyed by the customer's own surface form."""

    def __init__(self) -> None:
        self._entries: dict[str, Entry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def entries(self) -> list[Entry]:
        return list(self._entries.values())

    def record(
        self,
        tokens: Sequence[str],
        token_slots: Mapping[str, str],
        turn: int,
        source: str,
        strength: str = UNKNOWN,
    ) -> int:
        """Add new entries and refresh the ones the customer restated.

        Restating a revoked constraint makes it active again: the customer just
        said it, which is stronger evidence than an earlier override. A token
        first seen without a slot can acquire one later, when a longer gazetteer
        match in a later message classifies it.
        """
        gained = 0
        for token in tokens:
            entry = self._entries.get(token)
            if entry is None:
                gained += 1
                self._entries[token] = Entry(
                    surface=token,
                    normalized=normalize_term(token),
                    slot=token_slots.get(token),
                    status=ACTIVE,
                    source=source,
                    strength=strength,
                    first_turn=turn,
                    last_turn=turn,
                )
                continue
            if entry.status != ACTIVE:
                gained += 1
            entry.last_turn = turn
            entry.status = ACTIVE
            if strength == HARD:
                # Restating something as a requirement upgrades it; a later
                # unmarked mention never downgrades it back.
                entry.strength = HARD
            if entry.slot is None and token in token_slots:
                entry.slot = token_slots[token]
        return gained

    def apply_override(
        self,
        message_slots: Mapping[str, Sequence[str]],
        durable_slots: Sequence[str],
        opening_turn: int,
    ) -> None:
        """Revoke what the override revokes, keeping E11's three rules.

        A slot the override message names is superseded outright, including its
        durable terms, because the customer replaced it. Durable slots survive.
        Anything learned after the opening turn survives: an override revokes
        what the customer volunteered up front, not the answers they gave when
        the agent asked. E11 states that intent in a comment but cannot honour
        it for unclassified tokens, because those live only in the term list it
        throws away.
        """
        durable = set(durable_slots)
        for entry in self._entries.values():
            if entry.status != ACTIVE:
                continue
            if entry.slot is not None and entry.slot in message_slots:
                entry.status = SUPERSEDED
            elif entry.slot in durable:
                continue
            elif entry.first_turn > opening_turn:
                continue
            else:
                entry.status = REVOKED

    def project(self, limit: int) -> list[str]:
        """The FTS5 query terms: active entries, in the order first stated."""
        return [
            entry.surface
            for entry in self._entries.values()
            if entry.status == ACTIVE
        ][:limit]

    def hard_surfaces(self) -> set[str]:
        """Active entries the customer explicitly stated as requirements.

        Empty whenever nothing was marked, which is what makes the caller's
        fallback the pre-existing behaviour rather than a new one.
        """
        return {
            entry.surface
            for entry in self._entries.values()
            if entry.status == ACTIVE and entry.strength == HARD
        }

    def slots_view(self) -> dict[str, dict[str, int]]:
        """Active slotted entries in the shape the slot-based agent reports.

        Observability only. It lets one tracer read either state model.
        """
        view: dict[str, dict[str, int]] = {}
        for entry in self._entries.values():
            if entry.status != ACTIVE or entry.slot is None:
                continue
            view.setdefault(entry.slot, {})[entry.surface] = entry.first_turn
        return view
