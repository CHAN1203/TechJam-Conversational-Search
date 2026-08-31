# Test Gap Audit

Date: 2026-08-29. Audited commit: `0e63695`. Suite at audit time: 67 tests, all
passing.

> **Merged into `staging` on 2026-08-31 at E32.** The gaps and the argument
> stand; the specific figures below are the ones measured at audit time against
> E11 (`0.841838`). Section 6 records what the merge changed.

This audit asks one question: **which competition requirements can break without
a test failing?** It covers the scored submission path only. The session viewer
under `frontend/` is a development tool that is excluded from the submission
bundle, so its gaps are out of scope here.

Every claim below was reproduced against the frozen 50,000-item catalog and the
200-session public set. Verified behaviour is recorded alongside the gap,
because the point is not that the agent is broken — it is that correct
behaviour is currently unguarded.

## 1. What already works

Probed by wrapping the scored `Agent` in a contract checker and driving it with
the unmodified official evaluator across all 200 public sessions:

| Property | Result |
| --- | --- |
| `ask_attribute` always in the allowed enum or `null` | 0 violations |
| `message` always a string | 0 violations |
| `len(recommendations) <= top_k` | 0 violations |
| Recommendations unique | 0 violations |
| `usage` counts non-negative integers | 0 violations |
| Adversarial input (empty, whitespace, FTS5 metacharacters, SQL quote, unicode, 60k characters, stopwords only, digits only) | no exception on any case |
| Cross-session state isolation | no leakage between interleaved sessions |
| `respond` before `reset` | raises `RuntimeError`, as intended |

None of these properties is asserted by a test. FTS5 injection safety in
particular is an emergent property of `TOKEN_RE` being `[a-z0-9]+`: widening
that pattern would let quoting characters reach the `MATCH` expression, and a
resulting `sqlite3.OperationalError` is caught by the evaluator and scored as a
**miss**, not as a crash. The failure would be silent.

## 2. Gaps

| ID | Gap | Severity |
| --- | --- | --- |
| G1 | No regression guard on the retained score | Critical |
| G2 | Submission bundle is unverified and currently incomplete | Critical |
| G3 | `data/gazetteer.json` is an undeclared runtime dependency | High |
| G4 | Agent-contract invariants are untested | High |
| G5 | Input robustness is untested | High |
| G6 | No per-scenario regression guard | Medium |
| G7 | Resource profile unmeasured | Medium |
| G8 | Network policy undeclared | Low |

### G1: No regression guard on the retained score

`docs/experiment_history.md` records E11 as the current best with
TechnicalScore `0.841838`. No test asserts it. `docs/baseline_results.json`
pins the E0 weak baseline only.

Demonstrated: a build whose TechnicalScore has fallen to `0.808383` passes all
67 tests. A refactor can regress the headline result with a green suite.

### G2: Submission bundle is unverified and currently incomplete

`docs/submission_rules.md` requires an entry file exporting `Agent`, any
required local helper modules, a dependency manifest, and one command to run
the agent in the official harness.

Demonstrated, building a bundle from `starter/` plus `data/gazetteer.json`:

```text
ModuleNotFoundError: No module named 'analysis'
```

`starter/slots.py` imports `normalize_term` from `analysis.gazetteer`, so the
scored path depends on the diagnostics package. The minimal working set is:

```text
starter/__init__.py
starter/agent.py
starter/clarification.py
starter/reranker.py
starter/slots.py
analysis/__init__.py
analysis/gazetteer.py
data/gazetteer.json
```

**Superseded at merge time.** E18 made semantic reranking a default and E24-E27
added the constraint ledger, so the set is now `starter/` (including
`dense.py` and `ledger.py`), `analysis/__init__.py`, `analysis/gazetteer.py`,
`data/gazetteer.json` and `requirements.txt`. `tests/test_submission_bundle.py`
caught exactly this drift on merge -- the declared list was missing
`starter/ledger.py` and the bundle failed to import in isolation, which is the
failure mode G2 predicted.

Note that the rest of `analysis/` must **not** ship: `bm25_diagnostics.py` and
`experiment_results.py` import `evaluator.local_evaluator`, which does not
belong in a participant bundle. `analysis/__init__.py` holds only a docstring,
so importing `analysis.gazetteer` does not pull those modules in.

At audit time the repository had no dependency manifest and the agent used
only the standard library. Both have since changed: `requirements.txt` now
declares `scikit-learn` and `numpy`, which `starter/dense.py` needs to build
the dense index. There is still no packaging script.

### G3: `data/gazetteer.json` is an undeclared runtime dependency

`_load_gazetteer` degrades to an empty gazetteer when the file is missing, and
`test_missing_gazetteer_file_leaves_the_agent_usable` asserts that the agent
stays usable. Usable is not the same as scoring. Measured on the full public
set:

| Build | HitRate@10 | MRR | MTTC | TechnicalScore |
| --- | ---: | ---: | ---: | ---: |
| With `data/gazetteer.json` | 0.965 | 0.662125 | 2.965 | 0.841838 |
| Gazetteer absent | 0.925 | 0.649944 | 3.455 | 0.808383 |

Omitting one data file from the submission costs `0.033455` TechnicalScore
without raising an error anywhere. This is the failure mode G2 makes likely.

### G4: Agent-contract invariants are untested

