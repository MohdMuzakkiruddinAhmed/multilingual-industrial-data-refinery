# Synthetic catalog experiment results

432 cases; dev split; 6 independent product-family groups.

| Metric | Rules |
| --- | --- |
| Exact cases | 408 / 432 |
| Raw extraction F1 | 96.9% |
| Accepted-attribute precision | 100.0% |
| Accepted-attribute recall | 93.5% |
| Accepted-attribute F1 | 96.7% |
| Publication precision | 100.0% |
| Publication recall | 90.0% |
| Auto-acceptance coverage | 50.0% |
| Matching accuracy | 94.4% |
| Evidence-link coverage | 100.0% |
| Localization invariants | 100.0% |
| Unsafe publications | 0 |
| Unsupported accepted facts | 0 |
| False same-product decisions | 0 |
| Logical API requests | 0 |
| Logical reported tokens | 0 |
| Latency p50 / p95 (s) | 0.00 / 0.00 |

Physical usage: 0 requests, 0 reported tokens, 0 request errors, 26.89 seconds wall time.
Logical costs include the shared first extraction in each workflow. Physical totals count it once. No dollar cost is inferred.


## Breakdowns

### Language

| Group | Rules exact cases |
| --- | --- |
| ar | 102 / 108 |
| de | 102 / 108 |
| en | 102 / 108 |
| es | 102 / 108 |

### Market

| Group | Rules exact cases |
| --- | --- |
| ar-SA | 90 / 96 |
| de-DE | 90 / 96 |
| en-US | 90 / 96 |
| es-ES | 90 / 96 |
| es-MX | 48 / 48 |

### Scenario

| Group | Rules exact cases |
| --- | --- |
| active_conflict | 24 / 24 |
| ambiguous_voltage | 24 / 24 |
| clean | 24 / 24 |
| different_product | 24 / 24 |
| identity_collision | 24 / 24 |
| json_record | 24 / 24 |
| markdown_table | 24 / 24 |
| market_certificate | 24 / 24 |
| market_missing_certificate | 24 / 24 |
| missing_power | 24 / 24 |
| narrative | 0 / 24 |
| prompt_injection | 24 / 24 |
| related_variant | 24 / 24 |
| shuffled_synonyms | 24 / 24 |
| superseded_revision | 24 / 24 |
| unauthorized | 24 / 24 |
| unit_conversion | 24 / 24 |
| withdrawn | 24 / 24 |

### Format

| Group | Rules exact cases |
| --- | --- |
| clean | 336 / 336 |
| json_record | 24 / 24 |
| markdown_table | 24 / 24 |
| narrative | 0 / 24 |
| shuffled_synonyms | 24 / 24 |

## Injected-fault control experiment

1248 deliberately corrupted proposals: 0 accepted by the evidence gate; 1248 copied by the simulated no-check comparator.
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
