# Slot Memory and Retrieval Ablation

Date: 2026-08-29
Status: superseded by E11 (popularity prior, TechnicalScore `0.841838`).
E9 remains the retrieval and memory baseline that E11 builds on.
E5 kept with weak evidence; E6, E7, E8-A/B/C rejected.

## Summary

TechnicalScore improved from `0.730071` (E3-C) to `0.747917` (E9) on the full
200-session public set. HitRate@10 rose from `0.870` to `0.895` and Intent
Override from `0.600000` to `0.766667`.

Almost all of the gain came from one change that was not the point of the work:
giving every gazetteer term exactly one slot. The four experiments that were
deliberately designed to raise the score contributed `+0.003719` between them.

## Architecture

E9 is E3-C with two additions. Everything that produced the previous best score
is unchanged:

| Stage | Status |
| --- | --- |
| SQLite FTS5 index over 6 fields | unchanged |
| BM25 retrieval, OR over accumulated terms | unchanged |
| Candidate pool size 100 | unchanged (500 tested and rejected, E7) |
| Field-weight reranker, no IDF | unchanged (IDF tested and rejected, E8) |
| Candidate-aware clarification | unchanged, still the default policy |
| Constraint accumulation across turns | unchanged |
| **Mined slot vocabulary** | **new** (`analysis/gazetteer.py`, `data/gazetteer.json`) |
| **Slot-scoped intent override** | **new** (`starter/slots.py`, `starter/agent.py`) |

No retrieval or ranking behaviour changed. The gain comes from the agent
knowing which slot a word belongs to, so an override replaces one constraint
instead of clearing them all.

## Running it

The best configuration is the default. No flag, no alternate entry point:

```python
Agent(catalog_path)   # clarification_policy="candidate", gazetteer_path="data/gazetteer.json"
```

`python -m evaluator.local_evaluator` constructs exactly this and reports
TechnicalScore `0.747917`.

`data/gazetteer.json` is committed, so a checkout has it. If it is ever absent
or unreadable the agent **degrades silently** to the pre-slot behaviour rather
than raising, which keeps the scored path safe but will quietly cost
`0.747917 -> 0.733790`. If a run reports the lower number, check that the file
is present before looking anywhere else. Rebuild it with:

```
python -m scripts.build_gazetteer
```

## What was built

A slot vocabulary is mined offline from the frozen catalog and shipped as
`data/gazetteer.json` (19 KB), rebuilt by `python -m scripts.build_gazetteer`.

- `department` is normalized from `details.Department`. 6 canonical values,
  86.9% catalog coverage, 99.71% of populated values map.
- `category` is taken from taxonomy nodes at depth >= 2. Amazon merchandising
  nodes ("Prime Day: 30% off", "Westlake", "Clearance") appear only as a sole
  child of the root, so the depth rule excludes them structurally.
- `material`, `color`, `style`, `size` are seeded from the sparse `details`
  keys, then matched against title + features free text.

Seeding recovers far more coverage than the previous hand-written constants:

| Slot | Structured only | After bootstrap | Previous constants |
| --- | ---: | ---: | ---: |
| material | 4.1% | 81.6% | 54.7% |
| color | 4.9% | 69.5% | 33.3% |
| style | 3.5% | 61.1% | 36.5% |
| size | 1.8% | 51.0% | 20.9% |

`starter/slots.py` assigns terms in a message to their slot, longest match
first. `starter/agent.py` uses this so an intent override replaces only the
slots that changed instead of clearing all constraints.

## Results

| ID | Method | HitRate@10 | MRR | MTTC | TechnicalScore | Decision |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| E3-C | Candidate clarification (baseline) | 0.870 | 0.544236 | 4.410 | 0.730071 | previous best |
| E5 | Slot-aware override memory | 0.875 | 0.540300 | 4.290 | 0.733790 | kept, weak |
| E6 | Turn-aware override memory | 0.875 | 0.540300 | 4.290 | 0.733790 | no measurable effect |
| E7 | Candidate pool 500 | 0.875 | 0.528762 | 4.190 | 0.732329 | rejected |
| E8-A | Pool-frequency IDF | 0.790 | 0.459067 | 4.975 | 0.653220 | rejected, wrong reasoning |
| E8-B | Catalog IDF + pool 500 | 0.845 | 0.522619 | 4.625 | 0.706786 | rejected |
| E8-C | Catalog IDF + pool 100 | 0.860 | 0.540980 | 4.640 | 0.719494 | rejected |
| E9 | Slot conflict resolution | **0.895** | **0.549056** | **4.215** | **0.747917** | **current best** |

