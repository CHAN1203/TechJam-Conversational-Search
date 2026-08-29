# RRF Hybrid Retrieval

Date: 2026-08-30
Status: **rejected.** TechnicalScore `0.847923 -> 0.830909` (-0.017014).
Root cause traced precisely (see Result): fusion truncates the candidate
pool to 100 by *fused* rank before the reranker ever runs, which can evict
a mediocre-BM25-rank-but-genuinely-correct candidate to make room for
products whose only merit is also appearing in dense's separate (weaker,
noisier) ranking.

## Hypothesis

`TechJam.docx` Layer 1's third option, RRF Hybrid Retrieval: "Ignores
absolute scores and directly combines the BM25 leaderboard with the Dense
leaderboard... fairly merges the best literal match and closest meaning
lists." Never attempted -- E16 measured BM25 and dense retrieval
separately and found they are not redundant: dense recovers 2 of E13's 6
public misses that BM25 never reaches (`public_0052`, `public_0179`),
while BM25 correctly handles 63 sessions dense alone gets wrong. E16 was
deliberately a full replacement to isolate that evidence; this experiment
is the fusion E16 was building toward.

Hypothesis: fusing the two ranked candidate lists with Reciprocal Rank
Fusion (RRF), rather than replacing one with the other, should recover
some or all of dense's 2 unique hits while keeping BM25's precision on the
193 sessions it already gets right (194 counting the overlap with dense).

## Change from the last retained method (E13, TechnicalScore 0.847923)

- `starter/agent.py`: `Agent(retrieval_mode="rrf")` fetches BOTH the BM25
  candidate list (unchanged SQL query, same pool size) and the dense
  index's top-N list (`starter/dense.py`, from E16), then fuses them by
  standard RRF: `score(doc) = sum over lists containing doc of 1/(k + rank)`,
  `k = 60` (the constant from the original RRF paper, Cormack et al. 2009,
  and the value named in `docs/EXPERIMENT_WORKFLOW.md`'s own design intent
  for this layer). The fused, re-ranked-by-RRF-score top-100 becomes the
  candidate pool that E1/E11/E13's existing reranker, popularity, and
  Buying/Browsing routing logic operate on unchanged -- fusion only
  changes *which* 100 candidates enter that pipeline, not what happens to
  them afterward.
