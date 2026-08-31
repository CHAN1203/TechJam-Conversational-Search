# Staging Merge — 2026-08-31

An informal pull request. `staging` collects three working branches on top of
`main` at `22088dc`. Nothing has been pushed; `main` is untouched.

**TechnicalScore `0.906193 -> 0.917406` (`+0.011213`). Tests 197 -> 227.**

| | |
| --- | --- |
| Target | `main` @ `22088dc` |
| Head | `staging` @ `b0b6443` |
| Diff | 14 files, +2016 / -32 |
| Suite | 227 passing (4 skip without `TECHJAM_RUN_PUBLIC_SET=1`; 227/227 with it) |
| Evaluator | HitRate@10 `0.995`, MRR `0.823353`, MTTC `2.355`, TechnicalScore `0.917406` |

## Why this exists

Three branches were developed against different bases and one of them was 68
commits stale. Merging them needed reconciliation rather than fast-forwarding,
and one test failed on contact in a way worth recording — see
[The merge caught a live defect](#the-merge-caught-a-live-defect).

## Commit graph

```text
b0b6443  merge: reconcile the hardening guards with E32, land the E31 report
bf4b8aa  merge: submission bundle and score regression guards
9cc12b9  merge: E32 category field weight, E32-A and E33 rejected
22088dc  (main) docs: remove the retained hard/soft detection
```

Merged safest-first. The full suite and the official evaluator were run after
every step, not only at the end.

## Branches

| Branch | Base | Ahead/behind `main` | Disposition |
| --- | --- | ---: | --- |
| `experiment/ngram-phrase-bonus` | `22088dc` | 3 / 0 | Merged in full |
| `hardening/submission-and-regression-tests` | `0e63695` | 1 / **68** | Merged, then reconciled |
| `experiment/route-conditional-weights` | `22088dc` | 1 / 0 | **Report only**; code stays on the branch |

### `experiment/ngram-phrase-bonus` — merged in full

Three commits: `1a7af82`, `c656d45`, `5b101ff`.

- **E32, category field weight (kept, the only scoring change here).**
  `FIELD_WEIGHTS["categories"]` `3.0 -> 6.0`. `FIELD_WEIGHTS` had never been
  swept; the values came from E1 and survived twenty-eight experiments. The
  ordering was backwards, because `initial_message` composes the customer's
  opening line from `coarse_category(target.categories)`, so category words are
  quoted verbatim from the target while title words are only incidental.
  `0.906193 -> 0.917406`. No scenario loses a session. Boundary MRR regresses
  `1.000000 -> 0.911111` (one session of ten). Gain *grows* to `+0.021101`
  under the coverage-stress catalog, unlike E21 which reverses there.
- **E32-A, n-gram phrase bonus (rejected, no-op default).** `extract_phrases`
  generalises E19's bigrams to longer runs. `+0.002446` standalone but negative
  in combination with E32, so `PHRASE_MAX_N = 2` reproduces E19 exactly.
- **E33, union-hybrid retrieval (rejected, non-default mode).** Plus the
  query-side paraphrase stress diagnostic, which is the reason to read that
  report before writing the submission.

### `hardening/submission-and-regression-tests` — merged and reconciled

One commit, `831e342`, written against a base 68 commits old. Both tests
survived the gap; the reconciliation is in `b0b6443`.

### `experiment/route-conditional-weights` — report only

`cc5c10e`. E31 was rejected: the validation-split winner reversed on the full
set (`+0.000750 -> -0.005428`). Per `docs/EXPERIMENT_WORKFLOW.md` step 6B, the
report and the ledger row merge; the implementation
(`route_semantic_weights`, `route_popularity_weights`,
`tests/test_route_weights.py`) stays on the branch so a reviewer can
cross-check it without carrying rejected behaviour into the submission.

Renumbered `E29 -> E31` on merge: upstream had already used E29 and E30 on
`feat/hs` while this ran in parallel.

## The merge caught a live defect

`tests/test_submission_bundle.py` failed the moment it met current `main`:

```text
ModuleNotFoundError: No module named 'starter.ledger'
```

`SUBMISSION_PATHS` still described the E11-era bundle. **The declared
submission bundle would not have imported.** That is exactly the failure mode
the test was written for (gap G2 in `docs/test_gap_audit.md`), caught the first
time it ran against a moved codebase.

Fixed by adding `starter/dense.py`, `starter/ledger.py` and `requirements.txt`
to the declared list.

## Other reconciliation in `b0b6443`

- **`docs/current_best_results.json` regenerated.** It still pinned E11's
  `0.841838`, so the opt-in regression guard would have failed. Regenerated
  from a real evaluator run at E32.
- **The stdlib-only assertion was false.** E18 made semantic reranking a
  default, so `starter/dense.py` imports numpy and scikit-learn. Replaced with
  two tests that match reality: every third-party import in the bundle must be
  declared in `requirements.txt`, and no networking module may be imported at
  all. The offline guarantee is now enforced rather than assumed.
- **`docs/test_gap_audit.md` annotated.** Its E11-era figures were reading as
  current. The gaps and the argument stand; section 6 records what changed.

## Verification

```powershell
python -m unittest discover -s tests                       # 227 passing, 4 skipped
$env:TECHJAM_RUN_PUBLIC_SET = "1"
python -m unittest discover -s tests                       # 227 passing, 0 skipped
python -m evaluator.local_evaluator                        # TechnicalScore 0.917406
python -m scripts.build_coverage_stress_catalog
python -m scripts.run_dual_catalog_evaluation              # E32 gain +0.021101 stressed
python -m scripts.run_query_stress                         # paraphrase sensitivity
```

Also checked: `git diff --check` clean, `git ls-files docs/zh-CN reports/zh-CN`
empty, no secrets or private labels in the staged diffs.

## Risks and open items

- **Boundary MRR regression.** `1.000000 -> 0.911111` at E32, one session of
  ten off rank 1. HitRate@10 is unchanged at `1.0000`, and the same weight buys
  `+0.052410` MRR across the 80 Browsing sessions. A 10-session scenario cannot
  settle a weight on its own; recheck if Boundary is ever weighted more heavily.
- **The category dependency is now measured, and it is large.** Replacing the
  quoted taxonomy with a contentless placeholder costs `0.150384` and 31
  sessions. E32 does not deepen it — its gain persists under synonym rewording
  (`+0.010585`) and is neutral when the category is removed (`+0.000429`) — but
  this is the single most important limitation to disclose in the submission
  report. E33 establishes that no available retrieval change reduces it.
- **`_classify_route` is still dead code.** `COMPLETENESS_ALL_ROUTES = True`
  short-circuits its only reader, and E31 found no weight worth routing.
  Recommendation is to keep it and surface it as a labelled diagnostic rather
  than delete it, since `problem_statement.md` asks for Dual-Track Routing and a
  measured negative result answers that better than absent code — but it must
  not be presented as a scoring component.
- **Still open from the gap audit:** no packaging script, no recorded resource
  profile (G7), no exact Python version or one-command harness instruction, and
  the required short report (architecture, models, cost, limitations, team
  contributions) does not exist — `docs/experiment_history.md` is a ledger, not
  that report.
- **Untracked and deliberately not committed:** `TechJam.pdf`,
  `problem_statement.md`, `data/SHA256SUMS`.

## Reviewing this

Read in this order:

1. [`reports/experiments/field-weight-sweep.md`](../reports/experiments/field-weight-sweep.md) — the only scoring change.
2. [`reports/experiments/query-stress-and-hybrid-retrieval.md`](../reports/experiments/query-stress-and-hybrid-retrieval.md) — the submission-risk argument.
3. [`docs/test_gap_audit.md`](test_gap_audit.md) — what the new tests guard and what is still unguarded.
4. [`reports/experiments/route-conditional-weights.md`](../reports/experiments/route-conditional-weights.md) — the rejected routing work.
5. `docs/experiment_history.md` sections 1, T42 and T43.

The single highest-value diff to scrutinise is `starter/reranker.py`: it is one
changed number, and it is the whole `+0.011213`.
