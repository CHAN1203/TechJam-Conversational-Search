# Constraint Ledger Conversation State Experiment Design

## Status

Drafted 2026-08-30. Proposed as **E13**, after E12 MiniLM + Fixed-RRF Hybrid
Retrieval, which already holds the E12 identifier. The "Relationship to E12"
section argues for running this experiment first; that reordering is a decision
for the project owner and is not assumed anywhere else in this document.

## Goal

Replace the agent's two parallel, separately-maintained representations of what
the customer has said with one append-only constraint ledger, and derive the
retrieval query from that ledger every turn instead of patching a flat term list
in place.

The experiment is staged so that correctness fixes are measured before the
architecture change, and so that the architecture change cannot be credited with
gains that belong to the fixes.

## Current Baseline

E11 Popularity Prior is the retained method:

- candidate-aware clarification;
- slot-aware intent-override memory;
- BM25 Top-100 candidate generation, no IDF;
- field reranker with popularity weight `1.2`;
- official full-set HitRate@10 `0.965`, MRR `0.662125`, MTTC `2.965`,
  TechnicalScore `0.841838`;
- official fixed-split validation TechnicalScore `0.844722`.

## Measured Evidence

All numbers below were produced by replaying the 200 public sessions through the
unmodified E11 agent and the official evaluator loop, using
`python -m scripts.trace_session` and the same replay logic aggregated over every
sample. They describe the current implementation; they are not projections.

### The override destroys ranking that retrieval had already earned

| Measurement | Value |
| --- | ---: |
| intent_override sessions with the target in Top-10 **before** the override | 26 / 30 |
| of those, target **lost** from Top-10 at the override turn | 6 |
| of those, target kept but rank degraded (`1 -> 9`, `1 -> 6`, `2 -> 8`, ...) | frequent |
| intent_override sessions that finally missed and had seen the target earlier | 2 |

`public_0052` is the clearest case: rank 6 at turns 1 and 2, absent from the
Top-10 from turn 3 onward, final miss.

### A quarter of all turns cannot change the ranking

| Measurement | Value |
| --- | ---: |
| turns where the accumulated term list was unchanged and the target was unranked | 163 / 586 |

Retrieval is a pure function of the accumulated term list, so an unchanged list
returns an unchanged candidate order. Those turns spent a clarification question
and bought nothing.

### Five defects behind those numbers

1. **Destructive rebuild.** On an override, `_session_terms` is discarded and
   rebuilt from `_session_slots`. Terms the gazetteer never classified vanish,
   and surviving terms are replaced by their normalized form: `tees` becomes
   `tee`. FTS5 `unicode61` does not stem, so this silently changes what the
   query matches.
2. **Override filler enters the query permanently.** `actually`, `ignore`,
   `earlier`, `preference`, `what`, `need` are tokenized from the override
   sentence and never removed.
3. **The negation guard protects only one representation.** `_constraint_terms`
   returns `[]` for a no-preference reply, but `extract_slots` still runs, so
   `"I don't have an additional preference for use_case"` files `case` under
   `category`.
4. **Arrival turn is frozen.** `setdefault` records first arrival, so a
   constraint restated at turn 10 still reports `arrived=3` and cannot be
   distinguished from a stale one.
5. **Pollution lands in the one protected slot.** `button` and `case` are filed
   as `category`, which `DURABLE_SLOTS` preserves across every override.

Defects 1-5 share one cause: the query representation and the structured
representation are reconciled only at override time, destructively, through a
lossy vocabulary.

## Relationship to E12

E12's Gate 1 asks whether hybrid retrieval raises first-turn candidate
Recall@100 from `0.525` to at least `0.555`. The measurements above show that on
the scenario E12 most plausibly helps, 26 of 30 targets are already inside the
scored Top-10 before the override. The failure being measured is not "the target
was never retrieved" but "the target was retrieved and then discarded by state
handling". That does not invalidate E12, and dense retrieval may still help
Browsing and Boundary. It does mean E12's expected value on Intent Override is
lower than the design assumed, and that this experiment addresses a defect E12
cannot reach.

