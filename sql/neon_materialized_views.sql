-- =============================================================================
-- NEON materialized views: do aggregations in the database so the Streamlit app
-- only loads small result sets (no full-table load = no memory limit issues).
--
-- ALIGNED WITH NOTEBOOK: Uses bal_emited_usd (BAL emissions) for direct_incentives,
-- NOT bribe_amount_usd (bribes). Bribes = payments to voters; BAL emissions = protocol schedule.
-- If bal_emited_usd is missing, falls back to bribe_amount_usd for compatibility.
--
-- Run this in NEON (SQL Editor or psql) after your main table exists.
-- REPLACE "balancer_data" below with your table name if different (e.g. tokenomics).
-- If your table does not have gauge_address, remove the gauge_address lines from both views.
-- =============================================================================

-- 1) Pool summary: one row per pool (project_contract_address) with totals + pool_category.
--    Matches notebook behavioral engine: group by project_contract_address, exclude dead and low-record pools.
--    direct_incentives = bal_emited_usd (BAL emissions) with fallback to bribe_amount_usd.
DROP MATERIALIZED VIEW IF EXISTS mv_pool_summary;
CREATE MATERIALIZED VIEW mv_pool_summary AS
WITH base AS (
  SELECT
    TRIM(COALESCE(project_contract_address::text, '')) AS project_contract_address,
    MAX(pool_symbol) AS pool_symbol,
    MAX(blockchain) AS blockchain,
    MAX(version::text) AS version,
    MAX(CASE WHEN COALESCE(LOWER(TRIM(core_non_core::text)), '') IN ('true', '1', 't', 'yes') OR COALESCE(core_non_core::text, '') = 'True' THEN 1 ELSE 0 END) AS is_core_pool,
    MAX(TRIM(COALESCE(gauge_address::text, ''))) AS gauge_address,
    MAX(TRIM(COALESCE(pool_type::text, ''))) AS pool_type,
    SUM(COALESCE(bal_emited_votes, 0)::double precision) AS total_bal_emited_votes,
    SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) AS total_protocol_fee_usd,
    SUM(COALESCE(bal_emited_usd, bribe_amount_usd, 0)::double precision) AS total_direct_incentives,
    SUM(COALESCE(bribe_amount_usd, 0)::double precision) AS total_bribe_amount_usd,
    SUM(COALESCE(votes_received, 0)::double precision) AS total_votes_received,
    MIN(block_date) AS first_date,
    MAX(block_date) AS last_date,
    COUNT(*)::int AS n_records
  FROM balancer_data   -- change to your table name (e.g. tokenomics) if needed
  WHERE project_contract_address IS NOT NULL AND TRIM(project_contract_address::text) <> ''
  GROUP BY TRIM(COALESCE(project_contract_address::text, ''))
  HAVING COUNT(*) >= 4
    AND NOT (SUM(COALESCE(protocol_fee_amount_usd, 0)) = 0 AND SUM(COALESCE(bal_emited_usd, bribe_amount_usd, 0)) = 0)
),
with_metrics AS (
  SELECT *,
    total_protocol_fee_usd - total_direct_incentives AS dao_profit_usd,
    CASE WHEN COALESCE(total_direct_incentives, 0) > 0
         THEN total_protocol_fee_usd / total_direct_incentives ELSE 0 END AS emissions_roi,
    CASE WHEN total_protocol_fee_usd > 0
         THEN total_direct_incentives / total_protocol_fee_usd ELSE 1.0 END AS incentive_dependency
  FROM base
)
SELECT
  project_contract_address,
  pool_symbol,
  blockchain,
  version,
  is_core_pool,
  COALESCE(gauge_address, '') AS gauge_address,
  COALESCE(pool_type, '') AS pool_type,
  total_bal_emited_votes,
  total_protocol_fee_usd,
  total_direct_incentives AS direct_incentives,
  total_bribe_amount_usd,
  dao_profit_usd,
  emissions_roi,
  incentive_dependency,
  total_votes_received,
  first_date,
  last_date,
  -- Pool category (mirrors utils.classify_pools / notebook behavioral engine)
  -- roi = aggregate_roi (emissions_roi at pool-level = total_rev/total_inc)
  CASE
    WHEN total_direct_incentives = 0 AND total_protocol_fee_usd > 15000 THEN 'Legitimate'
    WHEN total_direct_incentives = 0 AND total_protocol_fee_usd > 0 THEN 'Sustainable'
    WHEN total_direct_incentives = 0 THEN 'Undefined'
    WHEN total_protocol_fee_usd = 0 THEN 'Mercenary'
    WHEN emissions_roi < 0.5 THEN 'Mercenary'
    WHEN dao_profit_usd < 0 THEN 'Mercenary'
    WHEN incentive_dependency > 0.8 THEN 'Mercenary'
    WHEN total_protocol_fee_usd < 5000 THEN 'Mercenary'
    WHEN dao_profit_usd > 5000 AND emissions_roi > 1.5 AND incentive_dependency < 0.5 THEN 'Legitimate'
    WHEN is_core_pool = 1 AND emissions_roi > 1.2 AND dao_profit_usd > 0 THEN 'Legitimate'
    WHEN dao_profit_usd >= 0 AND emissions_roi >= 0.5 THEN 'Sustainable'
    ELSE 'Undefined'
  END AS pool_category
