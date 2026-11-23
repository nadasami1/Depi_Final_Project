# Gold grain and quality interface

`fact_water_usage` has one row per governorate, year, season and crop/group.
Dimension keys describe governorate, crop, annual date and CAPMAS source.
`climate_source_id` separately identifies CCKP. `source_row_id` points to the
one-based row in the team's input CSV, excluding its header. Water is in m³;
climate is annual °C and mm. Source table and review status survive the join.
Arabic governorate names are carried from the team's CAPMAS records where
available; missing Arabic labels are not invented. Source ingestion dates use
recorded download metadata; FAOSTAT's unavailable retrieval date stays null.

`crop_yield_tons` is inherited from the team's ERD. If later populated it must
mean production in tonnes, not yield per area. Currently it and water_productivity
are null. A future migration should explicitly distinguish production_tonnes from
yield_kg_ha. A null does not mean zero production or zero efficiency.

Source total rows/columns, fruit area columns and all-season alternative bases
are excluded from detail. Deciduous/permanent fruit categories are marked as
groups. Separate annual water facts retain canals and Aswan bases: filter one,
never sum them together or add annual facts to detail facts.

`fact_crop_national` stays at Egypt/crop/year grain, preserving estimation flags
and missing values. It is not joined to local facts on year alone.
`fact_climate_annual` contains all 27 governorates for five years.
`coverage_governorate_year` marks absent supplied CAPMAS observations; absence
is not a confirmed reporting failure or zero irrigation.

## data_quality_log interface (T12)

| Column | Meaning |
| --- | --- |
| run_id | Unique identifier for the validation/build run |
| checked_at | UTC timestamp |
| dataset | Check scope |
| check_name | Stable check identifier |
| severity | error or warning |
| status | pass, warning or fail |
| failed_count | Violations of this check |
| total_count | Records examined by this check |
| details | Interpretation/action, including extraction review status |

Runs append, including failed runs. Unsupported units, duplicate keys, unmapped
governorates and missing climate values block the Gold build. Source review,
unavailable local production and missing national values are explicit warnings.
Map Nada's suite results to this schema or use `QualityLog.check` directly.
Do not sum failed_count across checks as a count of distinct bad records.

## References and limits

Conversion uses 1 feddan = 0.42 ha, as documented by FAO for Egypt:
https://www.fao.org/4/V9978E/v9978e0e.htm

The team CSV declares thousand_m3. This adapter converts those units, retaining
the extraction's zeros and QC flags; it does not reinterpret PDF symbols or certify
the extraction's original handling of '-' and '='.

PBIP follows Microsoft report/model contracts and uses the public authoring CLI:
- https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
- https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset

Its model embeds a data snapshot. Rebuild to update it. The report selects Wheat,
Rice and Maize, while the warehouse retains all crops. Climate is an unweighted
governorate mean, not a crop-area-weighted country observation. Five annual
points support descriptive comparison only, not causal attribution.
