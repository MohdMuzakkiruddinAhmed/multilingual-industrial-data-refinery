# Multilingual Industrial Data Refinery

**The expanded end-to-end experiment workflow is documented in
[EXPERIMENTS.md](EXPERIMENTS.md).** It adds 1,728 seeded cases, actual source files,
group-disjoint splits, paired NIM comparisons, fault-injection experiments, and
metric reports. The original 14-case walkthrough below remains available.

Read [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md) for measured outcomes and their
interpretation: 432 offline test cases, a 72-case paired live-NIM comparison,
49 passing unit tests, and the remaining narrative-verification limitation.

Current experiment entry points:

```powershell
python -m refinery.experiments run --split test --per-stratum 0 --out outputs/experiments/new-rules-run
# Requires NVIDIA_API_KEY in the environment:
python -m refinery.experiments run --split test --live --out outputs/experiments/new-nim-run
```

Open the [paired test dashboard](outputs/experiments/test-paired-nim/report.html)
or the [full rules test dashboard](outputs/experiments/test-rules-full/report.html).

A runnable Python proof of concept based on `draft.txt`. It uses NVIDIA NIM to
propose product attributes, then deterministic rules decide which facts are
supported and which catalog views qualify for **simulated local publication**.

Requires Python 3.11+. No third-party runtime or test dependencies.

See [TEST_RESULTS.md](TEST_RESULTS.md) for the measured offline/live results and
the [generated NIM review dashboard](outputs/nim-final/report.html) for this session.

## Run it

From this directory in PowerShell:

```powershell
python -m refinery generate
python -m refinery run --provider rules --out outputs/offline
Start-Process outputs/offline/report.html
python -m unittest discover -s tests -v
```

Run the same synthetic cases with NVIDIA NIM. Enter the key at the hidden prompt
so it is not written into shell command history:

```powershell
$nimSecret = Read-Host 'NVIDIA API key' -AsSecureString
$env:NVIDIA_API_KEY = [System.Net.NetworkCredential]::new('', $nimSecret).Password
try {
    python -m refinery run --provider nim --out outputs/nim
} finally {
    Remove-Item Env:NVIDIA_API_KEY
    Remove-Variable nimSecret
}
Start-Process outputs/nim/report.html
```

The application reads environment variables and does **not** load `.env` files.
`.env.example` documents their names; no actual key is saved in this project.

To run one case or limit requests:

```powershell
python -m refinery run --provider nim --case arabic_duplicate --max-calls 4 --timeout 30
```

Default model: `nvidia/nemotron-3-super-120b-a12b`.
Override with `--model` or `NIM_MODEL`. The older draft model ID
`nvidia/nemotron-3-nano-30b-a3b` returned HTTP 410 during setup; the current
model was explicitly selected after querying NVIDIA's model inventory and
testing it. An initial Lightning run exposed malformed responses and timeouts;
its results are retained separately. There is no automatic model or provider fallback.

The hosted API receives synthetic inputs and prompts. This is **not an offline
deployment**. A local NIM can be configured explicitly with
`NIM_BASE_URL=http://127.0.0.1:8000/v1` and its served `NIM_MODEL`; local GPU
deployment has not been tested. The client accepts NVIDIA HTTPS and loopback
endpoints only and does not follow redirects with credentials.

## What is implemented

```text
Registered sources + approved synthetic reference catalog
  -> NIM extraction proposals / explicit offline rules baseline
  -> exact quotation and typed-value checks
  -> optional one-step extraction repair for source-checkable omissions
  -> independent source-conflict checks and canonical attributes
  -> identity / variant assessment
  -> market requirements and controlled terminology rendering
  -> advisory NIM review if acceptance fails
  -> approved local export OR review queue
```

- Sources retain their original text, version, location, and SHA-256 digest.
- Each accepted attribute records exact character offsets, quotation, source
  digest, original value, and conversion rule. Offsets count Unicode code points.
- `Decimal` performs exact conversions; LLM arithmetic is independently checked.
- Unknown, ambiguous, and unsupported proposals cannot enter accepted facts.
- Conflicts are checked against **all** active recognized source facts, even
  when a model omits one of the conflicting sources.
- Matching uses manufacturer, literal part number, family, and protected
  attributes. Results are same product, related variant, different product, or
  insufficient evidence. No destructive merge operation exists in this PoC.
