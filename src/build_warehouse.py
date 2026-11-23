"""Build auditable local Gold tables without allocating national crop production."""

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from reshape_climate import main as prepare_climate
from standardize_faostat import main as prepare_faostat

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "datasets/gold"
LOG = ROOT / "datasets/quality/data_quality_log.csv"
UNITS = {"thousand_m3": ("m3", 1000.0), "m3": ("m3", 1.0),
         "feddan": ("ha", 0.42), "ha": ("ha", 1.0)}


class QualityLog:
    """Append one record per check/run; warnings do not become silent successes."""

    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.checked_at = datetime.now(timezone.utc).isoformat()
        self.rows = []

    def check(self, dataset, check, failed, total, detail="", severity="error"):
        self.rows.append(dict(run_id=self.run_id, checked_at=self.checked_at,
                              dataset=dataset, check_name=check,
                              severity=severity, status=("pass" if failed == 0 else
                              "warning" if severity == "warning" else "fail"),
                              failed_count=int(failed), total_count=int(total),
                              details=detail))

    def flush(self):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.rows).to_csv(LOG, mode="a", header=not LOG.exists(), index=False)

    def require_valid(self):
        if any(row["status"] == "fail" for row in self.rows):
            raise ValueError(f"Blocking data checks failed; inspect {LOG}")


def normalize_capmas(frame, quality):
    result = frame.copy()
    unknown = ~result.unit.isin(UNITS)
    quality.check("capmas", "supported_units", unknown.sum(), len(result))
    if unknown.any():
        raise ValueError(f"Unsupported CAPMAS units: {result.loc[unknown, 'unit'].unique()}")
    result["standardized_unit"] = result.unit.map(lambda unit: UNITS[unit][0])
    result["conversion_factor"] = result.unit.map(lambda unit: UNITS[unit][1])
    result["standardized_value"] = pd.to_numeric(result.value, errors="raise") * result.conversion_factor
    return result


