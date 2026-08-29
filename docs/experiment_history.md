# Experiment History and Method Comparison Matrix

This file is the project's experiment ledger. Every change to retrieval,
ranking, conversation state, or question policy must add a result here,
including failed experiments. It should answer three questions directly:

1. Where did the project start?
2. What changed in each experiment?
3. Which method is best, and why was each method kept or rejected?

> Current best: Candidate-aware Clarification, with public HitRate@10 `0.870`,
> MRR `0.544236`, MTTC `4.410`, and TechnicalScore `0.730071`.

Follow the [experiment workflow](EXPERIMENT_WORKFLOW.md) before starting or
recording another method.

## 1. Method comparison matrix

All formal results use the full 200-session public set, the frozen 50,000-item
catalog, and the unmodified official evaluator. `Δ` is measured against the
previous retained method.

| ID | Method | Main change | Automated tests | HitRate@10 | Δ HitRate | MRR | MTTC ↓ | Efficiency | TechnicalScore | Δ Score | Decision | Commit |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| E0 | Weak BM25 baseline | Return BM25 Top-10 directly; no state or questions | 3 | 0.125 | Reference | 0.068034 | 9.810 | 0.1190 | 0.106710 | Reference | Baseline | `3407835` |
| E1 | Field reranker v1 | Rerank BM25 Top-100 by field coverage | 10 | 0.160 | +0.035 | 0.076750 | 9.460 | 0.1540 | 0.133825 | +0.027115 | **Keep** | `db65ad2` |
| E1-A | Reranker + BM25 rank prior | Add the original BM25 rank as a bonus to E1 | Targeted | 0.155 | -0.005 | 0.073992 | 9.510 | 0.1490 | 0.129498 | -0.004327 | Reject | Not committed |
| E2 | Conversation State v1 | Accumulate constraints, handle overrides, ask profile-guided non-repeating questions | 14 | 0.870 | +0.710 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.589999 | Keep | `d770b6f` |
| E3-A | Fixed clarification | Use a fixed attribute question order | 21 | 0.865 | -0.005 | 0.523492 | 4.640 | 0.6360 | 0.716748 | -0.007076 | Reject | `fa84de2` |
| E3-B | Profile clarification | Use the E2 profile-first policy as the ablation baseline | 21 | 0.870 | +0.000 | 0.533748 | 4.565 | 0.6435 | 0.723824 | +0.000000 | Previous baseline | `fa84de2` |
| E3-C | Candidate-aware clarification | Ask first about a covered, varied attribute in the Top-100 candidates | 21 | **0.870** | **+0.000** | **0.544236** | **4.410** | **0.6590** | **0.730071** | **+0.006247** | **Current best** | `fa84de2` |
| E4 | Balanced clarification | Prioritize the intersection of profile preferences and current product differences | 23 during experiment | 0.870 | +0.000 | 0.536248 | 4.540 | 0.6460 | 0.725074 | -0.004997 | Reject | Behavior not on production branch |

The E1-A targeted test completed a red-green cycle. The behavior was then
removed because the evaluator regressed, so it is not in the final test suite
or a Git commit. The failed result remains in this matrix.

## 2. HitRate@10 by scenario

| Method | Buying | Browsing | Intent Override | Boundary |
| --- | ---: | ---: | ---: | ---: |
| E0 Weak BM25 | 0.2375 | 0.0250 | 0.133333 | 0.0000 |
| E1 Field reranker v1 | 0.2375 | 0.0875 | 0.133333 | 0.2000 |
| E1-A + BM25 rank prior | 0.2250 | 0.0875 | 0.133333 | 0.2000 |
| E2 Conversation State v1 | **0.8875** | **0.9625** | **0.533333** | **1.0000** |
| E3-A Fixed clarification | 0.8750 | **0.9625** | 0.566667 | 0.9000 |
| E3-B Profile clarification | **0.8875** | **0.9625** | 0.533333 | **1.0000** |
| E3-C Candidate-aware clarification | 0.8750 | **0.9625** | **0.600000** | 0.9000 |
| E4 Balanced clarification | **0.8875** | **0.9625** | 0.533333 | **1.0000** |

This table cannot prove private-set performance. It identifies which scenario
regressed so that an aggregate improvement does not hide a worse user experience.

## 3. Diagnostic matrices before implementation

### 3.1 First-turn BM25 candidate recall

Candidate Recall asks whether the target entered a larger candidate pool. It is
not the official, up-to-ten-turn HitRate@10.

| Scenario | Sessions | Recall@10 | Recall@50 | Recall@100 | Recall@500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Overall | 200 | 0.185 | 0.380 | 0.525 | 0.860 |
| Buying | 80 | 0.2375 | 0.4750 | 0.5875 | 0.9375 |
| Browsing | 80 | 0.0250 | 0.1875 | 0.3625 | 0.7625 |
| Intent Override | 30 | 0.533333 | 0.666667 | 0.833333 | 0.966667 |
| Boundary | 10 | 0.0000 | 0.3000 | 0.4000 | 0.7000 |

