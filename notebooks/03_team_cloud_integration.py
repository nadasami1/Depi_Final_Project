# Databricks notebook source
"""Mahmoud T12/T17/T22, using the team's actual IDs and Delta inputs.
Outputs belong to Mahmoud; existing T20 and DQ001..DQ004 records are preserved.
Gold remains staged in Silver until the project Gold external location is granted.
"""
import hashlib
import json
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

dbutils.widgets.text("run_tag", "")
run_tag = dbutils.widgets.get("run_tag")
if not run_tag or any(c not in "0123456789abcdef" for c in run_tag):
    raise ValueError("run_tag must be a source/code snapshot SHA256 hex digest")
bronze = "abfss://bronze@aqua1storage.dfs.core.windows.net/"
silver = "abfss://silver@aqua1storage.dfs.core.windows.net/"
raw = bronze + "mahmoud/source_snapshot/" + run_tag + "/"
destination = silver + "mahmoud/runs/" + run_tag
quality_path = silver + "T15_Data_Quality/data_quality_log"
quality_schema = spark.read.format("delta").load(quality_path).schema
checks = []

def check(name, frame, bad_condition, source="Integration", severity="Error", details=""):
    count = frame.filter(bad_condition).count()
    checks.append(("T12_" + run_tag[:16] + "_" + name, source, name, "Validation",
                   None, None, None, count, severity,
                   "Passed" if count == 0 else "Gap Detected" if severity == "Warning" else "Failed",
                   details, "No action required." if count == 0 else "Review source; do not invent values."))
    if count and severity == "Error":
        write_checks()
        raise ValueError(name + ": " + str(count) + " invalid records")

def write_checks():
    # One record per snapshot/check, preserving earlier team results.
    if len({row[0] for row in checks}) != len(checks):
        raise ValueError("Duplicate quality check IDs")
    result = spark.createDataFrame(checks, schema=quality_schema)
    DeltaTable.forPath(spark, quality_path).alias("target").merge(
        result.alias("source"), "target.check_id = source.check_id"
    ).whenNotMatchedInsertAll().execute()

def write(name, frame):
    path = destination + "/" + name
    frame.write.format("delta").option("delta.columnMapping.mode", "name").mode("overwrite").save(path)
    saved = spark.read.format("delta").load(path)
    if frame.count() != saved.count():
        raise ValueError(name + " read-back count mismatch")
    return saved

def unique(name, frame, keys):
    check(name, frame.groupBy(*keys).count(), F.col("count") != 1)

# COMMAND ----------
# T12: import the team's recorded CAPMAS extraction checks, not fabricated GX runs.
source_quality = spark.read.option("header", True).csv(
    bronze + "capmas/ProcessedCampas/capmas_quality_log.csv")
for row in source_quality.collect():
    status = (row["status"] or "").lower()
    if status not in ("ok", "review", "failed"):
        raise ValueError("Unknown CAPMAS quality status: " + status)
    check_id = "T12_" + run_tag[:16] + "_CAPMAS_" + row["year"] + "_" + row["table"]
    checks.append((check_id, "CAPMAS", "table_" + row["table"], "Source_Table_Validation",
                   None, None, int(row["year"]), 0 if status == "ok" else 1,
                   "Info" if status == "ok" else "Warning" if status == "review" else "Error",
                   "Passed" if status == "ok" else "Review Required" if status == "review" else "Failed",
                   "Source status=" + status + "; count unit=one table; issues=" + (row["issues"] or ""),
                   "Review extraction report." if status != "ok" else "No action required."))
write_checks()
if any(row[9] == "Failed" for row in checks):
    raise ValueError("Failed source quality result blocks processing")

# COMMAND ----------
# T17: retain raw numeric values, units and FAOSTAT flags before converting.
crop = spark.read.option("header", True).csv(raw + "faostat_crop_production_egypt_2016_2020.csv")
irrigation = spark.read.option("header", True).csv(raw + "faostat_irrigation.csv")

def fao_units(frame, label):
    rules = spark.createDataFrame(
        [("t", "kg", 1000.0), ("ha", "ha", 1.0),
         ("kg/ha", "kg/ha", 1.0), ("1000 ha", "ha", 1000.0)],
        ["source_unit", "standardized_unit", "conversion_factor"])
    result = frame.join(F.broadcast(rules), frame.Unit == rules.source_unit, "left")
    check("FAOSTAT_supported_units_" + label, result, F.col("conversion_factor").isNull(), "FAOSTAT")
    result = result.withColumn("source_numeric_value", F.expr("try_cast(Value as double)"))
    check("FAOSTAT_numeric_values_" + label,
          result, F.col("Value").isNotNull() & (F.trim("Value") != "") & F.col("source_numeric_value").isNull(), "FAOSTAT")
    result = result.withColumn("standardized_value", F.col("source_numeric_value") * F.col("conversion_factor"))
    check("FAOSTAT_nonnegative_" + label, result, F.col("standardized_value") < 0, "FAOSTAT")
    return result.drop("source_unit")

