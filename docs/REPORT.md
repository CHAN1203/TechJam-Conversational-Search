# Shopping Copilot — Project Report

TechJam 2026, Problem Statement 4: *Shopping Copilot: AI Conversational Search
and Recommendations*.

A multi-turn shopping agent that finds a hidden target product in a 50,000-item
Amazon catalog within ten turns. It runs offline, uses no LLM, reports zero
tokens, and costs nothing per session.

| Metric | Weak BM25 baseline | This system |
| --- | ---: | ---: |
| HitRate@10 | 0.125 | **0.995** |
| MRR | 0.068034 | **0.823353** |
| MTTC | 9.810 | **2.355** |
| Efficiency | 0.119 | **0.8645** |
| **TechnicalScore** | **0.106710** | **0.917406** |

Measured with the unmodified official evaluator on all 200 public sessions.
Reproduce with `python -m evaluator.local_evaluator`.

---

## 1. How the solution addresses the problem statement

The brief specifies four pillars. We built against all four, measured each, and
**two of them did not pay on this task**. Those negative results are reported
here rather than hidden, because knowing *why* a prescribed technique fails is
part of understanding the problem.

### Pillar I — Intent routing and hybrid pipeline

**Dual-track routing: built, measured, does not pay.**

`_classify_route` in [`starter/agent.py`](../starter/agent.py) classifies each
session Buying or Browsing on turn 1, from whether the opening message contains
a concrete non-durable constraint. Measured against the public set's own
scenario labels it is **95.0% accurate (152/160)**, and its errors are
structural rather than noisy — it misses Buying sessions whose constraint has
no gazetteer term (`"A key requirement is: Imported."`) and false-fires on
Browsing sessions whose category name contains an attribute word
(`"Bras Sports Bras"`).

The route originally gated a constraint-completeness bonus (E13, `+0.006085`).
E22 then found that applying the bonus on **every** route was worth a further
`+0.004071`, which left the classifier computed but unread. E31 tried to give
it a new job — per-route semantic and popularity weights — and was rejected:
the validation-split winner reversed on the full set (`+0.000750 → -0.005428`).

Why: HitRate@10 is already 0.995, so routing cannot buy coverage, and splitting
globally-tuned weights by route halves the evidence behind each without adding
a signal the ranker lacked. See
[`route-conditional-weights.md`](../reports/experiments/route-conditional-weights.md).

**Diverse dense retrieval for browsing: measured, actively harmful.** The brief
proposes routing Browsing sessions to a dense retriever. Dense retrieval as the
retrieval track scores **HitRate@10 0.670** against BM25's 0.995 (E16). Even
fused, it loses: RRF hybrid cost `-0.017014` (E17), traced to pool truncation
evicting correct candidates.

We fixed that specific flaw in E33 with a *union* mode that appends dense hits
after the full BM25 pool so recall cannot be displaced — and it still costs
`-0.004607`. See §5.

**Hybrid pipeline: delivered, at the ranking stage.** Every candidate's score
already includes a dense cosine-similarity term (E18). The pipeline is
`BM25 retrieval → multi-signal semantic reranking`; what it is not is
multi-route *retrieval*, because that was measured and rejected.

### Pillar II — Dialog strategy, multi-turn scenario evolution

**Dynamic state machine: delivered.** [`starter/ledger.py`](../starter/ledger.py)
holds a `ConstraintLedger` that accumulates constraints across turns with their
arrival turn and source (volunteered vs. answered). Intent Override revokes
what the customer volunteered on turn 1 while preserving the item they are
shopping for (`category`, `department` are durable) and everything they
answered when asked.

This is the single largest gain in the project: adding conversation state took
HitRate@10 from 0.160 to 0.870 (E2, `+0.589999`). Intent Override sessions now
score **HitRate@10 1.000**.

**Proactive guidance: delivered.**
[`starter/clarification.py`](../starter/clarification.py) picks the attribute to
ask about from the *current candidate pool* — the attribute that is both well
covered and most varied among the top 100, so the answer maximally splits the
pool (E3-C). A stuck-detector escalates to an open question when a turn adds no
ledger entry (E24-C). Together these hold MTTC at **2.355** against the
ten-turn limit.

