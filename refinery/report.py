"""Portable, interactive HTML review artifact. No external assets or dependencies."""
import json
from pathlib import Path


def write_report(run, path):
    payload = json.dumps(run, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
    Path(path).write_text(template.replace("__RUN_DATA__", payload), encoding="utf-8")
