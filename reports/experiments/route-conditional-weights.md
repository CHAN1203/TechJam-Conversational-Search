# Route-Conditional Reranking Weights (E31)

Date: 2026-08-31
Status: **Rejected.** TechnicalScore `0.906193 -> 0.906479` at best, and the
validation-split winner reverses on the full set.

## Why this was run

`problem_statement.md` makes Dual-Track Routing the first item of Pillar I, and
names "heterogeneous retrieval routing (weights, custom dynamic truncation, and
slot decay over time)" as in scope. This project has a route classifier, but it
is currently **dead code**.

E13 introduced `_classify_route` and gated the completeness bonus behind it.
E22 then found that applying the bonus on every route was worth `+0.004071`,
and set `COMPLETENESS_ALL_ROUTES = True`. That constant short-circuits the only
consumer of the route:

```python
if self.completeness_all_routes or self._session_route[session_id] == "buying":
```

So in the shipped configuration the route is computed once per session and
never read. This experiment asked whether any reranking weight *should* be
route-conditional, which is the question that decides whether the classifier
earns its place.

## Diagnostic first: how good is the classifier?

Before tuning anything, the classifier was measured against the public set's
own `scenario_type` labels. Opening messages were reconstructed exactly as the
evaluator generates them, and `_classify_route(extract_slots(message))` was
compared to the label. Labels were used for scoring the diagnostic only; no
label reaches the agent.

| True scenario | n | predicted Buying | predicted Browsing |
| --- | ---: | ---: | ---: |
| buying | 80 | 75 | 5 |
| browsing | 80 | 3 | 77 |
| intent_override | 30 | 5 | 25 |
| boundary | 10 | 1 | 9 |

**Buying/Browsing accuracy: 152/160 = `0.950`.**

The classifier is not the weak part. Its errors are structural rather than
random:

- False negatives are Buying sessions whose disclosed constraint carries no
  gazetteer slot term -- `"A key requirement is: Imported."`, or a long feature
  sentence like `"Decorative lightweight scarf: 2 wearing ways..."`. The
  message *is* specific; the gazetteer just has no entry for it.
- False positives are Browsing sessions whose category name happens to contain
  a slot word -- `"Travel Accessories Travel Wallets"`, `"Bras Sports Bras"`.

A near-perfect classifier is available by matching the simulator's templates
(`"A key requirement is:"` vs `"but I'm still exploring"`), but
`docs/competition_specification.md` reserves the right to paraphrase simulator
output, so template matching trades measurable robustness for public-set
accuracy the results below show is not the binding constraint anyway.

## Change

`starter/agent.py` gains `route_semantic_weights` and
`route_popularity_weights`, both `Mapping[str, float] | None` defaulting to
`None`. When a route has no entry the global weight is used, so the default
configuration is E28 by construction. `_needs_dense_index` also consults the
per-route semantic weights, so a route-only semantic weight still builds the
index.

Nothing else changes. Retrieval, state, clarification, and the completeness
bonus are untouched.

## Keep/reject threshold

Pre-registered: keep if full-set TechnicalScore improves over `0.906193` with
no scenario regressing by more than one session. The winner is selected on the
fixed `techjam-clarification-v1` validation split (80 sessions) and only then
confirmed on the full 200, per `docs/EXPERIMENT_WORKFLOW.md`.

## Validation split result (80 sessions)

Baseline `0.913103`. Every configuration is flat or worse:

| Configuration | Score | Δ |
| --- | ---: | ---: |
| baseline (global 1.0 / 1.2) | 0.913103 | — |
| browsing semantic 0.0 | 0.913013 | -0.000090 |
| browsing semantic 1.5 | 0.913103 | +0.000000 |
| browsing semantic 2.0 | 0.911228 | -0.001875 |
| browsing semantic 3.0 | 0.911040 | -0.002063 |
| buying semantic 0.0 | 0.913192 | **+0.000089** |
| buying semantic 1.5 | 0.913036 | -0.000067 |
| browsing popularity 0.0 | 0.881287 | -0.031816 |
| browsing popularity 0.6 | 0.913853 | **+0.000750** |
| browsing popularity 2.0 | 0.904211 | -0.008892 |
| buying popularity 0.0 | 0.889563 | -0.023540 |
| buying popularity 0.6 | 0.911854 | -0.001249 |
| buying popularity 2.0 | 0.910071 | -0.003032 |

