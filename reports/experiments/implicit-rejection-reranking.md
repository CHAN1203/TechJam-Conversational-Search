# E16: Implicit-Rejection Reranking

## Status

**Retained at `rejection_weight = 1.0`**, which is not the highest-scoring
value. The score keeps rising to a saturation point that violates the
submission rule requiring recommendations ordered best to worst; that region is
declined deliberately and the cost of declining it is `0.001625`.

Validation TechnicalScore `0.867378 -> 0.884128` (`+0.016750`), full
`0.868714 -> 0.876689` (`+0.007975`), HitRate@10 `0.980 -> 0.995`.

- Date: 2026-08-30
- Baseline: E13-C, `Agent(state_model="ledger", no_gain_probe=1)`
- Prior attempts on the same failure: [E15](exhaustion-triggered-idf.md) rejected,
  and widening the candidate pool ruled out by pool-position data

## The failure this addresses

Four sessions reach turn 10 without finding the target, and all four are stuck:
the information-gain counter runs for six consecutive turns while the agent
returns the same ten products. Three of the four have the target in the
candidate pool the whole time, at positions 11, 17 and 28.

E15 tried to fix this by reweighting terms and failed. Widening the pool was
ruled out without a run: it moves the three reachable targets further away
(`11 -> 13`, `17 -> 37`, `28 -> 40`) and cannot reach the fourth, which sits at
position 187 even in a 2,000-item pool.

## Change

The ledger records what the customer said. It did not record **what the agent
showed and the customer did not take**, which is negative evidence the
conversation supplies for free on every turn. A shopper who saw ten products
and kept talking has implicitly declined them, and returning the same ten is
the one outcome that cannot succeed.

`Agent` now counts what it has shown per session and, **only once the
information-gain counter says the conversation is stuck**, subtracts
`rejection_weight * times_shown` from a candidate's rerank score. While new
constraints are still arriving the ranking is improving for legitimate reasons
and the top of the list is left alone.

A second change follows from the same reasoning. Previously a stuck agent asked
`other` on every remaining turn. In this evaluator `other` is a strict superset
of every named attribute -- `customer_reply` short-circuits on
`attribute == "other"` -- so one empty answer to `other` proves nothing is left.
That is a property of the simulator, not of shoppers, and hard-coding it is
exactly the kind of assumption that does not transfer. The stuck agent now asks
`other` once and then keeps cycling named attributes.

## Sweep

| `rejection_weight` | Development | **Validation** | Full | HitRate@10 | MRR | MTTC |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 (off) | 0.869605 | 0.867378 | 0.868714 | 0.980 | 0.698381 | 2.540 |
| 0.5 | 0.871053 | 0.875253 | 0.872733 | 0.990 | 0.690776 | 2.475 |
| **1.0 (retained)** | 0.871730 | **0.884128** | 0.876689 | **0.995** | 0.694964 | 2.465 |
| 2.0 | 0.874064 | 0.884878 | 0.878389 | 0.995 | 0.699631 | 2.450 |
| 4.0 | 0.876443 | 0.885128 | 0.879917 | 0.995 | 0.704056 | 2.440 |
| 8.0 | 0.876477 | 0.885753 | 0.880187 | 0.995 | 0.704958 | 2.440 |
| 16.0 | 0.876477 | 0.885753 | 0.880187 | 0.995 | 0.704958 | 2.440 |
| 64.0 | 0.876477 | 0.885753 | 0.880187 | 0.995 | 0.704958 | 2.440 |

Scenarios at the retained weight: Buying `0.950000 -> 0.987500`, Browsing
`1.000000`, Boundary `1.000000`, Intent Override `1.000000`. No scenario
regresses. Three of the four misses are recovered; the fourth, `public_0020`,
is outside the candidate pool at every turn and unreachable by any reranking
change.

## Why the highest-scoring weight was declined

The curve is monotone and **saturates at weight 8**: 8, 16 and 64 are identical
in every digit. Saturation means the penalty exceeds any plausible difference
in match quality, so every unshown candidate outranks every shown one
regardless of how well it matches. That is not an ordering, it is a mechanical
exclusion, and `docs/submission_rules.md` requires that `recommendations` be
"ordered best to worst".

The effect is visible in what the recovered sessions report:

| Session | True pool position | Reported at weight 1.0 | Reported at weight 8.0 |
| --- | ---: | ---: | ---: |
| `public_0054` | 11 | 5 | **1** |
| `public_0161` | 17 | 6 | **2** |
| `public_0179` | 28 | 2 | 3 |

At saturation the agent reports rank 1 for an item it ranks eleventh. At weight
1.0 the penalty is around one field-weight unit against match scores in the 7
to 30 range, so it breaks near-ties and nothing more: a strongly matching item
the customer has already seen still outranks a weakly matching new one. That
invariant is locked by `test_relevance_still_outranks_novelty`, so a later
increase of the weight past the defensible range fails the suite.

The whole difference between the retained weight and the saturated one is
`0.001625` of validation TechnicalScore.

## Honest accounting

- The score at weight 1.0 is still partly earned by removing competitors rather
  than by ranking better. `public_0054`'s target sits at pool position 11 under
  the no-penalty model and is reported at 5. This is a genuine re-score under a
  stated belief -- six items above it each lost a point -- but the belief is a
  modelling choice, and a reader should be able to see exactly what it is.
- The aggregate MRR gain is small (`0.698381 -> 0.694964` at weight 1.0, in
  fact slightly *down*) while HitRate carries the improvement. If the mechanism
  were principally inflating rank quality, MRR would move in the other
  direction.
- The sweep does not have T15's shape. Development and validation do not peak
  independently and there is no plateau; the curve rises monotonically into a
  region the experiment declines on principle. The evidence is weaker than the
  popularity prior's and should not be presented as equivalent.

## Decision

Retain as **E16** at `rejection_weight = 1.0`. Recommended configuration:

```python
Agent(state_model="ledger", no_gain_probe=1, rejection_weight=1.0)
```

Constructor defaults are unchanged, so an unflagged `Agent()` still reproduces
E11 at `0.841838`. Automated tests: 127 before, 133 after.

## Limitations

- Three recovered sessions. The Buying gain rests on three of 80.
- The target is never penalised on the turn it is found: 199 hits, zero
  exceptions. For Buying, Browsing and Boundary this is a guarantee rather than
  an observation. A turn's own recommendations are recorded as shown only
  *after* that turn has been scored, and the evaluator ends the session the
  moment the target enters the Top-10, so "the target has been shown" and "the
  session is still running" cannot both hold; the target's shown count is
  therefore zero at every scoring call. `test_the_current_turn_is_not_penalised_by_its_own_recommendations`
  locks the ordering that this depends on.
- Intent Override is the one scenario where the guarantee does not follow. A
  hit before the override turn does not end the session, so the target can
  accumulate a penalty: 27 of 30 targets are shown pre-override and 13 of 30
  carry a non-zero penalty at some scoring call, up to `2.0` at the retained
  weight. None of them is penalised on the turn it is found, because the
  override message itself carries a new constraint, which resets the
  information-gain counter and lifts the penalty for that turn. That is an
  empirical observation holding 30 of 30, not a theorem, and a differently
  timed private override could break it.
- The penalty counts showings, not positions. An item shown once at rank 10 is
  penalised exactly as much as one shown once at rank 1.
- `public_0020` remains unreachable. Its target carries a single review against
  a target median of 6,846 and never enters the candidate pool; this is the
  documented cost of the popularity prior, named as a risk in T15.
