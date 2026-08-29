# Phrase-Independent Intent Override

Date: 2026-08-29
Status: **rejected as the default** (kept on `review/phrase-independent-override-implementation` for future reconsideration; see Root Cause and Decision below).

## Hypothesis

Intent Override is currently detected by `_is_intent_override()` matching one
literal sentence: the message must start with "actually" and contain "ignore
my earlier preference" -- the exact wording the local simulator's
`behavior_for()` generates. If a customer's real "change of mind" message is
phrased any other way, the agent will not clear the old slot value, and the
old and new preferences will both stay in the search query, diluting it.

The agent already computes, every turn, which gazetteer slot each message's
words belong to (`starter/slots.py`) and what is already on record for that
slot (`self._session_slots`). That is enough information to detect a change
of mind structurally: if a message supplies a new term for a slot that
already holds a *different* term, the customer has changed that preference,
regardless of the sentence they used to say it.

Hypothesis: broadening the override *trigger* from "matches one literal
sentence" to "matches the literal sentence OR conflicts with an
already-recorded slot value" will make Intent Override handling robust to
paraphrasing, without changing the override *mechanism* (which is already
implemented and validated by E5/E9), and without regressing the current
best score.

## Change from the last retained method (E11, TechnicalScore 0.841838)

- `starter/agent.py`: `_is_intent_override()` gains a second, independent
  path to `True` -- a same-slot conflict -- in addition to the existing
  literal-phrase check. The literal-phrase check is kept, not removed: it is
  strictly weaker than the new check (every message it catches also has a
  slot conflict, since the simulator's override message always restates the
  new value), so keeping it costs nothing and preserves a fallback if slot
  extraction ever misses a term.
- Nothing else changes: retrieval, ranking, popularity weight, clarification
  policy, and the override *mechanism* itself (which slots survive, which are
  cleared) are all untouched.

## Baseline

E11 Popularity Prior, `TechnicalScore 0.841838`, `HitRate@10 0.965`, on the
full 200-session public set, catalog `data/catalog.jsonl` (hard-linked from
the stable worktree).

## Keep/reject threshold

Keep if the full public-set `TechnicalScore` does not drop below `0.841838`
and Intent Override `HitRate@10` does not drop below `0.933333` (E11's
value). A change that only helps against paraphrasing the public set cannot
prove itself, since the public simulator only ever uses the one literal
sentence -- so the bar here is "does not regress", not "improves", and the
real payoff is robustness the public set cannot measure.

## Tests that will prove the behavior

1. A message that changes a slot's value *without* the literal "actually,
   ignore my earlier preference" phrase must still be treated as an
   override (slot replaced, not accumulated).
2. The literal-phrase path must keep working exactly as before (no
   regression on the existing override tests).
3. A message that repeats the *same* value for an already-known slot must
   **not** be treated as an override (no false positive from restating an
   unchanged preference).
4. A message that introduces a slot with no prior value must not be treated
   as an override (that is normal accumulation, not a change of mind).

## Known risks

- A customer mentioning a second, additional preference in the same slot
  category by coincidence (not actually replacing the first) could be
  misread as an override. Scoped to non-durable slots only
  (`DURABLE_SLOTS = ("category", "department")` are exempt, matching the
  existing exemption) to limit this to genuine preference attributes.