Two configurations improved, both by less than one session's worth of MRR.

## Full-set result (200 sessions)

| Configuration | Score | Δ | HitRate | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: |
| E28 baseline | 0.906193 | — | 0.995 | 0.789310 | 2.405 |
| browsing popularity 0.6 | 0.900765 | **-0.005428** | 0.990 | 0.782216 | 2.445 |
| buying semantic 0.0 | 0.906479 | +0.000286 | 0.995 | 0.790262 | 2.405 |
| combined | 0.901051 | -0.005142 | 0.990 | 0.783169 | 2.445 |

**The validation winner reverses.** `browsing popularity 0.6` gained
`+0.000750` on 80 sessions and loses `-0.005428` on 200, costing a session of
HitRate. It did raise Browsing MRR (`0.735417 -> 0.747445`) exactly as intended
— and still lost overall, because the same weight change dropped a session that
BM25 popularity had been carrying. That is the split doing its job.

`buying semantic 0.0` survives at `+0.000286`, which is a fifth of a session of
MRR and moves no hit rate. This project has rejected larger margins (E6 at
`+0.000000`, E23) as insufficient evidence.

## Decision

**Reject.** Neither weight is worth making route-conditional. Preserved on
`experiment/route-conditional-weights` with its tests.

Why it failed, beyond the numbers: the headroom this targeted is mostly gone.
HitRate@10 is `0.995` — one miss in 200 sessions — so routing cannot buy
coverage. The remaining loss is MRR, and MRR at this level is decided by which
of several already-retrieved good candidates lands at rank 1. Global weights
tuned across E11-E28 are already near a local optimum for that, and splitting
them by route halves the evidence behind each without adding a signal the
reranker did not have. The completeness bonus was different: E13 worked because
it added information (does this candidate satisfy *every* stated constraint)
rather than re-weighting information already present. E22 then showed even that
is better applied everywhere.

The honest reading of E13 -> E22 -> E31 is that **Buying/Browsing routing has
not paid on this evaluator since E22 removed its last live consumer.**

## What this implies for `_classify_route`

The function is 95% accurate and costs one `extract_slots` call already
computed for other reasons, but nothing reads its output. Two defensible
options, neither taken here because both exceed this experiment's scope:

1. Delete it and `self._session_route`, and record in the ledger that routing
   was measured and did not pay.
2. Keep it and surface the route in the session trace and the viewer, as an
   explicitly-labelled diagnostic that answers Pillar I without claiming a
   score it does not earn.

Option 2 is the recommendation: `problem_statement.md` weights Technical
Execution at 35% and Innovation & Problem Insight at 20%, and a measured
negative result with a working classifier is stronger evidence of problem
insight than silently deleted code. It must not be presented as a scoring
component.

## Reproduction

```powershell
python -m unittest discover -s tests          # 200 tests
python -m evaluator.local_evaluator           # TechnicalScore 0.906193 (default, unchanged)
```

Sweep and full-set confirmation were run with the agent constructed once and
`route_semantic_weights` / `route_popularity_weights` mutated between runs; the
dense index does not depend on either, and `reset()` clears all per-session
state.

## Limitations

- The validation split is 80 sessions. A `+0.000750` reading on it is inside
  the noise floor, which the full-set reversal confirms.
- Only two weights were made route-conditional. Pool size (dynamic truncation)
  and slot decay, both named in `problem_statement.md`, were not tested. E7
  already rejected a global pool increase (`100 -> 500`, `-0.001461`), so a
  per-route pool is the remaining untested cell.
- Public-set only; no coverage-stress run, since the method was rejected on
  official metrics first.
