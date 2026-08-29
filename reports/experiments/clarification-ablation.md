# Clarification Policy Ablation

Date: 2026-08-29
Implementation commit: `fa84de2`

## Hypothesis

Conversation State v1 always chooses question order from profile tags, but a
profile preference is not necessarily the attribute that best separates the
current products. Choosing questions from attributes that are both present and
varied in the current Top-100 candidates should narrow the results earlier and
rank the target product higher.

## Experiment design

The public set is split deterministically with seed
`techjam-clarification-v1`, stratified by `scenario_type / difficulty_bucket`:

| Split | Sessions | Boundary | Browsing | Buying | Intent Override |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 120 | 6 | 48 | 48 | 18 |
| Validation | 80 | 4 | 32 | 32 | 12 |

All policies use the same catalog, retriever, reranker, conversation state,
and evaluator. The only variable is how the clarification attribute is chosen:

- `fixed`: ask material, size, style, feature, use_case, and color in that order.
- `profile`: prioritize anonymized profile tags, then use the fixed order. This
  is the E2 baseline.
- `candidate`: measure coverage and variation for material, color, size, style,
  use case, and feature in the Top-100 candidates. Ask about a useful separating
  attribute first, then fall back to the fixed order.

The winner is selected only by validation TechnicalScore. Full-public metrics
are reported for historical comparison, not used to choose the winner. This
validation set is a local holdout from the released public set, not the
organizer's unreleased 800-session private set.

## Validation result and decision

| Policy | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Fixed | 0.900 | 0.565526 | 4.475 | 0.6525 | 0.750158 | Reject |
| Profile | 0.900 | 0.527748 | 4.325 | 0.6675 | 0.741824 | Previous baseline |
| Candidate | 0.900 | **0.570734** | **4.275** | **0.6725** | **0.755720** | **Keep** |

Candidate scores `0.013896` higher than profile and `0.005562` higher than
fixed on validation. All three have the same hit rate; the gain mainly comes
from ranking the target higher and finding it slightly earlier.

## Full-public historical comparison

| Policy | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed | 0.865 | 0.523492 | 4.640 | 0.6360 | 0.716748 |
| Profile | 0.870 | 0.533748 | 4.565 | 0.6435 | 0.723824 |
| Candidate | **0.870** | **0.544236** | **4.410** | **0.6590** | **0.730071** |

Compared with the E2 profile policy, candidate keeps HitRate unchanged,
improves MRR by `0.010488`, reduces MTTC by `0.155` turn, and improves
TechnicalScore by `0.006247`.

## Full HitRate@10 by scenario

| Policy | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| Fixed | 0.8750 | 0.9625 | 0.566667 | 0.9000 |
| Profile | 0.8875 | 0.9625 | 0.533333 | 1.0000 |
| Candidate | 0.8750 | 0.9625 | **0.600000** | 0.9000 |

Candidate improves Intent Override but regresses slightly in Buying and
Boundary. The next experiment should therefore analyze, on the development
split, when candidate should fall back to profile instead of adding a broader
rule. Validation must remain the only selection set.

## Performance optimization

The first full candidate run took `144.189s`, compared with `82.447s` for
profile. Each product was rebuilding and tokenizing text six times, once for
each attribute. After computing each candidate token set once and reusing it,
candidate took `88.492s` with every metric unchanged. Its overhead relative to
profile fell from about 75% to about 7%.

## Verification and reproduction

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation
python -m scripts.run_clarification_ablation --policies candidate --output reports\experiments\clarification-candidate-optimized.json
python -m evaluator.local_evaluator
```

- Automatic tests: 21/21 passed.
- Official evaluator entry point: HitRate@10 `0.870`, MRR `0.544236`, MTTC
  `4.410`, TechnicalScore `0.730071`.
- Raw three-policy result: [clarification-ablation.json](clarification-ablation.json)
- Optimized candidate rerun: [clarification-candidate-optimized.json](clarification-candidate-optimized.json)

## Limitations and next step

- Validation has only 80 sessions, including four Boundary sessions. Small
  differences should not be over-interpreted.
- Attribute recognition uses English keyword sets and does not cover synonyms,
  compound attributes, or negation.
- Attribute variation is only a proxy for information gain; it does not estimate
  the real candidate reduction after the user's answer.
- Analyze candidate/profile fallback failures on the development split next. If
  no clear, testable trigger exists, retain the simpler candidate policy.
