import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from refinery.contracts import parse_segment, MARKETS
from refinery.engine import (refine_case, register_sources, rule_proposals, validate_proposals,
                             publication_export, localize, dependent_cases)
from refinery.evaluation import evaluate
from refinery.nim import NimClient, NimError, parse_object
from refinery.report import write_report
from refinery.synthetic import dataset


class RefineryTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.expected = dataset()
        self.case = copy.deepcopy(self.inputs["cases"][0])
        self.catalog = self.inputs["catalog"]

    def refine(self, case=None, client=None):
        return refine_case(case or self.case, self.catalog, client)

    def test_full_synthetic_regression(self):
        results = [self.refine(c) for c in self.inputs["cases"]]
        metrics = evaluate(results, self.expected)
        self.assertEqual(metrics["passed"], 14)
        self.assertEqual(metrics["approved"], 8)
        self.assertEqual(metrics["unsupported_accepted_attributes"], 0)

    def test_exact_decimal_conversion(self):
        fact = parse_segment("Leistung: 1,5 kW")
        self.assertEqual(fact["value"], "1500")
        self.assertEqual(fact["status"], "derived")
        self.assertEqual(parse_segment("Power: 0.001 kW")["value"], "1")

    def test_ambiguous_and_malformed_values_rejected(self):
        for text in ("Voltage: 230/460 V", "Power: 1,500.5 W", "Voltage: 50 Hz",
                     "Power: -3 W", "Power: NaN W", "Power: 1.5", "Voltage: 0 V"):
            with self.subTest(text=text):
                self.assertIsNone(parse_segment(text))

    def test_forged_quote_does_not_accept_attribute(self):
        registry = register_sources(self.case["sources"])
        proposal = {"source_id": "en-1", "field": "power", "value": "9000", "unit": "W", "quote": "Power: 9000 W"}
        attrs, rejected, _ = validate_proposals([proposal], registry)
        self.assertNotIn("power", attrs)
        self.assertEqual(len(rejected), 1)

    def test_real_quote_with_forged_value_rejected(self):
        registry = register_sources(self.case["sources"])
        proposal = rule_proposals(registry)[-1]
        proposal["value"] = "9000"
        attrs, rejected, _ = validate_proposals([proposal], registry)
        self.assertFalse(attrs)
        self.assertEqual(rejected[0]["reason"], "proposed_value_disagrees_with_evidence")

    def test_wrong_field_and_partial_quote_rejected(self):
        registry = register_sources(self.case["sources"])
        for quote in ("230 V", "voltage: 230 V"):
            proposal = {"source_id": "en-1", "field": "power", "value": "230", "unit": "W", "quote": quote}
            self.assertFalse(validate_proposals([proposal], registry)[0])

    def test_malformed_proposals_are_quarantined(self):
        bad = [None, 5, "approve", {"field": []}, {"field": "power", "source_id": []}]
        attrs, rejected, _ = validate_proposals(bad, register_sources(self.case["sources"]))
        self.assertFalse(attrs)
        self.assertEqual(len(rejected), len(bad))

    def test_hidden_conflict_still_blocks(self):
        case = next(c for c in self.inputs["cases"] if c["id"] == "conflicting_sources")
        registry = register_sources(case["sources"])
        proposals = rule_proposals(registry[:1])
        attrs, _, conflicts = validate_proposals(proposals, registry)
        self.assertNotIn("voltage", attrs)
        self.assertIn("voltage", conflicts)

    def test_ambiguous_second_source_blocks(self):
        another = copy.deepcopy(self.case["sources"][0])
        another["id"] = "ambiguous-second"
        another["text"] = "Voltage: 230/460 V"
        self.case["sources"].append(another)
        self.assertEqual(self.refine()["state"], "review_required")

    def test_unknown_source_and_wrong_units_rejected(self):
        registry = register_sources(self.case["sources"])
        proposal = rule_proposals(registry)[-1]
        proposal["unit"] = "kW"
        self.assertFalse(validate_proposals([proposal], registry)[0])
        proposal["source_id"] = "not-registered"
        self.assertFalse(validate_proposals([proposal], registry)[0])

    def test_withdrawal_identifies_dependents_and_blocks_reprocessing(self):
        record = self.refine()
        self.assertEqual(dependent_cases([record], "en-1"), ["english_complete"])
        self.case["sources"][0]["active"] = False
        revised = self.refine()
        self.assertEqual(revised["state"], "review_required")
        self.assertIsNone(revised["publication"])

    def test_untrusted_revision_cannot_supersede_authorized_source(self):
        another = copy.deepcopy(self.case["sources"][0])
        another.update(id="untrusted", authorized=False, supersedes="en-1")
        self.case["sources"].append(another)
        self.assertTrue(register_sources(self.case["sources"])[0]["eligible"])

    def test_supersession_cycles_and_duplicate_ids_rejected(self):
        one = copy.deepcopy(self.case["sources"][0])
        two = {**one, "id": "two", "supersedes": one["id"]}
        one["supersedes"] = "two"
        with self.assertRaises(ValueError):
            register_sources([one, two])
        with self.assertRaises(ValueError):
            register_sources([one, one])

    def test_model_cannot_approve_or_supply_facts_without_evidence(self):
        class MaliciousClient:
            def extract(self, sources, feedback=None):
                return [{"field": "power", "source_id": "en-1", "value": "9000", "unit": "W", "quote": "Power: 9000 W", "state": "approved"}]
            def review(self, issues, sources):
                return {"summary": "Approved by model", "state": "approved"}
        record = self.refine(client=MaliciousClient())
        self.assertEqual(record["state"], "review_required")
        self.assertFalse(record["attributes"])
        self.assertIsNone(record["publication"])

    def test_api_failure_never_falls_back_to_rules(self):
        class BrokenClient:
            def extract(self, sources, feedback=None):
                raise NimError("NIM unavailable")
        record = self.refine(client=BrokenClient())
        self.assertFalse(record["attributes"])
        self.assertEqual(record["state"], "review_required")
        self.assertEqual(record["issues"][0]["code"], "provider_error")

    def test_bounded_retry_and_conditional_review(self):
        class OmissionClient:
            def __init__(self):
                self.extracts = self.reviews = 0
            def extract(self, sources, feedback=None):
                self.extracts += 1
                return []
            def review(self, issues, sources):
                self.reviews += 1
                return {"summary": "Need review"}
        client = OmissionClient()
        self.refine(client=client)
        self.assertEqual(client.extracts, 2)
        self.assertEqual(client.reviews, 1)

    def test_input_immutable(self):
        original = copy.deepcopy(self.case)
        self.refine()
        self.assertEqual(self.case, original)

    def test_market_views_preserve_facts(self):
        record = self.refine()
        for market in MARKETS:
            view = localize(record, market)
            for row in view["rows"]:
                self.assertEqual(row["canonical_value"], record["attributes"][row["field"]]["value"])

    def test_new_market_cannot_inherit_approval_with_missing_fields(self):
        record = self.refine()
        view = localize(record, "es-MX")
        self.assertEqual(view["state"], "review_required")
        self.assertEqual(view["missing_market_fields"], ["certification"])

    def test_identifier_collision_blocks_instead_of_merging(self):
        self.case["sources"][0]["text"] = self.case["sources"][0]["text"].replace("230 V", "110 V")
        record = self.refine()
        self.assertEqual(record["matching"]["outcome"], "insufficient_evidence")
        self.assertEqual(record["state"], "review_required")

    def test_localized_fact_tampering_blocks_publication(self):
        record = self.refine()
        record["view"]["rows"][0]["display"] = "Changed manufacturer"
        with self.assertRaises(ValueError):
            publication_export(record)

    def test_canonical_fact_tampering_blocks_publication(self):
        record = self.refine()
        record["attributes"]["voltage"]["value"] = "110"
        record["view"] = localize(record, record["market"])
        with self.assertRaises(ValueError):
            publication_export(record)

    def test_source_tampering_blocks_publication(self):
        record = self.refine()
        record["sources"][0]["text"] += "; Power: 9999 W"
        with self.assertRaises(ValueError):
            publication_export(record)

    def test_review_record_cannot_be_published(self):
        record = self.refine(next(c for c in self.inputs["cases"] if c["id"] == "missing_power"))
        with self.assertRaises(ValueError):
            publication_export(record)

    def test_unique_span_required(self):
        self.case["sources"][0]["text"] += "; voltage: 230 V"
        record = self.refine()
        self.assertNotIn("voltage", record["attributes"])

    def test_json_output_contract(self):
        self.assertEqual(parse_object('```json\n{"proposals": []}\n```'), {"proposals": []})
        for value in ("[]", "not json", None, '{"proposals": []} trailing'):
            with self.assertRaises(NimError):
                parse_object(value)

    def test_credentials_required_and_endpoint_restricted(self):
        with self.assertRaises(NimError):
            NimClient(api_key="", base_url="https://integrate.api.nvidia.com/v1")
        for url in ("http://integrate.api.nvidia.com/v1", "https://example.com/v1", "https://integrate.api.nvidia.com.evil.test/v1"):
            with self.assertRaises(NimError):
                NimClient(api_key="fake", base_url=url)

    def test_request_budget_is_enforced_before_network(self):
        client = NimClient(api_key="fake", max_calls=0)
        with self.assertRaisesRegex(NimError, "budget"):
            client.complete("system", {}, "test")

    def test_transient_transport_retry_is_bounded(self):
        client = NimClient(api_key="fake")
        def fail(*args):
            client.calls.append({"error": "HTTP 503"})
            raise NimError("HTTP 503", retryable=True)
        with patch.object(client, "_complete_once", side_effect=fail) as complete, patch("refinery.nim.time.sleep"):
            with self.assertRaises(NimError):
                client.complete("system", {}, "test")
            self.assertEqual(complete.call_count, 2)

    def test_authentication_errors_are_not_retried(self):
        client = NimClient(api_key="fake")
        with patch.object(client, "_complete_once", side_effect=NimError("HTTP 401")) as complete:
            with self.assertRaises(NimError):
                client.complete("system", {}, "test")
            self.assertEqual(complete.call_count, 1)

    def test_report_escapes_script_end_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.html"
            write_report({"payload": "</script><script>alert(1)</script>"}, path)
            self.assertNotIn('</script><script>alert(1)', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
