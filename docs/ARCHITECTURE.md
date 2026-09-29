# Architecture

The refinery separates proposed facts from accepted facts. Models can propose
or review extraction; deterministic code decides whether evidence supports a
record and whether it can enter a simulated publication export.

## Processing path

```text
Synthetic source files + source metadata
                  |
        Hash / path verification
                  |
        Eligible source registry
                  |
      Rules or NIM fact proposals
                  |
  Evidence, unit, and conflict validation
                  |
      Canonical record + identity match
                  |
       Market-specific catalog view
                  |
       Deterministic export checks
              /       \
       Local export   Review required
```

For conditional NIM, rejected or omitted source-checkable facts can trigger one
extraction-repair attempt before the final record is built. An advisory model
review may describe blocked records; it cannot override the gate.

## Module map

| Module | Responsibility |
| --- | --- |
| `refinery/contracts.py` | Attribute grammar, normalization, terminology, and market profiles |
| `refinery/engine.py` | Source registration, evidence checks, bounded repair, matching, localization, and export |
| `refinery/nim.py` | Hosted NIM requests, provider restrictions, budgets, retries, and audit capture |
| `refinery/synthetic.py` | Original handcrafted fixtures and separate expected outcomes |
| `refinery/benchmark_data.py` | Seeded v2 generation, disjoint product-family splits, and raw-file verification |
| `refinery/evaluation.py` | Original case-level evaluation |
| `refinery/experiments.py` | Frozen experiment manifest, paired workflows, checkpoints, and output orchestration |
| `refinery/experiment_metrics.py` | Benchmark scoring, paired analysis, and fault injection |
| `refinery/report.py`, `refinery/experiment_report.py` | Review dashboards, Markdown reports, and figures |

## Data boundaries

- **Sources are evidence, not instructions.** Source content is processed as
  untrusted input. Acceptance requires an eligible source and a complete,
  checkable quote under the supported grammar.
- **The oracle is evaluation-only.** Expected outcomes are held separately from
  extraction inputs and never supplied in model prompts.
- **Localization preserves technical identity.** Market views render terminology
  and decimal conventions without changing canonical product values.
- **The export is checked again.** Source registry, accepted attributes, market
  requirements, and localized view are checked before a local publication object
  is returned.
- **Live inference is explicit.** The rules workflow is offline. NIM runs require
  a process-environment API key and send the selected synthetic sources to NVIDIA.

## Reading the artifacts

Start with [`data/benchmark-v2-final/dataset_card.json`](../data/benchmark-v2-final/dataset_card.json)
and the [experiment protocol](../EXPERIMENTS.md). The
[paired experiment folder](../outputs/experiments/test-paired-nim/) includes its
manifest, per-workflow outputs, model-call audit, metrics, and reports.

Frozen results describe the implementation and settings recorded in their
manifests. Keep later experiments in new output folders and distinguish them
from historical measurements. Narrative verification remains a known coverage
limit; see [results and limitations](../EXPERIMENT_RESULTS.md).
