-- T22 target schema for an EXISTING Azure Synapse dedicated SQL pool.
-- No resources are provisioned or billed by this script.
-- Load matching datasets/gold CSVs via the team's ADF Copy activities.
-- Run on a new schema/database or migrate existing tables separately.

CREATE TABLE dbo.fact_water_usage (
    fact_id int NOT NULL,
    governorate_id int NOT NULL,
    crop_id int NOT NULL,
    date_id int NOT NULL,
    source_id int NOT NULL,
    climate_source_id int NOT NULL,
    year int NOT NULL,
    season varchar(24) NOT NULL,
    water_used_m3 decimal(24,4) NULL,
    water_unit varchar(8) NOT NULL,
    crop_yield_tons decimal(24,4) NULL,
    water_productivity decimal(24,8) NULL,
    production_status varchar(80) NOT NULL,
    mean_temperature_c decimal(12,4) NULL,
    annual_precipitation_mm decimal(12,4) NULL,
    review_required bit NOT NULL,
    source_table int NOT NULL,
    source_row_id int NOT NULL
) WITH (DISTRIBUTION = HASH(governorate_id), CLUSTERED COLUMNSTORE INDEX);

CREATE TABLE dbo.fact_water_annual (
    governorate_id int NOT NULL,
    year int NOT NULL,
    measurement_basis varchar(12) NOT NULL,
    water_used_m3 decimal(24,4) NULL,
    review_required bit NOT NULL,
    mean_temperature_c decimal(12,4) NULL,
    annual_precipitation_mm decimal(12,4) NULL,
    source_row_id int NOT NULL
) WITH (DISTRIBUTION = HASH(governorate_id), CLUSTERED COLUMNSTORE INDEX);

-- Annual and detail facts are alternative grains: do not union/sum them.
-- canals and aswan are alternative measurement bases: filter exactly one.
-- National production remains in fact_crop_national and must not join to a
-- governorate fact on year alone. Null production/productivity is intentional.
