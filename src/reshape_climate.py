"""Reshape the 2016-2020 climate data without changing the raw workbooks."""

from pathlib import Path

import pandas as pd

from ingest_climate import FILENAME


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datasets/raw/world_bank"
OUTPUT_DIR = ROOT / "datasets/processed/climate"
PERIODS = [f"{year}-07" for year in range(2016, 2021)]
VARIABLES = {"tas": "temperature", "pr": "precipitation"}


def reshape(metric, label):
    source = RAW_DIR / FILENAME.format(metric=metric)
    table = pd.read_excel(source, sheet_name="all", engine="openpyxl")

    required = ["code", "name"] + PERIODS
    missing = [column for column in required if column not in table.columns]
    if missing:
        raise ValueError(f"{source.name}: missing columns {missing}")
    if table[["code", "name"]].isna().any().any():
        raise ValueError(f"{source.name}: missing governorate code or name")
    if table["code"].duplicated().any():
        raise ValueError(f"{source.name}: duplicate governorate codes")

    # Keep the identifiers and turn the five period columns into rows.
    result = table[required].melt(
        id_vars=["code", "name"],
        value_vars=PERIODS,
        var_name="period",
        value_name=f"{label}_value",
    )
    result = result.rename(columns={
        "code": "governorate_code",
        "name": "governorate_name",
    })
    values = pd.to_numeric(result[f"{label}_value"], errors="raise")
    if values.isna().any():
        raise ValueError(f"{source.name}: missing climate values in 2016-2020")
    result[f"{label}_value"] = values
    return result.sort_values(["governorate_code", "period"]).reset_index(drop=True)


def main():
    # Validate both inputs before writing either output.
    tables = {label: reshape(metric, label) for metric, label in VARIABLES.items()}
    identifiers = ["governorate_code", "governorate_name", "period"]
    if not tables["temperature"][identifiers].equals(
        tables["precipitation"][identifiers]
    ):
        raise ValueError("Temperature and precipitation identifiers do not match")

    # Match each temperature with rainfall for the same governorate and period.
    combined = tables["temperature"].merge(
        tables["precipitation"],
        on=identifiers,
        how="inner",
        validate="one_to_one",
    ).rename(columns={
        "period": "source_period",
        "temperature_value": "mean_temperature_c",
        "precipitation_value": "annual_precipitation_mm",
    })
    # Verified annual product: retain the source label as well as the year.
    combined["year"] = combined["source_period"].str[:4].astype(int)
    combined = combined[[
        "governorate_code", "governorate_name", "year", "source_period",
        "mean_temperature_c", "annual_precipitation_mm",
    ]]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for label, table in tables.items():
        destination = OUTPUT_DIR / f"{label}_2016_2020.csv"
        table.to_csv(destination, index=False, encoding="utf-8")
        print(f"Saved {len(table)} rows: {destination}")

    destination = OUTPUT_DIR / "climate_2016_2020.csv"
    combined.to_csv(destination, index=False, encoding="utf-8")
    print(f"Saved {len(combined)} combined climate rows: {destination}")


if __name__ == "__main__":
    main()
