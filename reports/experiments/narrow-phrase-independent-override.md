# Narrow Phrase-Independent Intent Override

Date: 2026-08-30
Status: **kept.** Public-set behavior is byte-identical to E13, session for
session (0/200 differ) -- a pure robustness improvement with a proven zero
cost on the metric that can be measured here.

## Hypothesis

`_is_intent_override()` currently matches one literal sentence copied from
the local simulator's `behavior_for()` template. A first attempt at
generalizing this (`reports/experiments/phrase-independent-override.md`,
rejected) tried "any new term for an already-known non-durable slot is a
conflict" and regressed one Browsing session: a `feature`-turn's leftover
word ("synthetic") shared a gazetteer slot with a later, unrelated
`material`-turn's real answer ("cotton"), and got misread as an override.
That report's own "Limitations and next step" section named the fix: only
trust the broadened trigger when the conflicting slot is the one the
agent's own **previous `ask_attribute`** was actually about, not any
accumulated slot.

**Correction found before writing any code:** gating the trigger on
`slot == previous_ask_attribute` does **not** actually fix `public_0172`.
At the exact moment "cotton" conflicts with "synthetic" (turn 3), the
agent's own `last_asked` genuinely *was* `"material"` -- the question just
asked really was the one "cotton" answers. The contamination is not about
which question is being asked *now*; it's about where the *existing*
conflicting value ("synthetic") came from *earlier* (an unrelated
`feature` question, turn 2). Gating only the current turn's trigger cannot
see that history.

