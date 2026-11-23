# Azure execution — 2026-11-23

## Verified connection

Azure CLI signs in with the user's Microsoft identity. Authentication state is
local under ignored `work/azure-config`; credentials are not committed.
Databricks uses the Entra token, Azure workspace resource ID and ARM management
token headers. No new credentials, IAM roles or grants were created.

Project: `Aqua_Agri_Project`; ADLS account: `aqua1storage`.
Active workspace: https://adb-7405614270962201.1.azuredatabricks.net

The existing classic `aqua-cluster` is terminated with Azure quota exhaustion.
A bounded serverless notebook run succeeded without restarting that cluster:

https://adb-7405614270962201.1.azuredatabricks.net/?o=7405614270962201#job/244057972453241/run/1035669401534850

The read test returned 135 climate, 7,377 CAPMAS and four existing quality records.
The Swiss workspace denied the authenticated user access.

## Actual team inputs

- `silver/T20_Silver/CAPMAS_Final` and `Climate_Final`: Delta.
- `silver/reference/Governorates.csv`: the team's 27 governorate IDs.
- `silver/T15_Data_Quality/data_quality_log`: existing 12-column team schema.
- `bronze/capmas/ProcessedCampas/capmas_quality_log.csv`: 25 extraction results.
- Original local FAOSTAT CSVs, including units and flags, uploaded unchanged to
  `bronze/mahmoud/source_snapshot/<code-and-FAOSTAT-digest>/`.
  These are the existing project-source files, not a new FAOSTAT download.

The cloud notebook does not use the local provisional governorate ID adapter.
Earlier local reports and SQLite remain previews; they are not the cloud tables.

## Notebook

`/Shared/Mahmoud/AquaAgri/03_team_cloud_integration`

Source: `notebooks/03_team_cloud_integration.py`.
The `run_tag` widget identifies the code and uploaded FAOSTAT input snapshot.
It is not a hash of the team's mutable T20 inputs. For a later refresh, use a
new run tag and retain that run's input versions and execution evidence.

T12 imports actual extraction outcomes and records executed unit/key/join
checks into the existing team Delta log using MERGE on a snapshot/check ID.
Existing DQ001–DQ004 are retained. These are Spark checks and recorded CAPMAS
outcomes; they do not claim Nada's Great Expectations suite ran successfully.

T17 retains source values, units and flags; converts tonnes to kg, thousand ha
to ha, thousand m3 to m3 and feddan to ha; climate stays mm and degrees C.
Delta column mapping retains the original FAOSTAT column headers containing
spaces and parentheses. It uses Delta reader protocol 2/writer protocol 5 or
newer; downstream readers of these Silver tables must support column mapping.
The Gold staging tables have ordinary column names.

T22 builds the governorate/season/crop water fact from the team's IDs and climate.
Country-level crop production is retained separately. Governorate production and
water productivity remain null because no observed source supplies that grain.

All new data outputs are under `silver/mahmoud/runs/<run_tag>/`.
Each write is read back and its row count checked. Existing T20 tables are read
only. This run is not a multi-table transaction; only a successful run with its
validated result should be selected by downstream consumers.

## Remaining platform work

Creating an external location for `abfss://gold@aqua1storage.dfs.core.windows.net/`
with existing `aqua_credential` returned `PERMISSION_DENIED`: the user lacks
`CREATE EXTERNAL LOCATION` on that credential. No location or grants changed.
The current fact is therefore staged in Silver, not published to the Gold container.

The credential owner must register the project Gold external location and grant
the user's identity the required file access; then the fact can be published there.
Do not grant broad account administration merely to finish this step.

`aqua4synapse` has no dedicated SQL pool. Synapse artifact API access is denied.
The existing dedicated-pool loader has not run against Azure. Agree the team's
SQL serving target and give the relevant access before claiming the Synapse
part is deployed; creating a paid dedicated pool is not assumed.

API references:
- https://docs.databricks.com/api/jobs/v2/submit-run
- https://learn.microsoft.com/en-us/azure/storage/common/authorization-resource-provider

## Successful execution

Run: https://adb-7405614270962201.1.azuredatabricks.net/?o=7405614270962201#job/1119147417757601/run/199933389019983

Result: SUCCESS. Output prefix:
`abfss://silver@aqua1storage.dfs.core.windows.net/mahmoud/runs/fe89b191c3deed062de70f94d796cf7e7ec5fbd14c33ed2ce6fbbf67239bff41`

- T17 FAOSTAT crop: 1,137 rows; irrigation: seven rows.
- T17 CAPMAS: 7,377 rows; climate: 135 rows.
- T22 staged water fact: 4,404 rows; national crop fact: 381 rows.
- T12: 40 records for this successful run (25 source outcomes + 15 executed checks).

The first integration attempt stopped at the FAOSTAT Delta write because of
spaces/parentheses in source column headers. It had already recorded its 25
source outcomes. Those audit rows remain under its distinct run prefix; they do
not indicate a successful pipeline. Column mapping fixed the write and the run
above completed. The same correction also applies to notebook 01.

Nineteen existing local unit tests pass using the project's Anaconda environment.

## Independent read-back verification

https://adb-7405614270962201.1.azuredatabricks.net/?o=7405614270962201#job/765570327756910/run/382625575026671

A separate successful serverless run reopened the persisted Delta tables.
It confirmed all six fact/unit row counts, retained original team log records,
40 new successful-run check records, and zero duplicate quality IDs. It also
checked tonnes-to-kg values, null preservation, complete climate joins and that
no governorate production/productivity values were invented.
Verification source: `notebooks/04_verify_team_outputs.py` (this exact snapshot).
