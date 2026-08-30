# Query-Side Stemming

Date: 2026-08-30
Status: **rejected.** TechnicalScore `0.868476 -> 0.821424` (-0.047052).
The hypothesis that a pure superset expansion is "essentially risk-free"
was wrong -- traced and corrected below, not just asserted.

## Hypothesis

Not from `TechJam.docx` -- researched separately. `analysis/gazetteer.py`
already singularizes matched vocabulary terms (`normalize_term`), but only
for gazetteer-slot extraction. The raw free-text search terms that build
the actual FTS5 query (`_terms()` in `starter/agent.py`) are never stemmed:
FTS5's `unicode61` tokenizer does no stemming either, on the index side or
the query side. So a customer saying "shoes" (plural) literally cannot
match a catalog title that only says "shoe" (singular) via that specific
word, purely because of surface-form mismatch unrelated to genuine
relevance -- a classic, well-known IR problem (stemming/lemmatization),
untouched everywhere except the narrow gazetteer path.

Hypothesis: expanding each query term with its singularized form (when
different) as an *additional* OR-term -- not re-indexing the catalog,
not replacing anything -- should recover some literal-word mismatches at
essentially zero risk (a superset of the current query, never a subset).

## Change from the last retained method (E19, TechnicalScore 0.868476)

- New `starter/agent.py::_expand_with_stems(terms)`: for each term, add
  `analysis.gazetteer.normalize_term(term)` (already public, already
  proven on the gazetteer path) as an extra term when it differs from the
  original, deduplicated. Reuses existing, tested normalization logic
  rather than writing a second stemmer.
- Applied to the term list used for **both** the FTS5 MATCH expression and
  the terms passed to `rerank_candidates` (a stemmed variant should also
  count toward field-weight matching, not just retrieval) -- but **not**
  to `self._session_terms[session_id]`, the stored accumulated list that
  seeds next turn's query, so stemmed variants don't compound across turns.

## Baseline

E19 Phrase (Bigram) Bonus, `TechnicalScore 0.868476`, `HitRate@10 0.980`,
full 200-session public set.

## Keep/reject threshold

Keep if full-set TechnicalScore improves over `0.868476` with no scenario
regressing by more than 1 session. This is a pure superset expansion (no
existing term is ever removed), so the main risk is not "losing" matches
but diluting `bm25()`'s own term-frequency statistics with near-duplicate
tokens -- exactly what the evaluator run below checks.

## Tests that will prove the behavior

1. A plural query term gains its singular form as an extra term when they
   differ.
2. A term that is already its own singular form (e.g. "shoe") is not
   duplicated.
3. Order is preserved: original terms first, then added stems, with no
   duplicates anywhere in the combined list.
4. An agent-level test: a customer says "running shoes" (plural) and the
   only matching catalog title says "running shoe" (singular) -- the
   product is still found.

## Known risks

- `normalize_term`'s singularization rules were tuned for catalog taxonomy
  nodes and mined vocabulary terms (see `analysis/gazetteer.py`'s
  `_SIMPLE_PLURALS` comment), not free customer speech -- applying it more
  broadly could occasionally produce a wrong or nonsensical stem for a
  word it was never validated against, though the result is only ever an
  *added* term, never a replacement, capping the downside.

## Implementation

New `starter/stemming.py::expand_with_stems` (4 tests, `tests/test_stemming.py`),
wired into `starter/agent.py`: applied to the term list used for the FTS5
`MATCH` expression and the reranker's `query_terms`, but not to
`self._session_terms[session_id]`. 1 new agent-level test. 126/126 project
tests pass before the evaluator run below.

## Result

| Metric | E19 (baseline) | Query stemming |
| --- | ---: | ---: |
| HitRate@10 | 0.980 | 0.930 |
| MRR | 0.677607 -> | 0.666079 |
| MTTC | 2.815 | 3.170 |
| TechnicalScore | **0.868476** | 0.821424 |

Session-by-session: **2 recovered, 12 lost.** Net -10.

## Root cause, traced precisely on `public_0028`

Without stemming, the target sits at BM25 rank **95 of 100** from turn 3
onward -- barely inside the retrieval pool, but inside it. With stemming,
the query gained `case`, `organizer`, `wallet`, `matter` as extra OR-terms
(from `cases`, `organizers`, `wallets`, `matters`). The target's BM25 rank
under the expanded query: **not in the top 100 at all.**

**Why the "pure superset, essentially risk-free" hypothesis was wrong:**
retrieval's SQL query is `... MATCH ? ORDER BY bm25(...) LIMIT 100`. Adding
more OR-terms doesn't just add new *ways* for the true target to match --
it also makes *more of the other 50,000 products* qualify for the match at
all (anything containing any of the new stem terms now competes for the
same 100 slots). The pool is a **fixed-size window**, not an unbounded
list: growing the set of terms that can satisfy `MATCH` grows the
competition for that window at least as much as it helps the specific
target you're trying to find. A term is only "risk-free to add" if it
does not change who else qualifies -- which query expansion, by
definition, does not guarantee. This is the same fundamental failure mode
E17 found with RRF fusion (a borderline-but-correct candidate evicted from
the pool before the reranker runs), reached here by a completely different
mechanism (broadening one query's match criteria, not merging two ranked
lists).

A contributing, secondary factor: several added stem terms in this trace
(`matter`, from `matters`) come from the evaluator's own boilerplate
phrasing ("For that, what **matters** is: ...") rather than genuine
customer content -- already noisy before stemming, and stemming adds one
more near-duplicate low-signal term to an already crowded query rather
than fixing anything for this specific case.

## Decision

**Reject.** Confirms, via a second independent mechanism, the same lesson
E17 already taught: this project's fixed-size retrieval cutoff is more
fragile to *any* change that broadens the matching net than it first
appears, whether that broadening comes from a second ranked list (E17) or
extra query terms (this experiment). A change that adds recall in isolated
testing can still net-lose once the fixed pool size is accounted for.

## Reproduction

```
python -m unittest discover -s tests -v      # 126 tests
python -m evaluator.local_evaluator          # TechnicalScore 0.821424
```