Conclusion: the number of targets found grows from 37 in the Top-10 to 172 in
the Top-500. Ranking is therefore the first measured problem, so the project
tested a reranker before adding dense retrieval.

### 3.2 Catalog field coverage

| Field | Coverage | Experimental use |
| --- | ---: | --- |
| categories | 1.00000 | Main category and broad intent |
| title | 0.99996 | Highest-weight product matching |
| details | 0.96660 | Attribute and specification constraints |
| store | 0.99372 | Supporting brand/store signal |
| features | 0.89562 | Feature, material, and use-case terms |
| description | 0.52226 | Lower-weight supporting text |
| price | 0.21054 | Too sparse for a default hard filter |

## 4. Chronological test and experiment record

### T0: Reproduce the official baseline

- Date: 2026-08-29
- Method: unmodified official weak BM25 starter.
- Command: `python -m evaluator.local_evaluator`
- Data: 200 public sessions and 50,000 catalog items.
- Result: HitRate@10 `0.125`, MRR `0.068034`, MTTC `9.81`, TechnicalScore
  `0.106710`.
- Purpose: establish the fixed comparison point for every later method.

### T1: BM25 candidate recall and catalog coverage

- Added candidate rank, Recall@10/50/100/500, and per-scenario summaries.
- Added populated/missing statistics for catalog fields.
- Automatic tests increased from 3 to 7.
- Commands:

  ```powershell
  python -m scripts.analyze_bm25_recall
  python -m scripts.analyze_catalog
  python -m unittest discover -s tests -v
  ```

- Conclusion: test lightweight reranking over Top-100/500 candidates first.
- Commits: `583e79c`, `e33c097`, `c51573a`, `c438628`.
- Detailed evidence: [baseline diagnostic summary](../reports/baseline/diagnostic-summary.md).

### T2: Field reranker v1

- Expanded the BM25 candidate pool from 10 to 100.
- Counted only the highest-value field match for each query term: title `4.0`,
  categories `3.0`, features/details `2.0`, store `1.5`, description `1.0`.
- Preserved original BM25 order when scores tied.
- Added reranker unit tests and a real SQLite FTS5 integration test using TDD.
- Automatic tests increased from 7 to 10.
- Result: HitRate@10 `0.160`, TechnicalScore `0.133825`.
- Decision: Keep.
- Commit: `db65ad2`.
- Detailed evidence: [local reranker v1](../reports/experiments/local-reranker-v1.md).

### T3: BM25 rank-prior ablation

- Hypothesis: retaining part of the BM25 order could recover five E1 losses.
- Change: added a bonus that decreases with original BM25 rank.
- Result: HitRate@10 `0.155`, TechnicalScore `0.129498`, below E1.
- Decision: Reject; remove the code and the test that protected only the failed behavior.
- Commit: none. Results remain in the E1 report and this ledger.

### T4: Conversation State v1

- Accumulated valid query constraints across turns.
- Excluded explicit no-preference replies from query terms.
- Cleared old constraints when the user overrode the earlier intent.
- Used anonymized profile tags for non-repeating ask-attribute order.
- Returned a clarification question and Top-10 recommendations on every turn.
- Added four conversation behavior tests with TDD.
- Automatic tests increased from 10 to 14.
- Leakage check: `starter/` does not reference `ground_truth`, `public_set`,
  `intent_card`, or evaluator behavior fields.
- Result: HitRate@10 `0.870`, TechnicalScore `0.723824`.
- Decision: Keep; it was later replaced by E3-C as the best method.
- Commit: `d770b6f`.
- Detailed evidence: [conversation state v1](../reports/experiments/conversation-state-v1.md).

### T5: Reproduce results in an isolated worktree

- Created `experiment/clarification-ablation` from `d770b6f`.
- Reused the same `data/catalog.jsonl` through a hard link.
- 14/14 tests passed.
- The full evaluator reproduced HitRate@10 `0.870`, MRR `0.533748`, MTTC
  `4.565`, and TechnicalScore `0.723824`.
- Conclusion: the experiment environment matched the stable branch and was
  ready for clarification ablation.

### T6: Fixed split and clarification-policy ablation

- Date: 2026-08-29.
- Used seed `techjam-clarification-v1` to split the public set by scenario and
  difficulty into 120 development and 80 validation sessions.
- Compared fixed, profile, and candidate policies while keeping retrieval,
  ranking, and state logic unchanged.
- Selection rule: choose only by validation TechnicalScore.
- Validation scores: fixed `0.750158`, profile `0.741824`, candidate `0.755720`.
- Decision: candidate wins and becomes default; fixed is rejected and profile
  remains available as an ablation baseline.
- Full public: HitRate@10 `0.870`, MRR `0.544236`, MTTC `4.410`,
  TechnicalScore `0.730071`.
- Implementation commit: `fa84de2`.
- Detailed evidence: [clarification policy ablation](../reports/experiments/clarification-ablation.md).

### T7: Candidate-policy performance rerun