### Pillar III — Self-evolution and dynamic context programming

**Partially delivered, and we are explicit about the gap.**

What exists: the ledger is rebuilt every turn from active constraints, so the
query, the completeness requirement, and the clarification target are all
re-derived from evolving state rather than appended blindly. Term arrival turns
are tracked. Stuck-state detection switches strategy at runtime.

What does not exist: LLM-driven re-orchestration of the workflow itself. We
tested the nearest thing — rewriting the semantic query from the structured
ledger instead of the raw term bag (E29) — and found it worth `+0.000050`. The
diagnostic that matters is the **ceiling**: turning the semantic term off
entirely costs only `0.001871`, and nothing else consumes the rewritten query.
So *any* query rewrite, LLM or otherwise, competes for a `0.001871` budget.
That measurement is what settled the LLM question for us; see §4.

**Personalisation** uses the anonymised profile's `preference_tags` to order
clarification questions. It is deliberately a weak input: the profile is
aggregate and the constraint ledger carries far more signal.

### Pillar IV — Evaluation

Reported in §6, including per-scenario breakdowns and two robustness
diagnostics we built because the official metrics cannot detect the failure
modes we were most worried about.

---

## 2. Architecture

One turn, end to end. Full walkthrough in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

```text
respond(session_id, user_message, turn, top_k)
  │
  ├─ 1. Parse         no-preference detection; gazetteer slot extraction
  ├─ 2. State         ConstraintLedger: accumulate, or revoke on override
  ├─ 3. Route         _classify_route, turn 1 only (diagnostic; see Pillar I)
  ├─ 4. Retrieve      SQLite FTS5 BM25 over accumulated terms → top 100
  ├─ 5. Rerank        field weights × (popularity, price, semantic, phrase,
  │                   constraint completeness) → top 10
  └─ 6. Clarify       candidate-aware attribute choice, or open probe if stuck
```

**Retrieval.** SQLite FTS5 virtual table over `title`, `categories`,
`features`, `details`, `store`, `description`, built in-memory at construction.
Query is the accumulated active constraint terms joined with `OR`.

**Ranking** ([`starter/reranker.py`](../starter/reranker.py)) sums, per
candidate:

| Signal | Weight | Rationale |
| --- | ---: | --- |
| Field-weighted term match | `categories` 6.0, `title` 4.0, `features`/`details` 2.0, `store` 1.5, `description` 1.0 | see below |
| Popularity prior | `1.2 × log1p(rating_number)` | targets are purchase records; median target has 6,846 ratings vs. a catalog median of 12 |
| Price presence | `2.0` flat | 89% of targets are priced vs. 21% of the catalog; a priced listing is an active one |
| Semantic similarity | `1.0 × cosine` | TF-IDF + Truncated SVD (LSA) over the catalog |
| Phrase bonus | `1.0 ×` matching bigrams | adjacency is more specific than scattered words |
| Constraint completeness | `+4.0` | candidate matches *every* known constraint |

The single most important line in the system is `categories: 6.0`. The
evaluator composes the customer's opening message from
`coarse_category(target.categories)`, so **category words in the query are
quoted verbatim from the target's own category path**, while title words are
only ever incidental. Weighting `categories` below `title` — as the project did
for twenty-eight experiments — inverts the reliability ordering. Correcting it
was worth `+0.011213`, the largest single gain since E19, and it adds no new
signal at all. See
[`field-weight-sweep.md`](../reports/experiments/field-weight-sweep.md).

---

## 3. Development tools, libraries, datasets

