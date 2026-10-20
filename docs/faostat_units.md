# FAOSTAT unit preparation

Run from the repository root after installing `requirements.txt`:

```sh
python3 src/standardize_faostat.py
```

Original files are in `datasets/raw/faostat/`, downloaded from the team's
shared Drive folder. Standardized CSVs and a unit validation report are saved
in `datasets/processed/faostat/`.

## Conversions

| Source unit | Standard unit | Multiplier |
| --- | --- | ---: |
| t | kg | 1000 |
| ha | ha | 1 |
| kg/ha | kg/ha | 1 |
| 1000 ha | ha | 1000 |

The source columns, including `Value`, `Unit`, item identifiers, and flags, remain
unchanged. Added columns contain the converted value, unit, multiplier, value
availability, and geographic level. A missing source value remains missing;
it is never converted to zero. Source estimation and imputation flags remain
attached to their rows. Availability does not mean a value was directly observed.
Unsupported units and nonnumeric populated values cause the script to stop.

These files contain country-level data for Egypt. No national production is
allocated to governorates. The irrigation file measures land area, not water
volume; it cannot serve as a water-volume denominator.

Source folder:
https://drive.google.com/drive/folders/1I7AOjbuWTuiTUpmJ5xUFkuXhuqOmATzh

Original shared file IDs:
- Crop production: `1XBm9v-LRhpbJGzvTo2snmmDctPVhVEAd`
- Irrigation land area: `1ooKGjVa5DZrg3ze48CREssu_lxaUlLrd`

Keep numerator, denominator, crop, geographic level, time period, and units
consistent when constructing later indicators. Any agreed production estimates
must be stored separately and explicitly labeled as estimates.
