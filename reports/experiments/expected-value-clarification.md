# Expected-Value Clarification Policy

Date: 2026-08-29
Status: **rejected as the default.** Full-set TechnicalScore `0.847923 -> 0.847486`
(kept on `review/expected-value-clarification-implementation` -- see Result
and Decision below).

## Hypothesis

`TechJam.docx`'s Layer 4 explicitly names this as the next-step option, not
yet implemented: "Asks questions based on which question can statistically
eliminate the most incorrect products, factoring in the mathematical
probability of the user giving various answers." The current default
(`candidate` policy, `_candidate_order` in `starter/clarification.py`) scores
each attribute as `coverage * diversity`, where `coverage` is the fraction of
the Top-100 pool containing *any* known vocabulary word for that attribute
and `diversity` is `(distinct_values - 1) / distinct_values`. This is a
reasonable heuristic but is not actually the "expected value" the doc
describes: it ignores how the pool is *distributed* across those values (an
80/20 split scores identically to a 50/50 split, as long as both have 2
distinct values) and requires at least 2 distinct known values, discarding a
90/10 "has it / doesn't" split that still carries real information.

Hypothesis: scoring each attribute by **Shannon entropy** of its value
distribution over the current Top-100 candidates (including an explicit
"unknown" bucket for candidates that don't match any known vocabulary term
for that attribute) is a more faithful implementation of "expected
information gain," and should ask better-targeted questions than the
coverage/diversity heuristic, most likely improving Buying and Boundary --
the scenarios most sensitive to how quickly the pool actually narrows.

## Change from the last retained method (E13, TechnicalScore 0.847923)

- New `_expected_value_order()` in `starter/clarification.py`, added as a
  fourth policy option (`policy="expected_value"`), alongside `fixed`,
  `profile`, `candidate` -- not replacing any of them.
- For each of the six candidate attributes, every candidate is assigned to
  the vocabulary value it matches (or an explicit `"__none__"` bucket if it
  matches none). Entropy `H = -sum(p * log2(p))` over the resulting bucket
  counts (`p = count / len(candidates)`) is the attribute's score. Attributes
  are ranked by entropy descending, ties broken by the existing fixed
  priority order. An attribute with `H == 0` (every candidate in one bucket)
  is skipped -- it cannot discriminate at all, same spirit as the existing
  `len(observed) < 2` guard but expressed directly in the metric being
  optimized instead of a separate threshold.
- Only compared against the `candidate` policy directly (same retrieval,
  ranking, and state as E13); the default `Agent.clarification_policy` is
  changed only if this wins.

## Baseline

E13 Buying/Browsing Routing, `TechnicalScore 0.847923`, `HitRate@10 0.970`,
full 200-session public set (the current default policy is `candidate`).

## Keep/reject threshold

Keep if full-set `TechnicalScore` improves over `0.847923` with no scenario
regressing by more than 1 session. Reject otherwise. Following
`docs/EXPERIMENT_WORKFLOW.md`'s guidance to decide a clarification-policy
choice on the validation split, not the full set, before committing to a
number if the full-set result looks close.

## Tests that will prove the behavior

1. `_expected_value_order` ranks an attribute with a more even (higher
   entropy) value split above one with a lopsided split, both otherwise
   qualifying, using the coverage/diversity test's own fixture reworked to
   distinguish the two scoring rules.
2. An attribute where every candidate shares the same single value (entropy
   zero) is skipped, matching the existing "cannot discriminate" behavior.
3. A binary has-it/doesn't-have-it split (only 1 *known* value, but a
   nontrivial `"__none__"` bucket) is still considered, unlike the current
   policy's `len(observed) < 2` gate -- this is the one behavior the
   heuristic structurally cannot express.
4. `select_attribute("expected_value", ...)` still respects `asked_attributes`
   (never repeats a question), matching every other policy.

## Known risks

- Entropy rewards a perfectly even split without regard to *how much* of the
  pool is covered at all -- an attribute known for only 3 of 100 candidates
  but split 1/1/1 across three rare values could out-score one covering 80
  candidates split 40/40. Whether this matters in practice is exactly what
  the full evaluator run below checks.
