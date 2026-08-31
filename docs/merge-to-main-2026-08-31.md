# Merge to `main` — 2026-08-31

`staging` merged into `main` at `9ea155e`. This is the record of what landed,
what was deliberately left behind, and what a reviewer should check.

**TechnicalScore `0.906193 -> 0.917406` (`+0.011213`). Tests 197 -> 227.**

| | |
| --- | --- |
| Merge commit | `9ea155e` |
| Previous `main` | `22088dc` |
| Source | `staging` @ `09c86bb` (9 commits) |
| Diff | 16 files, +2182 / -32 |
| Suite | 227 passing (4 skip without `TECHJAM_RUN_PUBLIC_SET=1`; 227/227 with it) |
| Evaluator | HitRate@10 `0.995`, MRR `0.823353`, MTTC `2.355`, TechnicalScore `0.917406` |

The per-branch detail behind this merge is in
[`staging-merge-2026-08-31.md`](staging-merge-2026-08-31.md). This document is
the `main`-level summary.

## The one scoring change

**E32, category field weight.** `FIELD_WEIGHTS["categories"]` `3.0 -> 6.0` in
`starter/reranker.py`. That is the entire `+0.011213`.

`FIELD_WEIGHTS` had never been swept. Its values came from E1's information
hierarchy reasoning and survived twenty-eight experiments untouched, while
every other weight in the system was swept or triangulated.

The ordering was backwards. `evaluator/local_evaluator.py`'s `initial_message`
composes the customer's opening line from
`coarse_category(target.categories)`, so category words in the query are quoted
**verbatim from the target's own category path**, while title words are only
ever incidental — a target's title may share no term with anything the customer
says. `categories` was weighted below `title`.

Why this is not a tuning artifact:

- Raising `title` instead is sharply negative (`-0.067204` at `6.0`). The
  asymmetry is what the mechanism predicts and is not what generic weight
  sensitivity looks like.
- Selected on the `techjam-clarification-v1` validation split, then confirmed
  on the full 200. Every validation winner held — which mattered, because E31
  had just been rejected for a validation gain that reversed.
- Swept `2.0-10.0`. The gain plateaus across `4.5-6.0` and decays beyond `7.0`;
  validation and full set agree on `6.0`.
- Under the coverage-stress catalog the gain **grows** to `+0.021101` and
  recovers three stressed sessions of HitRate@10 (`0.980 -> 0.995`). E21 is the
  counter-example, reversing from `+0.012194` to `-0.020274` there.

Unlike every ranking experiment before it, E32 adds no new signal. It corrects
a mis-stated reliability ordering among signals already present.

### Scenario effect

| Scenario | HitRate@10 | MRR | MTTC |
| --- | ---: | --- | --- |
| Buying | 0.9875 (unchanged) | 0.810774 -> **0.840000** | 1.8875 -> 1.8375 |
| Browsing | 1.0000 (unchanged) | 0.735417 -> **0.787827** | 2.3250 -> 2.2875 |
| Intent Override | 1.0000 (unchanged) | 0.805556 -> 0.805556 | 3.9000 -> 3.9000 |
| Boundary | 1.0000 (unchanged) | 1.000000 -> **0.911111** | 2.7000 -> 2.6000 |

No scenario loses a session. **Boundary MRR regresses** — one target of ten
moved off rank 1. Recorded rather than smoothed over; see Risks.

## Rejected experiments that landed as evidence

Kept because `docs/EXPERIMENT_WORKFLOW.md` requires failed results to be
recorded, and because two of them close questions that would otherwise be
re-asked.

| ID | Method | Result | What it settles |
| --- | --- | ---: | --- |
| E31 | Route-conditional reranking weights | `-0.005428` | Buying/Browsing routing has not paid since E22 removed its last live consumer |
| E32-A | N-gram phrase bonus (runs of 3+) | `+0.002446` standalone, negative combined | E19's bigrams are the right stopping point |
| E33 | Union-hybrid retrieval | `-0.004607` | Hybrid retrieval does not insure against vague queries |

E31's implementation stays on `experiment/route-conditional-weights` per
workflow step 6B — only its report and ledger row are on `main`. E32-A and E33
ship as no-op defaults (`PHRASE_MAX_N = 2`, `retrieval_mode = "bm25"`) so the
measurements stay reproducible.

## New guards

