"""Count-based metrics with explicit denominators and paired group bootstrap."""
from collections import Counter
import random
from .evaluation import evaluate


def ratio(a, b):
    return a / b if b else None


def f1(tp, fp, fn):
    return ratio(2 * tp, 2 * tp + fp + fn)


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def score(records, oracle, cases, breakdown=True):
    base = evaluate(records, oracle)
    by_case = {c["id"]: c for c in cases}
    counts = Counter()
    confusion = Counter()
    localization_total = localization_correct = 0
    for r, detail in zip(records, base["details"]):
        gold = oracle[r["case_id"]]
        counts["attribute_tp"] += sum(gold["attributes"].get(k) == a["value"] for k, a in r["attributes"].items())
        counts["attribute_predicted"] += len(r["attributes"])
        counts["attribute_expected"] += len(gold["attributes"])
        actual_approved, eligible = r["state"] == "approved", gold["state"] == "approved"
        counts["publication_tp"] += actual_approved and eligible
        counts["publication_fp"] += actual_approved and not eligible
        counts["publication_fn"] += not actual_approved and eligible
        counts["publication_tn"] += not actual_approved and not eligible
        counts["state_correct"] += detail["checks"]["state"]
        counts["match_correct"] += detail["checks"]["match"]
        confusion[(gold["match"], r["matching"]["outcome"])] += 1
        counts["provider_failed_records"] += any(i["code"] == "provider_error" for i in r["issues"])
        counts["repair_records"] += any(d["action"] == "retry_extraction" for d in r["decisions"])
        counts["review_calls"] += bool(r.get("advisory_review"))
        # Deduplicate source-field-value-unit predictions. Source-level gold keeps
        # contradictory-but-explicit observations distinct from canonical truth.
        predicted = set()
        for p in r["proposals"]:
            if isinstance(p, dict):
                predicted.add(tuple(str(p.get(k)) for k in ("source_id", "field", "value", "unit")))
        wanted = {(sid, field, str(value), str({"voltage": "V", "frequency": "Hz", "power": "W"}.get(field)))
                  for sid, attrs in gold.get("source_attributes", {}).items() for field, value in attrs.items()}
        counts["raw_tp"] += len(predicted & wanted)
        counts["raw_predicted"] += len(predicted)
        counts["raw_expected"] += len(wanted)
        for row in r["view"]["rows"]:
            localization_total += 1
            a = r["attributes"].get(row["field"])
            localization_correct += bool(a and row["canonical_value"] == a["value"] and row["unit"] == a["unit"])
    tp, predicted, wanted = counts["attribute_tp"], counts["attribute_predicted"], counts["attribute_expected"]
    rawtp, rawpred, rawwanted = counts["raw_tp"], counts["raw_predicted"], counts["raw_expected"]
    pubtp, pubfp, pubfn = counts["publication_tp"], counts["publication_fp"], counts["publication_fn"]
    classes = ("same_product", "related_variant", "different_product", "insufficient_evidence")
    class_scores = []
    for label in classes:
        ctp = confusion[(label, label)]
        fp = sum(v for (a, b), v in confusion.items() if b == label and a != label)
        fn = sum(v for (a, b), v in confusion.items() if a == label and b != label)
        value = f1(ctp, fp, fn)
        if value is not None:
            class_scores.append(value)
    latency = [r.get("experiment_usage", {}).get("logical_seconds", 0) for r in records]
    base.update({"exact_case_accuracy": ratio(base["passed"], len(records)),
                 "attribute_precision": ratio(tp, predicted), "attribute_f1": f1(tp, predicted - tp, wanted - tp),
                 "raw_extraction_precision": ratio(rawtp, rawpred), "raw_extraction_recall": ratio(rawtp, rawwanted),
                 "raw_extraction_f1": f1(rawtp, rawpred - rawtp, rawwanted - rawtp),
                 "publication_precision": ratio(pubtp, pubtp + pubfp), "publication_recall": ratio(pubtp, pubtp + pubfn),
                 "publication_f1": f1(pubtp, pubfp, pubfn), "unsafe_publications": pubfp,
                 "unnecessary_reviews": pubfn, "state_accuracy": ratio(counts["state_correct"], len(records)),
                 "matching_accuracy": ratio(counts["match_correct"], len(records)),
                 "matching_macro_f1": sum(class_scores) / len(class_scores) if class_scores else None,
                 "matching_confusion": [{"expected": a, "predicted": b, "count": v} for (a, b), v in sorted(confusion.items()) if v],
                 "localization_invariant_rate": ratio(localization_correct, localization_total),
                 "logical_requests": sum(r.get("experiment_usage", {}).get("logical_requests", 0) for r in records),
                 "logical_tokens": sum(r.get("experiment_usage", {}).get("logical_tokens", 0) for r in records),
                 "latency_seconds_p50": quantile(latency, .5), "latency_seconds_p95": quantile(latency, .95),
                 "counts": dict(counts), "scope": "Seeded synthetic, group-disjoint benchmark; descriptive results only."})
    if breakdown:
        base["breakdowns"] = {}
        for axis in ("language", "market", "scenario", "format", "group"):
            groups = {}
            for record in records:
                groups.setdefault(by_case[record["case_id"]][axis], []).append(record)
            base["breakdowns"][axis] = {}
            for name, subset in groups.items():
                sub = score(subset, oracle, cases, breakdown=False)
                base["breakdowns"][axis][name] = {k: sub[k] for k in ("cases", "passed", "attribute_precision", "attribute_recall", "attribute_f1", "raw_extraction_f1", "auto_acceptance_rate", "publication_precision", "publication_recall", "unsafe_publications", "matching_accuracy")}
    return base


def paired_comparison(first, second, oracle, cases, samples=2000, seed=17):
    """Resample PRODUCT GROUPS, never treat translated siblings as independent."""
    a = {r["case_id"]: r for r in first}
    b = {r["case_id"]: r for r in second}
    groups = {}
    for case in cases:
        cid = case["id"]
        if cid not in a or cid not in b:
            continue
        def correct(r):
            g = oracle[cid]
            return r["state"] == g["state"] and r["matching"]["outcome"] == g["match"] and {k: v["value"] for k, v in r["attributes"].items()} == g["attributes"]
        groups.setdefault(case["group"], []).append(int(correct(b[cid])) - int(correct(a[cid])))
    keys = sorted(groups)
    observed = [x for key in keys for x in groups[key]]
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        values = [x for _ in keys for x in groups[rng.choice(keys)]]
        draws.append(sum(values) / len(values))
    return {"metric": "conditional minus single-pass exact-case accuracy", "paired_cases": len(observed),
            "groups": len(keys), "difference": sum(observed) / len(observed),
            "cluster_bootstrap_95_percent_interval": [quantile(draws, .025), quantile(draws, .975)],
            "bootstrap_samples": samples, "seed": seed,
            "caution": "Few synthetic groups; descriptive resampling interval, not evidence of real-world significance."}