def build():
    quality = QualityLog()
    try:
        prepare_climate()
        prepare_faostat()
        climate = pd.read_csv(ROOT / "datasets/processed/climate/climate_2016_2020.csv")
        capmas = pd.read_csv(ROOT / "datasets/raw/capmas_team/capmas_all_tables_long.csv")
        source_qc = pd.read_csv(ROOT / "datasets/raw/capmas_team/capmas_quality_log.csv")
        capmas["source_row_id"] = range(1, len(capmas) + 1)
        quality.check("capmas", "source_extraction_review", (capmas.qc != "ok").sum(),
                      len(capmas), "Retained as review_required; not certified observations", "warning")
        capmas = normalize_capmas(capmas, quality)
        quality.check("capmas", "negative_values", (capmas.standardized_value < 0).sum(), len(capmas))
        quality.check("capmas", "missing_values", capmas.standardized_value.isna().sum(), len(capmas))

        # Integration adapter for the existing team names; not a replacement for Nour's master.
        master = pd.read_csv(ROOT / "config/governorate_aliases.csv")
        lookup = {}
        for row in master.itertuples():
            for name in [row.governorate_name, row.canonical_name]:
                lookup[name.casefold().strip()] = row.governorate_id
        arabic_fallback = {"كفر الشيخ": "Kafr El Sheikh", "سوهاج": "Sohag"}
        def governorate_id(row):
            name = row.governorate_en
            if pd.isna(name):
                name = arabic_fallback.get(str(row.governorate_ar).strip(), "")
            return lookup.get(str(name).casefold().strip())
        capmas["governorate_id"] = capmas.apply(governorate_id, axis=1).astype("Int64")
        local = capmas[capmas.row_type == "governorate"].copy()
        quality.check("capmas", "unmapped_governorates", local.governorate_id.isna().sum(), len(local))
        keys = ["governorate_id", "year", "table_no", "variable"]
        quality.check("capmas", "duplicate_observation_keys", local.duplicated(keys, keep=False).sum(), len(local))
        quality.check("climate", "unique_governorate_year", climate.duplicated(["governorate_code", "year"], keep=False).sum(), len(climate))
        quality.check("climate", "missing_numeric_values", climate[["mean_temperature_c", "annual_precipitation_mm"]].isna().any(axis=1).sum(), len(climate))
        quality.require_valid()

        climate = climate.merge(master[["governorate_id", "governorate_code"]],
                                on="governorate_code", validate="many_to_one")
        climate_columns = ["governorate_id", "year", "mean_temperature_c", "annual_precipitation_mm"]
        # Crop/season details exclude the total columns and the separate all-season basis table.
        crops = local[(local.table_no.isin([6, 8, 10])) & (local.variable != "total")].copy()
        fruit = local[(local.table_no == 12) & local.variable.isin(["deciduous_water", "permanent_water"])].copy()
        fruit["variable"] = fruit.variable.str.replace("_water", "", regex=False) + "_fruit_group"
        detail = pd.concat([crops, fruit], ignore_index=True)
        assert detail.standardized_unit.eq("m3").all()
        crop_names = sorted(detail.variable.unique())
        crop_ids = {name: index + 1 for index, name in enumerate(crop_names)}
        detail["crop_id"] = detail.variable.map(crop_ids)
        detail["date_id"] = detail.year
        detail["source_id"] = 1
        detail["climate_source_id"] = 2
        detail["water_used_m3"] = detail.standardized_value
        detail["water_unit"] = "m3"
        detail["source_table"] = detail.table_no
        detail["review_required"] = detail.qc.ne("ok")
        detail["crop_yield_tons"] = float("nan")
        detail["water_productivity"] = float("nan")
        detail["production_status"] = "unavailable_at_governorate_crop_level"
        detail = detail.merge(climate[climate_columns], on=["governorate_id", "year"],
                              how="left", validate="many_to_one", indicator=True)
        quality.check("fact_water_usage", "climate_join_coverage", detail._merge.ne("both").sum(), len(detail))
        quality.check("fact_water_usage", "production_not_available", len(detail), len(detail),
                      "No governorate production invented; productivity left null", "warning")
        detail = detail.sort_values(["governorate_id", "year", "season", "crop_id"]).reset_index(drop=True)
        detail["fact_id"] = detail.index + 1
        fact_cols = ["fact_id", "governorate_id", "crop_id", "date_id", "source_id", "climate_source_id", "year", "season",
                     "water_used_m3", "water_unit", "crop_yield_tons", "water_productivity", "production_status",
                     "mean_temperature_c", "annual_precipitation_mm", "review_required", "source_table", "source_row_id"]

        # Canal and Aswan totals are different measurement bases: retain both, never add them.
        annual = local[(local.table_no == 21) & local.variable.isin(["total_canals", "total_aswan"])].copy()
        annual["measurement_basis"] = annual.variable.map({"total_canals": "canals", "total_aswan": "aswan"})
        annual["water_used_m3"] = annual.standardized_value
        annual["review_required"] = annual.qc.ne("ok")
        annual = annual.merge(climate[climate_columns], on=["governorate_id", "year"], how="left", validate="many_to_one")
        annual_cols = ["governorate_id", "year", "measurement_basis", "water_used_m3", "review_required",
                       "mean_temperature_c", "annual_precipitation_mm", "source_row_id"]

        national = pd.read_csv(ROOT / "datasets/processed/faostat/faostat_crop_production_egypt_2016_2020_standardized.csv")
        quality.check("faostat", "missing_source_values", national.standardized_value.isna().sum(), len(national),
                      "Missing source values retained, not replaced by zero", "warning")
        national_keys = ["Area", "Item", "Year", "Element"]
        quality.check("faostat", "duplicate_source_keys", national.duplicated(national_keys, keep=False).sum(), len(national))
        country = national.pivot(index=["Area", "Item", "Year"], columns="Element", values="standardized_value").reset_index()
        country = country.rename(columns={"Area": "country", "Item": "crop", "Year": "year",
                                          "Area harvested": "area_ha", "Production": "production_kg", "Yield": "yield_kg_ha"})
        flags = national.pivot(index=["Area", "Item", "Year"], columns="Element", values="Flag").reset_index()
        flags = flags.rename(columns={"Area": "country", "Item": "crop", "Year": "year",
                                      "Area harvested": "area_flag", "Production": "production_flag", "Yield": "yield_flag"})
        country = country.merge(flags, on=["country", "crop", "year"], validate="one_to_one")
        # Descriptive governorate mean, explicitly not a land-weighted national climate observation.
        climate_summary = climate.groupby("year", as_index=False).agg(
            governorate_mean_temperature_c=("mean_temperature_c", "mean"),
            governorate_mean_precipitation_mm=("annual_precipitation_mm", "mean"),
            climate_governorate_count=("governorate_id", "nunique"))
        country = country.merge(climate_summary, on="year", validate="many_to_one")
        country["geographic_level"] = "country"
        country["climate_aggregation"] = "unweighted_mean_of_27_governorates_not_crop_weighted"
        quality.require_valid()

        dim_gov = master.rename(columns={"canonical_name": "governorate_name_en", "governorate_name": "climate_source_name"})
        dim_crop = pd.DataFrame({"crop_id": list(crop_ids.values()), "crop_name": crop_names})
        aggregate = {"medical_aromatic", "others", "vegetables", "green_fodder", "deciduous_fruit_group", "permanent_fruit_group"}
        dim_crop["crop_type"] = dim_crop.crop_name.map(lambda name: "group" if name in aggregate else "crop")
        dim_date = pd.DataFrame({"date_id": range(2016, 2021), "year": range(2016, 2021),
                                 "month": [None]*5, "quarter": [None]*5, "grain": ["annual"]*5})
        dim_source = pd.DataFrame({"source_id": [1, 2, 3], "source_name": ["CAPMAS_team_extraction", "World_Bank_CCKP_CRU", "FAOSTAT"],
                                   "ingestion_date": [quality.checked_at[:10]]*3})
        # Coverage is an integration diagnostic, not proof that missing governorates had zero irrigation.
        grid = pd.MultiIndex.from_product([master.governorate_id, range(2016, 2021)], names=["governorate_id", "year"]).to_frame(index=False)
        observed = detail.groupby(["governorate_id", "year"]).agg(observation_count=("fact_id", "size"), review_required=("review_required", "max")).reset_index()
        coverage = grid.merge(observed, how="left", on=["governorate_id", "year"])
        coverage["observation_count"] = coverage.observation_count.fillna(0).astype(int)
        coverage["coverage_status"] = coverage.observation_count.map(lambda count: "no_capmas_observation" if count == 0 else "available")
        quality.check("coverage", "governorate_year_without_capmas", (coverage.observation_count == 0).sum(), len(coverage),
                      "No observation is not evidence of zero irrigation", "warning")
        tables = {"fact_water_usage": detail[fact_cols], "fact_water_annual": annual[annual_cols],
                  "fact_crop_national": country, "fact_climate_annual": climate,
                  "dim_governorate": dim_gov, "dim_crop": dim_crop, "dim_date": dim_date,
                  "dim_source": dim_source, "coverage_governorate_year": coverage,
                  "capmas_source_quality": source_qc}
        GOLD.mkdir(parents=True, exist_ok=True)
        for name, table in tables.items():
            table.to_csv(GOLD / f"{name}.csv", index=False)
        db = GOLD / "aquaagri.sqlite"
        temporary = GOLD / "aquaagri.tmp.sqlite"
        if temporary.exists():
            temporary.unlink()
        with sqlite3.connect(temporary) as connection:
            for name, table in tables.items():
                table.to_sql(name, connection, index=False, if_exists="replace")
            connection.execute("CREATE UNIQUE INDEX water_grain ON fact_water_usage(governorate_id, year, season, crop_id)")
            connection.execute("CREATE UNIQUE INDEX climate_grain ON fact_climate_annual(governorate_id, year)")
            connection.execute("CREATE UNIQUE INDEX annual_water_grain ON fact_water_annual(governorate_id, year, measurement_basis)")
        temporary.replace(db)
        provenance = {"run_id": quality.run_id, "created_at": quality.checked_at, "tables": {name: len(table) for name, table in tables.items()},
                      "inputs": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in sorted((ROOT / "datasets/raw").rglob("*")) if path.is_file() and path.suffix in [".csv", ".xlsx"]}}
        (GOLD / "build_manifest.json").write_text(json.dumps(provenance, indent=2) + "\n")
        print(json.dumps(provenance["tables"], indent=2))
    finally:
        quality.flush()


if __name__ == "__main__":
    build()
