# Databricks notebook source
import json
from pyspark.sql import functions as F
root = "abfss://silver@aqua1storage.dfs.core.windows.net/"
tag = "fe89b191c3deed062de70f94d796cf7e7ec5fbd14c33ed2ce6fbbf67239bff41"
def read(path):
    return spark.read.format("delta").load(root + path)
q = read("T15_Data_Quality/data_quality_log")
assert q.filter(F.col("check_id").isin("DQ001", "DQ002", "DQ003", "DQ004")).count() == 4
assert q.filter(F.col("check_id").startswith("T12_" + tag[:16] + "_")).count() == 40
assert q.groupBy("check_id").count().filter("count > 1").count() == 0
base = "mahmoud/runs/" + tag + "/"
counts = {}
for name, expected in [("T17/faostat_crop_units", 1137), ("T17/faostat_irrigation_units", 7),
                       ("T17/capmas_units", 7377), ("T17/climate_units", 135),
                       ("T22_Gold_Staging/fact_water_usage", 4404),
                       ("T22_Gold_Staging/fact_crop_national", 381)]:
    frame = read(base + name)
    counts[name] = frame.count()
    assert counts[name] == expected, (name, counts[name])
fao = read(base + "T17/faostat_crop_units")
assert fao.filter((F.col("Unit") == "t") &
                 (F.abs(F.col("standardized_value") - F.col("Value").cast("double") * 1000) > 0.0001)).count() == 0
assert fao.filter(F.col("Value").isNull() & F.col("standardized_value").isNotNull()).count() == 0
fact = read(base + "T22_Gold_Staging/fact_water_usage")
assert fact.filter(F.col("crop_yield_tons").isNotNull() | F.col("water_productivity").isNotNull()).count() == 0
assert fact.filter(F.col("mean_temperature_c").isNull() | F.col("annual_precipitation_mm").isNull()).count() == 0
dbutils.notebook.exit(json.dumps({"checks": "passed", "original_team_log_records": 4,
    "current_run_quality_records": 40, "duplicate_quality_ids": 0, "counts": counts}))
