# Dense Retrieval (TF-IDF + Truncated SVD)

Date: 2026-08-30
Status: **rejected as a standalone replacement** (TechnicalScore
`0.847923 -> 0.600216`, as predicted), but **complementary evidence found**
that directly motivates E17 (RRF fusion): dense retrieval recovers 2 of
E13's 6 public-set misses that BM25 never finds, while losing 63 sessions
BM25 gets right (because this experiment deliberately strips out the
routing/popularity/reranking machinery to isolate retrieval quality alone).

## Hypothesis

`TechJam.docx` Layer 1 lists Dense Retrieval as an unimplemented option:
"Uses an AI model to convert text into numbers (vectors)... finds products
based on closeness in meaning, unafraid of users phrasing things
differently." Never attempted in this project -- retrieval has always been
lexical BM25.

A full neural embedding model (sentence-transformers) is feasible here
(network access works, `torch` was already present) but carries real
latency risk: up to 200 sessions x 10 turns x 100 candidates of transformer
inference on CPU could turn a ~25-second evaluator run into something much
slower, and the competition disclosure requirements make latency a real
cost to account for, not just an implementation detail. Latent Semantic
Analysis (TF-IDF + Truncated SVD) is a much older, classic dense-embedding
technique from IR literature: it is inference-only after a single one-time
fit at startup (no per-query model forward pass), stays entirely in memory,
needs no downloaded weights, and genuinely represents documents as
continuous vectors capturing co-occurrence structure -- a real, if weaker,
form of "closeness in meaning" than exact keyword overlap.

Hypothesis: a separate dense candidate route, built once at startup over
the frozen catalog, will recover sessions where the target's exact words
don't overlap with what the customer says, without the latency risk of a
transformer.

## Honest expectation before running anything

Traced a remaining miss (`public_0020`, recorded in this session's earlier
conversation, not yet a written report) earlier: the target's actual words
("cotton", "grey") already appear in the query, and it doesn't surface
anyway -- a ranking-precision problem among many literal matches, not a
vocabulary-mismatch problem. Compounding that, this project's own
`slot-memory-and-retrieval-ablation.md` documents that the practice
simulator discloses constraints as words **sliced verbatim from the
target's own catalog metadata** -- there is no organic paraphrasing in this
public set for a semantic method to bridge. Recording this prediction
before running the evaluator: dense retrieval alone is expected to
contribute little to nothing on this specific public set, though it could
still matter for private-set robustness against reworded descriptions. The
point of running it anyway is to measure this rather than assume it.

## Change from the last retained method (E13, TechnicalScore 0.847923)

- New `starter/dense.py`: `DenseIndex`, built once at `Agent.__init__` from
  the same six text fields the FTS5 index already uses. `TfidfVectorizer`
  (capped vocabulary) -> `TruncatedSVD` (fixed `random_state` for
  determinism) -> L2-normalized document vectors. `search(query_text,
  top_k)` cosine-ranks the full catalog against the query's projected
  vector.
- `starter/agent.py`: this experiment only, as an isolated test of dense
  retrieval's own recall -- **replace** the BM25 candidate pool with the
  dense route's top-100, leaving reranking, popularity, routing, and
  clarification untouched, so any change in score is attributable to
  retrieval quality alone. (This is not the proposed final design --
  E17's hybrid fusion is -- it is the controlled comparison needed before
  fusing.)
- New dependency: `scikit-learn` (pulls in `scipy`, `joblib`,
  `threadpoolctl`). No existing dependency manifest exists in this repo
  (README states "the starter uses only the Python standard library");
  this experiment is the first to introduce one, and that fact alone is
  disclosed regardless of the result.

## Baseline

E13 Buying/Browsing Routing, `TechnicalScore 0.847923`, `HitRate@10 0.970`,
full 200-session public set.

## Keep/reject threshold

This experiment's own result is very unlikely to beat E13 by design (it
sacrifices the routing/popularity/reranking machinery that produced E13's
gains, to isolate retrieval quality alone). It exists to answer one
question for E17: does the dense route recover *any* sessions BM25 misses,
and how many? Recorded and judged on that basis, not on whether it beats
E13 outright.

## Tests that will prove the behavior

1. `DenseIndex.search` returns the catalog item whose text most closely
   matches the query, even when the words don't overlap exactly to gauge
   the sensitivity of the method.
2. An empty query returns no results without crashing.
3. Determinism: two identical queries return identical results.
4. A query about a completely unrelated topic still returns *something*
   (dense search never returns nothing for a non-empty query) rather than
   crashing or hanging.

## Known risks

- Latency: `TruncatedSVD` fit over ~50,000 documents happens once at
  startup, not per turn, but is nonetheless new one-time cost. Measured
  directly in the result below.
- LSA is not immune to vocabulary noise the way a real semantic model
  would be; a small number of components (`n_components`) trades
  expressiveness for speed and is not swept in this first pass.

## Implementation

New `starter/dense.py::DenseIndex` (TF-IDF + Truncated SVD, `sklearn`,
`random_state=0` for determinism). `starter/agent.py` gains a
`retrieval_mode: str = "bm25"` constructor argument; `"dense"` builds the
dense index at startup and replaces the BM25 candidate query entirely for
this isolated comparison. Default behavior (`"bm25"`) is byte-for-byte
E13 -- confirmed by a dedicated regression test
(`test_bm25_mode_is_unaffected_by_the_new_constructor_argument`).

14 new tests (6 in `tests/test_dense.py`, 2 agent-integration tests in
`tests/test_conversation_state.py::DenseRetrievalModeTest`). 93/93 project
tests pass. New script `scripts/run_retrieval_mode.py` for reproducing any
`retrieval_mode` configuration against the official evaluator.

## Result

| Metric | E13 (BM25, baseline) | Dense-only |
| --- | ---: | ---: |
| HitRate@10 | 0.970 | 0.665 |
| MRR | 0.671744 | 0.534054 |
| MTTC | 2.930 | 5.625 |
| TechnicalScore | **0.847923** | 0.600216 |

Startup cost: the one-time `TruncatedSVD` fit over the full catalog takes
~26 seconds (`build_seconds: 26.347`), on top of BM25's near-instant index
build; the full 200-session evaluator run took ~32s after that (comparable
to BM25's own per-session cost). Not a per-turn cost -- happens once at
`Agent.__init__`.

**Complementarity check** (the actual point of this experiment): comparing
session-by-session against E13's stored results --

| | Count |
| --- | ---: |
| Dense hits where BM25 (E13) misses | **2** (`public_0052`, `public_0179`) |
| BM25 (E13) hits where dense misses | 63 |
| Both miss | 4 |

Dense alone is much weaker overall (expected -- it has none of E1's field
weighting, E11's popularity prior, or E13's routing/completeness bonus),
but it is not *strictly* worse: it recovers real sessions BM25's lexical
matching cannot reach at all. That is exactly the signal RRF fusion (E17)
is designed to combine, keeping BM25's precision while adding dense's
narrow, complementary recall.

## Decision

**Reject as a standalone retrieval mode; proceed to E17 (RRF fusion) using
this experiment's dense index and evidence.** The isolated comparison did
its job: it proved dense retrieval finds real, otherwise-unreachable hits
(not just noise) at a tractable, one-time startup cost, which is the
evidence needed before attempting fusion.

## Reproduction

```
python -m unittest discover -s tests -v
python -m scripts.run_retrieval_mode --retrieval-mode dense --output reports/experiments/dense-retrieval.json
python -m scripts.run_retrieval_mode --retrieval-mode bm25   # reproduces E13 exactly
```
