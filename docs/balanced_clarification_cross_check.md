# Balanced Clarification Cross-Check Guide

> **Review-only branch:** `review/balanced-clarification-implementation`
>
> This implementation lost to the current Candidate policy. Do not merge it into `main`.

## What this branch preserves

This branch restores the exact Balanced behavior that produced the results in
[`reports/experiments/balanced-clarification.json`](../reports/experiments/balanced-clarification.json).
It is preserved so another AI or engineer can determine whether the low score came from:

1. a mistake in the implementation;
2. a weak experiment design; or
3. a limitation in the attribute-detection rules.

The production version on `main` continues to use Candidate clarification.

## Intended behavior in plain language

1. Look at the user's saved preference tags.
2. Convert known tags to question types, such as `fit -> size` and `comfort -> feature`.
3. Look at the current Top-100 products and identify attributes that genuinely vary.
4. First ask about attributes that are both preferred by the user and varied across products.
5. Then ask the remaining varied attributes in Candidate order.
6. Finally fall back to the default question order.
7. Never repeat an attribute that was already asked.

Example: if the user values style and the products include both casual and formal items,
ask about style first. If the user values material but every product is cotton, do not put
material ahead of a varied attribute such as color.

## Files to inspect

- `starter/clarification.py`: the Balanced ordering logic.
- `tests/test_clarification.py`: two behavior tests added for Balanced.
- `starter/agent.py`: passes the user profile, asked attributes, and current candidates into
  the policy selector. This file is unchanged on this branch.
- `scripts/run_clarification_ablation.py`: runs all policies on the same fixed split.
- `reports/experiments/balanced-clarification.md`: plain-language failure analysis.
- `reports/experiments/balanced-clarification.json`: raw aggregate results.

Review the exact implementation difference with:

```powershell
git diff main...HEAD -- starter/clarification.py tests/test_clarification.py
```

## Questions for the reviewer

Please answer each question with code evidence:

1. Does `_balanced_order` actually implement the seven intended steps above?
2. Can `_grounded_candidate_order` call an attribute “varied” for the wrong reason?
3. Are any profile tags incorrectly ignored or mapped to the wrong question type?
4. Does placing all profile-matched attributes before Candidate order make the policy too
   similar to Profile instead of truly balancing the two signals?
5. Could the fallback order or `asked_attributes` handling change the result unexpectedly?
6. Do the two unit tests cover the important logic, or can a wrong implementation still pass?
7. Is the evaluator comparison fair, with Candidate and Balanced differing only in question
   order?
8. If you find a bug, propose the smallest new failing test before proposing a fix.

Do not use `ground_truth`, `intent_card`, public target IDs, or evaluator-only fields inside
`starter/`. They may be used only for offline diagnosis and scoring.

## Reproduction commands

The catalog must exist at `data/catalog.jsonl`.

```powershell
python -m unittest discover -s tests -v
python -m scripts.run_clarification_ablation `
  --policies candidate balanced `
  --output reports\experiments\balanced-clarification-review.json
```

Expected fixed-validation results:

| Policy | HitRate@10 | MRR | MTTC ↓ | TechnicalScore |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0.900 | 0.570734 | 4.2750 | **0.755720** |
| Balanced | 0.900 | 0.527748 | 4.2625 | 0.743074 |

Runtime may change between machines. The four evaluation metrics above should not change.

## How to report a finding

Use one of these labels:

- **Implementation bug:** the code does not match the intended seven-step behavior.
- **Test gap:** the code may be wrong but the existing tests cannot catch it.
- **Design weakness:** the code is correct, but the intended policy is not a good method.
- **Evaluator concern:** the comparison is not isolating only the question-order change.

Include the affected file and line, a minimal example, and the test that should fail.
