# Constraint Ledger Stage 2: Weighted Projection and the Information-Gain Probe

## Status

**Split decision.** Term weighting by source is rejected: the validation
optimum is exactly the weight that turns it off. The information-gain probe is
retained at threshold `1` and is the largest single gain measured in this
project since the popularity prior.

Validation TechnicalScore `0.853190 -> 0.867378` (`+0.014188`), full-set
`0.854664 -> 0.868714` (`+0.014050`). Cumulative from E11: `0.841838 ->
0.868714`, `+0.026876`.

- Date: 2026-08-30
- Baseline: E13-B, `state_model="ledger"`, validation `0.853190`
- Design: [constraint ledger](../../docs/designs/2026-08-30-constraint-ledger-design.md)
- Split: seed `techjam-clarification-v1`, 80 validation sessions

## Part 1: term weighting by source (rejected)

The ledger records whether a constraint was `volunteered` in the opening
message or `answered` in reply to a specific question. Stage 2 passed a
multiplier per term into `rerank_candidates`, whose per-term weight slot T13
had deliberately kept open. `answered_weight` scales answered constraints;
`1.0` weighs every term the same and is therefore the off position.

| `answered_weight` | Development | **Validation** | Full |
| ---: | ---: | ---: | ---: |
| 0.6 | 0.835783 | 0.836582 | 0.836102 |
| **1.0 (off)** | — | **0.853190** | **0.854664** |
| 1.2 | 0.853384 | 0.851524 | 0.852640 |
| 1.5 | 0.850965 | 0.850040 | 0.850594 |

The optimum is the off position, on both sides of it. Down-weighting answered
constraints is much worse; up-weighting them is mildly worse. Where a
constraint came from carries no ranking signal this pipeline can use.

**Decision: reject.** The `term_weights` argument and
`ConstraintLedger.projection_weights` are retained as no-ops at their defaults,
following the T13 precedent that kept the tested `idf` argument for later
routing work. Neither contributes to any reported number. `decay_lambda`
remains `0` and was never swept: the public set contains no signal from which
to fit a decay rate.

## Part 2: the information-gain probe (retained)

Retrieval is a pure function of the projected terms, so a turn that adds no
active ledger entry cannot change the ranking. The ledger makes that
observable without reference to the target: compare the active entry count
before and after recording the reply. After `K` consecutive turns of no gain,
the agent stops working down the attribute order and asks an open question
instead.

This is the "Over-Generality -> proactive clarification" pillar from the
problem statement, computed from the agent's own state.

| `no_gain_probe` | Development | **Validation** | Full | HitRate@10 | MRR | MTTC | Intent Override |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| off | — | 0.853190 | 0.854664 | 0.975 | 0.677881 | 2.810 | 1.000000 |
| 0 (always ask) | **0.875813** | 0.858051 | 0.868708 | 0.975 | 0.687361 | **2.250** | 0.966667 |
| **1** | 0.869605 | **0.867378** | **0.868714** | **0.980** | **0.698381** | 2.540 | 1.000000 |
| 2 | 0.869272 | 0.857690 | 0.864639 | 0.980 | 0.692464 | 2.655 | 1.000000 |
| 3 | 0.867605 | 0.854190 | 0.862239 | 0.980 | 0.689131 | 2.725 | 1.000000 |

The validation optimum is interior. `K = 0` -- asking the open question
unconditionally, which is T9's rejected probe -- has the **best development
score of any configuration and a validation score `0.009327` below `K = 1`.
That gap in that direction is the signature of fitting the development split,
and it is also the only configuration that loses an intent_override session.
Selection followed the workflow and used validation alone.

### Result at `no_gain_probe = 1`

| Metric | E13-B | E13-C | Δ |
| --- | ---: | ---: | ---: |
| HitRate@10 | 0.975 | **0.980** | +0.005 |
| MRR | 0.677881 | **0.698381** | +0.020500 |
| MTTC | 2.810 | **2.540** | -0.270 |
| Efficiency | 0.8190 | 0.8460 | +0.0270 |
| **TechnicalScore** | 0.854664 | **0.868714** | **+0.014050** |
| **Validation** | 0.853190 | **0.867378** | **+0.014188** |

| Scenario | E13-B | E13-C |
| --- | ---: | ---: |
| Buying | 0.950000 | 0.950000 |
| Browsing | 1.000000 | 1.000000 |
| **Boundary** | 0.900000 | **1.000000** |
| Intent Override | 1.000000 | 1.000000 |

**Boundary moved.** It sat at `0.900000` through every popularity weight in
T15, through Stage 0, and through Stage 1, and the Stage 1 report said plainly
that whatever limited those ten sessions was not conversation state. That was
half right: the state model was not the limit, but the ability to *read* the
state was. A boundary session is one where the customer answers "I don't have a
preference" -- by construction, every turn adds nothing. That is exactly the
condition the probe detects.

### Dead turns

| Configuration | Dead turns | Sessions containing one |
| --- | ---: | ---: |
| E11 slots | 163 / 586 (27.8%) | — |
| E13-B ledger | 140 / 557 (25.1%) | 57 / 200 |
| E13-C probe = 1 | **85 / 504 (16.9%)** | 57 / 200 |

The count of sessions containing a dead turn is unchanged at 57, which is
correct and worth stating: the probe cannot prevent the first dead turn,
because that turn *is* the signal. What it does is stop the second, third and
fourth.

## Gate assessment

| # | Condition | Result |
| --- | --- | --- |
| 1 | validation exceeds E13-B's `0.853190` | **pass**, `0.867378` |
| 2 | no validation scenario HitRate@10 decreases | **pass** |
| 3 | the signal fires on sessions with dead turns and not on others | **pass**, with a caveat below |

On condition 3: the probe's signal is "no new active entry", while the tracer's
dead-turn definition additionally requires the target to be unranked. The
signal therefore fires on a superset -- it also fires on a turn that adds
nothing while the target happens to be ranked. That is correct behaviour, not a
false positive, but the two definitions are not identical and the condition as
written implied they were.

## Decision

- **Term weighting: reject.** Validation peaks at the off position.
- **Information-gain probe: retain at `no_gain_probe=1`** as **E13-C**.

Recommended configuration: `Agent(state_model="ledger", no_gain_probe=1)`.
Constructor defaults remain `state_model="slots"` and `no_gain_probe=None`, so
an unflagged `Agent()` still reproduces E11 at `0.841838`. Whether to flip the
defaults before submission is a separate decision and is not taken here.

Automated tests: 118 before, 127 after.

## Limitations

- **This is the experiment most exposed to the simulator.** The probe's value
  depends on the evaluator answering an `other` question with up to two
  undisclosed constraints while a named attribute yields at most one. T9
  documented that behaviour and warned that the private simulator is not
  guaranteed to match it. The *mechanism* -- noticing that questions have
  stopped yielding and asking openly instead -- is a general conversational
  strategy; the *size of the gain* is not guaranteed to transfer. If the
  private simulator treats `other` like any other attribute, this experiment
  degrades toward E13-B rather than breaking, because the probe only changes
  which question is asked.
- Boundary reaching `1.000000` is ten sessions out of ten. It cannot support a
  claim about the 800 private sessions.
- `K = 0` beating `K = 1` on development and losing on validation is a single
  observation on one split with one seed. It is consistent with overfitting but
  does not prove it.
- The rejected weighting arm swept four values. A finer sweep near `1.0` was
  not run, because the two nearest probes on either side both fell below the
  off position.