| Category | Used |
| --- | --- |
| Language | Python 3.11.4 |
| Libraries | Standard library; `scikit-learn==1.9.0`, `numpy==2.2.6` (see [`requirements.txt`](../requirements.txt)) |
| Retrieval | SQLite FTS5 (stdlib `sqlite3`), BM25 ranking function |
| Semantic model | `TfidfVectorizer` + `TruncatedSVD` (LSA, 200 components), fitted locally at startup |
| Editors / tooling | VS Code; Claude Code for pair programming; `unittest` for tests; git worktrees for parallel experiments |
| Dev-only UI | React 18 + TypeScript + Vite session viewer (`frontend/`, excluded from the submission bundle) |
| APIs | **None.** No LLM API, no external service, no credentials |
| Dataset | Organizer's frozen 50,000-item `Clothing_Shoes_and_Jewelry` catalog and 200 public sessions, derived from Amazon Reviews 2023 (McAuley Lab, UCSD). See [`DATA_ATTRIBUTION.md`](../DATA_ATTRIBUTION.md) |
| Derived assets | `data/gazetteer.json` — slot vocabularies mined from the frozen catalog by `scripts/build_gazetteer.py` |

---

## 4. Model choice and cost

**No LLM is used. Reported token usage is zero. Marginal cost per session is
$0.00. No network access is required at any point.**

This was a measured decision, not an ideological one. Three findings drove it:

1. **The budget is tiny.** The only component an LLM would plausibly improve is
   the semantic query. Disabling the semantic term entirely costs `0.001871`,
   so that is the entire prize available to any query rewrite. An LLM competing
   for `0.001871` would cost latency, tokens, a network dependency, and the
   zero-token property (T41).
2. **Determinism is worth more than marginal quality here.** Scoring is exact
   `parent_asin` equality. Our reranker's decisions are inspectable and
   reproducible to six decimal places; an LLM reranker would not be.
3. **The rules discourage it.** `docs/submission_rules.md` warns that scoring
   may run with network access disabled, and requires an offline fallback to be
   documented. A system that needs no fallback cannot fail that way.

Our advice to anyone reproducing this: reach for a model **after** the
deterministic pipeline stops improving, not before. The first four layers took
TechnicalScore from 0.107 to 0.917 without one.

---

## 5. Feasibility: latency, memory, robustness

Measured on Windows 11, Python 3.11.4, single process, no GPU.

| Figure | Value |
| --- | ---: |
| Agent construction (index build, once) | 25.7 s |
| Peak RSS during scoring | 802 MB |
| Per-turn latency, mean | 96.8 ms |
| Per-turn latency, median | 91.6 ms |
| Per-turn latency, p95 | 182.7 ms |
| Per-turn latency, p99 | 237.1 ms |
| Per-turn latency, max | 269.7 ms |
| 200 public sessions, wall clock | 45.6 s |
| Projected 800 private sessions | ≈ 3.5 min including construction |
| Tokens (prompt + completion) | **0** |
| Estimated model cost | **$0.00** |

**Memory is the figure to watch.** 802 MB peak, dominated by the in-memory FTS5
index and the dense matrix. The brief requires in-memory execution and forbids
external vector DB clusters, so this is the intended shape, but a tight memory
cap would be the one constraint this system could fail. Construction is also
25.7 s, which matters if the harness constructs per session rather than once.

### Robustness diagnostics

Official metrics cannot detect the two failure modes we were most worried
about, so we built diagnostics for both.

**Catalog sparsity.** A stress catalog masks `title`, `features`,
`description`, `price` and `details` down to catalog-wide coverage rates. The
E32 category weight **gains** there (`+0.021101`, versus `+0.011213` official)
and recovers three stressed sessions. By contrast the price prior (E21)
reverses under the same test (`+0.012194 → -0.020274`) and is flagged in the
ledger as carrying transfer risk.

**Customer wording.** `analysis/query_stress.py` rewrites the customer's
message in flight while the unmodified evaluator drives the session:

| Perturbation | TechnicalScore | HitRate@10 |
| --- | ---: | ---: |
| None | 0.917406 | 0.995 |
| Simulator sentence frames removed | 0.916277 | 0.995 |
| Head nouns replaced with synonyms | 0.891770 | 0.965 |
| **Category phrase removed entirely** | **0.767022** | **0.840** |

Phrasing barely matters; **naming the catalog's taxonomy matters enormously**.
This is our most important disclosed limitation — see §8.

