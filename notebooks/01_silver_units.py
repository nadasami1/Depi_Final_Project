# Databricks notebook source
# T17: Spark unit conversion for raw CAPMAS and FAOSTAT CSV inputs in ADLS.
# Requires the team's existing ADLS external location / identity permissions.
dbutils.widgets.text("raw_base", "")
dbutils.widgets.text("silver_base", "")
raw_base = dbutils.widgets.get("raw_base").rstrip("/")
silver_base = dbutils.widgets.get("silver_base").rstrip("/")
if not raw_base.startswith("abfss://") or not silver_base.startswith("abfss://"):
    raise ValueError("Set raw_base and silver_base to permitted abfss:// paths")

# COMMAND ----------
from pyspark.sql import functions as F

def convert_units(frame, source_unit, source_value, rules):
    mapping = spark.createDataFrame([(key, unit, factor) for key, (unit, factor) in rules.items()],
                                    ["_source_unit", "standardized_unit", "conversion_factor"])
    result = frame.join(F.broadcast(mapping), frame[source_unit] == mapping._source_unit, "left")
    if result.filter(F.col("standardized_unit").isNull()).limit(1).count():
        raise ValueError("Unsupported unit in source; conversion stopped")
    numeric = F.expr(f"try_cast(`{source_value}` as double)")
    malformed = F.col(source_value).isNotNull() & (F.trim(F.col(source_value)) != "") & numeric.isNull()
    if result.filter(malformed).limit(1).count():
        raise ValueError("Non-numeric populated source value")
    return result.withColumn("standardized_value", numeric * F.col("conversion_factor")).drop("_source_unit")

# COMMAND ----------
capmas = spark.read.option("header", True).csv(raw_base + "/capmas_team/capmas_all_tables_long.csv")
capmas = convert_units(capmas, "unit", "value", {
    "thousand_m3": ("m3", 1000.0), "m3": ("m3", 1.0), "feddan": ("ha", 0.42), "ha": ("ha", 1.0)})
capmas.write.format("delta").mode("overwrite").save(silver_base + "/capmas_units")
for filename in ["faostat_crop_production_egypt_2016_2020.csv", "faostat_irrigation.csv"]:
    frame = spark.read.option("header", True).csv(raw_base + "/faostat/" + filename)
    converted = convert_units(frame, "Unit", "Value", {
        "t": ("kg", 1000.0), "ha": ("ha", 1.0), "kg/ha": ("kg/ha", 1.0), "1000 ha": ("ha", 1000.0)})
    converted.write.format("delta").option("delta.columnMapping.mode", "name").mode("overwrite").save(silver_base + "/" + filename[:-4])

# COMMAND ----------
# Climate already uses °C and mm: ingest original Excel separately with the local
# downloader/reshape scripts. Publish their processed CSVs to Silver using
# publish_adls.py; do not relabel copied processed data as untouched Bronze.