Corrected hypothesis: track, per slot-term, the question that was being
asked when that term was recorded (or a sentinel for "volunteered, nothing
was asked"). When checking for a conflict, only compare the new term
against **existing terms that were themselves legitimate, on-topic answers
for this slot** -- discarding any existing term that arrived as an
incidental side effect of a *different* question. A term is on-topic if it
arrived on the opening turn, was volunteered with no question pending, or
was recorded while this same slot was what had just been asked.

## Change from the last retained method (E13, TechnicalScore 0.847923)

- `starter/agent.py`: new `self._session_last_asked: dict[str, str | None]`,
  updated to this turn's `ask_attribute` at the end of every `respond()`
  call, so the *next* turn knows what question its message is answering.
- New `self._session_slot_topic: dict[str, dict[str, dict[str, str]]]`
  (`session_id -> slot -> term -> topic`), populated alongside the existing
  slot-merge loop, purely additive -- `self._session_slots`'s existing
  `{term: arrived_turn}` shape and everything that reads it (the
  durable/`arrived > OPENING_TURN` override-survival filter) is untouched.
  `topic` is `"opening"` on turn 1, the previous turn's `ask_attribute` if
  one was pending, or `"volunteered"` if nothing was.
- `_is_intent_override()` gains a second path to `True`: for each
  non-durable slot in the message, filter that slot's existing terms down
  to ones whose topic is `"opening"`, `"volunteered"`, or this same slot
  (i.e. discard anything that arrived as a side effect of a *different*
  question), and only treat a conflict against that filtered, legitimate
  set as an override. A term with no legitimate history to conflict with
  (like "synthetic", whose only topic is `"feature"`) is simply not
  something a later answer can "override" -- it was never really an
  established value for this slot's own question in the first place.
- The literal-phrase check is kept, unchanged, as before.
- Nothing else changes: retrieval, ranking (including E13's routing bonus),
  and the clarification policy are all untouched.

## Baseline

E13 Buying/Browsing Routing, `TechnicalScore 0.847923`, `HitRate@10 0.970`,
full 200-session public set (the current merged default on `main`).

## Keep/reject threshold

Keep if full-set `TechnicalScore` does not drop below `0.847923` and no
scenario regresses at all (the standard the first attempt failed to meet on
Browsing). As before, this cannot *improve* the public score on its own
merit -- the public simulator only ever phrases an override one way -- so
"does not regress" is the bar, and the payoff is robustness the public set
cannot measure.

## Tests that will prove the behavior

1. The exact `public_0172`-shaped false positive from the rejected attempt
   must not recur: a term that arrived answering one question (e.g.
   `feature`) must not be treated as an established value that a later,
   different question's (`material`) real answer can "conflict" with.
2. A paraphrased change of mind, volunteered with no question pending (no
   literal phrase), replacing a value that *was* legitimately established
   (opening turn or a direct answer), must still be treated as an
   override -- the core behavior this experiment exists to recover.
3. The three existing safety-net tests from the rejected attempt
   (repeating the same value, a brand-new slot, the literal phrase itself)
   must all still pass unchanged.
4. A slot whose only existing content is off-topic contamination (case 1)
   must accept a later real answer as ordinary accumulation, not silently
   discard the contamination as a "conflict" -- both values can coexist in
   the query, matching what let the baseline find `public_0172`'s target.

## Known risks

- The topic bookkeeping is new state (`_session_slot_topic`) with its own
  surface for bugs, separate from the already-validated `_session_slots`.
  Kept intentionally as a parallel, additive structure rather than
  reshaping the existing one, specifically to avoid touching the
  already-working durable/override-survival logic.
- Still narrower than "any conflict, anywhere": a slot's *first* legitimate
  value can only be established on the opening turn, when volunteered
  unprompted, or when directly asked about -- a term arriving purely as
  contamination can never itself become "the thing to override" until a
  legitimate value exists to compare against. This is intentional (that's
  exactly what caused the regression), not an oversight.

## Implementation

`starter/agent.py`:

- `self._session_last_asked[session_id]`: this turn's own `ask_attribute`,
  recorded at the end of every `respond()` call, so the *next* turn knows
  what question its message is answering.
- `self._session_slot_topic[session_id][slot][term] -> bool`: whether that
  term has *ever* been recorded in a legitimate context for that slot.
  Deliberately OR-accumulated across every mention (`retained_topics[term]
  = retained_topics.get(term, False) or legitimate_now`) rather than
  overwritten, so a term's legitimacy, once earned, survives an unrelated
  later repeat in a different context, and vice versa -- a first-write- or
  last-write-wins policy would each have their own false-positive/negative
  edge case; "ever legitimate" does not.
- `_is_intent_override()` gains the conflict path: for each non-durable
  slot in the message, filter existing terms to ones flagged legitimate,
  and only treat a conflict against *that* filtered set as an override.

11 new/ported tests in `tests/test_conversation_state.py`
(`NarrowPhraseIndependentOverrideTest`): the `public_0172`-shaped
contamination case reproduced in miniature, the recovered
unprompted-paraphrase capability, and the three safety nets carried over
from the rejected broad attempt. All red-green verified. 90/90 project
tests pass.

## Result

Full 200-session public set: **every metric and every scenario is
identical to E13** (`TechnicalScore 0.847923`, `HitRate@10 0.970`, etc.).
Verified at the session level, not just in aggregate: comparing
`sessions[]` between this run and E13's stored evidence JSON gives **0
differing sessions out of 200** (hit status, rank, and turn all match
exactly). This is the expected, ideal outcome the contract predicted: the
public simulator only ever phrases an override one way (the literal
sentence), so the new structural path has nothing to fire on here, and its
entire value is provably-zero-cost robustness against a differently-worded
private-set simulator.

## Decision

**Keep.** Clears the threshold in the strongest possible sense (not "no
regression greater than one session" but "no difference at all,
anywhere"), while directly addressing a documented, twice-flagged risk
(`slot-memory-and-retrieval-ablation.md` and the rejected first attempt
both named the literal-phrase dependency as the most likely private-set
failure point). Unlike the first attempt, this one earns its
generalization without spending any of the public score to get it.

## Reproduction

```
python -m unittest discover -s tests -v      # 90 tests
python -m evaluator.local_evaluator          # TechnicalScore 0.847923, identical to E13
```