We tested whether hybrid retrieval insures against it. It does not: union-mode
hybrid costs `0.004607` on clean queries and recovers only `0.001840` in the
worst case. The reason is mechanical — our dense index is TF-IDF + SVD, which
models term co-occurrence and is therefore still lexical, so it degrades
*together* with BM25 rather than complementarily. A pretrained sentence encoder
might not, but it cannot ship under the submission rules. See
[`query-stress-and-hybrid-retrieval.md`](../reports/experiments/query-stress-and-hybrid-retrieval.md).

---

## 6. Results

### Overall (200 public sessions, unmodified official evaluator)

| Metric | Value |
| --- | ---: |
| HitRate@10 | 0.995 |
| MRR | 0.823353 |
| MTTC | 2.355 |
| Efficiency | 0.8645 |
| TechnicalScore | 0.917406 |

199 of 200 sessions find the target, at a mean of 2.36 turns against a ten-turn
budget.

### By scenario

| Scenario | n | HitRate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: |
| Buying | 80 | 0.9875 | 0.840000 | 1.8375 |
| Browsing | 80 | 1.0000 | 0.787827 | 2.2875 |
| Intent Override | 30 | 1.0000 | 0.805556 | 3.9000 |
| Boundary | 10 | 1.0000 | 0.911111 | 2.6000 |

Intent Override's MTTC of 3.9 is near its floor: the evaluator blocks
conversion until the override is delivered on turn 3 or 4.

### How it got there

Every retained and rejected method is in
[`experiment_history.md`](experiment_history.md). The five largest gains:

| Change | Δ TechnicalScore |
| --- | ---: |
| Conversation state (E2) | +0.589999 |
| Popularity prior (E11) | +0.093921 |
| Phrase bonus (E19) | +0.018594 |
| Category field weight (E32) | +0.011213 |
| Constraint completeness, all routes (E13 + E22) | +0.010156 |

---

## 7. How we worked

This is the part we would most want a reviewer to look at, because it is why
the numbers are trustworthy rather than merely high.

- **Every experiment is recorded, including failures.**
  [`experiment_history.md`](experiment_history.md) holds 46 numbered
  experiments and variants; **26 of them — 57% — were rejected**, each with the
  measurement that killed it and, where we could establish one, a traced
  mechanism.
- **Development and validation splits are separated.** Methods are chosen on a
  fixed 80-session validation split (`techjam-clarification-v1`) and only then
  confirmed on all 200. This is not ceremony: E31 gained `+0.000750` on
  validation and *reversed* to `-0.005428` on the full set. Selecting on the
  full set would have shipped a regression.
- **Thresholds are pre-registered.** Keep/reject criteria are written down
  before the run, so a marginal result cannot be argued into a win afterwards.
- **The evaluator is never modified.** The session viewer records turns by
  wrapping the agent in a proxy that the unmodified `evaluate()` drives, and a
  test asserts that observing a session does not change its metrics.
- **Guards protect the result.** 227 automated tests, including a pinned
  full-set score regression guard and a submission-bundle test that builds the
  declared bundle in an isolated subprocess. That bundle test caught a real
  defect the first time it ran against a moved codebase: the declared bundle
  was missing `starter/ledger.py` and would not have imported.

---

## 8. Limitations

1. **Dependence on the customer naming the catalog's taxonomy.** Removing the
   category phrase costs `0.150384` and 31 sessions. Two mitigating facts: the
   private set is scored by the same `initial_message`, which always emits the
   category, so this needs the simulator *replaced* rather than paraphrased;
   and the realistic paraphrase case (synonym substitution) costs `0.025636`.
   We also verified E32 does not deepen the dependency — its gain persists
   under synonym rewording and is neutral when the category is removed. But it
   is the failure mode we would fix first with more time.
2. **Semantic understanding is shallow.** TF-IDF + SVD is latent semantic
   analysis, not a language model. It cannot resolve "something for a rainy
   hike" to waterproof trail footwear unless those words co-occur in the
   catalog.
3. **Tuned against one simulator.** Several weights exploit regularities of the
   public simulator. We built two stress diagnostics precisely because we did
   not trust the public numbers alone, but neither substitutes for unseen data.
4. **Boundary MRR regressed** at E32, `1.000000 → 0.911111` — one session of
   ten off rank 1. Ten sessions cannot settle a weight; flagged for recheck.
