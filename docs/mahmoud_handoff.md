# Mahmoud's local data preparation handoff

## Ready for review

- **T02:** repository folders and naming conventions, delivered in PR #1.
- **T08 local preparation:** original climate files, repeatable download script,
  and provenance manifest. ADLS upload and Azure integration are pending.
- **Climate preparation:** 2016-2020 temperature and rainfall reshaped and joined
  into 135 unique governorate-year rows. Original codes and period labels retained.
- **T17 local preparation for available inputs:** FAOSTAT production converted
  from tonnes to kilograms and irrigation land area from thousand hectares to
  hectares. Temperature remains degrees Celsius, rainfall millimeters, area
  hectares, and yield kilograms per hectare. Cloud/Databricks integration is pending.

## How to run

Python 3.9 or newer:

```sh
python3 -m pip install -r requirements.txt
python3 src/ingest_climate.py
python3 src/reshape_climate.py
python3 src/standardize_faostat.py
```

Only climate ingestion requires network access. The FAOSTAT source files are
included unchanged; the unit script reads these local files.

## Outputs

| File under datasets/processed/ | Contents |
| --- | --- |
| climate/climate_2016_2020.csv | 135 governorate-year rows with temperature and precipitation |
| climate/temperature_2016_2020.csv | 135 long-format temperature rows |
| climate/precipitation_2016_2020.csv | 135 long-format precipitation rows |
| faostat/faostat_crop_production_egypt_2016_2020_standardized.csv | 1137 country-level source rows plus standardized-unit columns |
| faostat/faostat_irrigation_standardized.csv | 7 country-level land-area rows plus standardized-unit columns |
| faostat/unit_validation_report.json | Counts, missing values, source flags, years, and units |

## Verified

- Climate governorate/year keys are unique; all 270 climate values match source
  workbooks and raw workbook checksums remain unchanged.
- CCKP annual and monthly API products confirm Cairo's 2016 temperature is
  22.48 annually versus 29.10 in July. See `climate_ingestion.md` for evidence.
- All original FAOSTAT columns, rows, identifiers, flags, and values are retained.
- All supported unit conversions reconcile with the original numeric values.
- The 12 missing crop values remain missing; no values were filled or estimated.

## Dependencies and remaining assigned work

- CAPMAS tables and the team's agreed governorate master mapping are required
  before building the final governorate-level joins in **T22**.
- No production allocation or national-to-governorate join is performed here.
- **T12:** this unit report is a local check, not the team's integrated
  `data_quality_log`; coordinate that interface with Nada and Nour.
- **T29:** climate-versus-yield charts require crop/yield data at the agreed
  geographic level and an agreed treatment of estimates.
- **T34:** these are preparation/run notes. Final architecture and full project
  README depend on the integrated pipeline.
- This delivery does not claim that all of Mahmoud's tasks or the Azure pipeline
  are complete. Review and merge PR #1 before merging the preparation PR.
