"""Proposal -> evidence validation -> canonical record -> controlled market view."""
import hashlib
import json
from copy import deepcopy
from .contracts import (FIELDS, REQUIRED, PROTECTED, MARKETS, LABELS, ALIASES, SCHEMA_VERSION,
                        POLICY_VERSION, TERMINOLOGY_VERSION, parse_segment, segments, same_value, segment_field)
from .nim import NimError


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def register_sources(sources):
    ids = [s["id"] for s in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source IDs")
    known = set(ids)
    edges = {s["id"]: s["supersedes"] for s in sources if s.get("supersedes")}
    for sid, target in edges.items():
        if target not in known:
            raise ValueError("Superseded source must be registered")
        visited = {sid}
        while target in edges:
            if target in visited:
                raise ValueError("Cyclic source supersession")
            visited.add(target)
            target = edges[target]
        if target in visited:
            raise ValueError("Cyclic source supersession")
    # Withdrawal does not revive evidence explicitly superseded by an authorized revision.
    superseded = {s["supersedes"] for s in sources if s.get("supersedes") and s.get("authorized")}
    return [{**deepcopy(s), "sha256": digest(s),
             "eligible": bool(s.get("active") and s.get("authorized") and s["id"] not in superseded)} for s in sources]


def rule_proposals(sources):
    """Offline rule baseline; does not pretend to be an LLM or read the oracle."""
    output = []
    for source in sources:
        for quote, _ in segments(source["text"]):
            fact = parse_segment(quote)
            if fact:
                output.append({"source_id": source["id"], "field": fact["field"],
                               "value": fact["value"], "unit": fact["unit"], "quote": quote})
    return output


def validate_proposals(proposals, registry):
    by_id = {s["id"]: s for s in registry}
    attributes, rejected, conflicts = {}, [], []
    for proposal in proposals:
        reason = None
        if not isinstance(proposal, dict):
            rejected.append({"proposal": proposal, "reason": "invalid_proposal_schema"})
            continue
        field = proposal.get("field")
        sid = proposal.get("source_id")
        if not isinstance(field, str) or field not in FIELDS or not isinstance(sid, str):
            rejected.append({"proposal": proposal, "reason": "invalid_proposal_schema"})
            continue
        src = by_id.get(sid)
        quote = proposal.get("quote")
        if not src or not src["eligible"]:
            reason = "source_unavailable_or_ineligible"
        elif not isinstance(quote, str) or not quote:
            reason = "missing_quote"
        else:
            requested_quote = quote.strip()
            # Harmless document punctuation may be omitted by the model. Resolve
            # to one complete ORIGINAL segment, never fabricate evidence text.
            anchors = [(text, start) for text, start in segments(src["text"])
                       if text == requested_quote or (text.startswith('"') and requested_quote.startswith('"')
                                                      and text.rstrip(",") == requested_quote.rstrip(","))]
            if len(anchors) == 1:
                quote, start = anchors[0]
            fact = parse_segment(quote)
            if len(anchors) != 1:
                reason = "quote_not_unique_complete_source_segment"
            elif not fact or fact["field"] != field:
                reason = "quote_does_not_support_field"
            elif not same_value(field, proposal.get("value"), fact["value"]) or proposal.get("unit") != fact["unit"]:
                reason = "proposed_value_disagrees_with_evidence"
        if reason:
            rejected.append({"proposal": proposal, "reason": reason})
            continue
        evidence = {"source_id": sid, "source_version": src["version"], "source_sha256": src["sha256"],
                    "location": src["location"], "quote": quote, "start": start, "end": start + len(quote),
                    "original_value": fact["original_value"], "rule": fact["rule"],
                    "quote_anchor_rule": "unique-complete-segment:outer-whitespace-and-json-comma-v1"}
        if field not in attributes:
            attributes[field] = {"value": fact["value"], "unit": fact["unit"], "status": fact["status"], "evidence": [evidence]}
        elif attributes[field]["value"] == fact["value"]:
            if evidence not in attributes[field]["evidence"]:
                attributes[field]["evidence"].append(evidence)
        else:
            conflicts.append(field)

    # Independently inspect all recognized active evidence. An LLM cannot conceal
    # a contradictory source by omitting it from its proposals.
    observed = {}
    for src in registry:
        if not src["eligible"]:
            continue
        for quote, _ in segments(src["text"]):
            fact = parse_segment(quote)
            if fact:
                observed.setdefault(fact["field"], set()).add(fact["value"])
    conflicts = sorted(set(conflicts) | {f for f, values in observed.items() if len(values) > 1})
    for field in conflicts:
        attributes.pop(field, None)
    return attributes, rejected, conflicts


def match_product(attributes, catalog):
    values = {k: a["value"] for k, a in attributes.items()}
    if not all(field in values for field in REQUIRED):
        return {"outcome": "insufficient_evidence", "candidate_id": None, "reason": "required_identity_or_technical_attributes_missing"}
    variants = []
    for candidate in catalog:
        reference = candidate["attributes"]
        if candidate.get("status") != "approved":
            continue
        if values["manufacturer"] == reference["manufacturer"] and values["part_number"] == reference["part_number"]:
            differences = [field for field in (*PROTECTED, "family") if values[field] != reference[field]]
            if differences:
                return {"outcome": "insufficient_evidence", "candidate_id": candidate["id"], "reason": "identifier_collision", "conflicts": differences}
            return {"outcome": "same_product", "candidate_id": candidate["id"], "reason": "manufacturer_part_and_protected_attributes_agree"}
        if values["manufacturer"] == reference["manufacturer"] and values["family"] == reference["family"]:
            variants.append(candidate["id"])
    if variants:
        return {"outcome": "related_variant", "candidate_id": variants[0], "reason": "same_explicit_family_different_part"}
    return {"outcome": "different_product", "candidate_id": None, "reason": "no_approved_identity_match"}


def localize(record, market):
    profile = MARKETS[market]
    missing = [field for field in profile["required"] if field not in record["attributes"]]
    rows = []
    for field, attribute in record["attributes"].items():
        display = attribute["value"]
        if field in PROTECTED:
            display = display.replace(".", profile["decimal"]) + " " + attribute["unit"]
        rows.append({"field": field, "label": LABELS[profile["language"]][field], "display": display,
                     "canonical_value": attribute["value"], "unit": attribute["unit"],
                     "evidence_ids": [e["source_id"] for e in attribute["evidence"]]})
    return {"market": market, "language": profile["language"], "locale": profile["locale"],
            "profile_version": "demo-market-v1", "terminology_version": TERMINOLOGY_VERSION,
            "title": profile["title"], "direction": "rtl" if profile["language"] == "ar" else "ltr",
            "canonical_record_id": record["id"], "canonical_sha256": digest(record["attributes"]),
            "rows": rows, "missing_market_fields": missing,
            "state": "review_required" if missing else record["state"]}


def publication_export(record):
    """Controlled local export. This is not an enterprise publication integration."""
    if record["state"] != "approved" or record["issues"]:
        raise ValueError("Publication blocked: record requires review")
    originals = [{k: v for k, v in s.items() if k not in ("sha256", "eligible")} for s in record["sources"]]
    registry = register_sources(originals)
    if registry != record["sources"]:
        raise ValueError("Publication blocked: source registry changed")
    checked, rejected, conflicts = validate_proposals(record["proposals"], registry)
    if checked != record["attributes"] or rejected or conflicts:
        raise ValueError("Publication blocked: facts changed or unsupported")
    if any(f not in checked for f in MARKETS[record["market"]]["required"]):
        raise ValueError("Publication blocked: required attributes missing")
    if record["matching"]["reason"] == "identifier_collision":
        raise ValueError("Publication blocked: catalog identity conflict")
    for src in registry:
        if src["eligible"]:
            for quote, _ in segments(src["text"]):
                if segment_field(quote) and not parse_segment(quote):
                    raise ValueError("Publication blocked: unresolved source expression")
    expected_view = localize(record, record["market"])
    if record["view"] != expected_view:
        raise ValueError("Publication blocked: localized view changed")
    return {"record_id": record["id"], "state": "published", "simulation": True,
            "view": {**deepcopy(record["view"]), "state": "published"},
            "canonical_attributes": deepcopy(record["attributes"])}


def refine_case(case, catalog, client=None, review=True, repair=True):
    if case["market"] not in MARKETS:
        raise ValueError("Unknown market")
    registry = register_sources(case["sources"])
    eligible = [s for s in registry if s["eligible"]]
    issues, decisions = [], []
    proposals, superseded_proposals = [], []
    if eligible:
        try:
            proposals = client.extract(eligible) if client else rule_proposals(eligible)
            decisions.append({"action": "extract", "source_ids": [s["id"] for s in eligible], "provider": "nim" if client else "rules"})
        except NimError as exc:
            issues.append({"code": "provider_error", "detail": str(exc)})
    else:
        issues.append({"code": "no_eligible_sources"})
    attributes, rejected, conflicts = validate_proposals(proposals, registry)
    # One bounded repair opportunity based on source-checkable omissions, not expected answers.
    supported_fields = {p["field"] for p in rule_proposals(eligible)} - set(conflicts)
    omitted = sorted(supported_fields - set(attributes))
    if client and repair and (omitted or rejected) and not any(i["code"] == "provider_error" for i in issues):
        decisions.append({"action": "retry_extraction", "reason": "supported_fields_omitted", "fields": omitted})
        try:
            retry = client.extract(eligible, {"missing_supported_fields": omitted, "rejected": rejected})
            # Keep the failed attempt in audit history, but allow a corrected
            # proposal to supersede it. Source-wide conflict checks still apply.
            superseded_proposals = list(rejected)
            proposals = [p for p in proposals if not any(p == bad["proposal"] for bad in rejected)] + retry
            attributes, rejected, conflicts = validate_proposals(proposals, registry)
        except NimError as exc:
            issues.append({"code": "provider_error", "detail": str(exc)})
    for field in conflicts:
        issues.append({"code": "conflicting_active_evidence", "field": field})
    for src in eligible:
        for quote, _ in segments(src["text"]):
            if segment_field(quote) and not parse_segment(quote):
                issues.append({"code": "unresolved_source_expression", "source_id": src["id"], "quote": quote})
    for field in MARKETS[case["market"]]["required"]:
        if field not in attributes:
            issues.append({"code": "missing_required_attribute", "field": field})
    # Unsupported proposals are retained for review, never silently accepted.
    if rejected:
        issues.append({"code": "rejected_proposals", "count": len(rejected)})
    matching = match_product(attributes, catalog)
    if matching["reason"] == "identifier_collision":
        issues.append({"code": "catalog_identity_conflict", "fields": matching["conflicts"]})
    state = "review_required" if issues else "approved"
    advisory = None
    if state == "review_required":
        decisions.append({"action": "escalate", "reason": "acceptance_checks_failed"})
        if client and review and eligible and not any(i["code"] == "provider_error" for i in issues):
            try:
                advisory = client.review(issues, eligible)
            except NimError as exc:
                advisory = {"error": str(exc), "authority": "advisory_only"}
    else:
        decisions.append({"action": "accept", "reason": "all_deterministic_checks_passed"})
    identity = {k: attributes[k]["value"] for k in ("manufacturer", "part_number") if k in attributes}
    record = {"id": "product-" + digest(identity)[:16] if len(identity) == 2 else "unresolved-" + case["id"],
              "case_id": case["id"], "market": case["market"], "schema_version": SCHEMA_VERSION,
              "policy_version": POLICY_VERSION, "attributes": attributes, "sources": registry,
              "proposals": proposals, "rejected_proposals": rejected, "superseded_proposals": superseded_proposals, "issues": issues,
              "matching": matching, "state": state, "decisions": decisions, "advisory_review": advisory,
              "lifecycle": ["proposed", "checked", state]}
    record["view"] = localize(record, case["market"])
    record["publication"] = publication_export(record) if state == "approved" else None
    if record["publication"]:
        record["lifecycle"].append("published")
    return record


def dependent_cases(results, source_id):
    """Find records requiring reprocessing after source withdrawal or correction."""
    return [r["case_id"] for r in results if any(s["id"] == source_id for s in r["sources"])]
