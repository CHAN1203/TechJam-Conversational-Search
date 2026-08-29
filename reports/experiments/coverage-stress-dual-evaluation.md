# Coverage-Stress Dual Evaluation

## Question

Does the current best Agent retain its public-session result when public-target
metadata is made no more complete than the corresponding 50,000-item catalog
field prevalence? This is a sensitivity diagnostic, not an official evaluation
or a competing Agent method.

## Construction

The deterministic `coverage-stress-v1` build used the frozen 50,000-row source
catalog and 200 public sessions. It preserves every row identifier and row order,
and masks only present, over-covered fields on target products. The generated
catalog SHA-256 was
`f0a1e6381f613409fee279db7d25f6b7603e46f6952b2ae7f3c10635447630a5` on two
consecutive builds.

## Verified invariants

| Check | Result |
| --- | --- |
| Source rows / public sessions / distinct targets | 50,000 / 200 / 200 |
| Target matches | 200 |
| Ordered identifiers preserved | pass |
| Non-target rows preserved | pass |
| No fields filled | pass |
| Planned counts matched | pass |
| Generated catalog ignored | `.gitignore:13:data/generated/` |

## Target coverage before and after

| Field | Catalog present | Original | Desired | Masked | Stress | Shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| title | 50,000 | 200 | 200 | 0 | 200 | 0 |
| categories | 50,000 | 200 | 200 | 0 | 200 | 0 |
| details | 48,330 | 200 | 193 | 7 | 193 | 0 |
| store | 49,686 | 200 | 199 | 1 | 199 | 0 |
| features | 44,781 | 200 | 179 | 21 | 179 | 0 |
| description | 26,113 | 89 | 104 | 0 | 89 | 15 |
| price | 10,527 | 178 | 42 | 136 | 42 | 0 |
| average rating | 50,000 | 200 | 200 | 0 | 200 | 0 |
| rating count | 50,000 | 200 | 200 | 0 | 200 | 0 |

## Official versus coverage-stress result

| Catalog | HitRate@10 | MRR | MTTC | Efficiency | TechnicalScore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Official | 0.965 | 0.662125 | 2.965 | 0.8035 | 0.841838 |
| Coverage-stress | 0.965 | 0.682284 | 2.915 | 0.8085 | 0.848885 |
| Stress minus official | +0.000 | +0.020159 | -0.050 | +0.0050 | +0.007047 |

## Scenario result

| Scenario | Official HitRate / MRR / MTTC | Stress HitRate / MRR / MTTC | Stress minus official HitRate | Stress minus official MRR | Stress minus official MTTC |
| --- | --- | --- | ---: | ---: | ---: |
| Buying (80) | 0.9500 / 0.696905 / 2.2875 | 0.9500 / 0.714940 / 2.2750 | +0.000000 | +0.018035 | -0.0125 |
| Browsing (80) | 1.0000 / 0.665595 / 2.8250 | 1.0000 / 0.688408 / 2.7625 | +0.000000 | +0.022813 | -0.0625 |
| Intent Override (30) | 0.933333 / 0.587685 / 4.933333 | 0.933333 / 0.601852 / 4.933333 | +0.000000 | +0.014167 | +0.0000 |
| Boundary (10) | 0.9000 / 0.579444 / 3.6000 | 0.9000 / 0.613333 / 3.2000 | +0.000000 | +0.033889 | -0.4000 |

The candidate clarification and `1.2` popularity entry points were also run in
dual mode. Each produced official, coverage-stress, and stress-minus-official
payloads; both full results match the table above.

## Interpretation

Official metrics select methods; the official result exactly reproduces the
retained `0.965` HitRate@10 and `0.841838` TechnicalScore. Stress metrics are a
metadata-sensitivity diagnostic. No combined score is valid, and this result
does not replace the official score or qualify as a submission result.

The stress run changes both retrieval-visible metadata and evaluator-materialized
customer disclosures. Under this particular deterministic masking, HitRate@10
is unchanged and rank-related aggregates improve slightly. That direction is
descriptive only, not evidence that metadata removal improves the method.

## Limitations

The construction matches marginal field presence only, not field correlations or
value distributions. Description remains `89/200`, with an unavoidable
15-target shortfall because no imputation is allowed. It does not correct the
public targets' popularity bias, can be overfit by repeated use, and cannot
forecast private results.

## Reproduction commands

```powershell
python -m unittest discover -s tests -v
python -m scripts.build_coverage_stress_catalog
python -m scripts.build_coverage_stress_catalog
git check-ignore -v data/generated/catalog-coverage-stress.jsonl
python -m scripts.run_dual_catalog_evaluation --output reports\experiments\coverage-stress-baseline.json
python -m scripts.run_clarification_ablation --policies candidate --output reports\experiments\coverage-stress-candidate.json
python -m scripts.run_popularity_sweep --weights 1.2 --output reports\experiments\coverage-stress-popularity.json
python -m scripts.run_dual_catalog_evaluation --catalog-mode official --output results_official_reproduction.json
```

`results_official_reproduction.json` is temporary and ignored; do not use the
tracked dual-baseline filename for an official-only reproduction.
