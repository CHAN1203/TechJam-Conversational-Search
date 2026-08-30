# Constraint Satisfaction on All Routes

Date: 2026-08-30
Status: **E22, current best.** TechnicalScore `0.880670` -> `0.884741`.

## Where it came from

Two proposals about rebalancing constraints against priors, tested together:

1. **Make the satisfaction bonus prior-proof.** A 6,614-rating item scores
   `1.2 * log1p(6614) = 10.56` from popularity alone, against E13's
   `COMPLETENESS_BONUS = 4.0`. A popular item missing a constraint can
   therefore outrank an exact match: good for HitRate, bad for MRR.
2. **Weight constraints by turn.** Later answers are more specific -- the
   customer volunteers a category first and details later -- so a term that
   arrived on turn 4 should count for more than the opening category.

Only the first produced a gain, and not for the reason proposed.

## The premise, measured

The popularity term across the full 50,000-item catalog:

| | Value |
| --- | ---: |
| Median | 3.08 |
| p90 | 6.68 |
| p99 | 9.73 |
| Max | 15.50 |
| Spread, median to p99 | **6.65** |

The spread does exceed `COMPLETENESS_BONUS = 4.0`, so the described failure is
arithmetically possible. It is narrower than it first appears, though: if the
exact match earns full title weight on every constraint it wins on the match
score alone, regardless of popularity. The failure needs the *completing* term
to land in a cheap field:

    POPULAR_PARTIAL  leather 4.0 + buckle 4.0            + 10.56  = 18.56
    EXACT            leather 4.0 + buckle 4.0 + belt 1.0 +  2.88
                                              + bonus 4.0         = 15.88

Both cases are pinned by `PriorProofCompletenessTest` in
`tests/test_reranker.py`.

## Sweep

All arms on the standard split and seed (`techjam-clarification-v1`, 80
validation sessions), on top of E21.

| Arm | Validation delta | Full delta | MRR |
| --- | ---: | ---: | ---: |
| baseline E21 | -- | -- | 0.756899 |
| bonus 8, Buying only | **+0.000000** | **+0.000000** | 0.756899 |
| bonus 16, Buying only | **+0.000000** | **+0.000000** | 0.756899 |
| **all routes, bonus 4** | +0.003214 | **+0.004071** | 0.770470 |
| all routes, bonus 8 | +0.003214 | +0.003238 | 0.766026 |
| all routes, bonus 16 | **+0.003339** | +0.003288 | 0.766192 |
| all routes, bonus 40 | +0.003339 | +0.003288 | 0.766192 |

**Raising the bonus alone does nothing.** Not "little" -- `+0.000000` to six
decimals, with byte-identical output at 8.0 and 16.0. The constructed failure
above is real but evidently never decides a session in the Buying candidate
pools that actually occur. Prior-proofing is rejected on its own terms.

The entire gain comes from a change that was not proposed: applying the bonus
to **Browsing** sessions, which E13 excluded. A Browsing session opens vague,
but once it answers a clarification question it has disclosed a constraint
just as concrete as a Buying session's, and rewarding a candidate that
satisfies all of them is worth `+0.004071`.

Bonus magnitude does have an effect stacked on top of route generalization,
but a tiny one (`+0.000125` validation) that saturates by 16.0 -- identical at
40.0, i.e. completeness has become lexicographic. Split roughly 26:1 in favour
of the route change over the magnitude change.

`bonus 4, all routes` is shipped. Validation marginally prefers `bonus 16`
(`+0.000125`), but full-set prefers `bonus 4` by `+0.000783`, and both
coverage-stress measures prefer it as well (below). Changing a tuned constant
to buy `+0.000125` on one split of four was not worth it.

## Turn-recency weighting (rejected)

`term_weights` scales each query term by `1 + recency_weight * (arrival_turn
- 1)`. The agent records the first turn each surviving term entered the query,
rebuilt against `unique_terms` every turn so an override that drops a term
also drops its arrival record.

| `recency_weight` | Validation delta | Full delta | HitRate@10 |
| ---: | ---: | ---: | ---: |
| 0.1 | -0.000217 | -0.000762 | 0.980 |
| 0.25 | -0.003244 | -0.005046 | 0.980 |
| 0.5 | -0.016098 | -0.015506 | 0.970 |
| 1.0 | -0.026436 | -0.031340 | 0.960 |

No peak and no plateau: a clean monotonic decline on both splits, costing hits
from `0.5` upward. The sequence intuition does not hold here. Retrieval is an
accumulating OR query, so the opening category term is what keeps the
candidate pool on-topic; down-weighting it relative to later details widens
the pool rather than sharpening it. Recorded as E23, rejected. The code path
is retained at `RECENCY_WEIGHT = 0.0` for ablation.

Combining the two was also worse than E22 alone: `+0.003309` validation /
`+0.002876` full, against E22's `+0.003214` / `+0.004071`.

## Result

| Metric | E21 | E22 |
| --- | ---: | ---: |
| HitRate@10 | 0.980 | 0.980 |
| MRR | 0.756899 | **0.770470** |
| MTTC | 2.820 | 2.820 |
| Efficiency | 0.8180 | 0.8180 |
| TechnicalScore | 0.880670 | **0.884741** |

No scenario hit rate moves (Buying `0.9875`, Browsing `1.0000`, Intent
Override `0.933333`, Boundary `0.9000`). The whole gain is MRR, which is what
a reordering rule that never changes the candidate pool should produce.

## Coverage-stress: E22 holds, and helps more

| Catalog | E21 | E22 | Delta |
| --- | ---: | ---: | ---: |
| Official | 0.880670 | 0.884741 | **+0.004071** |
| Coverage-stress | 0.853574 | 0.859162 | **+0.005588** |

Validation agrees: `+0.003214` official, `+0.005250` stress.

This is the opposite behaviour to the price prior, whose gain reverses from
`+0.012194` to `-0.020274` under the same diagnostic. Constraint satisfaction
does not depend on how the public targets' metadata was populated -- it is a
statement about the conversation, not about the catalog -- so degrading target
metadata does not invert it. It helps slightly *more* under stress, consistent
with the pool being harder to separate when target metadata is sparser.

E22 does not recover the 3 sessions the price prior loses under stress:
HitRate@10 stays `0.965` on every stress arm.

## Limitations

- The gain is pure MRR on both catalogs. It reorders; it never rescues a
  session that was missed.
- `bonus 4` versus `bonus 16` is decided by `+0.000783` on the full set
  against `+0.000125` on validation. Both are small enough that the private
  set could order them either way; the choice was made on parsimony -- the
  magnitude knob demonstrably does nothing on its own -- not on a decisive
  margin.
- Route classification is frozen at turn 1 (E13). A session misrouted as
  Browsing now still gets the bonus, which is why this change is safe, but the
  reverse error is untested.
