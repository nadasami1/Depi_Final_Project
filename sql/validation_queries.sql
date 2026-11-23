-- Local SQLite queries (Synapse uses the same grouping logic).
SELECT governorate_id, year, season, crop_id, COUNT(*) AS records
FROM fact_water_usage
GROUP BY governorate_id, year, season, crop_id
HAVING COUNT(*) > 1;

SELECT COUNT(*) AS orphan_governorates
FROM fact_water_usage f
LEFT JOIN dim_governorate d ON f.governorate_id = d.governorate_id
WHERE d.governorate_id IS NULL;

-- Source review status must remain visible.
SELECT year, review_required, COUNT(*) AS records
FROM fact_water_usage GROUP BY year, review_required;

-- Select ONE basis before summarizing annual irrigation water.
SELECT year, SUM(water_used_m3) AS canal_water_m3
FROM fact_water_annual
WHERE measurement_basis = 'canals' AND review_required = 0
GROUP BY year;
