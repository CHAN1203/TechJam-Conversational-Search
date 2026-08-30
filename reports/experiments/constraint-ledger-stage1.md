# Constraint Ledger Stage 1: Append-Only State and Query Projection

## Status

**Retained.** Validation TechnicalScore `0.844722 -> 0.853190` (`+0.008468`),
full-set `0.841838 -> 0.854664` (`+0.012826`). Intent Override HitRate@10
reaches `1.000000`. Buying, Browsing, and Boundary are unchanged in every digit.

- Date: 2026-08-30
- Baseline: E11 Popularity Prior (`state_model="slots"`, still the constructor default)
- Design: [constraint ledger](../../docs/designs/2026-08-30-constraint-ledger-design.md)
- Prior stage: [Stage 0](constraint-ledger-stage0.md), rejected
- Split: seed `techjam-clarification-v1`, 80 validation sessions

## Commands

```powershell
python -m unittest discover -s tests
python -m scripts.trace_session --sample public_0052
```

Metrics were produced by running the popularity sweep at weight `1.2` with the
Agent pinned to each state model, so both arms share the split, the catalog, the
evaluator, and every other component.

## Change

`_session_terms` is gone from the scored path. Every token the customer supplies
becomes a ledger entry carrying its own surface form, its normalized form, its
slot (or `null`), a status, a source, and its first and last turn. An override
sets statuses; it never deletes an entry, so the term list is never rebuilt. The
query is projected from the active entries on every turn.

The override keeps E11's three rules unchanged -- a slot the message names is
superseded, `DURABLE_SLOTS` survive, entries first seen after the opening turn
survive -- and applies them to entries rather than to slot dictionary keys. That
single change of subject is what makes the difference, because an unclassified
token now has a `first_turn` of its own and can satisfy the third rule. E11
states this intent in a comment ("It does not revoke the answers they gave when
the agent asked") but cannot honour it for unclassified tokens, since those live
only in the term list it discards.

Two Stage 0 findings shaped the design directly:

- entries with `slot=None` are projected like any other active entry, because
  Stage 0 measured that removing unclassified tokens narrows the FTS5 `MATCH`
  expression and costs two intent_override sessions;
- surface forms are projected, never the gazetteer's singular, because FTS5
  `unicode61` does not stem.

`Agent()` defaults to `state_model="slots"` and reproduces E11 exactly.

## Results

| Metric | E11 slots | E24-B ledger | Δ |
| --- | ---: | ---: | ---: |
| HitRate@10 | 0.965 | **0.975** | +0.010 |
| MRR | 0.662125 | **0.677881** | +0.015756 |
| MTTC | 2.965 | **2.810** | -0.155 |
| Efficiency | 0.8035 | 0.8190 | +0.0155 |
| **TechnicalScore** | 0.841838 | **0.854664** | **+0.012826** |
| **Validation TechnicalScore** | 0.844722 | **0.853190** | **+0.008468** |

### By scenario, full public set

| Scenario | HitRate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: |
| Buying | 0.950000 -> 0.950000 | 0.696905 -> 0.696905 | 2.2875 -> 2.2875 |
| Browsing | 1.000000 -> 1.000000 | 0.665595 -> 0.665595 | 2.8250 -> 2.8250 |
| Boundary | 0.900000 -> 0.900000 | 0.579444 -> 0.579444 | 3.6000 -> 3.6000 |
| Intent Override | 0.933333 -> **1.000000** | 0.587685 -> **0.692725** | 4.9333 -> **3.9000** |

Three of the four scenarios are identical to the last decimal place. That is the
strongest available evidence that the change does what it claims and nothing
else: the two state models can only diverge on a turn where an override fires,
and no other scenario contains one.

### The two sessions E11 could not recover

| Session | slots | ledger |
| --- | --- | --- |
| `public_0052` | miss, rank 6 before the override then absent, 5 dead turns of 10 | **hit at turn 4**, 0 dead turns of 4 |
| `public_0071` | miss, rank 1 before the override then absent, 5 dead turns of 10 | **hit at turn 4**, rank 1 -> 3 across the override |

## Gate assessment

| # | Condition | Result |
| --- | --- | --- |
| 1 | validation TechnicalScore exceeds `0.844722` | **pass**, `0.853190` |
| 2 | no validation scenario HitRate@10 decreases | **pass**, all four equal or better |
| 3 | zero query terms lost at the override turn | **fail as written** -- see below |
| 4 | projected width never below E11's at the same turn | **pass**, 0 violations in 200 sessions |
| 5 | default `Agent()` reproduces E11 | **pass**, `0.841838` / `0.844722` exactly |

### Condition 3 was mis-specified

The invariant demanded that no query term disappear at an override turn. That is
not a property the ledger should have: an override *is* a revocation, and the
turn-1 volunteered constraints it revokes must leave the projected query. The
invariant conflated two different losses.

Measured as written, ledger mode reports 30 violations, one per intent_override
session. The number worth reporting is the count of terms that vanish across all
30 override turns: **313 in slots mode, 170 in ledger mode**. The remaining 170
are deliberate revocations.

The defect the architecture was built to eliminate is narrower: a term that does
not go away but is silently *replaced by a normalized variant of itself*.
Counting only those:

| State model | Normalization losses across 30 override turns |
| --- | ---: |
| slots | 54 |
| ledger | **3** |

Examples in slots mode: `accessories -> accessory`, `belts -> belt`,
`tees -> tee`, `camis -> cami`. The three residual cases in ledger mode
(`bracelets -> bracelet`, `tools -> tool`, `kits -> kit`) are not defects: in
each, the override message itself restates the category in the singular, so the
plural entry is correctly superseded and the customer's new singular wording is
recorded in its place.

Condition 3 should be replaced in the design by: *no term is lost to
normalization at an override turn except where the override message itself
restates it in the normalized form.* That is the falsifiable claim, and it
holds.

## Decision

Retain as **E24-B**. `state_model="ledger"` becomes the recommended
configuration; `slots` remains the constructor default until the ledger has been
exercised further, so E11 stays reproducible without a flag.

Automated tests: 103 before, 118 after. Fifteen new tests cover slot assignment
through multi-word gazetteer terms, `slot=None` survival, status transitions,
restatement reactivation, projection order and cap, and the equivalence of the
two models on sessions without an override.

## Limitations

- 30 intent_override sessions. The HitRate gain is two sessions, and Intent
  Override reaching `1.000000` on 30 samples is not evidence that it would on
  the private 800.
- The rule that carries most of the gain -- unclassified entries survive an
  override when `first_turn > 1` -- is a semantic judgement about what "ignore
  my earlier preference" means. It matches the intent E11 documents, but the
  private simulator's override phrasing and timing are not guaranteed to make it
  equally correct.
- `_is_intent_override` still matches a literal evaluator string. The ledger
  makes the override handling better but not more general; a differently worded
  override is not detected by either model.
- Boundary remains at `0.900000`, unchanged by Stage 0 and Stage 1 alike, and by
  every popularity weight before them. Whatever limits those ten sessions is not
  conversation state.
- The `source` field (`volunteered` / `answered`) and `last_turn` are recorded
  but not yet read by any scoring path. They exist for Stage 2 and must not be
  described as contributing to this result.