`docs/agent_api_contract.json` constrains the turn response. Nothing asserts
`ask_attribute` membership, the `top_k` bound, uniqueness, `message` type, or
non-negative `usage`. See section 1 for the current measured behaviour.

### G5: Input robustness is untested

The simulator's customer messages are templated today, but
`docs/competition_specification.md` states the organizer may add natural-language
paraphrasing, and `docs/submission_rules.md` reserves the right to run the agent
under restricted conditions. No test pins behaviour on malformed, hostile, or
oversized input.

### G6: No per-scenario regression guard

Section 2 of `docs/experiment_history.md` exists so that "an aggregate
improvement does not hide a worse user experience". E4-B was rejected for
collapsing Intent Override from `0.633333` to `0.333333` while overall
TechnicalScore moved only `-0.006019`. No test enforces the per-scenario
floors, so the same class of regression can pass review again.

### G7: Resource profile unmeasured

The agent indexes 50,000 products into an in-memory SQLite FTS5 table at
construction. Observed: roughly 6 seconds to index, roughly 60 seconds for 200
sessions. The 800-session private set implies roughly 4 minutes plus indexing.
No peak memory figure and no per-turn time budget have been recorded, while
`docs/submission_rules.md` warns of CPU, memory, and timeout restrictions.

### G8: Network policy undeclared

`docs/submission_rules.md` requires the submission to document whether it needs
network access. The agent imports only `json`, `math`, `re`, `sqlite3`, and
`pathlib`, so it is fully offline, but the repository does not state this and no
test asserts it.

## 3. Work done in this branch

Two tests close G1 through G6. They were chosen because each one covers several
gaps at once and neither changes the scored path.

| Test | Gaps closed |
| --- | --- |
| `tests/test_public_set_regression.py` | G1, G6 |
| `tests/test_submission_bundle.py` | G2, G3, G4, G5 |

G7 and G8 are documentation and measurement tasks, not test gaps, and remain
open. See section 4.

### `tests/test_public_set_regression.py`

Pins the retained result. Reads the expected metrics from
`docs/current_best_results.json` rather than hard-coding them, matching the
existing `docs/baseline_results.json` convention and the workflow rule against
typing remembered scores into evidence.

The run costs about a minute and needs the untracked `data/catalog.jsonl`, so it
is opt-in:

```powershell
$env:TECHJAM_RUN_PUBLIC_SET = "1"
python -m unittest tests.test_public_set_regression -v
```

It skips with a clear reason when the variable is unset or the catalog is
absent, so `python -m unittest discover -s tests` stays fast and green on a
fresh clone.

### `tests/test_submission_bundle.py`

Declares the submission file list as `SUBMISSION_PATHS`, copies exactly those
files into a temporary directory, and runs the agent there in a **subprocess**
with `PYTHONPATH` cleared and the working directory set to the bundle. The
subprocess matters: an in-process import would resolve against the repository
and prove nothing about the bundle.

Inside the isolated bundle it builds a small synthetic catalog, runs several
turns, and asserts the contract invariants and the adversarial input cases from
section 1. It also asserts that `data/gazetteer.json` is present in the bundle
and parses with its expected slots, so an omission fails loudly instead of
costing score silently.

This test runs in the default suite and needs no catalog download.

## 4. Still open

- **G2 residual.** The tests now pin the true dependency set, but the agent
  still reaches into `analysis/` for one function. Inlining `normalize_term`
  into `starter/slots.py` would reduce the bundle to `starter/` plus the
  gazetteer. That edits the scored path, so it is left as a separate decision.
- **Dependency manifest.** `requirements.txt` now exists. The exact Python
  version and a one-command harness instruction are still required by
  `docs/submission_rules.md`.
- **G7.** Record peak memory and per-turn latency, and confirm the 800-session
  private run fits any stated timeout.
- **G8.** State the offline guarantee in `README.md` as the rules require.
- **Report deliverable.** `docs/experiment_history.md` is an experiment ledger,
  not the required short report covering architecture, models, cost,
  limitations, and team contributions.

## 5. Reproduction

```powershell
python -m unittest discover -s tests
python -m unittest tests.test_submission_bundle -v
$env:TECHJAM_RUN_PUBLIC_SET = "1"; python -m unittest tests.test_public_set_regression -v
python -m evaluator.local_evaluator
```

## 6. What the merge into `staging` changed

Merged on 2026-08-31, on top of E32 (`0.917406`). Both tests survived a
68-commit gap in their base, and one of them earned its keep immediately.

- **G1 closed and re-pinned.** `docs/current_best_results.json` was regenerated
  from a real evaluator run at E32: HitRate@10 `0.995`, MRR `0.823353`, MTTC
  `2.355`, TechnicalScore `0.917406`. The opt-in regression test passes against
  it.
- **G2 caught a live defect.** `SUBMISSION_PATHS` still described the E11-era
  bundle. Running it against current `main` failed with
  `ModuleNotFoundError: No module named 'starter.ledger'` -- the declared
  submission bundle would not have imported. Fixed by adding `starter/dense.py`,
  `starter/ledger.py` and `requirements.txt`.
- **G8 partially closed.** The stdlib-only assertion was replaced by two tests
  that match reality: every third-party import in the bundle must be declared in
  `requirements.txt`, and no networking module may be imported at all. The
  offline guarantee is now enforced rather than assumed.
- Suite: 227 tests, all passing; 4 skip without `TECHJAM_RUN_PUBLIC_SET=1`.
