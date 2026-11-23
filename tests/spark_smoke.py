"""Execute both notebook transforms using local Spark and Parquet as a test sink.

Only ADLS path validation and the Delta storage format are replaced in this test.
This verifies Spark expressions and row results, not ADLS access or Delta commits.
Run separately: python tests/spark_smoke.py (requires pyspark 3.5.x and Java).
"""
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
from pyspark.sql import SparkSession

ROOT = Path(__file__).resolve().parents[1]
spark = SparkSession.builder.master("local[2]").appName("AquaAgriNotebookSmoke").config("spark.sql.shuffle.partitions", "2").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")


def run_notebook(filename, widgets):
    widget_api = SimpleNamespace(text=lambda *args: None, get=lambda name: widgets[name])
    source = (ROOT / "notebooks" / filename).read_text()
    source = source.replace('startswith("abfss://")', 'startswith("file://")')
    source = source.replace('.format("delta")', '.format("parquet")')
    exec(compile(source, filename, "exec"), {"spark": spark, "dbutils": SimpleNamespace(widgets=widget_api)})


try:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        run_notebook("01_silver_units.py", {"raw_base": (ROOT / "datasets/raw").as_uri(),
                                            "silver_base": (target / "silver").as_uri()})
        crop = spark.read.parquet(str(target / "silver/faostat_crop_production_egypt_2016_2020"))
        assert crop.count() == 1137
        assert crop.filter("standardized_value IS NULL").count() == 12
        assert crop.filter("Unit = 't' AND abs(standardized_value - cast(Value as double) * 1000) > 0.000001").count() == 0
        capmas = spark.read.parquet(str(target / "silver/capmas_units"))
        assert capmas.count() == 7377
        assert capmas.filter("unit = 'thousand_m3' AND abs(standardized_value - cast(value as double) * 1000) > 0.000001").count() == 0
        run_notebook("02_gold_delta.py", {"published_gold": (ROOT / "datasets/gold").as_uri(),
                                          "delta_gold": (target / "gold").as_uri()})
        fact = spark.read.parquet(str(target / "gold/fact_water_usage"))
        assert fact.count() == 4404
        assert fact.filter("crop_yield_tons IS NOT NULL OR water_productivity IS NOT NULL").count() == 0
        assert fact.filter("mean_temperature_c IS NULL").count() == 0
        print("Both Spark notebooks passed: source conversions, null preservation, Gold row counts and climate joins. Delta/ADLS not exercised.")
finally:
    spark.stop()
