import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from refinery.benchmark_data import generate, write_benchmark, load_case_documents, select_cases, fingerprint, SCENARIOS
from refinery.contracts import parse_segment
from refinery.engine import refine_case, rule_proposals
from refinery.experiment_metrics import score, paired_comparison
from refinery.experiments import SharedFirstResponse, fault_experiment


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.oracle = generate(groups=8)

    def test_semantic_generator_is_seeded(self):
        other, golden = generate(groups=8)
        self.assertEqual(fingerprint(self.inputs), fingerprint(other))
        self.assertEqual(self.oracle, golden)
        changed, _ = generate(seed=2, groups=8)
        self.assertNotEqual(fingerprint(other), fingerprint(changed))

    def test_family_splits_are_disjoint(self):
        groups = {split: {c["group"] for c in self.inputs["cases"] if c["split"] == split} for split in ("train", "dev", "test")}
        self.assertFalse(groups["train"] & groups["dev"])
        self.assertFalse(groups["dev"] & groups["test"])
        self.assertFalse(groups["train"] & groups["test"])

    def test_balanced_stratified_selection(self):
        selected = select_cases(self.inputs)
        self.assertEqual(len(selected), len(SCENARIOS) * 4)
        self.assertEqual(len({(c["language"], c["scenario"]) for c in selected}), len(selected))

    def test_source_payloads_do_not_contain_oracle_metadata(self):
        for case in select_cases(self.inputs):
            for source in case["sources"]:
                self.assertNotIn("scenario", source)
                self.assertNotIn("expected", source)
                self.assertNotIn(case["scenario"], source["id"])

    def test_table_json_synonyms_and_arabic_digits(self):
        examples = {"| Nennleistung | 1,5 kW |": ("power", "1500"),
                    '"rated voltage": "0.23 kV",': ("voltage", "230"),
                    "MPN = FM123-A": ("part_number", "FM123-A"),
                    "القدرة المقننة: ١٫٥ kW": ("power", "1500")}
        for text, pair in examples.items():
            fact = parse_segment(text)
            self.assertEqual((fact["field"], fact["value"]), pair)

    def test_no_invented_narrative_entailment(self):
        self.assertIsNone(parse_segment("The motor operates at 230 V and 50 Hz."))

    def test_json_indentation_and_comma_resolve_to_original_evidence(self):
        from refinery.engine import register_sources, validate_proposals
        case = next(c for c in self.inputs["cases"] if c["scenario"] == "json_record")
        registry = register_sources(case["sources"])
        proposal = rule_proposals(registry)[0]
        proposal["quote"] = "  " + proposal["quote"].rstrip(",")
        accepted, rejected, _ = validate_proposals([proposal], registry)
        self.assertFalse(rejected)
        ev = accepted[proposal["field"]]["evidence"][0]
        self.assertEqual(case["sources"][0]["text"][ev["start"]:ev["end"]], ev["quote"])

    def test_oracle_retains_explicit_conflicting_raw_facts(self):
        case = next(c for c in self.inputs["cases"] if c["scenario"] == "active_conflict")
        golden = self.oracle[case["id"]]
        self.assertNotIn("voltage", golden["attributes"])
        self.assertEqual(len({a["voltage"] for a in golden["source_attributes"].values()}), 2)

    def test_actual_documents_are_loaded_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            write_benchmark(folder, groups=8)
            inputs = json.loads((Path(folder) / "sources.json").read_text(encoding="utf-8"))
            case = inputs["cases"][0]
            loaded = load_case_documents(case, folder)
            self.assertEqual(loaded, case)
            (Path(folder) / case["sources"][0]["path"]).write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                load_case_documents(case, folder)

    def test_frozen_dataset_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            write_benchmark(folder, groups=8)
            with self.assertRaises(ValueError):
                write_benchmark(folder, groups=8)

    def test_document_path_traversal_rejected(self):
        case = copy.deepcopy(self.inputs["cases"][0])
        case["sources"][0]["path"] = "../outside.txt"
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "escapes"):
                load_case_documents(case, folder)

    def test_raw_and_accepted_metrics_have_different_denominators(self):
        case = next(c for c in self.inputs["cases"] if c["scenario"] == "active_conflict")
        record = refine_case(case, self.inputs["catalog"])
        m = score([record], self.oracle, [case])
        self.assertEqual(m["raw_extraction_f1"], 1)
        self.assertEqual(m["attribute_f1"], 1)
        self.assertGreater(m["counts"]["raw_expected"], m["counts"]["attribute_expected"])

    def test_narrative_misses_are_not_removed_from_metrics(self):
        case = next(c for c in self.inputs["cases"] if c["scenario"] == "narrative")
        record = refine_case(case, self.inputs["catalog"])
        m = score([record], self.oracle, [case])
        self.assertEqual(m["passed"], 0)
        self.assertEqual(m["attribute_recall"], 0)
        self.assertEqual(m["publication_recall"], 0)
        self.assertEqual(m["unnecessary_reviews"], 1)

    def test_shared_response_is_copied_not_mutated(self):
        proposals = [{"field": "power", "value": "1500"}]
        client = SharedFirstResponse(proposals, None)
        result = client.extract([])
        result[0]["value"] = "bad"
        self.assertEqual(proposals[0]["value"], "1500")

    def test_single_pass_disables_repair_and_review(self):
        case = self.inputs["cases"][0]
        client = SharedFirstResponse([], None)
        record = refine_case(case, self.inputs["catalog"], client, repair=False, review=False)
        self.assertIsNone(record["advisory_review"])
        self.assertFalse(any(d["action"] == "retry_extraction" for d in record["decisions"]))

    def test_repair_can_correct_an_invalid_proposal_without_erasing_audit(self):
        case = self.inputs["cases"][0]
        class RepairClient:
            def extract(self, sources, feedback=None):
                proposals = rule_proposals(sources)
                if feedback is None:
                    proposals[-1]["value"] = "999999"
                return proposals
        record = refine_case(case, self.inputs["catalog"], RepairClient(), review=False)
        self.assertEqual(record["state"], "approved")
        self.assertTrue(record["superseded_proposals"])
        self.assertFalse(record["rejected_proposals"])

    def test_group_bootstrap_identical_arms_zero_difference(self):
        cases = select_cases(self.inputs)[:8]
        records = [refine_case(c, self.inputs["catalog"]) for c in cases]
        comparison = paired_comparison(records, records, self.oracle, cases, samples=30)
        self.assertEqual(comparison["difference"], 0)
        self.assertEqual(comparison["cluster_bootstrap_95_percent_interval"], [0, 0])

    def test_injected_faults_are_rejected(self):
        cases = select_cases(self.inputs)[:8]
        result = fault_experiment(cases, self.oracle)
        self.assertGreater(result["counts"]["injected_claims"], 0)
        self.assertEqual(result["counts"]["guarded_wrong_acceptances"], 0)


if __name__ == "__main__":
    unittest.main()