- This changes only *which* attribute gets asked; it does not change what
  the simulated customer is willing to reveal (`evaluator/local_evaluator.py`
  is unmodified), so any gain is strictly from better-targeted questions.

## Implementation

`starter/clarification.py`: new `_expected_value_order()`, wired in as a
fourth policy string (`"expected_value"`), alongside the existing three.
`starter/agent.py`'s default `clarification_policy="candidate"` is
unchanged -- this experiment only compares policies, it does not switch the
default ahead of a result.

7 new tests in `tests/test_clarification.py` (`ExpectedValuePolicyTest`),
all red-green verified. 83/83 project tests pass.

Compared using the project's own `scripts/run_clarification_ablation.py` on
the fixed `techjam-clarification-v1` split (120 development / 80
validation), the same tool and seed `popularity-prior.md` and the original
`clarification-ablation.md` used, per `docs/EXPERIMENT_WORKFLOW.md`'s
"decide a clarification-policy choice on the validation split" rule.

## Result

| Split | `candidate` (baseline) | `expected_value` | Δ |
| --- | ---: | ---: | ---: |
| Validation (80) TechnicalScore | **0.850222** | 0.848503 | -0.001719 |
| Development (120) TechnicalScore | 0.846391 | **0.846808** | +0.000417 |
| Full (200) TechnicalScore | **0.847923** | 0.847486 | -0.000437 |
| Full HitRate@10 | 0.970 | **0.975** (+1 session) | +0.005 |
| Full MRR | **0.671744** | 0.670619 | -0.001125 |
| Full MTTC | **2.930** | 3.060 | +0.130 (slower) |

Full-set scenario breakdown:

| Scenario | `candidate` | `expected_value` |
| --- | ---: | ---: |
| Buying | 0.9625 (MRR 0.720952) | 0.9625 (MRR 0.705327) |
| Browsing | 1.0000 (MRR 0.665595) | 1.0000 (MRR 0.659345) |
| Intent Override | 0.933333 (MRR 0.587685) | **0.966667** (MRR **0.611296**, +1 session) |
| Boundary | 0.9000 (MRR 0.579444) | 0.9000 (MRR **0.661111**, but MTTC 3.6 -> 4.4) |

Both the pre-registered threshold and the project's own validation-split
decision rule agree: `candidate` wins. `expected_value` is not uniformly
worse, though -- it genuinely improves Intent Override (a real extra hit,
better average rank) and Boundary's MRR, but costs a little MTTC/MRR in
Browsing and Buying, the two largest scenarios by session count (80 each).
With 160 of 200 sessions in those two, a small per-session softening there
outweighs a clear win concentrated in the 30-session Intent Override
scenario in the aggregate score.

## Decision

**Reject as the default.** Genuinely close (a 0.0437% TechnicalScore
difference on the full set, well within the range that could flip with a
different random seed or a slightly different candidate pool), but both
decision rules point the same direction, so there is no ambiguity to resolve
in `expected_value`'s favor here. The interesting result is *not* "entropy
doesn't work" -- it demonstrably helps the hardest scenario -- but that this
project's current default already sits close to a local optimum for the
`candidate` heuristic's own tradeoffs, and a more principled formula does
not automatically buy more than a well-tuned heuristic already captures.

Preserved on `review/expected-value-clarification-implementation`. A
narrower idea worth trying later, suggested directly by this result:
route the clarification *policy* itself the same way E13 routes retrieval
-- e.g. use `expected_value` only once an Intent Override has been detected
(mirroring the already-tried-and-reverted `E10` override-routed IDF
pattern, but applied to Layer 4 instead of Layer 2), so the Browsing/Buying
majority keeps `candidate` while Intent Override sessions get the policy
that measurably helps them. Not attempted here, to keep this experiment to
one idea.

## Reproduction

```
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation --policies candidate expected_value
python -m evaluator.local_evaluator
```

Branch: `review/expected-value-clarification-implementation` (implementation
and tests preserved, not merged into the default agent configuration).
