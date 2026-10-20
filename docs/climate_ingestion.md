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

The source sheet does not state measurement units or explain the `-07` period
suffix. Verify these in the provider's metadata before interpreting or converting
values. The filenames say annual; do not assume the columns describe July-only
observations. Preserve the period labels during ingestion.

## Later preparation

Keep all periods in raw storage. A later transformation can select 2016-2020
and reshape the wide sheets into one observation per governorate, period,
and variable. Governorate name reconciliation remains a separate team task.