FROM with_metrics
WITH DATA;

-- UNIQUE index required for REFRESH MATERIALIZED VIEW CONCURRENTLY (avoids locking base table)
CREATE UNIQUE INDEX ON mv_pool_summary (project_contract_address);

-- 2) Monthly series: one row per (month, project_contract_address) for time-series charts
--    direct_incentives = bal_emited_usd (BAL emissions) with fallback to bribe_amount_usd
DROP MATERIALIZED VIEW IF EXISTS mv_monthly_series;
CREATE MATERIALIZED VIEW mv_monthly_series AS
SELECT
  date_trunc('month', (block_date::date))::date AS year_month,
  TRIM(COALESCE(project_contract_address::text, '')) AS project_contract_address,
  MAX(pool_symbol) AS pool_symbol,
  SUM(COALESCE(bal_emited_votes, 0)::double precision) AS bal_emited_votes,
  SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) AS protocol_fee_amount_usd,
  SUM(COALESCE(bal_emited_usd, bribe_amount_usd, 0)::double precision) AS direct_incentives,
  SUM(COALESCE(bribe_amount_usd, 0)::double precision) AS bribe_amount_usd,
  SUM(COALESCE(votes_received, 0)::double precision) AS votes_received,
  MAX(CASE WHEN COALESCE(LOWER(TRIM(core_non_core::text)), '') IN ('true', '1', 't', 'yes') OR COALESCE(core_non_core::text, '') = 'True' THEN 1 ELSE 0 END) AS is_core_pool,
  MAX(TRIM(COALESCE(gauge_address::text, ''))) AS gauge_address,
  MAX(TRIM(COALESCE(pool_type::text, ''))) AS pool_type
FROM balancer_data   -- change to your table name (e.g. tokenomics) if needed
WHERE project_contract_address IS NOT NULL AND TRIM(project_contract_address::text) <> ''
GROUP BY date_trunc('month', (block_date::date)), TRIM(COALESCE(project_contract_address::text, ''))
WITH DATA;

-- UNIQUE index required for REFRESH MATERIALIZED VIEW CONCURRENTLY (avoids locking base table)
CREATE UNIQUE INDEX ON mv_monthly_series (year_month, project_contract_address);
CREATE INDEX ON mv_monthly_series (year_month);
CREATE INDEX ON mv_monthly_series (project_contract_address);

-- 3) Refresh (run after loading new data into the base table)
--    Use CONCURRENTLY so the base table is not locked and the app can keep reading:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pool_summary;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_series;

-- If your table is tokenomics (or another name), replace "balancer_data" in both CTE/views above.
--
-- REQUIREMENT: Base table must have bal_emited_usd (BAL emissions in USD). The create_final_dataset
-- output and merge_votes_bribes pipeline include it. If your table lacks it, add the column from
-- Votes_Emissions.daily_emissions_usd, or replace bal_emited_usd with bribe_amount_usd in the SQL.
