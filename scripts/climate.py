import pandas as pd
import os

pr_file = r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\raw\Climate\cru-x0.5_timeseries_pr_timeseries_annual_1901-2025_mean_historical_cru_ts4.10_mean.xlsx"
tas_file = r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\raw\Climate\cru-x0.5_timeseries_tas_timeseries_annual_1901-2025_mean_historical_cru_ts4.10_mean.xlsx"


df_pr = pd.read_excel(pr_file, sheet_name="all")
df_tas = pd.read_excel(tas_file, sheet_name="all")

# reshape to long format
df_pr_long = df_pr.melt(id_vars=["code", "name"], var_name="year_raw", value_name="rainfall_mm")
df_tas_long = df_tas.melt(id_vars=["code", "name"], var_name="year_raw", value_name="temp_c")

# extract year from '2016-07' format
df_pr_long["year"] = df_pr_long["year_raw"].str[:4].astype(int)
df_tas_long["year"] = df_tas_long["year_raw"].str[:4].astype(int)

# merge both files
df_climate = pd.merge(
    df_pr_long[["name", "year", "rainfall_mm"]],
    df_tas_long[["name", "year", "temp_c"]],
    on=["name", "year"],
    how="inner"
)

df_climate = df_climate.rename(columns={"name": "governorate"})

# keep only needed years
years = [2016, 2017, 2018, 2019, 2020]
df_climate = df_climate[df_climate["year"].isin(years)]


out_path = r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\processed\Climate\climate_annual.csv"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
df_climate.to_csv(out_path, index=False, encoding="utf-8-sig")


print(df_climate.shape)
print(df_climate.head())
print(df_climate.shape)
print(df_climate['governorate'].nunique())
print(df_climate.isna().sum())