- First full run: candidate `144.189s`, profile `82.447s`.
- Optimization: tokenize each candidate once and reuse the token set for all six
  attributes.
- Optimized candidate run: `88.492s`, with every metric unchanged.
- Automatic tests increased to 21; an integration test locks the default Agent
  to the candidate policy.
- The official evaluator entry point reproduced TechnicalScore `0.730071`.

### T8: Balanced clarification ablation

- Date: 2026-08-29.
- Reason: on full public, E3-C found one fewer Buying and one fewer Boundary
  target than profile.
- Read-only reruns tied the failures to a generic material answer and a Boundary
  first-turn no-preference response that spent an important question.
- Method: first ask about a profile preference when it also varies across the
  current candidates; otherwise use candidate order.
- TDD: added two tests for prioritizing a varied preference and skipping a
  preference with no candidate variation; 23/23 tests passed during the experiment.
- Validation: Candidate `0.755720`, Balanced `0.743074`, down `0.012646`.
- Full public: Balanced recovered one Buying and one Boundary hit but lost two
  Intent Override hits; TechnicalScore fell from `0.730071` to `0.725074`.
- Decision: Reject; Candidate remains the default. The exact rejected code and
  tests are preserved on `review/balanced-clarification-implementation`.
- Detailed evidence: [balanced clarification experiment](../reports/experiments/balanced-clarification.md).

## 5. Current automated test coverage

| Test module | Tests | Behavior protected |
| --- | ---: | --- |
| `test_evaluator.py` | 3 | Output normalization, miss turn, hidden-field materialization |
| `test_bm25_diagnostics.py` | 3 | Rank, cutoff recall, first-turn measurement |
| `test_catalog_profile.py` | 1 | Coverage meaning for empty collections |
| `test_reranker.py` | 2 | Complete-constraint priority and BM25 tie order |
| `test_agent_reranking.py` | 1 | Agent reranks a larger candidate pool |
| `test_conversation_state.py` | 6 | Accumulation, negation, override, non-repeating questions, policy selection and default |
| `test_clarification.py` | 2 | Fixed/profile difference and candidate grounded-attribute selection |
| `test_clarification_ablation.py` | 1 | Multiple policies and splits on the real FTS5 evaluator |
| `test_experiment_split.py` | 1 | Fixed split size, stratification, and no dev/validation overlap |
| `test_experiment_results.py` | 1 | Split metrics, scenario metrics, and TechnicalScore |
| **Total** | **21** | Current full regression suite |

Run the full tests:

```powershell
python -m unittest discover -s tests -v
```

Run the official public evaluator:

```powershell
python -m evaluator.local_evaluator
```

## 6. How to update this ledger

Follow the full [experiment workflow](EXPERIMENT_WORKFLOW.md). For every method:

1. Assign the next ID, such as `E5`; use `E5-A` and `E5-B` for variants.
2. Add a method-matrix row even when the result fails.
3. Add Buying, Browsing, Intent Override, and Boundary to the scenario matrix.
4. Add a chronological entry with the hypothesis, change, commands, test count,
   metrics, decision, and commit or review branch.
5. Store only aggregate metrics. Never record private labels or credentials.
6. For a rejected method, state which retained method beat it and by how much.
7. Update "Current best" at the top without overwriting historical results.
8. Update the local Chinese mirror, but never stage or push it.

New experiment template:

```markdown
### T<N>: <Experiment name>

- Date: YYYY-MM-DD
- Hypothesis:
- Change from the last retained method:
- New or changed tests:
- Commands:
- Overall: HitRate@10, MRR, MTTC, Efficiency, TechnicalScore
- Scenarios: Buying, Browsing, Intent Override, Boundary
- Decision: Keep / Reject / Need more evidence
- Commit or review branch:
- Limitations and next step:
```

## 7. Metric meanings and comparison rules

- **HitRate@10:** share of sessions that find the target within ten turns; higher
  is better.
- **MRR:** average reciprocal target rank; higher means the target appears nearer
  the top.
- **MTTC:** average first-hit turn, with a miss counted as turn 11; lower is better.
- **Efficiency:** `clip((11 - MTTC) / 10, 0, 1)`.
- **TechnicalScore:** `0.50 × HitRate + 0.30 × MRR + 0.20 × Efficiency`.
- Candidate Recall and official HitRate@10 are not directly comparable.
- Public-set improvement does not guarantee private-set improvement. Keep failed
  experiments and ablation evidence.

## 8. Evidence sources

- [Official baseline JSON](baseline_results.json)
- [Evaluation configuration](evaluation_config.json)
- [Baseline diagnostics](../reports/baseline/diagnostic-summary.md)
- [Field reranker experiment](../reports/experiments/local-reranker-v1.md)
- [Conversation state experiment](../reports/experiments/conversation-state-v1.md)
- [Clarification policy ablation](../reports/experiments/clarification-ablation.md)
- [Balanced clarification experiment](../reports/experiments/balanced-clarification.md)
- [Adaptive retrieval design](superpowers/specs/2026-08-29-adaptive-intent-aware-retrieval-design.md)
