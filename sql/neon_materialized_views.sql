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
  FROM balancer_data   
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
CREATE UNIQUE INDEX ON mv_pool_summary (project_contract_address);

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
CREATE UNIQUE INDEX ON mv_monthly_series (year_month, project_contract_address);
CREATE INDEX ON mv_monthly_series (year_month);
CREATE INDEX ON mv_monthly_series (project_contract_address);
DROP MATERIALIZED VIEW IF EXISTS mv_daily_series;
CREATE MATERIALIZED VIEW mv_daily_series AS
SELECT
  (block_date::date) AS block_date,
  TRIM(COALESCE(project_contract_address::text, '')) AS project_contract_address,
  MAX(pool_symbol) AS pool_symbol,
  MAX(blockchain) AS blockchain,
  MAX(version::text) AS version,
  MAX(TRIM(COALESCE(gauge_address::text, ''))) AS gauge_address,
  MAX(TRIM(COALESCE(pool_type::text, ''))) AS pool_type,
  SUM(COALESCE(swap_amount_usd, 0)::double precision) AS swap_amount_usd,
  SUM(COALESCE(tvl_usd, 0)::double precision) AS tvl_usd,
  SUM(COALESCE(tvl_eth, 0)::double precision) AS tvl_eth,
  SUM(COALESCE(total_protocol_fee_usd, protocol_fee_amount_usd, 0)::double precision) AS total_protocol_fee_usd,
  SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) AS protocol_fee_amount_usd,
  SUM(COALESCE(swap_fee_usd, 0)::double precision) AS swap_fee_usd,
  SUM(COALESCE(yield_fee_usd, 0)::double precision) AS yield_fee_usd,
  MAX(COALESCE(swap_fee_percent, 0)::double precision) AS swap_fee_percent,
  (MAX(CASE WHEN COALESCE(LOWER(TRIM(core_non_core::text)), '') IN ('true', '1', 't', 'yes') OR COALESCE(core_non_core::text, '') = 'True' THEN 1 ELSE 0 END) = 1)::boolean AS core_non_core,
  SUM(COALESCE(bal_emited_votes, 0)::double precision) AS bal_emited_votes,
  SUM(COALESCE(bal_emited_usd, bribe_amount_usd, 0)::double precision) AS direct_incentives,
  SUM(COALESCE(protocol_fee_amount_usd, 0)::double precision) - SUM(COALESCE(bal_emited_usd, bribe_amount_usd, 0)::double precision) AS dao_profit_usd,
  SUM(COALESCE(votes_received, 0)::double precision) AS votes_received,
  SUM(COALESCE(bribe_amount_usd, 0)::double precision) AS bribe_amount_usd
FROM balancer_data
WHERE project_contract_address IS NOT NULL AND TRIM(project_contract_address::text) <> ''
  AND version::text = '2'
GROUP BY (block_date::date), TRIM(COALESCE(project_contract_address::text, ''))
WITH DATA;
CREATE UNIQUE INDEX ON mv_daily_series (block_date, project_contract_address);
CREATE INDEX ON mv_daily_series (project_contract_address);
CREATE INDEX ON mv_daily_series (block_date);

