# Query Stress and Union-Hybrid Retrieval (E33)

Date: 2026-08-31
Status: **Union-hybrid rejected. Diagnostic retained.** The submission stays on
`retrieval_mode="bm25"`.

## The question

Everything retained so far was selected on a public set whose customer
utterances come from a small set of fixed sentence frames. A reasonable worry
before submitting: the private sessions may be vaguer or worded differently,
and a system tuned on literal overlap could fall over where a semantic
retriever would not. If so, it is worth **giving up public score** for a hybrid
that survives the private set.

That is a testable claim, so it was tested rather than argued.

## First correction: the system is already hybrid at the ranking stage

`SEMANTIC_WEIGHT = 1.0` has been on by default since E18. Every candidate's
score already includes a dense cosine-similarity term. What is BM25-only is
**retrieval** — which 100 candidates reach the reranker.

So the exposure is precisely scoped: *if BM25 fails to retrieve the target into
the pool, no amount of semantic reranking can recover it.* That is the only
thing a hybrid retriever could fix.

## The missing diagnostic

T25 stresses the **catalog** by masking sparse fields. Nothing stressed the
**customer**. `analysis/query_stress.py` adds that: a transparent proxy rewrites
the message in flight while the unmodified evaluator drives the session, so
ground truth and scoring are untouched.

| Level | What changes | What survives |
| --- | --- | --- |
| `L0_clean` | nothing | — |
| `L1_no_scaffold` | the simulator's fixed sentence frames removed | every constraint |
| `L2_no_category` | the quoted catalog taxonomy replaced with "something" | constraints, but the category **information** is gone |
| `L3_synonyms_only` | head nouns swapped (`watches -> timepieces`) | all information, reworded |

`L1` and `L3` are rewordings. `L2` removes information, and is the severe case.

## Result 1: the dependency is real, and it is on the category phrase

Full 200-session public set, current retained configuration:

| Level | Score | HitRate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: |
| L0 clean | 0.917406 | 0.995 | 0.823353 | 2.355 |
| L1 no scaffold | 0.916277 | 0.995 | 0.817923 | 2.330 |
| **L2 no category** | **0.767022** | **0.840** | 0.703075 | 4.195 |
| L3 synonyms only | 0.891770 | 0.965 | 0.805901 | 2.625 |

Sentence framing is irrelevant (`-0.001129`). Synonym rewording costs
`-0.025636`. **Removing the category phrase costs `-0.150384` and 31 sessions
of HitRate@10.** The whole system is load-bearing on the customer naming the
catalog's own taxonomy.

## Result 2: hybrid retrieval does not fix it

E17 fused BM25 and dense by RRF then truncated to 100, and its report traced
the regression to that truncation evicting correct candidates. `retrieval_mode
= "union"` (E33) avoids it by construction: dense hits are **appended after**
BM25's full pool rather than competing for its slots, so BM25 recall cannot be
displaced and the reranker decides.

| Level | bm25 | union | dense | union − bm25 |
| --- | ---: | ---: | ---: | ---: |
| L0 clean | **0.917406** (hit 0.995) | 0.912799 (hit 0.995) | 0.627875 (hit 0.670) | **-0.004607** |
| L2 no category | 0.767022 (hit 0.840) | 0.768862 (hit 0.845) | 0.398900 (hit 0.425) | **+0.001840** |
| L3 synonyms only | 0.891770 (hit 0.965) | 0.890725 (hit 0.970) | 0.605843 (hit 0.650) | **-0.001045** |

**Union costs `0.004607` on the public set and buys `0.001840` in the worst
stress case** — one session of HitRate. At the realistic paraphrase level it is
net negative. Dense retrieval alone is catastrophic at every level.

The insurance does not insure anything, so the premium is not worth paying.

## Why the hypothesis failed

The dense index is TF-IDF + Truncated SVD over the same catalog text
(`starter/dense.py`) — Latent Semantic Analysis, not a sentence embedding. It
models term co-occurrence, so it is still fundamentally lexical. When the query
loses its most informative content, LSA has no better idea what "something"
means than BM25 does. **The two degrade together rather than complementarily**,
which is exactly what the table shows: dense's score falls by a larger fraction
than BM25's at L2 (`0.628 -> 0.399`) rather than holding up.

A real pretrained sentence encoder might behave differently. It is also
unavailable: `docs/submission_rules.md` warns that scoring may run without
network access, and `problem_statement.md` puts downloaded model weights and
heavy vector infrastructure out of scope. So the alternative that could have
justified the trade cannot be built here.

The honest framing: **this is a query-content problem, not a
retrieval-algorithm problem.** No retrieval strategy available within the rules
recovers information the customer never said.

## Result 3: E32 is not the fragile bet it looks like

E32 raised the category field weight, so it is fair to ask whether it deepened
this exact dependency. It does not:

| Level | categories 3.0 | categories 6.0 | E32 gain |
| --- | ---: | ---: | ---: |
| L0 clean | 0.906193 | 0.917406 | +0.011213 |
| L2 no category | 0.766593 | 0.767022 | +0.000429 |
| L3 synonyms only | 0.881185 | 0.891770 | +0.010585 |

The gain **persists under synonym rewording** (`+0.010585`, essentially the
clean gain) and is **neutral when the category is removed entirely**. E32 does
not add fragility; it exploits a dependency the system already had. Combined
with its coverage-stress behaviour (gain grows to `+0.021101`), it is the
best-evidenced layer in the project.

## Decision

**Reject union-hybrid; submit `retrieval_mode="bm25"`.**

The trade the question proposed — pay public score for private robustness — is
only worth making if the payment buys robustness. Measured, it buys `0.001840`
at a cost of `0.004607`, and is net negative at the realistic stress level.

**Retain the diagnostic.** `analysis/query_stress.py`,
`scripts/run_query_stress.py` and `tests/test_query_stress.py` stay, because
the L2 number is the single most important limitation to disclose in the
submission report and it should be reproducible.

**Retain `retrieval_mode="union"`** as a non-default mode with the E17
truncation flaw fixed, so the comparison can be rerun if the private-set
behaviour turns out to differ.

## How much should the L2 number actually worry us?

Less than its size suggests, for one specific reason: the private set is scored
by **the same `evaluator/local_evaluator.py`**. `initial_message` always emits
`coarse_category(target.categories)`. L2 cannot occur unless the organizer
replaces the simulator, not merely paraphrases it. The specification's
paraphrase clause covers wording, and L1/L3 — the levels that model wording —
cost `0.001129` and `0.025636` respectively.

So the realistic downside is roughly `0.026`, not `0.150`, and no available
retrieval change reduces it.

## Reproduction

```powershell
python -m unittest discover -s tests            # 214 tests
python -m scripts.run_query_stress              # all levels, all modes
python -m scripts.run_query_stress --modes bm25 # default configuration only
```

## Limitations

- Four stress levels, one synonym map of 28 head nouns, hand-written. It is a
  smoke test for wording sensitivity, not a model of how a real paraphraser
  would behave.
- L2 removes information rather than rewording it, so it is an upper bound on
  damage rather than a forecast.
- Only `union` was tried as a fusion rule. RRF with an enlarged post-fusion
  pool (E17's flaw fixed a different way) was not retested, though union
  dominates it by construction on the recall argument.
- No sentence-embedding retriever was tested, because none can ship under the
  submission rules. That leaves the central counterfactual unmeasured.
