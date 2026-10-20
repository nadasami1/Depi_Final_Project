# Reshape climate data

From the repository root, install the dependencies if needed and run:

```sh
python3 -m pip install -r requirements.txt
python3 src/reshape_climate.py
```

The script reads the two original workbooks and selects the five source columns
`2016-07` through `2020-07`. It creates separate temperature and precipitation
CSV files in `datasets/processed/climate/`. Each row contains a governorate code,
governorate name, original period label, and numeric value. The current files
produce 135 rows each: 27 governorates times 5 periods.

The script also creates `climate_2016_2020.csv`, joining both variables for
the same governorate and original period with a one-to-one match. The combined
table has 135 rows and these columns:

| Column | Meaning |
| --- | --- |
| governorate_code | Source governorate identifier, preserved unchanged |
| governorate_name | Source English name, preserved unchanged |
| year | Year of the verified annual observation |
| source_period | Original label, such as 2016-07 |
| mean_temperature_c | Annual mean temperature in degrees Celsius |
| annual_precipitation_mm | Annual accumulated precipitation in millimeters |

For Cairo in 2016, the combined row contains temperature 22.48 and precipitation
14.70. The join does not average, sum, or convert the source values. Names are
not mapped to the team's governorate master table here. Climate data alone does
not measure irrigation water use or agricultural water efficiency.

For example, Cairo's `2016-07` temperature value is preserved as `22.48`.
Raw workbooks are not modified. The script checks required columns, missing
identifiers and values, duplicate governorate codes, and matching identifiers
between temperature and precipitation.

This is local table reshaping, not a completed Silver layer or Azure task.
CCKP indicator metadata defines temperature (`tas`) in degrees Celsius and
precipitation (`pr`) in millimeters; see the sources and annual-product
interpretation in `climate_ingestion.md`. Output column names remain unchanged.
Direct comparison of CCKP's annual and monthly API products for Cairo confirms
that the `-07` annual labels represent annual data: 2016 temperature is 22.48
annually versus 29.10 for July alone. The mean of January-December values rounds
to 22.48. Original period labels are retained for provenance. No unit conversion,
name reconciliation, or interpolation is applied.
