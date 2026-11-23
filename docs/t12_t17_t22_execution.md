# T12, T17 and T22 execution handoff

## T12: team results now enter the same log

Every build imports the 25 source CAPMAS table-validation results into
`datasets/quality/data_quality_log.csv`, in the same run as local key/unit/join
checks. Source `review` remains a warning; source `failed` blocks the build.

For Nada's Great Expectations suites, export the suite validation result with
`validation_result.to_json_dict()` and save its JSON in `datasets/quality_inputs/`.
Then run `python src/run_pipeline.py`. Both `type` and legacy `expectation_type`
are accepted. This imports actual results; it does not invent or run missing
suites. No suite export has been supplied yet.

The count unit for a GX outcome is one expectation. The original result dictionary
(including unexpected row counts when present) is preserved in details. A failed
BOOLEAN_ONLY check remains a failure even when it has no unexpected_count.
Malformed exports also block publication. Build provenance hashes include the
result files and governorate adapter, so changed results require a fresh build.

References:
- https://docs.greatexpectations.io/docs/core/run_validations/run_a_validation_definition/
- https://docs.greatexpectations.io/docs/reference/api/core/expectationvalidationresult_class/

## T17: workspace execution

The actual Spark notebook transformations passed CI smoke tests against the team's
data, with local Parquet sinks. Live Delta execution still requires the existing
Databricks workspace and storage permission. Follow `docs/azure_runbook.md`; no
account or credentials are present in the repository or on the local machine.

## T22: executable Synapse load

The local fact build runs now. For the live load into the team's existing dedicated
SQL pool, create the targets once using `sql/gold_synapse.sql` and
`sql/quality_log_synapse.sql`. Use the team's authenticated Microsoft identity.
The machine running the loader needs Microsoft ODBC Driver 18 and
`pip install -r requirements-azure.txt`.

```sh
python src/run_pipeline.py
python src/load_synapse.py --dry-run
python src/load_synapse.py --server WORKSPACE.sql.azuresynapse.net --database POOL
```

No password or token is stored in files. DefaultAzureCredential obtains an Entra
token for SQL at runtime. The loader preflights target columns before writes,
refuses nonempty facts by default, preserves nulls, checks row counts, and commits
both facts and quality history in one transaction. Failures roll back the DML.
`--replace` explicitly replaces existing fact rows, but never deletes quality
history. Log rows already present by run_id/dataset/check_name are not appended
again. Do not use --replace on a shared table until replacement is agreed.

The loader's transaction behavior is tested with a test double; this is not a
substitute for an actual Synapse driver/network/permission test. No live Synapse
load or Databricks Delta write has occurred without the team's account details.

Microsoft token/ODBC reference:
https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory
