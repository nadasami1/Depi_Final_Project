"""Standardize units while retaining FAOSTAT's original columns and flags."""

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datasets/raw/faostat"
OUTPUT_DIR = ROOT / "datasets/processed/faostat"
FILES = ["faostat_crop_production_egypt_2016_2020.csv", "faostat_irrigation.csv"]
# Original unit: (standard unit, multiplier).
UNIT_RULES = {"t": ("kg", 1000), "ha": ("ha", 1),
              "kg/ha": ("kg/ha", 1), "1000 ha": ("ha", 1000)}


def standardize(filename):
    # Preserve identifiers, original values, notes, and estimation flags as text.
    table = pd.read_csv(RAW_DIR / filename, dtype=str, keep_default_na=False,
                        encoding="utf-8-sig")
    required = ["Area", "Item", "Element", "Year", "Unit", "Value", "Flag"]
    missing_columns = [column for column in required if column not in table]
    if missing_columns:
        raise ValueError(f"{filename}: missing columns {missing_columns}")
    unknown_units = sorted(set(table["Unit"]) - set(UNIT_RULES))
    if unknown_units:
        raise ValueError(f"{filename}: unsupported units {unknown_units}")

    values = pd.to_numeric(table["Value"].replace("", float("nan")), errors="raise")
    table["standardized_unit"] = table["Unit"].map(lambda unit: UNIT_RULES[unit][0])
    table["conversion_factor"] = table["Unit"].map(lambda unit: UNIT_RULES[unit][1])
    table["standardized_value"] = values * table["conversion_factor"]
    table["value_status"] = values.map(lambda value: "missing" if pd.isna(value) else "available")
    table["geographic_level"] = "country"
    report = {
        "source_file": filename,
        "rows": len(table),
        "missing_values_preserved": int(values.isna().sum()),
        "areas": sorted(table["Area"].unique().tolist()),
        "years": sorted(table["Year"].unique().tolist()),
        "original_units": sorted(table["Unit"].unique().tolist()),
        "standardized_units": sorted(table["standardized_unit"].unique().tolist()),
        "source_flags_preserved": table["Flag"].value_counts().to_dict(),
    }
    return table, report


def main():
    results = {filename: standardize(filename) for filename in FILES}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for filename, (table, report) in results.items():
        destination = OUTPUT_DIR / filename.replace(".csv", "_standardized.csv")
        table.to_csv(destination, index=False, encoding="utf-8")
        reports.append(report)
        print(f"Saved {len(table)} rows, {report['missing_values_preserved']} missing values: {destination}")
    (OUTPUT_DIR / "unit_validation_report.json").write_text(
        json.dumps(reports, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
