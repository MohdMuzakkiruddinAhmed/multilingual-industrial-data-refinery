# Contributing

Contributions should make the refinery easier to reproduce, inspect, or evaluate.
Use the issue forms for bugs and proposals, and include a minimal synthetic case
when reporting extraction or validation behavior.

## Local development

Use Python 3.11 or newer. From the repository root, create and activate a virtual
environment, then run:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m refinery run --provider rules --out outputs/contribution-smoke
```

These checks run offline. The original demo should return 14/14 exact cases.
Matplotlib is optional: install `.[plots]` to regenerate figures. GitHub Actions
runs the offline checks on Python 3.11, 3.12, and 3.13 without an API key.

## Research artifacts

- Preserve frozen datasets, raw source bytes, historical manifests, and audit logs.
  Put new experiments in a fresh folder; most new output folders are ignored.
- Keep expected answers separate from extraction and model prompts.
- Report accuracy together with acceptance coverage, failures, usage, and limitations.
- Record the seed, settings, model, and relevant code revision for new measurements.
- Add a focused regression test when changing evidence acceptance or publication behavior.

Pipeline changes do not rewrite historical findings. Explain any changed
assumptions and record new results separately. The benchmark's known narrative
misses are measured outcomes, while unit tests are strict regression checks.

## Pull requests

Describe the problem, resulting behavior, and checks you ran. Keep changes focused
and link any relevant issue or synthetic scenario. New dependencies should have a
clear purpose; the core runtime currently uses the standard library only.

Do not commit API credentials, private catalog data, environment files, or
unredacted logs. Use synthetic examples in public issues. Live NIM experiments
are optional, explicit runs with a process-scoped `NVIDIA_API_KEY`.
