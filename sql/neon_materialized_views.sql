-- =============================================================================
-- NEON materialized views: do aggregations in the database so the Streamlit app
-- only loads small result sets (no full-table load = no memory limit issues).
--
-- Run this in NEON (SQL Editor or psql) after your main table exists.
-- REPLACE "balancer_data" below with your table name if different (e.g. tokenomics).
-- =============================================================================

-- 1) Pool summary: one row per pool with totals + computed pool_category (Legitimate/Mercenary/Undefined)
--    Streamlit loads this for pool list, top 20, worst 20, and to join with monthly series.
DROP MATERIALIZED VIEW IF EXISTS mv_pool_summary;
CREATE MATERIALIZED VIEW mv_pool_summary AS
WITH base AS (
  SELECT
    pool_symbol,
    MAX(blockchain) AS blockchain,
    MAX(version::text) AS version,
    MAX(CASE WHEN COALESCE(core_non_core::text, '') IN ('true', '1', 't', 'yes') THEN 1 ELSE 0 END) AS is_core_pool,
    SUM(COALESCE(bal_emited_votes, 0)::double precision) AS total_bal_emited_votes,
    SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) AS total_protocol_fee_usd,
    SUM(COALESCE(bribe_amount_usd, 0)::double precision) AS total_bribe_amount_usd,
    SUM(COALESCE(votes_received, 0)::double precision) AS total_votes_received,
    MIN(block_date) AS first_date,
    MAX(block_date) AS last_date
  FROM balancer_data   -- change to your table name (e.g. tokenomics) if needed
  WHERE pool_symbol IS NOT NULL AND TRIM(pool_symbol) <> ''
  GROUP BY pool_symbol
),
with_metrics AS (
  SELECT *,
    total_protocol_fee_usd - total_bribe_amount_usd AS dao_profit_usd,
    CASE WHEN COALESCE(total_bribe_amount_usd, 0) > 0
         THEN total_protocol_fee_usd / total_bribe_amount_usd ELSE 0 END AS emissions_roi,
    CASE WHEN total_protocol_fee_usd > 0
         THEN total_bribe_amount_usd / total_protocol_fee_usd ELSE 1.0 END AS incentive_dependency
  FROM base
)
SELECT
  pool_symbol,
  blockchain,
  version,
  is_core_pool,
  total_bal_emited_votes,
  total_protocol_fee_usd,
  total_bribe_amount_usd AS direct_incentives,
  dao_profit_usd,
  emissions_roi,
  incentive_dependency,
  total_votes_received,
  first_date,
  last_date,
  -- Simplified pool_category (mirrors utils.classify_pools logic)
  CASE
    WHEN total_bribe_amount_usd = 0 AND total_protocol_fee_usd > 10000 THEN 'Legitimate'
    WHEN total_bribe_amount_usd = 0 THEN 'Undefined'
    WHEN total_protocol_fee_usd = 0 THEN 'Mercenary'
    WHEN emissions_roi < 0.5 THEN 'Mercenary'
    WHEN dao_profit_usd < -1000 THEN 'Mercenary'
    WHEN incentive_dependency > 0.8 THEN 'Mercenary'
    WHEN dao_profit_usd > 0 AND emissions_roi > 1.0 THEN 'Legitimate'
    WHEN is_core_pool = 1 AND emissions_roi > 0.7 THEN 'Legitimate'
    WHEN total_protocol_fee_usd < 5000 THEN 'Mercenary'
    ELSE 'Undefined'
  END AS pool_category
FROM with_metrics
WITH DATA;

-- UNIQUE index required for REFRESH MATERIALIZED VIEW CONCURRENTLY (avoids locking base table)
CREATE UNIQUE INDEX ON mv_pool_summary (pool_symbol);

-- 2) Monthly series: one row per (month, pool_symbol) for time-series charts
DROP MATERIALIZED VIEW IF EXISTS mv_monthly_series;
CREATE MATERIALIZED VIEW mv_monthly_series AS
SELECT
  date_trunc('month', (block_date::date))::date AS year_month,
  pool_symbol,
  SUM(COALESCE(bal_emited_votes, 0)::double precision) AS bal_emited_votes,
  SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) AS protocol_fee_amount_usd,
  SUM(COALESCE(bribe_amount_usd, 0)::double precision) AS bribe_amount_usd,
  SUM(COALESCE(votes_received, 0)::double precision) AS votes_received,
  MAX(CASE WHEN COALESCE(core_non_core::text, '') IN ('true', '1', 't', 'yes') THEN 1 ELSE 0 END) AS is_core_pool
FROM balancer_data   -- change to your table name (e.g. tokenomics) if needed
WHERE pool_symbol IS NOT NULL AND TRIM(pool_symbol) <> ''
GROUP BY date_trunc('month', (block_date::date)), pool_symbol
WITH DATA;

-- UNIQUE index required for REFRESH MATERIALIZED VIEW CONCURRENTLY (avoids locking base table)
CREATE UNIQUE INDEX ON mv_monthly_series (year_month, pool_symbol);
CREATE INDEX ON mv_monthly_series (year_month);
CREATE INDEX ON mv_monthly_series (pool_symbol);

-- 3) Refresh (run after loading new data into the base table)
--    Use CONCURRENTLY so the base table is not locked and the app can keep reading:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_pool_summary;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_series;

-- If your table is tokenomics (or another name), replace "balancer_data" in both CTE/views above.
