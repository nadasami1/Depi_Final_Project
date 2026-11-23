# Azure execution runbook

The original local-preview procedure below predates the successful live connection.
For the actual team paths, executed notebook and current blockers, use
[Azure live execution](azure_live_execution_2026_11_23.md).
The scripts do not provision resources or grant access.

1. The Azure lead supplies an existing ADLS Gen2 account and filesystem. Authenticate
   using the team's approved DefaultAzureCredential flow, with storage data access.
2. Run `python src/run_pipeline.py`, then `python -m unittest discover -s tests -v`.
3. Run `python src/publish_adls.py --dry-run`. Install `requirements-azure.txt` and
   run with `--account ACCOUNT --filesystem FILESYSTEM` to upload.
4. Note the new versioned prefix from the output. Bronze contains unchanged
   climate/FAOSTAT inputs and the team's CAPMAS CSV extraction snapshot, not a
   replacement for the original PDF bulletins.
5. Import `notebooks/01_silver_units.py` into Databricks. Set raw_base to
   `abfss://FILESYSTEM@ACCOUNT.dfs.core.windows.net/<run-prefix>/bronze` and
   silver_base to a writable Delta target. Spark/Delta and permitted external
   locations are workspace prerequisites. The notebook converts CSV units.
6. Import `notebooks/02_gold_delta.py`. Set published_gold to the run's `/gold`
   path and delta_gold to a writable target. It casts numerical facts, checks
   duplicates and writes Delta tables.
7. Coordinate dimension definitions with Nour. The Azure lead can execute
   `sql/gold_synapse.sql` in a dedicated SQL pool and load matching CSV columns
   using ADF Copy. Map review_required to a SQL bit, retain null production,
   and validate unique grain and dimension keys after loading.

Validate row counts and sample converted values after each live step. Publishing
creates a new run directory rather than overwriting Bronze history. Local tests
and the dry run do not verify cloud access, Delta commits, Synapse loads or Power BI
Service refresh. No account keys are stored in the repository.

`tests/spark_smoke.py` runs the actual notebook transformations with local Spark
and a Parquet test sink. This tests expressions and results without cloud access;
it does not verify Delta transaction writes or workspace permissions.