## Non-Goals

- Do not change the official evaluator, catalog, public labels, fixed split,
  seed, or scoring rules.
- Do not introduce an LLM, an external API, or any network dependency.
- Do not claim a time-decay effect without evidence. See "Decay" below.
- Do not fabricate confidence values. See "Confidence" below.
- Do not change retrieval, the field reranker, the popularity weight, or the
  clarification policy in Stage 0 or Stage 1.
- Do not read `ground_truth`, `public_set`, `intent_card`, or evaluator-only
  behavior fields from any module under `starter/`.
- Do not use coverage-stress results to choose a method.

### Decay

The design records `first_turn` and `last_turn` per entry and exposes a
`freshness` term in the weight function, defaulting to `lambda = 0` (no decay).
It is not tuned or claimed in this experiment. MTTC is `2.965`, sessions are
capped at 10 turns, and the simulator has no mechanism by which a preference
weakens gradually: constraints are revoked by a single override message or not
at all. There is no signal in the public set from which to fit a decay rate, and
a report that claims one would not survive review.

### Confidence

Extraction is deterministic whole-word gazetteer matching, so a per-term
confidence would be `1.0` for every entry. The design instead records a
`source` field with three observable values -- `volunteered` (stated
unprompted), `answered` (given in reply to a specific asked attribute), and
`profile` (inferred from `user_profile.preference_tags`) -- and derives a prior
from that. This is defensible from the transcript alone. A numeric confidence
that is not derived from an observable difference must not be added.

## Chosen Approach

### Stage 0: correctness fixes on the existing structure (E13-A) -- MEASURED, REJECTED

Run on 2026-08-30. Result: rejected as specified. Of the three fixes, one
regressed validation by `-0.001198`, one by `-0.007573`, and one was exactly
score-neutral and was retained on correctness grounds. Full ablation and
interpretation: [Stage 0 report](../../reports/experiments/constraint-ledger-stage0.md).

The load-bearing finding is that removing conversational filler from the query
*costs* two intent_override sessions. Those terms widen the FTS5 `MATCH`
expression and therefore change which hundred documents enter the candidate
pool; they contribute nothing in the reranker. The pipeline depends on query
width, not query cleanliness. Stage 1 must not narrow the query -- see
"Stage 1 gate" below, which gained a width invariant as a result.

The original Stage 0 specification follows, unchanged, for the record.

No new data structure. Fix defects 1-5 in place:

- preserve the original surface form when the override rebuilds the term list;
- add the override sentence's own function words to `STOPWORDS`;
- apply the no-preference guard to `extract_slots` as well as
  `_constraint_terms`;
- record last-seen turn alongside first-seen turn.

Stage 0 exists so that Stage 1 has a clean baseline. The project has already
mis-attributed a gain once: E5 and E6 were credited to slot-aware memory logic,
and T14 later showed the gain belonged to the gazetteer contamination fix.
Running Stage 0 and Stage 1 together would repeat that error.

### Stage 1: the constraint ledger and query projection (E13-B) -- MEASURED, RETAINED

Run on 2026-08-30. Validation `0.844722 -> 0.853190`, full `0.841838 ->
0.854664`, Intent Override HitRate@10 `0.933333 -> 1.000000`, with Buying,
Browsing and Boundary identical to the last decimal. Report:
[Stage 1](../../reports/experiments/constraint-ledger-stage1.md).

Gate condition 3 was mis-specified and is corrected below. The specification
that follows is otherwise as written before the run.

Delete `_session_terms`. The ledger becomes the single source of truth, and the
query is projected from it on every turn:

```python
def project_query(ledger, turn):
    return [(entry.surface, weight(entry, turn))
            for entry in ledger if entry.status == "active"]
```

Entry schema:

