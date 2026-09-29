"""Build a portable source/data/results archive without editing experiment code."""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"
NAME = "multilingual-industrial-data-refinery"
STAGE = RELEASES / "github-ready" / NAME
ZIP = RELEASES / (NAME + "-github.zip")

README = """# Multilingual Industrial Data Refinery

An evidence-controlled research prototype for refining multilingual industrial
motor catalogs with NVIDIA NIM. Sources become typed canonical records and
market-specific views; deterministic checks govern simulated publication.

**Included:** all source code, 49 offline tests, synthetic datasets and raw
documents, complete experiment results, model request audits, and review dashboards.

## Measured results

The v2 dataset contains **1,728 cases**, **1,920 source documents**, **24 product
families**, **four languages**, and **18 scenarios**. Product families are disjoint
across train/development/test splits. The full offline test covers 432 cases; the
paired live comparison covers the same 72 held-out cases in every workflow.

| Workflow | Exact cases | Accepted-attribute F1 | Auto-acceptance | Logical API calls |
| --- | ---: | ---: | ---: | ---: |
| Rules | 68/72 | 96.67% | 50.0% | 0 |
| NIM single pass | 67/72 | 96.52% | 48.61% | 66 |
| NIM conditional repair | 68/72 | 96.67% | 50.0% | 103 |

All three workflows had zero unsafe publication decisions and zero unsupported
accepted facts on these cases. Conditional repair recovered one record at the
cost of 37 additional calls. Narrative evidence verification remains the main
coverage limitation. These synthetic results do not establish production accuracy.

Read [the interpretation](EXPERIMENT_RESULTS.md),
[the full generated report](outputs/experiments/test-paired-nim/RESULTS.md), or
[the metric JSON](outputs/experiments/test-paired-nim/summary.json).

![Experiment comparison](outputs/experiments/test-paired-nim/comparison.png)

## Quick start

Python 3.11 or newer is required. Core inference, scoring, and tests use the
standard library. Matplotlib is optional for regenerating plots.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[plots]"
python -m unittest discover -s tests -v
python -m refinery run --provider rules --out outputs/local-demo
```

The `.[plots]` extra can be omitted for a dependency-free runtime installation.

## View the saved dashboards

After extracting or cloning, open this file in a browser:

`outputs/experiments/test-paired-nim/report.html`

Or serve the repository locally:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8000/outputs/experiments/test-paired-nim/report.html`.
GitHub's repository file viewer shows HTML source; use the Markdown report for
in-repository reading and a local browser for the interactive case explorer.

## Reproduce the experiment

```bash
# Entire deterministic test split, with a new output directory.
python -m refinery.experiments run --split test --per-stratum 0 --out outputs/my-rules-run

# Requires NVIDIA_API_KEY in this process environment.
python -m refinery.experiments run --split test --live --max-calls 180 --timeout 20 --out outputs/my-nim-run
```

The default live model is `nvidia/nemotron-3-super-120b-a12b`. Both NIM workflows
share the first model response; additional repair/review calls remain live.
Hosted inference sends the synthetic documents to NVIDIA. There is no implicit
provider fallback. Saved request errors remain included in the experiment.

Set a key with a hidden PowerShell prompt:

```powershell
$nimSecret = Read-Host 'NVIDIA API key' -AsSecureString
$env:NVIDIA_API_KEY = [System.Net.NetworkCredential]::new('', $nimSecret).Password
try {
    python -m refinery.experiments run --split test --live --out outputs/my-live-run
} finally {
    Remove-Item Env:NVIDIA_API_KEY
    Remove-Variable nimSecret
}
```

`.env.example` documents configuration names; the application reads environment
variables and does not automatically load `.env` files. No real key is included.

## Repository layout

```text
refinery/                  Pipeline, NIM client, generation, evaluation, reports
tests/                     Offline regression and adversarial tests
data/
  sources.json             Original 14-case dataset
  expected.json            Original oracle
  benchmark-v2-final/      Canonical 1,728-case dataset and raw documents
  benchmark-v2/            Preserved preflight generator artifact
outputs/
  experiments/
    test-paired-nim/       Main paired live experiment, audits, figures, dashboards
    test-rules-full/       All 432 held-out rules cases
    dev-rules/             Development baseline
    dev-nim-smoke/         Development API smoke test
  ...                      Earlier PoC runs and diagnostics
.github/workflows/         Offline CI; no API key or live inference needed
EXPERIMENTS.md             Reproduction protocol and metric definitions
EXPERIMENT_RESULTS.md      Main measured findings and limitations
POC_GUIDE.md               Original detailed walkthrough
PACKAGE_CONTENTS.md       Archive inventory and verification notes
SHA256SUMS.txt             Per-file integrity checksums
```

## Dataset and methodology

Synthetic truth is generated before source rendering and independently of the
production parser. Raw files are hash-verified during ingestion. Expected answers
never enter model prompts. The final benchmark includes JSON, table rows, labeled
text, synonyms, decimal/unit variations, Arabic digits, conflicts, revisions,
missing facts, prompt injection, and narrative cases.

Publication is a local simulation. Approval metadata is fixture-defined;
localization is controlled terminology rendering. The system is bounded
orchestration, not a production enterprise integration. See
[EXPERIMENTS.md](EXPERIMENTS.md) for limitations and the next controlled experiments.

## Upload to GitHub

Extract this ZIP and use the **contents of this folder** as the repository root.
Keep `.github`, `.gitignore`, `.gitattributes`, and `.env.example` included.
The ZIP itself is a distribution archive; pushing the extracted files makes the
code, documentation, and results browsable in GitHub.

For an empty GitHub repository, from this extracted folder:

```bash
git init
git add .
git commit -m "Add multilingual data refinery and experiment results"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

The committed `.gitignore` includes the bundled historical results and ignores
new run folders. Use a fresh output folder for new experiments. Historical
snapshots should remain unchanged; future code changes will naturally have a
different hash from their recorded manifests.
"""