crop = write("T17/faostat_crop_units", fao_units(crop, "crop"))
irrigation = write("T17/faostat_irrigation_units", fao_units(irrigation, "irrigation"))
capmas = spark.read.format("delta").load(silver + "T20_Silver/CAPMAS_Final")
climate = spark.read.format("delta").load(silver + "T20_Silver/Climate_Final")
master = spark.read.option("header", True).option("inferSchema", True).csv(silver + "reference/Governorates.csv")
rules = spark.createDataFrame([("thousand_m3", "m3", 1000.0), ("feddan", "ha", 0.42)],
                             ["source_unit", "standardized_unit", "conversion_factor"])
capmas = capmas.join(F.broadcast(rules), capmas.unit == rules.source_unit, "left").drop("source_unit")
check("CAPMAS_supported_units", capmas, F.col("conversion_factor").isNull(), "CAPMAS")
capmas = capmas.withColumn("standardized_value", F.col("value").cast("double") * F.col("conversion_factor"))
check("CAPMAS_nonnegative", capmas, F.col("standardized_value") < 0, "CAPMAS")
capmas = write("T17/capmas_units", capmas)
# Climate source is already mm and degrees C. Explicitly document these units.
climate = (climate.withColumn("rainfall_unit", F.lit("mm"))
           .withColumn("temperature_unit", F.lit("degC")))
unique("Climate_unique_grain", climate, ["governorate_id", "year"])
check("Climate_missing_values", climate, F.col("rainfall_mm").isNull() | F.col("temp_c").isNull(), "Climate")
climate = write("T17/climate_units", climate)

# COMMAND ----------
# T22: only governorate observations, no national/regional totals in the detail fact.
local = capmas.filter(F.col("row_type") == "governorate")
check("CAPMAS_missing_ID", local, F.col("governorate_id").isNull(), "CAPMAS")
unmatched = local.join(master.select("governorate_id"), "governorate_id", "left_anti")
check("CAPMAS_unknown_ID", unmatched, F.lit(True), "CAPMAS")
detail = local.filter(
    (F.col("table_no").isin(6, 8, 10) & (F.col("variable") != "total")) |
    ((F.col("table_no") == 12) & F.col("variable").isin("deciduous_water", "permanent_water")))
detail = detail.withColumn("crop_name", F.when(F.col("table_no") == 12,
    F.concat(F.regexp_replace("variable", "_water$", ""), F.lit("_fruit_group"))).otherwise(F.col("variable")))
crops = detail.select("crop_name").distinct().withColumn("crop_id", F.row_number().over(Window.orderBy("crop_name")))
detail = detail.join(crops, "crop_name")
climate_join = climate.select("governorate_id", "year",
    F.col("temp_c").alias("mean_temperature_c"), F.col("rainfall_mm").alias("annual_precipitation_mm"))
detail = detail.join(climate_join, ["governorate_id", "year"], "left")
check("Water_climate_join", detail,
      F.col("mean_temperature_c").isNull() | F.col("annual_precipitation_mm").isNull())
unique("Water_unique_grain", detail, ["governorate_id", "year", "season", "crop_id"])
detail = (detail.withColumn("governorate_id", F.col("governorate_id").cast("int"))
          .withColumn("water_used_m3", F.col("standardized_value"))
          .withColumn("water_unit", F.lit("m3"))
          .withColumn("review_required", F.col("qc") != "ok")
          .withColumn("source_table", F.col("table_no"))
          .withColumn("crop_yield_tons", F.lit(None).cast("double"))
          .withColumn("water_productivity", F.lit(None).cast("double"))
          .withColumn("production_status", F.lit("unavailable_at_governorate_crop_level"))
          .withColumn("fact_id", F.row_number().over(Window.orderBy("governorate_id", "year", "season", "crop_id"))))
fact = detail.select("fact_id", "governorate_id", "year", "season", "crop_id", "crop_name",
    "water_used_m3", "water_unit", "mean_temperature_c", "annual_precipitation_mm",
    "review_required", "source_table", "governorate_ar", "governorate_en",
    "crop_yield_tons", "water_productivity", "production_status")
fact = write("T22_Gold_Staging/fact_water_usage", fact)
write("T22_Gold_Staging/dim_governorate", master)
write("T22_Gold_Staging/dim_crop", crops)
# National crop data stays national; never broadcast production to each governorate.
national = (crop.groupBy("Area", "Item", "Year").pivot("Element", ["Area harvested", "Production", "Yield"])
            .agg(F.first("standardized_value"))
            .select(F.col("Area").alias("country"), F.col("Item").alias("crop"),
                    F.col("Year").cast("int").alias("year"), F.col("Area harvested").alias("area_ha"),
                    F.col("Production").alias("production_kg"), F.col("Yield").alias("yield_kg_ha")))
write("T22_Gold_Staging/fact_crop_national", national)
check("Governorate_production_unavailable", fact, F.col("crop_yield_tons").isNull(),
      severity="Warning", details="Country-level FAOSTAT cannot supply observed governorate production. Productivity remains null.")
write_checks()
dbutils.notebook.exit(json.dumps({
    "destination": destination, "water_rows": fact.count(),
    "national_crop_rows": national.count(), "climate_rows": climate.count(),
    "quality_checks": len(checks), "gold_status": "staged_in_silver_pending_gold_location_permission"}))
