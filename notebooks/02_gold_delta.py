# Databricks notebook source
# Publish validated local Gold tables as typed Delta tables.
dbutils.widgets.text("published_gold", "")
dbutils.widgets.text("delta_gold", "")
published = dbutils.widgets.get("published_gold").rstrip("/")
destination = dbutils.widgets.get("delta_gold").rstrip("/")
if not published.startswith("abfss://") or not destination.startswith("abfss://"):
    raise ValueError("Both widgets require existing permitted abfss:// paths")

# COMMAND ----------
from pyspark.sql import functions as F

tables = ["fact_water_usage", "fact_water_annual", "fact_crop_national",
          "fact_climate_annual", "dim_governorate", "dim_crop", "dim_date", "dim_source"]
for table in tables:
    data = spark.read.option("header", True).option("inferSchema", True).csv(published + "/" + table + ".csv")
    for column in ["water_used_m3", "crop_yield_tons", "water_productivity",
                   "mean_temperature_c", "annual_precipitation_mm"]:
        if column in data.columns:
            data = data.withColumn(column, F.col(column).cast("double"))
    if table == "fact_water_usage":
        if data.groupBy("governorate_id", "year", "season", "crop_id").count().filter("count > 1").limit(1).count():
            raise ValueError("Duplicate Gold fact grain; write blocked")
    data.write.format("delta").mode("overwrite").option("overwriteSchema", True).save(destination + "/" + table)