- Scenario-specific regression risk is concentrated in Browsing and Buying,
  where a slot could coincidentally be "corrected" mid-conversation without
  it being a real override (e.g. the agent mis-extracts a slot on turn 1,
  and turn 2's clarification answer looks like a conflict). The full
  evaluator run below checks this directly.

## Implementation

`starter/agent.py`: `_is_intent_override()` gains a second path to `True` --
a conflict between an already-recorded, non-durable slot value and a new
term supplied for that same slot -- alongside the existing literal-phrase
check (kept, not removed, since it is strictly weaker: every message it
catches also has a slot conflict).

```python
def _is_intent_override(message, message_slots=None, accumulated_slots=None):
    ...
    if lowered.startswith("actually") and "ignore my earlier preference" in lowered:
        return True
    if message_slots and accumulated_slots:
        for slot, new_terms in message_slots.items():
            if slot in DURABLE_SLOTS:
                continue
            existing = accumulated_slots.get(slot)
            if existing and not (set(new_terms) & set(existing)):
                return True
    return False
```

Four new tests added to `tests/test_conversation_state.py`
(`PhraseIndependentOverrideTest`), all red-green verified individually:

1. `test_paraphrased_change_of_mind_drops_the_revoked_value` -- new behavior.
2. `test_repeating_the_same_value_is_not_a_false_override` -- guards against
   restating an unchanged preference wiping an unrelated slot.
3. `test_a_brand_new_slot_is_not_a_false_override` -- guards ordinary
   Information Accumulation from being misread as Intent Override.
4. `test_literal_override_phrase_still_works` -- regression guard on the
   existing, already-validated path.

All four passed after implementation; 77/77 project tests passed
(`python -m unittest discover -s tests -v`).

## Result

| Metric | E11 (baseline) | This experiment | Δ |
| --- | ---: | ---: | ---: |
| HitRate@10 | 0.965 | 0.960 | -0.005 |
| MRR | 0.662125 | 0.661292 | -0.000833 |
| MTTC | 2.965 | 3.005 | +0.040 |
| Efficiency | 0.8035 | 0.7995 | -0.0040 |
| TechnicalScore | **0.841838** | 0.838288 | **-0.003550** |

| Scenario | E11 | This experiment |
| --- | ---: | ---: |
| Buying | 0.9500 | 0.9500 |
| Browsing | **1.0000** | 0.9875 |
| Intent Override | 0.933333 | 0.933333 |
| Boundary | 0.9000 | 0.9000 |

One Browsing session (`public_0172`) flips from a hit (rank 6, turn 3) to a
miss. Intent Override itself does not move -- expected and predicted in the
hypothesis: the public simulator only ever phrases an override one way, so
it cannot reward robustness to other phrasings, only penalize any collateral
damage the broader trigger causes elsewhere.

## Root cause of the regression (traced, not guessed)

Replayed `public_0172` turn by turn (`starter/agent.py` unmodified vs. this
change, same inputs):

- Turn 1: category slot fills with `shoe`, `fashion sneaker` (durable).
- Turn 2: the agent asks about `feature`; the customer discloses "Synthetic
  sole" -- and the gazetteer maps the word `synthetic` into the **material**
  slot (a legitimate mining result: "synthetic" is a real material term),
  even though the simulator disclosed it as a `feature` answer, not a
  `material` answer. `material` slot: `{"synthetic": 2}`.
- Turn 3: the agent asks about `material`; the customer discloses "cotton;
  100% Cotton". `message_slots = {"material": ["cotton"]}`. Existing
  material slot is `{"synthetic": 2}`. `{"cotton"} & {"synthetic"}` is
  empty, so the new trigger fires: this is scored as an override.
- The override mechanism (already validated, unchanged) then does exactly
  what it is designed to do: it replaces the material slot's contents
  entirely rather than adding to them. `synthetic` is dropped; the search
  loses that word for the rest of the conversation. The baseline (material
  slot allowed to hold both `synthetic` and `cotton` at once) still had
  `synthetic` in the query at turn 3 and found the target at rank 6;  this
  version does not.

This is **not** a bug in the sense of code failing to match its rule -- the
code does exactly what `_is_intent_override()` says. It is a **design
weakness**: the rule assumes a gazetteer slot holds one value that a
customer either keeps or replaces, but `material` here legitimately
accumulates two independent, non-conflicting facts across two different
clarifying questions ("synthetic sole" and "cotton [upper]") before any
real change of mind ever happens. A single shoe can genuinely have both. The
generalized trigger cannot tell "this is a new value for the same question"
apart from "this is an answer to a different question that happens to share
a gazetteer slot."

## Decision

**Reject as the default.** The pre-registered threshold (full-set
`TechnicalScore` must not drop below `0.841838`) is not met. The measured
cost (-0.00355 TechnicalScore, one Browsing session) is small, and the
benefit (robustness to a differently-worded override on the private set) is
real but unmeasurable on this public set -- so this is a judgment call about
risk tolerance, not a clear-cut technical rejection, and is left to the
project owner rather than decided unilaterally here.

Preserved on `review/phrase-independent-override-implementation` for
reconsideration. A narrower version worth trying later: only trust the
generalized trigger when the conflicting slot is the one the agent's
*previous* `ask_attribute` was actually about, rather than any accumulated
slot -- which would have prevented this exact false positive (turn 3 asked
about `material`; the conflict was with a `feature`-turn's leftover) without
losing the paraphrase-robustness this experiment set out to gain. That
requires plumbing the previous turn's `ask_attribute` into `respond()`,
which this experiment deliberately did not do, to keep the change to one
idea (per `docs/EXPERIMENT_WORKFLOW.md`'s "change one idea at a time" rule).

## Reproduction

```
python -m unittest discover -s tests -v      # 77 tests, includes the 4 new ones
python -m evaluator.local_evaluator          # TechnicalScore 0.838288
```

Branch: `review/phrase-independent-override-implementation` (implementation
and tests preserved; not merged into the default agent configuration).
