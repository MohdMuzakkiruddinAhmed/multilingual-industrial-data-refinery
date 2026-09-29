"""Oracle scoring stays outside the extraction and acceptance pipeline."""
from collections import Counter


def evaluate(results, expected):
    details = []
    correct_attributes = total_attributes = expected_attributes = 0
    evidence_valid = 0
    for record in results:
        oracle = expected[record["case_id"]]
        actual = {k: v["value"] for k, v in record["attributes"].items()}
        correct = sum(oracle["attributes"].get(k) == v for k, v in actual.items())
        correct_attributes += correct
        total_attributes += len(actual)
        expected_attributes += len(oracle["attributes"])
        for attribute in record["attributes"].values():
            registry = {s["id"]: s for s in record["sources"]}
            evidence_valid += bool(attribute["evidence"]) and all(
                e["source_id"] in registry and registry[e["source_id"]]["eligible"] and
                registry[e["source_id"]]["sha256"] == e["source_sha256"] and
                registry[e["source_id"]]["text"][e["start"]:e["end"]] == e["quote"]
                for e in attribute["evidence"])
        checks = {"state": record["state"] == oracle["state"],
                  "match": record["matching"]["outcome"] == oracle["match"],
                  "attributes": actual == oracle["attributes"]}
        details.append({"case_id": record["case_id"], "passed": all(checks.values()), "checks": checks,
                        "expected": oracle, "actual": {"state": record["state"], "match": record["matching"]["outcome"], "attributes": actual}})
    approved = [r for r in results if r["state"] == "approved"]
    published_correct = sum(d["passed"] for d in details if d["actual"]["state"] == "approved")
    languages = {}
    for record, detail in zip(results, details):
        for language in set(s["language"] for s in record["sources"]):
            group = languages.setdefault(language, {"cases": 0, "passed": 0, "approved": 0})
            group["cases"] += 1
            group["passed"] += detail["passed"]
            group["approved"] += record["state"] == "approved"
    markets = {}
    for record, detail in zip(results, details):
        group = markets.setdefault(record["market"], {"cases": 0, "passed": 0, "approved": 0})
        group["cases"] += 1
        group["passed"] += detail["passed"]
        group["approved"] += record["state"] == "approved"
    return {"cases": len(results), "passed": sum(d["passed"] for d in details),
            "approved": len(approved), "review_required": len(results) - len(approved),
            "auto_acceptance_rate": len(approved) / len(results) if results else 0,
            "accepted_record_correctness": published_correct / len(approved) if approved else None,
            "attribute_correctness": correct_attributes / total_attributes if total_attributes else None,
            "attribute_recall": correct_attributes / expected_attributes if expected_attributes else None,
            "unsupported_accepted_attributes": total_attributes - correct_attributes,
            "evidence_link_coverage": evidence_valid / total_attributes if total_attributes else None,
            "false_same_product_decisions": sum(d["actual"]["match"] == "same_product" and d["expected"]["match"] != "same_product" for d in details),
            "state_counts": dict(Counter(r["state"] for r in results)),
            "by_language": languages, "by_market": markets, "details": details,
            "scope": "Handcrafted synthetic regression cases; not a real-world performance estimate."}
