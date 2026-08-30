# E23-B: Exhaustion-Triggered Catalog IDF

## Status

**Rejected.** Zero sessions of 200 changed outcome, at any threshold. The value
of the experiment is the mechanism it exposed, which also explains why E8 and
E10 failed.

- Date: 2026-08-30
- Baseline: E22-C, `Agent(state_model="ledger", no_gain_probe=1)`,
  full `0.868714`, validation `0.867378`
- Prior diagnostic: [rank-margin](rank-margin-diagnostic.md)

## Hypothesis

The three in-pool Buying misses all carry hard constraints made of generic
material words (`fabric`, `cotton`, `spandex`), and the reranker weights every
query term identically. Weighting by catalog rarity should let a distinctive
word outrank a ubiquitous one.

E8 rejected catalog IDF applied unconditionally, and E10 rejected it routed on
an override signal. This experiment applies it on a third signal: the
information-gain counter from E22-C. The reasoning was that while information
is still arriving, any term may yet become decisive, so discounting early risks
discarding a constraint the customer has not finished expressing; once the
counter says nothing new has arrived, the term list is final and rarity can be
applied with no such risk. The counter is also a perfect predictor of failure
on the public set: every session that gets stuck fails, and every session that
fails gets stuck.

## Result

| `exhaustion_idf` | HitRate@10 | MRR | MTTC | TechnicalScore | Sessions changed vs off |
| ---: | ---: | ---: | ---: | ---: | ---: |
| off | 0.980 | 0.698381 | 2.540 | 0.868714 | — |
| 1 | 0.980 | 0.698381 | 2.540 | 0.868714 | **0** |
| 2 | 0.980 | 0.698381 | 2.540 | 0.868714 | **0** |

Not one session's hit, hit turn, or rank changed. The mechanism was verified to
fire: on triggering turns the per-term multipliers move from a flat `1.0` to a
spread of `0.93` to `7.42`.

## Why nothing changed

The reordering is real; it simply never lifts a target into the Top-10. Pool
position of the target on the stuck turn, for the four Buying misses:

| Session | Without IDF | With IDF | |
| --- | ---: | ---: | --- |
| `public_0020` | not in pool | not in pool | unreachable either way |
| `public_0054` | 11 | **27** | worse |
| `public_0161` | 17 | **30** | worse |
| `public_0179` | 28 | 27 | marginally better |

IDF moves the target *away* from the Top-10 in two of the three cases where it
was reachable. The hypothesis was not merely ineffective; it had the direction
wrong.

## The mechanism, and why it also explains E8 and E10

Catalog IDF weights by rarity. In this pipeline the rarest words in the query
are not the most informative ones -- they are the evaluator's own phrasing.

Query terms for `public_0054`, ordered by the weight IDF assigns:

| Term | Products matched | IDF weight | Origin |
| --- | ---: | ---: | --- |
| `matters` | 29 | **7.42** | evaluator template |
| `requirement` | 36 | **7.21** | evaluator template |
| `key` | 612 | **4.41** | evaluator template |
| `sweatshirts` | 905 | 4.03 | customer constraint |
| `hoodies` | 1,149 | 3.80 | customer constraint |
| `what` | 1,968 | 3.27 | evaluator template |
| `fabric` | 8,675 | 1.91 | customer constraint |
| `soft` | 11,224 | 1.70 | customer constraint |
| `closure` | 19,303 | 1.28 | customer constraint |
| `women` | 32,347 | **0.93** | customer constraint |

The three highest weights in the query go to words from "A key requirement is:"
and "For that, what matters is:". `matters` is weighted **eight times** as
heavily as `women`, the customer's actual stated attribute. Those words are
rare precisely because they are not product vocabulary; they appear in a
handful of product descriptions by coincidence, and rarity weighting reads that
coincidence as importance.

Rarity and informativeness are not the same quantity here. Any rarity-based
weighting systematically promotes conversational scaffolding over stated
constraints, which is a sufficient explanation for E8's and E10's failures as
well. Their reports recorded the result; none of them recorded this cause.

## The interaction with Stage 0

Stage 0 measured that **removing** those same template words costs two
intent_override sessions, because they widen the FTS5 `MATCH` expression and
change which hundred candidates enter the pool. E23-B measures that **weighting**
them is worse than not weighting anything.

Taken together: the template words must be present in the query and must not be
weighted. That is exactly the configuration the retained agent already has, and
neither half of it is obvious in isolation. It also means a query-cleaning step
and a rarity-weighting step cannot be evaluated independently; removing the
junk would change what IDF does, and vice versa.

## Decision

Reject. The `exhaustion_idf` parameter and `_effective_term_weights` were
removed; `starter/agent.py` is byte-identical to E22-C. The optional `idf`
argument on `rerank_candidates` stays, per the T13 precedent.

The honest conclusion for the next experiment is stronger than the result: no
term-weighting scheme derived from catalog statistics is likely to work while
the query contains evaluator phrasing, because those words dominate every
rarity measure. A scheme that separates product vocabulary from conversational
vocabulary would have to come first, and Stage 0 shows that simply deleting the
latter costs sessions.

## Limitations

- Four stuck sessions and 200 total. The zero-change result is unusually clean,
  but it is one configuration of one weighting scheme on one public set.
- Only catalog document frequency was tested. A rarity measure computed over
  product vocabulary alone, or one that excludes terms absent from every
  candidate, was not tried and is not ruled out.
- `public_0020` is outside the candidate pool at every turn, so no reranking
  change of any kind can affect it.
