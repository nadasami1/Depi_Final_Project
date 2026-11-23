import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from team_quality import gx_checks, record_team_results
from build_warehouse import QualityLog


class TeamQualityTests(unittest.TestCase):
    def test_boolean_only_failure_is_not_zero_failed_rows(self):
        result = gx_checks({"results": [{"success": False, "result": {},
                            "expectation_config": {"type": "expect_column_to_exist"}}]})
        self.assertEqual(result[0]["failed"], 1)
        self.assertEqual(result[0]["total"], 1)

    def test_old_and_new_expectation_names_are_supported(self):
        result = gx_checks({"results": [
            {"success": True, "expectation_config": {"type": "new"}},
            {"success": False, "expectation_config": {"expectation_type": "old"},
             "result": {"unexpected_count": 12, "element_count": 100}}]})
        self.assertEqual([x["failed"] for x in result], [0, 1])
        self.assertEqual(json.loads(result[1]["details"])["result"]["unexpected_count"], 12)

    def test_invalid_export_is_logged_and_blocks_build(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "invalid.json").write_text('{"results": []}')
            log = QualityLog()
            record_team_results(log, pd.DataFrame(columns=["year", "table", "status", "rows", "issues"]), path)
            with self.assertRaises(ValueError):
                log.require_valid()

    def test_team_review_is_warning_but_failed_extraction_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            records = pd.DataFrame([{"year": 2020, "table": 6, "status": "review", "rows": 26, "issues": "mismatch"},
                                    {"year": 2020, "table": 8, "status": "failed", "rows": 0, "issues": "extraction error"}])
            log = QualityLog()
            record_team_results(log, records, Path(directory))
            self.assertEqual([row["status"] for row in log.rows], ["warning", "fail"])
            with self.assertRaises(ValueError):
                log.require_valid()
