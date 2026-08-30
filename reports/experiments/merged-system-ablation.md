# Merged-System Ablation

## Status

Diagnostic. No change to the agent. It answers a question the method matrix
structurally cannot: what each retained mechanism is worth **in the final
system**, as opposed to what it bought on the day it was introduced.

- Date: 2026-08-30
- Configuration: the merged agent, `Agent(catalog_path)` with no arguments,
  TechnicalScore `0.902484`
- Method: turn off one retained mechanism at a time, re-run the official
  evaluator over all 200 public sessions, and record the loss.

## Why the matrix cannot answer this

The `Delta Score` column means "change against the previous retained method".
Every row was measured on the system as it stood at that moment. Two things
break that reading here:

1. E22-E25 were developed in parallel with E12-E21 and measured against E11,
   so their deltas do not telescope with the rows above them.
2. Even within one line, a delta is a historical fact, not a current one. A
   mechanism that recovered three sessions in isolation may recover none once
   later mechanisms recover the same sessions by other means.

Marginal contribution is comparable across every row because all of them are
measured against the same system.

## Results

| Mechanism removed | TechnicalScore | **Marginal contribution** | HitRate@10 | MRR | MTTC |
| --- | ---: | ---: | ---: | ---: | ---: |
| *(nothing -- full system)* | 0.902484 | — | 0.995 | 0.776613 | 2.400 |
| Popularity prior (E11) | 0.842313 | **-0.060171** | 0.990 | 0.599375 | 2.625 |
| Constraint ledger + probe + penalty (E22-E24) | 0.880670 | **-0.021814** | 0.980 | 0.756899 | 2.820 |
| Price presence prior (E21) | 0.890116 | -0.012368 | 0.995 | 0.736385 | 2.415 |
| Information-gain probe + penalty (E22-C, E24) | 0.892670 | -0.009814 | 0.990 | 0.769565 | 2.660 |
| Phrase bigram bonus (E19) | 0.893245 | -0.009239 | 0.995 | 0.746149 | 2.405 |
| Buying/Browsing routing (E13) | 0.897872 | -0.004612 | 0.995 | 0.761573 | 2.405 |
| Semantic reranking (E18) | 0.900761 | **-0.001723** | 0.995 | 0.769871 | 2.385 |
| Implicit-rejection penalty (E24) | 0.902401 | **-0.000083** | 0.995 | 0.776669 | 2.400 |

Removing the whole constraint-ledger stack reproduces E21 exactly at
`0.880670`, which confirms the harness: the ablation of our line lands on the
other line's measured score to six decimals.

### The ledger stack, decomposed

The three mechanisms are nested -- the probe needs the ledger's per-turn
information signal, and the penalty is gated on the probe -- so they were
removed cumulatively.

| Mechanism | Marginal contribution |
| --- | ---: |
| Constraint ledger | **+0.012000** |
| Information-gain probe | **+0.009731** |
| Implicit-rejection penalty | **+0.000083** |

## Two findings that change what should be kept

### The popularity prior dwarfs everything built since

Removing E11 costs `0.060171`, three times the next largest mechanism and
roughly the sum of everything else in the table. Ten experiments across two
parallel lines have collectively added less than that one prior. Any account
of this system that does not say so is misleading about where its performance
comes from.

### Two mechanisms have stopped paying

**The implicit-rejection penalty (E24) contributes `0.000083`** -- within
noise, and MRR is fractionally *higher* without it (`0.776669` against
`0.776613`). It was worth `+0.014050` when measured on its own line. What
changed is that the three Buying sessions it rescued are now rescued by better
ranking: the phrase bonus, the price prior and semantic reranking between them
put those targets in the Top-10 before the conversation ever gets stuck. The
mechanism still fires; it simply arrives after the problem has been solved.

Removing it also removes the only part of this system that needed an argument
about the submission rule requiring recommendations "ordered best to worst".
That argument was sound at weight `1.0`, but not having to make it is better
than making it for `0.000083`.

**Acted on.** E24 was removed on 2026-08-30 (T36). The agent scores `0.902401`
without it, exactly this table's prediction, with every scenario hit rate
unchanged. `rejection_weight`, `_shown_penalty`, `_session_shown` and the
reranker's `shown_penalty` parameter are gone; the two tests that protected
probe behaviour rather than the penalty were kept.

**Semantic reranking (E18) contributes `0.001723`**, and it is the sole reason
`requirements.txt` exists. `starter/agent.py` imports `starter/dense.py`
unconditionally, so scikit-learn, scipy, joblib and threadpoolctl are required
to import the Agent at all. That is the entire third-party dependency footprint
of the project, bought for `0.001723`. Whether that trade is worth making is a
judgment about feasibility and reproducibility rather than about score, and it
belongs to whoever owns that experiment.

## Limitations

- Single removals only. Interactions between two removed mechanisms are not
  measured, and the marginal contributions do not sum to the total: they
  overlap wherever two mechanisms rescue the same session.
- 200 public sessions. A mechanism contributing near zero here is not proven
  useless on the private 800; it is proven redundant *against the other
  mechanisms currently present*.
- The nested decomposition of the ledger stack assumes the removal order
  reflects the dependency order, which it does: the probe cannot run without
  the ledger's signal, and the penalty is gated on the probe.