5. **The route classifier is dead code.** 95% accurate, computed every session,
   read by nothing. We keep it as a documented diagnostic rather than deleting
   a measured negative result, but it earns no score.
6. **Memory footprint is 802 MB** and construction takes 25.7 s. A tight
   organizer memory cap is the constraint most likely to break this system.
7. **The scored path imports `analysis/gazetteer.py`** for a single function, so
   the submission bundle carries a diagnostics module it barely uses.

---

## 9. What we would do with more time

1. **Attack the category dependency directly.** Build a category classifier
   over the catalog taxonomy that maps free-text descriptions onto category
   paths, so a customer who says "something warm for winter" still reaches the
   right branch. This targets the `0.150384` exposure and is the highest-value
   remaining work.
2. **A real sentence encoder, offline.** A small pretrained embedding model
   shipped as local weights would test whether genuine semantic retrieval
   rescues the vague-query case where LSA cannot. The rules make this awkward,
   not impossible.
3. **Joint weight optimisation.** Every weight was swept one axis at a time
   around the current point. A joint search may find a better optimum.
4. **Close the resource gap.** Reduce the 802 MB footprint, and record
   behaviour under an enforced memory cap.
5. **Per-route candidate pool size** — the one untested cell from the routing
   work (a global pool increase was rejected as E7).

---

## 10. Team contributions

Commit distribution on `main` at the time of writing:

| Contributor | Commits |
| --- | ---: |
| CHAN1203 | 53 |
| YapHS0514 | 25 + 5 |
| jinlinjinlin | 17 |
| Izackyy | 12 |
| Gentleseann | 3 |

> **To be completed by the team.** Commit counts are a poor proxy for
> contribution and are given only as a factual starting point. Each member
> should describe their own area — retrieval, ranking, conversation state,
> clarification policy, evaluation tooling, the session viewer, documentation —
> before submission. This section is required by the problem statement and must
> not be left as a table of numbers.

---

## 11. Reproduction

```bash
# 1. Python 3.10+ (developed and measured on 3.11.4)
pip install -r requirements.txt

# 2. Catalog — not in the repository
#    Download catalog.jsonl.gz from the participant-kit release, verify it
#    against data/SHA256SUMS, then:
gzip -dk catalog.jsonl.gz && mv catalog.jsonl data/catalog.jsonl

# 3. Score
python -m evaluator.local_evaluator          # TechnicalScore 0.917406

# 4. Tests
python -m unittest discover -s tests         # 227 tests
TECHJAM_RUN_PUBLIC_SET=1 python -m unittest discover -s tests   # + score guard

# 5. Diagnostics
python -m scripts.run_query_stress           # wording sensitivity
python -m scripts.build_coverage_stress_catalog
python -m scripts.run_dual_catalog_evaluation   # catalog sparsity
```

**Network access is not required at any stage after the catalog download.**

**One demonstrated multi-turn session:** run the session viewer
(`python -m frontend.server.app`, then `npm --prefix frontend run dev`) and
enter any sample number 1–200. It replays the session turn by turn through the
unmodified evaluator, showing the conversation, the ranked list, the agent's
slot state, and the hidden intent card advancing together. The viewer is a
development tool and is excluded from the submission bundle.

---

## 12. Further reading

| Document | Contents |
| --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Per-turn walkthrough of the running code |
| [`experiment_history.md`](experiment_history.md) | All 33 experiments, retained and rejected, with a comparison matrix |
| [`EXPERIMENT_WORKFLOW.md`](EXPERIMENT_WORKFLOW.md) | The method: splits, thresholds, evidence rules |
| [`field-weight-sweep.md`](../reports/experiments/field-weight-sweep.md) | The largest recent gain (E32) |
| [`query-stress-and-hybrid-retrieval.md`](../reports/experiments/query-stress-and-hybrid-retrieval.md) | Why the submission stays on BM25 retrieval |
| [`test_gap_audit.md`](test_gap_audit.md) | What the tests guard and what remains unguarded |
| [`merge-to-main-2026-08-31.md`](merge-to-main-2026-08-31.md) | Most recent integration and its risks |