GITIGNORE = """# Credentials and local environments
.env
.env.*
!.env.example
.venv/
venv/
__pycache__/
*.py[cod]
.pytest_cache/
*.egg-info/
build/
dist/
releases/
.coverage
htmlcov/
.DS_Store
Thumbs.db

# Preserve bundled research outputs; ignore new local runs by default.
outputs/*
!outputs/README.md
!outputs/offline/
!outputs/nim/
!outputs/nim-final/
!outputs/nim-json-check/
!outputs/nim-super/
!outputs/nim-targeted-retry/
!outputs/experiments/
outputs/experiments/*
!outputs/experiments/test-paired-nim/
!outputs/experiments/test-rules-full/
!outputs/experiments/dev-rules/
!outputs/experiments/dev-nim-smoke/
"""

WORKFLOW = """name: Offline tests

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install core package
        run: python -m pip install -e .
      - name: Run offline unit tests
        run: python -m unittest discover -s tests -v
      - name: Run original end-to-end regression
        run: python -m refinery run --provider rules --out outputs/ci-smoke
"""


def write(relative, text):
    path = STAGE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build():
    if STAGE.exists() or ZIP.exists():
        raise SystemExit("Release path exists; preserve the previous archive and choose a fresh release path.")
    STAGE.mkdir(parents=True)
    copied = []
    for directory in ("refinery", "tests", "data", "outputs", "tools"):
        for src in sorted((ROOT / directory).rglob("*")):
            if not src.is_file() or "__pycache__" in src.parts or src.suffix in (".pyc", ".pyo"):
                continue
            relative = src.relative_to(ROOT)
            if directory == "outputs" and src.parent == ROOT / "outputs":
                continue  # Temporary dashboard syntax-check JS files only.
            dst = STAGE / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(relative.as_posix())
    for src in ROOT.iterdir():
        if src.is_file() and (src.suffix == ".md" or src.name in ("draft.txt", "pyproject.toml", ".env.example")):
            name = "POC_GUIDE.md" if src.name == "README.md" else src.name
            shutil.copy2(src, STAGE / name)
    write("README.md", README)
    write(".gitignore", GITIGNORE)
    write(".gitattributes", "* text=auto eol=lf\n*.png binary\n# Preserve the exact bytes of frozen evidence and experiment snapshots.\ndata/** -text\noutputs/** -text\n")
    write(".github/workflows/tests.yml", WORKFLOW)
    write("CONTRIBUTING.md", """# Contributing

Run `python -m unittest discover -s tests -v` before proposing a change.
Use a fresh seed/output folder for new experiments. Preserve the frozen datasets,
historical manifests, source hashes, and audit logs; document new measurements
separately. Expected answers must not enter inference prompts.

CI runs offline tests and the original rules regression; it does not call NIM.
The workflow follows the official [checkout](https://github.com/actions/checkout)
and [setup-python](https://github.com/actions/setup-python) action interfaces.
Live runs are explicit local experiments with a process-scoped NVIDIA_API_KEY.
Do not include credentials, real private catalogs, or local environment files in
commits. The shipped data and model prompts are synthetic research artifacts.
""")
    write("data/README.md", """# Datasets

- `benchmark-v2-final/`: canonical v2 dataset, 1,728 cases and 1,920 raw files.
  `sources.json` is the input manifest; `expected.json` is the separate oracle;
  `dataset_card.json` records hashes, seed, composition, and limitations.
- `sources.json` / `expected.json`: original 14-case PoC fixtures.
- `benchmark-v2/`: preserved preflight generator output, not the dataset used
  for the reported final v2 experiments.

All supplied records are synthetic. Product-family splits and ground-truth
definitions are described in `../EXPERIMENTS.md`.
""")
    write("outputs/README.md", """# Saved runs

Start with `experiments/test-paired-nim/report.html` or its `RESULTS.md`.
The final 72-case paired comparison, full 432-case rules evaluation, development
runs, and original PoC diagnostics are all retained. `calls.json` stores model
requests/responses without authorization headers. Checkpoints are included,
including the incomplete early `nim/` run, which is not a full benchmark.

See `../EXPERIMENT_RESULTS.md` for the final interpretation and
`../TEST_RESULTS.md` for the historical PoC diagnostics. Historical run manifests
describe the code/settings that produced them; not every early run used the final
implementation. New output folders are ignored by Git by default.
""")
    inventory = {"package": NAME, "included": "All project code, synthetic datasets, saved experiments, model audits, and checkpoints.",
                 "excluded": ["Python bytecode and caches", "temporary dashboard syntax-check JS files", "credentials and local environments", "Git metadata", "release archives"],
                 "copied_research_files": len(copied), "source_code_preserved": True,
                 "live_api_key_included": False}
    write("PACKAGE_MANIFEST.json", json.dumps(inventory, indent=2) + "\n")
    write("PACKAGE_CONTENTS.md", """# Archive contents and integrity

This distribution contains the complete code, all three synthetic-data snapshots,
raw source documents, all saved experimental results, request audits, checkpoints,
dashboards, figures, and methodology notes. Temporary interpreter/cache files and
dashboard syntax-check scratch files are excluded.

The original README is retained as `POC_GUIDE.md`. Packaging adds the repository
README, Git settings, offline CI, and dataset/output indexes. Pipeline Python files
and archived experiment evidence retain their original bytes.

`SHA256SUMS.txt` records the SHA-256 digest of every included file except itself.
It is a distribution-time integrity list; update it if intentionally changing the
package. The ZIP is accompanied by its own `.sha256` file outside the archive.

No Git repository, remote URL, API credential, or license grant is created by this
packaging step. The GitHub workflow is provided but has not been run on GitHub.
Offline tests are verified locally from the staged repository before delivery.
""")
    suspicious = []
    pattern = re.compile(rb"nvapi-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    for path in STAGE.rglob("*"):
        if path.is_file() and pattern.search(path.read_bytes()):
            suspicious.append(path.relative_to(STAGE).as_posix())
    if suspicious:
        raise SystemExit("Credential scan blocked packaging: " + ", ".join(suspicious))
    checksums = []
    for path in sorted(STAGE.rglob("*")):
        if path.is_file():
            checksums.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.relative_to(STAGE).as_posix())
    write("SHA256SUMS.txt", "\n".join(checksums) + "\n")
    with ZipFile(ZIP, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, NAME + "/" + path.relative_to(STAGE).as_posix())
    with ZipFile(ZIP) as archive:
        failure = archive.testzip()
        if failure:
            raise SystemExit("Archive integrity failure: " + failure)
        count = len(archive.namelist())
    checksum = hashlib.sha256(ZIP.read_bytes()).hexdigest()
    ZIP.with_suffix(".zip.sha256").write_text(checksum + "  " + ZIP.name + "\n", encoding="utf-8")
    print(json.dumps({"zip": str(ZIP), "stage": str(STAGE), "files": count, "zip_mib": round(ZIP.stat().st_size / 1024**2, 2), "sha256": checksum, "credential_scan": "clean"}, indent=2))


if __name__ == "__main__":
    build()