- English, German, Spanish, and Arabic source labels map to one typed schema.
- Market views cover en-US, de-DE, es-ES, es-MX, and ar-SA. Spanish profiles
  differ in decimal display and a fictional organization certificate requirement.
  `TEST-CERT-*` values are synthetic placeholders, not real certifications.
- Localized rows are rendered from approved terminology, rather than freely
  generated prose. This verifies fact preservation, not unrestricted translation.
- Conditional orchestration supports one repair attempt and advisory evidence
  review. Deterministic code retains acceptance authority.
- Simulated publication checks evidence again and rejects modified views.
- Source supersession and withdrawal affect reprocessing. `dependent_cases`
  identifies affected records; an external revocation event system is future work.

## Synthetic evaluation

14 handcrafted cases cover multilingual duplicates, a technically different
variant, missing power, ambiguous voltage, conflicting active sources, a
superseded revision, missing and supplied market certificates, prompt injection,
withdrawn evidence, and a different manufacturer/product.

`data/sources.json` contains the inputs. `data/expected.json` is the independently
specified oracle, loaded only by evaluation. Expected answers never enter model
prompts. NIM requests use JSON mode and a 30-second default network timeout.
These fixtures exercise known control boundaries; they do not establish
general model accuracy or language coverage.

Each run writes:

| Artifact | Contents |
| --- | --- |
| `report.html` | Searchable case explorer with facts, evidence, decisions, and localized views |
| `run.json` | Full results, oracle comparisons, metrics, versions, and usage |
| `calls.json` | NIM prompts, text responses, request hashes, usage, and timings; no authorization header |
| `checkpoint.json` | Completed records, updated after every case |
| `publications.json` | Approved simulated exports |

Reported metrics include exact case correctness, accepted-record correctness,
auto-acceptance coverage, accepted-attribute correctness/recall, evidence-link
coverage, false same-product decisions, language/market breakdowns, request
counts, tokens, and elapsed time. Transient HTTP/network errors get one bounded
retry against the same endpoint/model and count toward the request budget.
Authentication and malformed-output errors are not retried by transport.
Unrecovered provider failures are recorded and the CLI exits nonzero; no offline
result is substituted. A nonzero exit also reports an
oracle mismatch. Inspect `run.json` rather than assuming every live run passes.

## Code map

| File | Responsibility |
| --- | --- |
| `refinery/contracts.py` | Approved schema, aliases, units, market profiles, terminology |
| `refinery/synthetic.py` | Synthetic sources and separate expected outcomes |
| `refinery/nim.py` | NIM API adapter, extraction/review contracts, bounded requests |
| `refinery/engine.py` | Registration, acceptance checks, matching, localization, export |
| `refinery/evaluation.py` | Oracle metrics and breakdowns |
| `refinery/dashboard.html` | Standalone interactive review UI |
| `refinery/cli.py` | Reproducible command-line runs and artifacts |
| `tests/test_refinery.py` | Regression and adversarial boundary tests |

## Scope and next experiments

The parser intentionally accepts a narrow labeled-fact grammar, now including
equals signs, flat JSON properties, Markdown rows, approved synonyms, and
Arabic-Indic numbers. It is not a
general semantic entailment checker. It supports only the stated units and
identifier forms. Source authorization and reference approval are fixture
metadata, not an implemented enterprise trust authority. Hashes detect accidental
changes; they do not authenticate an attacker who can rewrite all local files.
Approval is defined under PoC rules and does not establish real source truth.

NIM supplies extraction and advisory review; this is a bounded conditional
workflow, not the draft's full four-agent architecture. Translation models,
embedding retrieval, UNSPSC, arbitrary PDFs, OCR, a human approval UI, persistent
publication services, and capability routing are not implemented. Hosted model
aliases may change, so the response model ID, prompts, settings, and dataset hash
are recorded, but immutable model weights are not available from this endpoint.

The expanded synthetic experiment and text/JSON/Markdown adapters are now
implemented; see EXPERIMENTS.md. Next: test with authorized real data and bilingual technical
reviewers; then compare a fixed workflow and conditional workflow using identical
models, evidence, and checks. See [PLAN.md](PLAN.md).

Official API references checked during implementation:
- [NVIDIA Nemotron Super hosted API](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b-infer)
- [NVIDIA Nemotron 3.5 Lightning NIM guide](https://docs.nvidia.com/nim/large-language-models/2.0.10/get-started/advanced/get-started-nemotron-3.5-lightning.html)
- [NVIDIA hosted model API](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-30b-a3b)
