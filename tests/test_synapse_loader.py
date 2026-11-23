import re
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from load_synapse import upload, rows_for_sql


class FakeConnection:
    """Transaction behavior test double; not a claim of Synapse execution."""
    def __init__(self, counts=None, fail_on=None):
        self.counts = dict(counts or {})
        self.initial = self.counts.copy()
        self.fail_on = fail_on
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self

    def execute(self, sql):
        self.table = re.findall(r"\[dbo\]\.\[([^]]+)\]", sql)[0]
        if sql.startswith("DELETE"):
            self.counts[self.table] = 0
        return self

    def fetchone(self):
        return (self.counts.get(self.table, 0),)

    def fetchall(self):
        return []

    def executemany(self, sql, rows):
        name = re.findall(r"\[dbo\]\.\[([^]]+)\]", sql)[0]
        if name == self.fail_on:
            raise RuntimeError("simulated insert failure")
        self.counts[name] = self.counts.get(name, 0) + len(rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.counts = self.initial.copy()
        self.rolled_back = True

    def close(self):
        pass


class SynapseLoaderTests(unittest.TestCase):
    def test_nulls_remain_null_and_booleans_become_bits(self):
        result = rows_for_sql(pd.DataFrame({"review_required": [True, False], "value": [1.0, float("nan")]}))
        self.assertEqual(result, [(1, 1.0), (0, None)])

    def test_existing_fact_is_not_overwritten_by_default(self):
        connection = FakeConnection({"fact_water_usage": 10})
        with self.assertRaisesRegex(ValueError, "not empty"):
            upload(connection, {"fact_water_usage": pd.DataFrame({"fact_id": [1]})})
        self.assertFalse(connection.committed)
        self.assertEqual(connection.counts["fact_water_usage"], 10)

    def test_failed_second_table_rolls_back_first_table(self):
        connection = FakeConnection(fail_on="fact_water_annual")
        with self.assertRaises(RuntimeError):
            upload(connection, {"fact_water_usage": pd.DataFrame({"fact_id": [1]}),
                                "fact_water_annual": pd.DataFrame({"year": [2016]})})
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)
        self.assertEqual(connection.counts, {})

    def test_success_commits_validated_counts(self):
        connection = FakeConnection()
        result = upload(connection, {"fact_water_usage": pd.DataFrame({"fact_id": [1, 2]})})
        self.assertTrue(connection.committed)
        self.assertEqual(result["fact_water_usage"]["target_rows"], 2)
