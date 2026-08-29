# Balanced Clarification Experiment

Date: 2026-08-29
Result: Rejected; the current Candidate policy remains unchanged

## Problem this experiment tried to solve

The Candidate policy looks at the current products and asks about the attribute
that best separates them. It performs best overall, but on the full public set
it finds one fewer Buying target and one fewer Boundary target than the older
Profile policy.

Individual reruns found these causes:

- Buying `public_0054`: Candidate asks about material too early and receives the
  generic answer `Soft Fabric`, which later pushes the correct item out of the
  Top 10. Profile asks about features earlier, receives `Pull On closure` and
  `Machine Wash`, and finds the item on turn 3.
- Boundary `public_0180`: the simulated user always answers "no preference" to
  the first question. Candidate spends that turn asking the important feature
  question. Profile asks about material first and feature second, then finds the
  item on turn 10.

## Method tested

Balanced uses one simple rule:

> First ask about an attribute the user usually cares about when that attribute
> also separates the current products. Otherwise, use Candidate's original
> product-difference order.

For example, if the user cares about style and the candidates include both
casual and formal products, the system asks about style first. If every product
is cotton, it does not ask about material first even when the user usually cares
about material.

Retrieval, ranking, conversation memory, the fixed split, and the evaluator all
remain unchanged. Only question order changes.

## Validation decision table

| Method | HitRate@10 | MRR | MTTC ↓ | Efficiency | TechnicalScore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Candidate (current) | 0.900 | **0.570734** | 4.275 | 0.67250 | **0.755720** |
| Balanced (experiment) | 0.900 | 0.527748 | **4.2625** | **0.67375** | 0.743074 |

Balanced finds products slightly earlier on average, but ranks the correct
products noticeably lower. Its validation score is `0.012646` below Candidate,
so it does not meet the keep threshold of exceeding `0.755720`.

## Full-public diagnosis

| Method | HitRate@10 | MRR | MTTC ↓ | TechnicalScore |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0.870 | **0.544236** | **4.410** | **0.730071** |
| Balanced | 0.870 | 0.536248 | 4.540 | 0.725074 |

### HitRate@10 by scenario

| Method | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0.8750 | 0.9625 | **0.600000** | 0.9000 |
| Balanced | **0.8875** | 0.9625 | 0.533333 | **1.0000** |

Balanced recovers one Buying target and one Boundary target, but loses two
Intent Override targets. In plain language, it fixes the two visible examples
while making other situations worse.

## Decision

- Reject Balanced and do not make it the default policy.
- Remove the experimental behavior and the two tests that protect only that
  rejected behavior from the production branch.
- Keep Candidate as the current version.
- Retain this report and the raw JSON so the failed experiment is reproducible.
- Preserve the exact rejected implementation on branch
  `review/balanced-clarification-implementation` for independent cross-checking.

## Run record

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation --policies candidate balanced --output reports\experiments\balanced-clarification.json
```

- While the experiment implementation existed: 23/23 tests passed.
- After removing the rejected method: the formal 21-test suite was restored.
- Raw result: [balanced-clarification.json](balanced-clarification.json)
- Cross-check guide on the review branch:
  `docs/balanced_clarification_cross_check.md`

## Recommended next step

Do not add another broad hybrid policy. Improve input text handling instead,
starting with reducing the ranking effect of repeated generic terms such as
`fabric / soft fabric`. This problem comes directly from the failed case and
does not change question order for every scenario.
