# Synthetic catalog experiment results

8 cases; dev split; 6 independent product-family groups.

| Metric | Rules | NIM single pass | NIM conditional |
| --- | --- | --- | --- |
| Exact cases | 8 / 8 | 7 / 8 | 7 / 8 |
| Raw extraction F1 | 100.0% | 99.1% | 99.1% |
| Accepted-attribute precision | 100.0% | 100.0% | 100.0% |
| Accepted-attribute recall | 100.0% | 87.2% | 87.2% |
| Accepted-attribute F1 | 100.0% | 93.2% | 93.2% |
| Publication precision | 100.0% | 100.0% | 100.0% |
| Publication recall | 100.0% | 80.0% | 80.0% |
| Auto-acceptance coverage | 62.5% | 50.0% | 50.0% |
| Matching accuracy | 100.0% | 87.5% | 87.5% |
| Evidence-link coverage | 100.0% | 100.0% | 100.0% |
| Localization invariants | 100.0% | 100.0% | 100.0% |
| Unsafe publications | 0 | 0 | 0 |
| Unsupported accepted facts | 0 | 0 | 0 |
| False same-product decisions | 0 | 0 | 0 |
| Logical API requests | 0 | 8 | 14 |
| Logical reported tokens | 0 | 9,826 | 15,814 |
| Latency p50 / p95 (s) | 0.00 / 0.00 | 2.93 / 13.11 | 5.52 / 18.54 |

Physical usage: 14 requests, 15,814 reported tokens, 0 request errors, 67.23 seconds wall time.
Logical costs include the shared first extraction in each workflow. Physical totals count it once. No dollar cost is inferred.

## Paired comparison

Conditional minus single-pass exact-case accuracy: +0.00 percentage points. Group-bootstrap 95% interval: [+0.00, +0.00] points.
This is a descriptive interval over a few synthetic groups, not a claim of statistical or real-world superiority.

The conditional workflow produced +0 additional exactly correct records and used 6 additional logical API requests. Advisory review does not independently authorize acceptance; extra calls do not imply better quality.

## Breakdowns

### Language

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| ar | 8 / 8 | 7 / 8 | 7 / 8 |

### Market

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| ar-SA | 7 / 7 | 6 / 7 | 6 / 7 |
| es-MX | 1 / 1 | 1 / 1 | 1 / 1 |

### Scenario

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| active_conflict | 1 / 1 | 1 / 1 | 1 / 1 |
| ambiguous_voltage | 1 / 1 | 1 / 1 | 1 / 1 |
| clean | 1 / 1 | 1 / 1 | 1 / 1 |
| different_product | 1 / 1 | 1 / 1 | 1 / 1 |
| identity_collision | 1 / 1 | 1 / 1 | 1 / 1 |
| json_record | 1 / 1 | 0 / 1 | 0 / 1 |
| markdown_table | 1 / 1 | 1 / 1 | 1 / 1 |
| market_certificate | 1 / 1 | 1 / 1 | 1 / 1 |

### Format

| Group | Rules exact cases | NIM single pass exact cases | NIM conditional exact cases |
| --- | --- | --- | --- |
| clean | 6 / 6 | 6 / 6 | 6 / 6 |
| json_record | 1 / 1 | 0 / 1 | 0 / 1 |
| markdown_table | 1 / 1 | 1 / 1 | 1 / 1 |

## Injected-fault control experiment

32 deliberately corrupted proposals: 0 accepted by the evidence gate; 32 copied by the simulated no-check comparator.
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
