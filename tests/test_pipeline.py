"""Run with python3 -m unittest discover -s tests -v."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_warehouse import QualityLog, normalize_capmas, build
from standardize_faostat import standardize


class PipelineTests(unittest.TestCase):
    def test_unit_conversion_and_missing_not_zero(self):
        quality = QualityLog()
        frame = pd.DataFrame({"unit": ["thousand_m3", "feddan", "m3", "ha"],
                              "value": [2, 10, 0, None]})
        out = normalize_capmas(frame, quality)
        self.assertEqual(out.standardized_value[:3].tolist(), [2000, 4.2, 0])
        self.assertTrue(pd.isna(out.standardized_value.iloc[3]))
        self.assertEqual(out.standardized_unit.tolist(), ["m3", "ha", "m3", "ha"])

    def test_unsupported_unit_blocks_conversion(self):
        quality = QualityLog()
        with self.assertRaisesRegex(ValueError, "Unsupported CAPMAS"):
            normalize_capmas(pd.DataFrame({"unit": ["unknown"], "value": [1]}), quality)
        self.assertEqual(quality.rows[0]["status"], "fail")

    def test_quality_log_appends_and_failure_blocks(self):
        with tempfile.TemporaryDirectory() as folder, patch("build_warehouse.LOG", Path(folder) / "log.csv"):
            for count in [0, 2]:
                log = QualityLog()
                log.check("sample", "missing", count, 10)
                log.flush()
                if count:
                    with self.assertRaises(ValueError):
                        log.require_valid()
            saved = pd.read_csv(Path(folder) / "log.csv")
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved.run_id.nunique(), 2)
            self.assertEqual(saved.status.tolist(), ["pass", "fail"])

    def test_original_faostat_fields_and_flags_preserved(self):
        table, report = standardize("faostat_crop_production_egypt_2016_2020.csv")
        raw = pd.read_csv(ROOT / "datasets/raw/faostat/faostat_crop_production_egypt_2016_2020.csv", dtype=str, keep_default_na=False)
        pd.testing.assert_frame_equal(table[raw.columns], raw)
        self.assertEqual(report["missing_values_preserved"], 12)
        self.assertEqual(table.standardized_value.isna().sum(), 12)

    def test_fact_integrity_no_totals_or_fabricated_production(self):
        fact = pd.read_csv(ROOT / "datasets/gold/fact_water_usage.csv")
        crops = pd.read_csv(ROOT / "datasets/gold/dim_crop.csv")
        govs = pd.read_csv(ROOT / "datasets/gold/dim_governorate.csv")
        self.assertGreater(len(fact), 0)
        self.assertFalse(fact.duplicated(["governorate_id", "year", "season", "crop_id"]).any())
        self.assertTrue(set(fact.governorate_id) <= set(govs.governorate_id))
        self.assertTrue(set(fact.crop_id) <= set(crops.crop_id))
        self.assertNotIn("total", crops.crop_name.tolist())
        self.assertNotIn(21, fact.source_table.unique())
        self.assertFalse(fact[["mean_temperature_c", "annual_precipitation_mm"]].isna().any().any())
        self.assertTrue(fact.crop_yield_tons.isna().all())
        self.assertTrue(fact.water_productivity.isna().all())
        self.assertGreater(fact.review_required.sum(), 0)
        raw = pd.read_csv(ROOT / "datasets/raw/capmas_team/capmas_all_tables_long.csv")
        raw["source_row_id"] = range(1, len(raw)+1)
        joined = fact.merge(raw[["source_row_id", "value"]], on="source_row_id", validate="one_to_one")
        self.assertEqual(len(joined), len(fact))
        self.assertTrue((joined.water_used_m3 == joined.value * 1000).all())

    def test_annual_water_bases_not_combined(self):
        annual = pd.read_csv(ROOT / "datasets/gold/fact_water_annual.csv")
        self.assertEqual(set(annual.measurement_basis), {"canals", "aswan"})
        self.assertFalse(annual.duplicated(["governorate_id", "year", "measurement_basis"]).any())

    def test_rerun_replaces_facts_without_duplicate_rows(self):
        # Two complete builds must yield identical business tables, with distinct log runs.
        with tempfile.TemporaryDirectory() as folder, \
             patch("build_warehouse.GOLD", Path(folder) / "gold"), \
             patch("build_warehouse.LOG", Path(folder) / "quality.csv"):
            build()
            first = pd.read_csv(Path(folder) / "gold/fact_water_usage.csv")
            build()
            second = pd.read_csv(Path(folder) / "gold/fact_water_usage.csv")
            pd.testing.assert_frame_equal(first, second)
            logs = pd.read_csv(Path(folder) / "quality.csv")
            self.assertEqual(logs.run_id.nunique(), 2)


if __name__ == "__main__":
    unittest.main()