| Field | Meaning |
| --- | --- |
| `surface` | the customer's original token, used verbatim for FTS5 |
| `normalized` | the gazetteer key, used only for slot identity and conflict tests |
| `slot` | the assigned slot, or `null` when the gazetteer does not classify it |
| `status` | `active`, `revoked`, or `superseded` |
| `source` | `volunteered`, `answered`, or `profile` |
| `first_turn`, `last_turn` | arrival and most recent restatement |

An override sets `status` rather than deleting the entry. Because nothing is
deleted, the term list never has to be rebuilt, and defect 1 becomes structurally
impossible rather than merely fixed. Unclassified terms survive an override with
`slot: null`, which the current implementation cannot represent.

The override rules keep E11's semantics exactly: a slot named by the override
message is superseded, `DURABLE_SLOTS` survive, and entries with
`first_turn > 1` survive. Only the representation changes.

### Stage 2: weighted projection and an information-gain stop (E13-C) -- MEASURED, SPLIT

Run on 2026-08-30. Term weighting by source is **rejected**: validation peaks at
`answered_weight = 1.0`, the off position, with both neighbours below it. The
information-gain probe is **retained** at threshold 1: validation `0.853190 ->
0.867378`, full `0.854664 -> 0.868714`, and Boundary moves off `0.900000` for
the first time in the project. Report:
[Stage 2](../../reports/experiments/constraint-ledger-stage2.md).

The `brand` sub-question below resolved as the design hoped: no exclusion list
was added. `brand` is now skipped in practice because asking it produces no new
ledger entry, and the probe reacts to that observation rather than to knowledge
of the evaluator's internals.

The specification that follows is as written before the run.

Conditional on Stage 1 being retained. Pass per-term weights into
`rerank_candidates`, which currently treats every query term identically -- the
weight dimension is unused, and E8's IDF attempt to fill it was rejected.

Add a convergence signal: if a turn adds no new `active` entry, the ledger
records no information gain. Two consecutive such turns mean the clarification
policy is not converging. This is the observable that the problem statement's
"Over-Generality -> proactive clarification" pillar asks for, and the current
agent has no way to compute it.

A separate sub-question, to be decided before implementation: `brand` is in
`DEFAULT_ATTRIBUTE_ORDER` but `classify_constraint` can never return it, so
asking it is always a dead turn. Removing it justified by reading the
evaluator's source is simulator overfitting. Removing it justified by the
agent's own observation that an asked attribute returned no new entry is a
general mechanism that happens to also fix this case. Only the second
justification is acceptable, and it belongs to the information-gain work, not to
a hardcoded exclusion list.

## Component Boundaries

### `starter/ledger.py`

Pure ledger primitives: entry construction, status transitions, override
application, and query projection. No SQLite, no evaluator import, no file IO.

### `starter/agent.py`

Holds one ledger per session and calls `project_query` before building the FTS5
expression. Constructor gains `state_model="slots" | "ledger"`, defaulting to
`slots`, so E11 remains reproducible byte-for-byte from the default path.

### `analysis/session_trace.py` and `scripts/trace_session.py`

Already implemented. Provide the before/after instrument for every stage,
including the structural invariant Stage 1 must satisfy.

## Experiment Contracts

All stages use the official catalog, all 200 public sessions, the unmodified
evaluator, and seed `techjam-clarification-v1` with the 80-session validation
split. Selection is on validation TechnicalScore only; the full 200 sessions are
run afterward for historical reporting.

### Stage 0 gate

These are correctness fixes, so the bar is non-regression rather than
improvement:

1. validation TechnicalScore is at least E11's `0.844722`;
2. no validation scenario HitRate@10 decreases;
3. the full suite passes, with a targeted test per defect that fails before the
   fix for the stated reason.

A neutral result is recorded as neutral and retained anyway, with the
justification stated as correctness. A regression means the fix is wrong or the
behavior it removed was load-bearing; investigate before proceeding.

### Stage 1 gate

