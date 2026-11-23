# Mahmoud's presentation rehearsal

## Two-minute explanation

My part ingests climate workbooks without changing their source values and records
provenance. I select the same five years as the irrigation data, reshape the
sheets into governorate-year observations, and standardize the units.

I joined the team's CAPMAS extraction to annual climate using an explicit name
adapter. The detail fact has 4,404 rows with source row IDs and review flags.
Subtotals and alternative annual water bases are separate, avoiding double counts.

The pipeline logs each run's checks and can be rerun without duplicating facts.
Missing values remain missing. National production is not allocated to governorates,
so unsupported local production and water productivity are null.

The trend report compares national crop yield with climate context. It shows
co-movement, not proof that climate caused yield changes. I also prepared an
ADLS publisher, Spark/Delta notebooks and SQL fact DDL for cloud integration.

## Likely questions

- **Why annual labels ending -07?** The annual API gives Cairo 2016 as 22.48;
  July in the monthly API is 29.10. The 12-month mean rounds to 22.48.
- **Why no local productivity?** Compatible governorate production is absent.
  Joining national production by year alone would invent local values.
- **What about extraction errors?** Review flags remain and must be filtered or
  disclosed. The adapter does not claim to repair or certify the original PDFs.
- **How are double counts prevented?** Exclude totals from detail, keep annual
  facts separate, and select exactly one measurement basis.
- **What remains live?** Cloud execution with the team's identity, Power BI
  Windows refresh/visual acceptance, and rehearsal with the actual team.

## Demo order

Run pipeline; inspect quality log; query SQLite fact; show trend PNG; open PBIP
on Windows; show Azure publication plan. Do not describe local tests as a live
cloud deployment. Each teammate should rehearse their own part and handoff.
