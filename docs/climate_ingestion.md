# Climate ingestion

## Run locally

Python 3.9 or newer is required. No third-party packages are needed.
From the repository root, run:

```sh
python3 src/ingest_climate.py
```

The script downloads the two original XLSX files from the team's shared Drive
folder into `datasets/raw/world_bank/`. This is the local preparation for T08;
uploading to ADLS and connecting Azure orchestration remain to be implemented.

It preserves the original filenames and file bytes. Source URLs, download times
in UTC, file sizes, and SHA-256 checksums are recorded in
`ingestion_manifest.json`. A checksum is a fingerprint used to check that a file
has not changed. If a source changes, the script refuses to replace an existing
raw file. Use `--output-dir` to store the new version separately.

## Source inspection

Team climate folder:
https://drive.google.com/drive/folders/1pt1tpkct6lhHgunW6LyRvP3gdscaMEAC

Both workbooks contain a sheet named `all`, 27 governorate rows, and 127 columns:
`code`, `name`, and 125 period columns from `1901-07` through `2025-07`.
The filenames identify `pr` (precipitation) and `tas` (temperature).

For the project's proposed 2016-2020 period, each workbook has 135 numeric
observations (27 governorates times 5 periods). No missing values or duplicate
governorate codes were found in that inspection. Governorate codes and names
match between the two files. This checks completeness within these files,
not accuracy against the original climate provider or compatibility with CAPMAS.

The source sheet does not state measurement units. CCKP's indicator metadata,
reviewed on 2026-10-20, defines `tas` as average surface air temperature in degrees
Celsius and `pr` as accumulated precipitation in millimeters. Its CRU workflow
describes annual temperature averages and annual precipitation sums.

Sources:
- https://climateknowledgeportal.worldbank.org/index.php/metadata
- https://climateknowledgeportal.worldbank.org/metadata

### Annual versus monthly verification (2026-10-20)

Directly queried CCKP's annual and monthly CRU TS4.10 API products for Cairo
(`EGY.4076561515`). The annual temperature product returns `2016-07: 22.48`,
matching the team's workbook. The monthly product returns July 2016 as `29.10`.
The arithmetic mean of the 12 monthly temperature values for January-December
2016 is `22.475833...`, which rounds to the workbook's annual value `22.48`.

For precipitation, the annual product returns `2016-07: 14.70`; July alone is
`0.18`. The rounded monthly values sum to `14.69`; the `0.01` difference from
the annual value is consistent with rounding at the monthly/annual output stages.

Thus `-07` is the annual product's timestamp label, not evidence that these
annual values describe July alone. The internal choice of July for the label
is not established by this check. Retain the original labels for provenance.
No unit conversion is needed to retain degrees Celsius and millimeters.

API evidence (replace `tas` with `pr` for precipitation):
- https://cckpapi.worldbank.org/cckp/v1/cru-x0.5_timeseries_tas_timeseries_annual_1901-2025_mean_historical_cru_ts4.10_mean/EGY.4076561515
- https://cckpapi.worldbank.org/cckp/v1/cru-x0.5_timeseries_tas_timeseries_monthly_1901-2025_mean_historical_cru_ts4.10_mean/EGY.4076561515

## Later preparation

Keep all periods in raw storage. A later transformation can select 2016-2020
and reshape the wide sheets into one observation per governorate, period,
and variable. Governorate name reconciliation remains a separate team task.