| Test file | Guards |
| --- | --- |
| `tests/test_public_set_regression.py` | The retained score and every per-scenario metric, pinned to `docs/current_best_results.json`. Opt-in via `TECHJAM_RUN_PUBLIC_SET=1`. |
| `tests/test_submission_bundle.py` | The declared submission bundle imports and runs in a subprocess with `PYTHONPATH` cleared; contract compliance; hostile input; declared dependencies; no networking imports. |
| `tests/test_field_weight_sweep.py` | `categories > title`, so a future re-tune cannot silently undo E32. |
| `tests/test_query_stress.py` | The paraphrase-stress transforms. |

**The bundle guard caught a live defect the first time it ran against current
`main`:** `SUBMISSION_PATHS` still described the E11-era bundle, and building it
failed with `ModuleNotFoundError: No module named 'starter.ledger'`. The
declared submission bundle would not have imported. Fixed by adding
`starter/dense.py`, `starter/ledger.py` and `requirements.txt`.

## New diagnostics

- `analysis/query_stress.py` + `scripts/run_query_stress.py` — rewrites the
  customer's wording in flight while the unmodified evaluator drives the
  session. Answers "how much does this depend on the simulator's exact
  phrasing?" See Risks.
- `retrieval_mode="union"` — non-default. Appends dense hits after the BM25 pool
  instead of E17's fuse-then-truncate, so BM25 recall cannot be displaced. Kept
  so the hybrid comparison is rerunnable.

## Risks carried into `main`

1. **The category dependency is large and now measured.** Replacing the quoted
   taxonomy with a contentless placeholder costs `0.150384` and 31 sessions.
   E32 does **not** deepen it — the gain persists under synonym rewording
   (`+0.010585`) and is neutral when the category is removed (`+0.000429`) —
   but this is the single most important limitation to disclose in the
   submission report. Mitigating context: the private set is scored by the same
   `evaluator/local_evaluator.py`, whose `initial_message` always emits the
   category, so this requires replacing the simulator rather than paraphrasing
   it. The realistic exposure is the `0.025636` of synonym rewording, and E33
   establishes that no available retrieval change reduces it.
2. **Boundary MRR regression** at E32, one session of ten. HitRate@10 unchanged
   at `1.0000`; the same weight buys `+0.052410` MRR across 80 Browsing
   sessions. A 10-session scenario cannot settle a weight on its own.
3. **`_classify_route` is dead code.** `COMPLETENESS_ALL_ROUTES = True`
   short-circuits its only reader, and E31 found no weight worth routing.
   Recommendation: keep it and surface it as a labelled diagnostic rather than
   delete it, since `problem_statement.md` asks for Dual-Track Routing and a
   measured negative result answers that better than absent code. It must not
   be presented as a scoring component.
4. **Score reproducibility.** `docs/current_best_results.json` pins `0.917406`
   as measured with `scikit-learn==1.9.0` / `numpy==2.2.6`. The ledger already
   notes small drift across scikit-learn versions.

## Still open

Carried forward from `docs/test_gap_audit.md`, none of it closed by this merge:

- No packaging script, exact Python version, or one-command harness
  instruction, all required by `docs/submission_rules.md`.
- No recorded resource profile (peak memory, per-turn latency) against the
  organizer's stated CPU/memory/timeout restrictions.
- **The required short report does not exist.** `docs/experiment_history.md` is
  an experiment ledger, not the architecture/models/cost/limitations/team
  contributions report the specification asks for.
- `starter/slots.py` still imports `normalize_term` from `analysis/`, so the
  bundle carries the diagnostics package for one function. Inlining it would
  reduce the bundle to `starter/` plus assets.

## Verification run before pushing

```powershell
python -m unittest discover -s tests                  # 227 passing, 4 skipped
$env:TECHJAM_RUN_PUBLIC_SET = "1"
python -m unittest discover -s tests                  # 227 passing, 0 skipped
python -m evaluator.local_evaluator                   # TechnicalScore 0.917406
```

Also checked: `git diff --check` clean, no `zh-CN` files tracked, and every
outgoing commit scanned for credentials and private labels.

## Branches

| Branch | State |
| --- | --- |
| `main` | `9ea155e` — this merge |
| `staging` | `09c86bb` — integration branch, pushed |
| `experiment/ngram-phrase-bonus` | `5b101ff` — E32/E32-A/E33, pushed, merged |
| `experiment/route-conditional-weights` | `334454b` — E31 review branch, pushed, **code intentionally unmerged** |
| `hardening/submission-and-regression-tests` | `831e342` — local only; contents are in `main` via `staging` |
