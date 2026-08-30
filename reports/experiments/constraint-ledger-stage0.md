# Constraint Ledger Stage 0: Override State Correctness Fixes

## Status

**Rejected as specified.** Two of three fixes regressed the validation split and
were reverted. The third is exactly score-neutral and is retained on correctness
grounds, as the Stage 0 gate provides for.

- Date: 2026-08-30
- Baseline: E11 Popularity Prior, validation TechnicalScore `0.844722`,
  full TechnicalScore `0.841838`
- Design: [constraint ledger](../../docs/designs/2026-08-30-constraint-ledger-design.md)
- Split: seed `techjam-clarification-v1`, 80 validation sessions

## Commands

```powershell
python -m unittest discover -s tests
python -m scripts.run_popularity_sweep --weights 1.2 --output reports\experiments\constraint-ledger-stage0.json
python -m scripts.trace_session --sample public_0052
```

## Hypothesis

The tracer showed that in 26 of 30 intent_override sessions the target is
already inside the scored Top-10 before the override, and that 6 of those lose
it at the override turn. Three defects were held responsible:

- **A, surface-form loss.** The override rebuilds the query term list from the
  gazetteer's singular slot terms, so `tees` becomes `tee`. FTS5 `unicode61`
  does not stem, so the query stops matching documents it matched one turn
  earlier.
- **B, conversational filler.** The override sentence's own words -- `actually`,
  `ignore`, `earlier`, `preference`, `what`, `need` -- become permanent query
  terms.
- **C, unguarded slot extraction.** The no-preference guard covers
  `_constraint_terms` but not `extract_slots`, so `"no additional preference for
  use_case"` files `case` under `category`, where `DURABLE_SLOTS` then protects
  it from every later override.

Each fix was given a targeted test that failed against E11 for its stated
reason before implementation.

## Ablation

Each row changes only the named fixes; retrieval, reranking, clarification,
popularity weight `1.2`, the evaluator, and the split are identical throughout.
The `none` row reproduces E11 bit for bit, which validates the harness.

| Configuration | HitRate@10 | MRR | MTTC | TechnicalScore | Intent Override HR | **Validation** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| none (E11) | 0.965 | 0.662125 | 2.965 | 0.841838 | 0.933333 | **0.844722** |
| A surface form | **0.970** | 0.649028 | 2.895 | 0.841808 | **0.966667** | 0.843524 |
| B stopwords | 0.955 | 0.660669 | 2.970 | 0.836301 | **0.866667** | 0.837149 |
| C slot guard | 0.965 | 0.662125 | 2.965 | 0.841838 | 0.933333 | **0.844722** |
| A + C | **0.970** | 0.648903 | 2.895 | 0.841771 | **0.966667** | 0.843430 |
| A + B + C | 0.965 | 0.661669 | **2.860** | **0.843801** | 0.933333 | 0.839274 |

No configuration reaches the gate value of `0.844722` except C, which equals it
by changing nothing.

## Findings

### 1. Fix A works exactly as predicted, and the score still does not move

A recovers one intent_override session, raising that scenario from `0.933333`
to `0.966667`, and improves MTTC. It also lowers MRR by `0.013097`. Under the
official weighting the three effects almost exactly cancel:

```text
HitRate  +0.005000 x 0.50 = +0.002500
MRR      -0.013097 x 0.30 = -0.003929
Efficiency +0.007000 x 0.20 = +0.001400
                              ---------
                              -0.000029   (measured: -0.000030)
```

The mechanism is real; the plural surface forms match a wider document set, so
the session that was previously lost is now found, and several sessions where
the target was already found rank it slightly lower.

### 2. Fix B is actively harmful, and that is the important result

Removing conversational filler costs two intent_override sessions, dropping
that scenario from `0.933333` to `0.866667`. The filler is load-bearing.

The mechanism is candidate pool composition, not relevance. Those terms sit in
the FTS5 `MATCH` expression, so they widen the set of documents that can enter
the Top-100 pool. They contribute nothing in the reranker, where a term that
matches no field adds zero to every candidate. Removing them narrows the query
and returns a different hundred documents to rerank, and empirically a worse
hundred.

The current agent therefore depends on query *width* rather than query
*cleanliness*, and it did so without anyone having decided that.

### 3. Fix C changes no outcome on the public set

C produces metrics identical to E11 in every digit and every scenario. The
`category: case` pollution is real but never decides a session among 200. This
matches E6, where a better-motivated override rule also produced zero measured
change.

### 4. The fixes do not compose

`A + B + C` scores `0.843801` on the full set, above both `A + C` (`0.841771`)
and `B` alone (`0.836301`), while scoring worst of all on validation
(`0.839274`). Reasoning about these changes one at a time does not predict their
combination, so "obviously correct" is not a safe basis for bundling them.

## Decision

- **A: reject.** Fails the validation gate at `0.843524`. The implementation and
  its test are reproduced below and should be preserved on a review branch, per
  the T8 precedent.
- **B: reject.** Fails at `0.837149` and is the largest single regression
  measured in this experiment.
- **C: retain.** Exactly score-neutral, so it is retained on the correctness
  justification the Stage 0 gate allows: it stops a wrong value from entering
  the one slot type that survives every override. The retained agent reproduces
  E11 at validation `0.844722` and full `0.841838`.

Automated tests: 102 before, 103 after. The two tests protecting rejected
behaviours were removed with their code.

## Rejected implementation, preserved for review

```python
def _surface_terms(slot_term: str, session_terms: list[str]) -> list[str]:
    """Re-express a normalized slot term in the customer's own wording."""
    surfaces: list[str] = []
    for token in _terms(slot_term):
        match = next(
            (term for term in session_terms if normalize_term(term) == token),
            None,
        )
        surfaces.append(match or token)
    return surfaces
```

Used in the override branch in place of `_terms(term)`. Fix B added a
`CONVERSATIONAL_STOPWORDS` set of `actually, additional, earlier, ignore,
matters, need, prefer, preference, what` to `STOPWORDS`.

## Implications for Stage 1

Stage 1 proposed deleting `_session_terms` and projecting the query from active
ledger entries. Finding 2 says that projection must not be a *narrower* query
than E11 produces today, or Stage 1 inherits B's regression of `-0.005448`
before it has done anything else.

Two consequences for the design:

1. Unclassified tokens must be admitted as ledger entries with `slot: null` and
   projected like any other active entry. The spec already requires this; it is
   now a hard requirement rather than a nicety.
2. The Stage 1 structural invariant should be extended: as well as losing zero
   query terms at the override turn, the projected query must contain at least
   as many distinct terms as E11's accumulated list at the same turn. That is
   checkable with the tracer and cheap to assert.

A separate hypothesis this raises, which this experiment does not test: if pool
composition is doing this much work, the pool-size decision (E7, rejected at 500
with a contaminated gazetteer) may interact with query cleanliness and could be
worth re-measuring jointly. That is speculation and must not be reported as a
result.

## Limitations

- 30 intent_override sessions, of which single sessions move the scenario rate
  by `0.033333`. Every effect measured here rests on one to two sessions.
- The full set and the validation split disagree in sign for `A + B + C`
  (`+0.001963` full, `-0.005448` validation). Selection followed the workflow
  and used validation only, but the disagreement is itself a warning that these
  differences are near the noise floor of a 200-session set.
- The filler words removed in B were chosen partly from evaluator message
  templates. A different simulator would produce different filler, so finding 2
  describes this pipeline's sensitivity to query width, not a general property
  of conversational stopwords.
