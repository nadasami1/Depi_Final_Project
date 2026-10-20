# AquaAgri Egypt

DEPI Data Engineering graduation project: combine irrigation, crop production,
and climate data to analyze agricultural water use and reporting gaps in Egypt.

## Repository structure

```text
datasets/
  raw/          Original source files, kept unchanged
src/            Reusable Python code for the data pipeline
notebooks/      Data exploration and development notebooks
docs/           Source descriptions, data dictionary, and design documents
reports/        Findings, charts, and Power BI deliverables
```

These folders are a starting structure. Data, pipeline implementation, and reports
will be added through the team's assigned tasks. Empty folders contain `.gitkeep`
because Git tracks files rather than empty folders.

## Naming conventions

- Use lowercase `snake_case` for new folders and authored filenames, for example
  `climate_ingestion.py` and `data_dictionary.md`.
- Keep original downloaded filenames inside `datasets/raw/`. Group files by source,
  for example `datasets/raw/capmas/` and `datasets/raw/world_bank/`.
- Include the period in data filenames you generate, for example
  `climate_2016_2020.csv`. Use `YYYY-MM-DD` for a full date in a filename.
- Use descriptive Python function and variable names in `snake_case`.
- Do not overwrite raw data with cleaned output. Choose processed-data storage
  when implementing that pipeline stage.
- Keep passwords, access tokens, and connection strings out of Git. Local `.env`
  files are ignored.

## Team workflow

1. Update your local `main` branch before starting a task.
2. Create a task branch, for example `mahmoud/climate-ingestion`.
3. Commit only files related to that task, with a descriptive commit message.
4. Push the branch and open a pull request for review before merging into `main`.

## Available steps

- [Local climate ingestion](docs/climate_ingestion.md): download the team's
  original climate workbooks and record source metadata using Python.

Azure orchestration and the remaining pipeline stages are not implemented yet.
