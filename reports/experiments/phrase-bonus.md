# Phrase (Bigram) Bonus

Date: 2026-08-30
Status: **kept -- new current best.** TechnicalScore `0.849882 -> 0.868476`
(+0.018594), the largest single gain since E13. 2 sessions recovered, 0
lost. `phrase_weight` is now `1.0` by default.

## Hypothesis

Not from `TechJam.docx` -- researched separately, since the doc's remaining
Layer 1/2 options (Dense Retrieval, RRF, Cross-Encoder) are now all tried
(E16/E17/E18). This is a classic, well-established IR technique: the
current pipeline (E1's field-weighted reranker) scores every query word
independently, so a candidate containing "running" and "shoe" anywhere,
in any order, scores identically to one whose title literally says
"running shoe" as an adjacent phrase. A document matching an exact
customer-stated phrase is typically more specific and relevant than one
matching the same words scattered apart (e.g. "running errands" +
"dress shoe" would score identically to "running shoe" under pure
bag-of-words scoring).

Hypothesis: rewarding candidates whose text contains the customer's
adjacent word-pairs (bigrams) as a literal substring, on top of the
existing independent-term scoring, should improve precision without
touching retrieval (same BM25 candidate pool, same risk profile as E18 --
not E16/E17's pool-eviction risk).

## Change from the last retained method (E18, TechnicalScore 0.849882)

- `starter/reranker.py` gains a `_bigrams(text)` helper (consecutive
  token pairs from the *current turn's raw message only*, not the full
  accumulated query history -- phrase relationships are a property of one
  utterance, not a bag accumulated across turns) and `phrase_terms`/
  `phrase_weight` parameters on `rerank_candidates`, following the same
  additive-term pattern as `popularity_weight`/`semantic_weight`.
  Bonus = `phrase_weight * count of bigrams found as a literal substring
  in the candidate's combined field text`.
- `starter/agent.py`: computes bigrams from `user_message` (this turn's
  raw text) each turn and passes them through. New
  `Agent(phrase_weight=PHRASE_WEIGHT)` constructor argument.

## Baseline

E18 Semantic Reranking Score, `TechnicalScore 0.849882`, `HitRate@10
0.970`, full 200-session public set.

## Keep/reject threshold

Keep if full-set TechnicalScore improves over `0.849882` with no scenario
regressing by more than 1 session. A reasoned, lightly-triangulated
weight (same 2-3 point approach as E18), not a full sweep.

## Tests that will prove the behavior

1. `_bigrams` extracts consecutive word pairs correctly, lowercased,
   ignoring stopword-only pairs is not required (kept simple: literal
   adjacency, not filtered).
2. A candidate containing the exact phrase outranks one containing the
   same two words apart, all else equal.
3. `phrase_weight=0.0` (or omitting `phrase_terms`) leaves ranking
   byte-for-byte unchanged -- regression guard.
4. A single-word message (no bigrams possible) does not crash and
   contributes no phrase bonus.

## Known risks

- Only checks the current turn's message for phrases, so a phrase spread
  across two turns (unlikely in this dataset's turn structure, but
  possible) is not detected -- a deliberate scope limit, not a bug.
- Substring matching on combined field text could technically match a
  phrase spanning a field boundary by coincidence (e.g. end of "features"
  concatenated with start of "details"); acceptable risk given the
  existing codebase already concatenates fields similarly elsewhere
  (`_candidate_text` in `clarification.py`).

## Implementation

New `starter/reranker.py::extract_bigrams` (consecutive token pairs from
one piece of text) and `phrase_terms`/`phrase_weight` on
`rerank_candidates`, following the established additive-term pattern.
`starter/agent.py` computes bigrams from `user_message` (this turn's raw
text) each turn. New `PHRASE_WEIGHT = 1.0` default.

**Bug found and fixed along the way, unrelated to this experiment's own
logic:** `scripts/run_retrieval_mode.py`'s `--semantic-weight` had a
hardcoded default of `0.0`, silently overriding `Agent`'s own default
(`1.0` since E18) whenever the script was invoked without that flag --
stale ever since E18 changed the constructor default and this script
wasn't updated to match. Fixed by making both `--semantic-weight` and the
new `--phrase-weight` default to `None`, meaning "use whatever `Agent`
itself defaults to," so this class of staleness cannot recur when a
default changes again later.

10 new tests (`ExtractBigramsTest`, `PhraseBonusTest` in
`tests/test_reranker.py`). 115/115 project tests pass.

## Result

Triangulated three weights (not a full sweep), on top of E18's
`semantic_weight=1.0`:

| `phrase_weight` | TechnicalScore | HitRate@10 | MRR | MTTC |
| ---: | ---: | ---: | ---: | ---: |
| 0.0 (E18) | 0.849882 | 0.970 | 0.677607 | 2.920 |
| 0.5 | 0.855221 | 0.970 | 0.693071 | 2.885 |
| **1.0** | **0.868476** | **0.980** | **0.715919** | **2.815** |
| 2.0 | 0.866975 | 0.980 | 0.707583 | 2.765 |

At `1.0`: **2 sessions recovered** (`public_0161`, `public_0179` -- the
latter also one of E16's dense-only hits, recovered here by a completely
different mechanism), **0 lost**. This is the largest single-experiment
gain recorded since E13, and the cleanest: no scenario regresses on any
metric.

Scenario breakdown at `phrase_weight=1.0`: buying `0.9625 -> 0.9875` (+2
sessions vs E18), browsing `1.0000` unchanged, intent_override `0.933333`
unchanged, boundary `0.9000` unchanged (though MRR rises across the
board).

## Decision

**Keep. New current best.** `PHRASE_WEIGHT = 1.0` is now the `Agent`
default, confirmed with the plain, unmodified `Agent()` construction. The
size of this gain, relative to E18's much smaller one, suggests the
existing bag-of-words scoring really was leaving real precision on the
table for phrase-shaped constraints (e.g. "black leather belt" as an
adjacent description) -- consistent with this being a well-established,
generally effective IR technique rather than a dataset-specific quirk.

## Reproduction

```
python -m unittest discover -s tests -v      # 115 tests
python -m evaluator.local_evaluator          # TechnicalScore 0.868476, default Agent()
```