- `retrieval_mode="bm25"` (the default) and `retrieval_mode="dense"`
  (E16's isolated test) are both unaffected -- this adds a third mode, it
  does not change the other two.

## Baseline

E13 Buying/Browsing Routing, `TechnicalScore 0.847923`, `HitRate@10 0.970`,
full 200-session public set. E16's dense-only run
(`reports/experiments/dense-retrieval.json`) as the secondary comparison
for complementarity.

## Keep/reject threshold

Keep if full-set TechnicalScore improves over `0.847923` with no scenario
regressing by more than 1 session. Given E16 found only 2 uniquely-dense
hits against 63 uniquely-BM25 hits, the realistic best case is recovering
some fraction of those 2 sessions -- a small, not dramatic, improvement is
the honest expectation, recorded before running anything.

## Tests that will prove the behavior

1. A pure RRF fusion function: given two ranked lists with a partial
   overlap, the fused order matches hand-computed RRF scores for a small,
   verifiable case.
2. A document appearing in both lists outranks one appearing in only one
   list, all else equal (RRF's core property).
3. Fusion degrades gracefully when one list is empty (falls back to
   ranking by the other alone, not crashing or producing nothing).
4. `retrieval_mode="bm25"` and `retrieval_mode="dense"` remain byte-for-byte
   unaffected by this addition (regression guard, same style as E16's).

## Known risks

- `k=60` is the standard RRF constant, not swept against this dataset.
- Fusing a much weaker overall signal (dense, TechnicalScore 0.600 alone)
  into a much stronger one (BM25, 0.848 alone) risks the weak signal
  demoting good BM25 candidates just as easily as promoting good dense-only
  ones -- RRF's rank-based (not score-based) design limits this, but it is
  exactly what the evaluator run below will show either way.

## Implementation

New `starter/fusion.py::reciprocal_rank_fusion`. `starter/agent.py` gains
`Agent(retrieval_mode="rrf")`: fetches BM25's top-100 and dense's top-100
independently, fuses them, and truncates to the top 100 by *fused* rank --
that truncated set is what E1/E11/E13's existing reranker then scores, same
as before. `retrieval_mode="bm25"` internals were refactored into a
`_bm25_rank()` helper (reused by both bm25 and rrf modes) with a dedicated
regression test confirming byte-identical output to the un-refactored
version.

6 new tests (`tests/test_fusion.py`) plus 2 agent-integration tests
(`tests/test_conversation_state.py::RrfHybridRetrievalModeTest`). One test's
initial assertion was itself wrong on inspection: RRF's rank-based scoring
is convex, so two extreme ranks {1,3} score marginally *higher* than two
middling ranks {2,2} -- a real property of the formula, not a bug, and the
test was corrected to a case that isn't sensitive to that edge effect
before being trusted. 107/107 project tests pass.

## Result

| Metric | E13 (BM25) | RRF Hybrid |
| --- | ---: | ---: |
| HitRate@10 | 0.970 | 0.945 |
| MRR | 0.671744 | 0.665696 |
| MTTC | 2.930 | 3.065 |
| TechnicalScore | **0.847923** | 0.830909 |

Session-by-session against E13: **1 recovered** (`public_0071`, not either
of E16's two dense-only hits), **6 lost**
(`public_0040, public_0083, public_0087, public_0103, public_0174,
public_0198`). Net -5 sessions.

**Root cause, traced precisely on `public_0040`** (a session E13 hits at
rank 1 -- as confident a hit as this pipeline produces): the target enters
BM25's own top-100 at turn 6, but only at rank 72. It is **not** in dense's
top-100 at all (`None of 100`, every turn). E13's reranker is evidently very
effective at recognizing a mediocre-BM25-rank-but-genuinely-correct
candidate once it's in the pool -- it promotes rank 72 all the way to rank 1
after applying field weighting, the completeness bonus, and popularity.
Under RRF, though, the candidate *pool itself* is truncated to the top 100
by **fused** rank before the reranker ever runs: enough other products get
a joint BM25+dense score boost (from also appearing, even mediocrely, in
dense's separate ranking) to push the target's fused rank *outside* the
top 100 entirely. The reranker never gets a chance -- the candidate isn't
in its input at all. This is not a reranking failure; it's retrieval
discarding a genuinely correct candidate to make room for others whose only
qualification is agreement between two lists, one of which (dense, measured
standalone in E16 at TechnicalScore 0.600) is meaningfully noisier on this
specific dataset.

## Decision

**Reject.** Confirms E16's own prediction risk directly: "fusing a much
weaker overall signal into a much stronger one risks the weak signal
demoting good BM25 candidates." That happened net 6 times for 1 recovery.
The mechanism (pool truncation before reranking) is now understood
precisely, which is more useful than the raw score: it points at a
specific, narrow fix rather than "hybrid retrieval doesn't work here."

## Limitations and next step

A narrower fix follows directly from the traced mechanism: take the
**union** of BM25's own top-100 and dense's top-100 (padding, not
truncating), so BM25's full candidate net is never shrunk to make room for
dense-only agreement -- dense would then only ever *add* candidates BM25's
net missed, never displace ones it already caught. Not attempted here, to
keep this experiment to testing standard RRF as the doc describes it
before trying a variant.

## Reproduction

```
python -m unittest discover -s tests -v
python -m scripts.run_retrieval_mode --retrieval-mode rrf --output reports/experiments/rrf-hybrid-retrieval.json
```
