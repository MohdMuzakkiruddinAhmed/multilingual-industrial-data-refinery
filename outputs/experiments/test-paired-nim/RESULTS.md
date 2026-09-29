# Synthetic catalog experiment results

72 cases; test split; 6 independent product-family groups.

| Metric | Rules | NIM single pass | NIM conditional |
| --- | --- | --- | --- |
| Exact cases | 68 / 72 | 67 / 72 | 68 / 72 |
| Raw extraction F1 | 96.9% | 99.3% | 98.5% |
| Accepted-attribute precision | 100.0% | 100.0% | 100.0% |
| Accepted-attribute recall | 93.5% | 93.3% | 93.5% |
| Accepted-attribute F1 | 96.7% | 96.5% | 96.7% |
| Publication precision | 100.0% | 100.0% | 100.0% |
| Publication recall | 90.0% | 87.5% | 90.0% |
| Auto-acceptance coverage | 50.0% | 48.6% | 50.0% |
| Matching accuracy | 94.4% | 93.1% | 94.4% |
| Evidence-link coverage | 100.0% | 100.0% | 100.0% |
| Localization invariants | 100.0% | 100.0% | 100.0% |
| Unsafe publications | 0 | 0 | 0 |
| Unsupported accepted facts | 0 | 0 | 0 |
| False same-product decisions | 0 | 0 | 0 |
| Logical API requests | 0 | 66 | 103 |
| Logical reported tokens | 0 | 76,013 | 104,542 |
| Latency p50 / p95 (s) | 0.00 / 0.00 | 2.75 / 7.15 | 3.16 / 11.58 |

Physical usage: 103 requests, 104,542 reported tokens, 2 request errors, 317.72 seconds wall time.
Logical costs include the shared first extraction in each workflow. Physical totals count it once. No dollar cost is inferred.

## Paired comparison

Conditional minus single-pass exact-case accuracy: +1.39 percentage points. Group-bootstrap 95% interval: [+0.00, +4.17] points.
This is a descriptive interval over a few synthetic groups, not a claim of statistical or real-world superiority.

The conditional workflow produced +1 additional exactly correct records and used 37 additional logical API requests. Advisory review does not independently authorize acceptance; extra calls do not imply better quality.

## Breakdowns

### Language

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| ar | 17 / 18 | 17 / 18 | 17 / 18 |
| de | 17 / 18 | 16 / 18 | 17 / 18 |
| en | 17 / 18 | 17 / 18 | 17 / 18 |
| es | 17 / 18 | 17 / 18 | 17 / 18 |

### Market

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| ar-SA | 15 / 16 | 15 / 16 | 15 / 16 |
| de-DE | 15 / 16 | 14 / 16 | 15 / 16 |
| en-US | 15 / 16 | 15 / 16 | 15 / 16 |
| es-ES | 15 / 16 | 15 / 16 | 15 / 16 |
| es-MX | 8 / 8 | 8 / 8 | 8 / 8 |

### Scenario

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| active_conflict | 4 / 4 | 4 / 4 | 4 / 4 |
| ambiguous_voltage | 4 / 4 | 4 / 4 | 4 / 4 |
| clean | 4 / 4 | 4 / 4 | 4 / 4 |
| different_product | 4 / 4 | 4 / 4 | 4 / 4 |
| identity_collision | 4 / 4 | 4 / 4 | 4 / 4 |
| json_record | 4 / 4 | 3 / 4 | 4 / 4 |
| markdown_table | 4 / 4 | 4 / 4 | 4 / 4 |
| market_certificate | 4 / 4 | 4 / 4 | 4 / 4 |
| market_missing_certificate | 4 / 4 | 4 / 4 | 4 / 4 |
| missing_power | 4 / 4 | 4 / 4 | 4 / 4 |
| narrative | 0 / 4 | 0 / 4 | 0 / 4 |
| prompt_injection | 4 / 4 | 4 / 4 | 4 / 4 |
| related_variant | 4 / 4 | 4 / 4 | 4 / 4 |
| shuffled_synonyms | 4 / 4 | 4 / 4 | 4 / 4 |
| superseded_revision | 4 / 4 | 4 / 4 | 4 / 4 |
| unauthorized | 4 / 4 | 4 / 4 | 4 / 4 |
| unit_conversion | 4 / 4 | 4 / 4 | 4 / 4 |
| withdrawn | 4 / 4 | 4 / 4 | 4 / 4 |

### Format

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| clean | 56 / 56 | 56 / 56 | 56 / 56 |
| json_record | 4 / 4 | 3 / 4 | 4 / 4 |
| markdown_table | 4 / 4 | 4 / 4 | 4 / 4 |
| narrative | 0 / 4 | 0 / 4 | 0 / 4 |
| shuffled_synonyms | 4 / 4 | 4 / 4 | 4 / 4 |

## Injected-fault control experiment

208 deliberately corrupted proposals: 0 accepted by the evidence gate; 208 copied by the simulated no-check comparator.
This is a deterministic fault-injection experiment, not a measured NIM hallucination rate. The unchecked comparator never publishes.

## Limitations and metric definitions

- Raw extraction F1 compares deduplicated source/field/value/unit tuples with the independent source-level oracle. Contradictory but explicitly stated facts are valid raw extractions.
- Accepted-attribute F1 compares canonical field/value pairs with conflict-resolved ground truth; missing facts count as false negatives.
- Publication precision measures correct publishability decisions among approvals. Accepted-record correctness additionally checks all attributes and identity.
- Publication recall measures approved records among all ideally publishable records. Narrative records remain in the denominator even when the narrow verifier cannot accept them.
- Provider failures stay in denominators; successful reruns never replace failed attempts in this report.
- Evidence-link coverage is structural traceability. It is not independent proof of source truth.
- Localization is controlled terminology rendering and value preservation, not a human-rated translation-quality benchmark.
- Splits separate product families; they share rendering templates. No real data, trained model, or independently validated bilingual gold labels are claimed.
- Synthetic test families are held apart from development. Model prompts and evaluation configuration are saved in the pre-run manifest; the oracle never enters model requests.

## Artifacts

- `summary.json`: machine-readable metrics, counts, breakdowns, and paired comparison.
- `manifest.json` / `protocol.json`: frozen inputs, source hashes, prompts, and experimental design.
- `calls.json`: actual NIM request/response audit when live inference is enabled.
- Per-workflow `run.json`, `report.html`, and `publications.json`.
- `comparison.png` and `comparison.svg`: standard Matplotlib figures (when installed).
