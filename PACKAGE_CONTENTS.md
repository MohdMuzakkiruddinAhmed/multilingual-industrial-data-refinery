# Package contents and integrity

This repository contains the code, synthetic-data snapshots, raw source documents,
saved experiments, model request audits, checkpoints, dashboards, figures, and
methodology notes from the supplied research archive.

The GitHub presentation adds a visual README, architecture guide, contribution
guidance, issue forms, and package metadata. The pipeline, tests, datasets, and
saved experimental results retain their original bytes. `POC_GUIDE.md` preserves
the original implementation walkthrough.

`SHA256SUMS.txt` records the SHA-256 digest of the published files except itself.
It is refreshed for this repository publication; it is not the checksum list of
the original ZIP. The source ZIP remains unchanged outside the repository.
`PACKAGE_MANIFEST.json` records its digest and this publication's scope.

To verify an unmodified checkout with Python, run this from the repository root:

```python
import hashlib
from pathlib import Path

for line in Path("SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
    expected, name = line.split("  ", 1)
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual == expected, name
print("All recorded files match.")
```

Update the checksum list when intentionally changing package contents. Frozen
experiment manifests retain the code and dataset hashes from their original runs.

`tools/package_github.py` is the original archive-building utility, retained for
historical context. It embeds the earlier README and packaging templates and does
not preserve the current presentation; use GitHub's source ZIP or `git archive`
to distribute the current tracked repository.

No API credential or license grant is included. Interpreter caches, local virtual
environments, and new local experiment folders are excluded from the publication.