Per scenario, E3-C to E9:

| Scenario | E3-C | E9 |
| --- | ---: | ---: |
| Buying | 0.8750 | 0.8750 |
| Browsing | 0.9625 | 0.9625 |
| Intent Override | 0.600000 | **0.766667** |
| Boundary | 0.9000 | 0.9000 |

## Why E9 mattered more than the experiments around it

The first gazetteer let a term belong to several slots: `small` was both a
color and a size, `women` both a department and a category, `hoodie` both a
category and a style. That silently corrupted the override logic E5 and E6
were trying to improve. A size answer marked the color slot as replaced and
discarded a real color constraint; a mention of gender wiped the category slot.

Support counts cannot break these ties. Category counts come from the taxonomy
while attribute counts come from free text, and `silver` scored identically
under material and color because coverage is measured over the same text. The
fix is a fixed precedence by source reliability:

    department > material > size > category > color > style

Cross-slot terms went from 27 to 0. E5 and E6 were correct logic applied to
incorrect data; fixing the data released the gain they were reaching for.

## Rejected experiments worth remembering

**E8-A is a reasoning error, not a tuning failure.** IDF was computed over the
candidate pool. The pool is the set of documents the query already matched, so
the query's most discriminating term appears in nearly all of them and was
penalized as uninformative. Document frequency must come from the whole
catalog. `Agent._catalog_idf` reads it from `fts5vocab` if this is retried.

**E7 and E8 both traded Browsing for Intent Override.** Every setting that
helped the hardest scenario hurt the easiest one:

| | pool100 no IDF | pool500 no IDF | pool100 IDF | pool500 IDF |
| --- | ---: | ---: | ---: | ---: |
| Intent Override | 0.633 | 0.700 | **0.733** | 0.667 |
| Browsing | **0.9625** | 0.950 | 0.900 | 0.888 |

Browsing has 80 sessions and Intent Override 30, so Browsing losses dominate
the total. This argues for routing rather than a single global setting: the
agent detects override messages itself, so it can change retrieval behavior
from that turn onward without reading any label.

**A diagnostic probe (E4-B) showed clarification is saturated.** Asking `other`
every turn scores `0.724052`. Browsing is identical to the tuned policy at
`0.9625`. Note that the local simulator can never answer `category` or `brand`,
and answers `other` with two constraints where specific attributes give one.
That is a property of the practice simulator and not a submission strategy.

## Verification

    python -m unittest discover -s tests -v      # 53 tests
    python -m scripts.build_gazetteer            # rebuilds data/gazetteer.json
    python -m evaluator.local_evaluator          # TechnicalScore 0.747917

The evaluator and public labels are unmodified. The agent reads only the
catalog, the anonymized profile, and messages delivered through the official
interface.

## Limitations

- Public set only. Intent Override rests on 30 sessions, so `+0.166667` there
  is 5 sessions. The private set is unverified.
- The practice customer's constraints are sliced verbatim from the target
  product's own metadata. The organizer reserves the right to reword them, and
  slot matching is exact-term matching, so a paraphrase harness is worth
  building before trusting these numbers.
- `_is_intent_override` still matches a literal phrase copied from the local
  simulator. The private set ships its own `behavior` dicts with their own
  wording. This is the most likely silent failure in the current agent.
- The clarification policy choice (fixed / profile / candidate) was decided on
  the contaminated gazetteer by a `0.005562` margin. It should be re-run.

## Next

1. Re-run the clarification ablation on the clean gazetteer.
2. Scenario routing, using the Browsing / Intent Override tension above.
3. Paraphrase-robustness harness, and replace the literal override phrase match.