Both a score gate and a mechanism gate must pass:

1. validation TechnicalScore exceeds Stage 0's retained value;
2. no validation scenario HitRate@10 decreases;
3. **structural invariant, loss:** across all 30 intent_override sessions, no
   term is lost to normalization at the override turn, except where the
   override message itself restates that term in its normalized form.

   The original wording demanded zero query terms lost, which the ledger should
   not satisfy: an override is a revocation, and the constraints it revokes must
   leave the query. Measured on the corrected definition, normalization losses
   fall from 54 in slots mode to 3 in ledger mode, and all three residuals are
   the licensed case. Measured on the original wording the run reports 30
   violations, one per session, all of them deliberate revocations;
4. **structural invariant, width:** at every turn the projected query contains
   at least as many distinct terms as E11's accumulated list at the same turn.
   Added after Stage 0 measured a `-0.005448` validation regression caused
   purely by narrowing the query;
5. the default `Agent()` path reproduces E11 exactly.

Conditions 3 and 4 are the falsifiable claims the architecture makes. If the score gate
passes but condition 3 fails, the ledger is not doing what it was designed to do
and the score gain has another cause.

### Stage 2 gate

1. validation TechnicalScore exceeds Stage 1's retained value;
2. no validation scenario HitRate@10 decreases;
3. the information-gain signal is shown to fire on the sessions the tracer marks
   as containing dead turns, and not on sessions without them.

## Expected Effect

An upper bound, derived by assuming the override preserves the pre-override rank
in all 26 sessions where the target was already ranked. It is a ceiling, not a
prediction, and the true value will be lower.

| Metric | E11 | Upper bound |
| --- | ---: | ---: |
| intent_override HitRate@10 | 0.9333 | 1.0000 |
| intent_override MRR | 0.587685 | ~0.72 |
| intent_override MTTC | 4.933 | ~3.5 (the override turn is a hard floor) |
| TechnicalScore | 0.841838 | ~0.857 |

About `+0.015`, comparable to T14's `+0.014`. The case for the work is not the
size of the gain; it is that the gain is a defect repair with low private-set
generalization risk, and that the resulting state model is the one the problem
statement's Dialog Strategy and Self-Evolution pillars describe.

## Testing

Tests must not require the 50,000-product catalog or network access. Use small
catalogs and temporary gazetteers, as `tests/test_session_trace.py` does.

Required coverage:

- one targeted test per Stage 0 defect, red before the fix;
- ledger status transitions, including supersede-then-restate;
- projection excludes non-active entries and preserves surface forms;
- override application preserves E11 semantics slot for slot;
- unclassified terms survive an override with `slot: null`;
- `Agent()` default remains byte-identical to E11 behavior;
- `state_model="ledger"` changes only query construction;
- the structural invariant check over the tracer output;
- the full regression suite before and after each stage.

## Evidence and Documentation

Each stage produces a JSON result and a Markdown report under
`reports/experiments/`, plus its own method-matrix row and chronological entry in
`docs/experiment_history.md`, including if rejected. Reports state commands,
catalog hash, test counts, overall and scenario metrics, gate outcomes,
limitations, and branch or commit. English is tracked; Chinese mirrors stay
ignored.

## Failure Handling and Interpretation

- A Stage 0 regression blocks Stage 1. Do not proceed by skipping it.
- If Stage 1 passes the score gate but fails the structural invariant, record
  the score but do not claim the mechanism.
- If Stage 1 is score-neutral and passes the invariant, that is a legitimate
  outcome: the architecture is defensible on correctness and on the Stage 2
  capability it unlocks, and the report should say the score did not move rather
  than searching for a favorable framing.
- The 200 public sessions contain only 30 intent_override cases. Six sessions
  drive most of the measured effect. Public-set gains do not guarantee
  private-set gains.
- Boundary sits at `0.9000` across every popularity weight and is unchanged by
  everything measured here. It is limited by something this experiment does not
  address.
