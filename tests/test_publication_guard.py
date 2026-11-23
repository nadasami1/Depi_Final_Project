import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from publish_adls import inventory


class PublicationGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for folder in ["datasets/gold", "datasets/raw", "datasets/quality"]:
            (self.root / folder).mkdir(parents=True)
        self.source = self.root / "datasets/raw/source.csv"
        self.source.write_text("value\n1\n")
        manifest = {"run_id": "validated-run", "inputs": {
            "datasets/raw/source.csv": hashlib.sha256(self.source.read_bytes()).hexdigest()}}
        (self.root / "datasets/gold/build_manifest.json").write_text(json.dumps(manifest))
        self.write_log("validated-run", "pass")

    def tearDown(self):
        self.temp.cleanup()

    def write_log(self, run, status):
        with (self.root / "datasets/quality/data_quality_log.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=["run_id", "status"])
            writer.writeheader()
            writer.writerow({"run_id": run, "status": status})

    def test_current_validated_source_can_be_planned(self):
        with patch("publish_adls.ROOT", self.root):
            self.assertIn("bronze/source.csv", [record["path"] for record in inventory()])

    def test_changed_source_blocks_publish(self):
        self.source.write_text("value\n2\n")
        with patch("publish_adls.ROOT", self.root), self.assertRaisesRegex(ValueError, "Input changed"):
            inventory()

    def test_newer_unbuilt_run_blocks_publish(self):
        self.write_log("new-unbuilt-run", "pass")
        with patch("publish_adls.ROOT", self.root), self.assertRaisesRegex(ValueError, "does not match"):
            inventory()

    def test_failed_run_blocks_publish(self):
        self.write_log("validated-run", "fail")
        with patch("publish_adls.ROOT", self.root), self.assertRaisesRegex(ValueError, "failed checks"):
            inventory()
