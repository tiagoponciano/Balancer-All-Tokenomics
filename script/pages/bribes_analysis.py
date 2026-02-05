import streamlit as st
import utils
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import os

st.set_page_config(page_title="Bribes Analysis", layout="wide", page_icon="💰")

# Check authentication
if not utils.check_authentication():
    st.stop()

utils.inject_css()

import streamlit.components.v1 as components

try:
    # Bribes page uses main data (Balancer-All-Tokenomics.csv). "Bribes" = direct_incentives (USD); votes = votes_received.
    df = utils.load_data()
    if df.empty:
        st.warning("⚠️ No data. Ensure `Balancer-All-Tokenomics.csv` is in `data/`.")
        st.stop()

    df_bribes = df.copy()
    # Fill missing pool_symbol so bribes from unknown pools are not dropped in groupby
    df_bribes["pool_symbol"] = (
        df_bribes["pool_symbol"]
        .fillna(df_bribes["project_contract_address"])
        .replace("", pd.NA)
    )

    # Séries auxiliares (nem sempre existem)
    pool_name_series = df_bribes.get("pool_name")
    if pool_name_series is None:
        pool_name_series = df_bribes["pool_symbol"]

    pool_title_series = df_bribes.get("pool_title")
    if pool_title_series is None:
        pool_title_series = df_bribes["pool_symbol"]

    # 👉 Regra principal:
    # se pool_symbol estiver vazio, usar pool_name, depois pool_title, depois contract
    df_bribes["pool_symbol"] = (
        df_bribes["pool_symbol"]
        .fillna(pool_name_series)
        .fillna(pool_title_series)
        .fillna(df_bribes["project_contract_address"])
    )

    # If pool_symbol is a URL, prefer pool_name (or pool_title) for display
    is_url = df_bribes["pool_symbol"].astype(str).str.startswith(("http://", "https://")) | \
            df_bribes["pool_symbol"].astype(str).str.contains("balancer.fi/pools", na=False)

    # Se for URL, usar nome amigável
    df_bribes["pool_symbol"] = df_bribes["pool_symbol"].mask(
        is_url,
        pool_name_series.fillna(pool_title_series).fillna(df_bribes["project_contract_address"])
    )
    # Sanitize any residual URL-like values in pool name/title to avoid links in UI
    def _strip_url(val, fallback):
        s = str(val)
        if s.startswith(("http://", "https://")) or "balancer.fi/pools" in s:
            return fallback
        return val
    df_bribes["pool_symbol"] = df_bribes.apply(
        lambda r: _strip_url(r.get("pool_symbol"), r.get("project_contract_address")),
        axis=1
    )
    if "pool_title" in df_bribes.columns:
        df_bribes["pool_title"] = df_bribes.apply(
            lambda r: _strip_url(r.get("pool_title"), r.get("pool_symbol")),
            axis=1
        )
    if "pool_name" in df_bribes.columns:
        df_bribes["pool_name"] = df_bribes.apply(
            lambda r: _strip_url(r.get("pool_name"), r.get("pool_symbol")),
            axis=1
        )
    # Helper: ensure we always have a human-readable label (never a URL)
    def _safe_pool_label(row):
        for key in ["pool_name", "pool_title", "pool_symbol"]:
            val = row.get(key)
            if pd.notna(val) and str(val).strip() != "":
                s = str(val)
                if s.startswith(("http://", "https://")) or "balancer.fi/pools" in s:
                    continue
                return s
        return row.get("project_contract_address")
    if "gauge_address" in df_bribes.columns:
        df_bribes["gauge_address"] = df_bribes["gauge_address"].fillna(df_bribes["project_contract_address"]).astype(str)
    else:
        df_bribes["gauge_address"] = df_bribes["project_contract_address"].fillna("").astype(str)
    df_bribes["pool_title"] = df_bribes["pool_symbol"].fillna("")
    df_bribes["pool_name"] = df_bribes["pool_symbol"].fillna("")
    df_bribes["vebal_votes"] = df_bribes["votes_received"]
    latest = df_bribes["block_date"].max()
    sub = df_bribes[df_bribes["block_date"] == latest]
    total_v = sub["votes_received"].sum()
    rank_df = sub.groupby("pool_symbol", as_index=False)["votes_received"].sum()
    rank_df["vebal_pct_votes"] = (rank_df["votes_received"] / total_v) if total_v else 0
    rank_df["vebal_ranking"] = rank_df["votes_received"].rank(method="min", ascending=False).astype(int)
    df_bribes = df_bribes.merge(
        rank_df[["pool_symbol", "vebal_pct_votes", "vebal_ranking"]].rename(columns={"vebal_pct_votes": "_pct", "vebal_ranking": "_rank"}),
        on="pool_symbol",
        how="left",
    )
    df_bribes["vebal_pct_votes"] = df_bribes["_pct"].fillna(0)
    df_bribes["vebal_ranking"] = df_bribes["_rank"]
    df_bribes = df_bribes.drop(columns=["_pct", "_rank"], errors="ignore")

    df_votes = df[["pool_symbol", "project_contract_address", "votes_received", "block_date"]].drop_duplicates()
    df_votes = df_votes.rename(columns={"votes_received": "votes", "project_contract_address": "gauge"})
except Exception as e:
    st.error(f"❌ Error loading data: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

# Initialize session state
if 'pool_filter_mode_bribes' not in st.session_state:
    st.session_state.pool_filter_mode_bribes = 'all'  # Default: show all pools
if 'version_filter_bribes' not in st.session_state:
    st.session_state.version_filter_bribes = 'all'  # Default: show all versions
if 'gauge_filter_bribes' not in st.session_state:
    st.session_state.gauge_filter_bribes = 'all'  # Default: show all pools
if 'show_performance_by_pool' not in st.session_state:
    st.session_state.show_performance_by_pool = False
if 'performance_page' not in st.session_state:
    st.session_state.performance_page = 1

components.html("""
<script>
console.log('[Button IDs] Script loaded via components.html (bribes_analysis.py)!');

function applyButtonIds() {
    const contexts = [
        { doc: document, name: 'document' },
        { doc: window.parent?.document, name: 'parent' },
        { doc: window.top?.document, name: 'top' }
    ];
    
    let totalButtons = 0;
    let perfButtonFound = false;
    
    contexts.forEach(({ doc, name }) => {
        if (!doc) return;
        
        try {
            const buttons = doc.querySelectorAll('button[data-testid*="stBaseButton"], button');
            
            buttons.forEach((button) => {
                let text = '';
                try {
                    text = (button.textContent || button.innerText || '').trim();
                    if (!text || text.length === 0) {
                        const markdownEl = button.querySelector('[data-testid="stMarkdownContainer"]');
                        if (markdownEl) {
                            text = (markdownEl.textContent || markdownEl.innerText || '').trim();
                        }
                    }
                    if (!text || text.length === 0) {
                        const pEl = button.querySelector('p');
                        if (pEl) {
                            text = (pEl.textContent || pEl.innerText || '').trim();
                        }
                    }
                } catch(e) {}
                
                const textLower = text.toLowerCase();
                
                // Apply IDs with correct prefixes
                if (text === 'V2' || textLower === 'v2') {
                    if (!button.id || !button.id.startsWith('btn_v2_')) {
                        button.id = 'btn_v2_version_filter';
                    }
                } else if (text === 'V3' || textLower === 'v3') {
                    if (!button.id || !button.id.startsWith('btn_v3_')) {
                        button.id = 'btn_v3_version_filter';
                    }
                } else if (text === 'All Versions' || textLower === 'all versions') {
                    if (!button.id || !button.id.startsWith('btn_all_versions_')) {
                        button.id = 'btn_all_versions_version_filter';
                    }
                } else if (text === 'Gauge' || textLower === 'gauge') {
                    if (!button.id || !button.id.startsWith('btn_gauge_')) {
                        button.id = 'btn_gauge_filter';
                    }
                } else if (text === 'No Gauge' || textLower === 'no gauge') {
                    if (!button.id || !button.id.startsWith('btn_no_gauge_')) {
                        button.id = 'btn_no_gauge_filter';
                    }
                } else if (text === 'Top 20' || textLower === 'top 20') {
                    if (!button.id || !button.id.startsWith('btn_top20')) {
                        button.id = 'btn_top20';
                    }
                } else if (text === 'Worst 20' || textLower === 'worst 20') {
                    if (!button.id || !button.id.startsWith('btn_worst20')) {
                        button.id = 'btn_worst20';
                    }
                } else if (text === 'Select All' || textLower === 'select all') {
                    if (!button.id || !button.id.startsWith('btn_select_all')) {
                        button.id = 'btn_select_all';
                    }
                } else if (text.includes('Logout') || text.includes('🚪') || textLower.includes('logout')) {
                    if (!button.id || !button.id.startsWith('btn_logout')) {
                        button.id = 'btn_logout';
                    }
                } else if (text.includes('Show Performance') || text.includes('Performance by Pool') || textLower.includes('performance') || text.includes('🔍')) {
                    if (!button.id || button.id !== 'btn_performance_by_pool') {
                        button.id = 'btn_performance_by_pool';
                        button.classList.add('performance-button-fallback');
                        button.setAttribute('data-button-type', 'performance');
                        
                        // Apply all inline styles directly (maximum priority)
                        const styles = {
                            'width': '250px',
                            'min-width': '250px',
                            'max-width': '250px',
                            'height': '56px',
                            'padding': '0.625rem 1.5rem',
                            'font-weight': '600',
                            'background': 'linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%)',
                            'border': '1.5px solid rgba(103, 162, 225, 0.45)',
                            'color': '#8BB5F0',
                            'border-radius': '12px',
                            'transition': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            'box-shadow': '0 3px 12px rgba(103, 162, 225, 0.15)',
                            'position': 'relative',
                            'overflow': 'hidden',
                            'letter-spacing': '0.02em'
                        };
                        
                        Object.keys(styles).forEach(prop => {
                            button.style.setProperty(prop, styles[prop], 'important');
                        });
                        
                        perfButtonFound = true;
                    }
                }
            });
            
            totalButtons += buttons.length;
        } catch(e) {
            // Silent error handling
        }
    });
}

// Execute immediately and after delays
applyButtonIds();
setTimeout(applyButtonIds, 100);
setTimeout(applyButtonIds, 500);
setTimeout(applyButtonIds, 1000);
setTimeout(applyButtonIds, 2000);
setInterval(applyButtonIds, 3000);

// Observe DOM changes
if (window.MutationObserver) {
    const observer = new MutationObserver(() => {
        setTimeout(applyButtonIds, 100);
    });
    
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    }
    
    try {
        if (window.parent && window.parent.document && window.parent.document.body) {
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
        }
    } catch(e) {}
}
</script>
""", height=0)


# Determine filter pools based on mode - using only bribes data
if st.session_state.pool_filter_mode_bribes == 'top20':
    filter_label = "Top 20 Pools"
elif st.session_state.pool_filter_mode_bribes == 'worst20':
    filter_label = "Worst 20 Pools"
else:  # 'all' - default mode, show everything
    filter_label = "All Pools"

# Bribes page uses merged only. Pool = pool_symbol; bribe = direct_incentives; votes = votes_received.
pool_match_col = "pool_symbol"
pool_col = "pool_symbol"

# Pool filters at the top of sidebar
def reset_performance_view():
    """Reset performance view when filter changes"""
    st.session_state.show_performance_by_pool = False
    st.session_state.performance_page = 1

# Version filter at the top of sidebar
utils.show_version_filter('version_filter_bribes', on_change_callback=reset_performance_view)

# Gauge filter (Gauge / No Gauge)
utils.show_gauge_filter('gauge_filter_bribes', on_change_callback=reset_performance_view)

utils.show_pool_filters('pool_filter_mode_bribes', on_change_callback=reset_performance_view)

# Date filter: Year + Quarter (using dynamic filters)
# Note: For bribes page, we need to filter both df and df_bribes
df_combined_for_filter = df.copy()
df_combined_for_filter = utils.show_date_filter_sidebar(df_combined_for_filter, key_prefix="date_filter_bribes")

# Extract the date range from filtered df and apply to both dataframes
if not df_combined_for_filter.empty and 'block_date' in df_combined_for_filter.columns:
    min_date = df_combined_for_filter['block_date'].min()
    max_date = df_combined_for_filter['block_date'].max()
    df = df[(df['block_date'] >= min_date) & (df['block_date'] <= max_date)]
    df_bribes = df_bribes[(df_bribes['block_date'] >= min_date) & (df_bribes['block_date'] <= max_date)]
else:
    df = df_combined_for_filter

# Apply version filter
df = utils.apply_version_filter(df, 'version_filter_bribes')
df_bribes = utils.apply_version_filter(df_bribes, 'version_filter_bribes')

# Apply gauge filter
df = utils.apply_gauge_filter(df, 'gauge_filter_bribes')
df_bribes = utils.apply_gauge_filter(df_bribes, 'gauge_filter_bribes')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

# Build display dataframe from date-filtered df_bribes (and date-filtered df for top/worst)
if st.session_state.pool_filter_mode_bribes == "top20":
    top_pools = utils.get_top_pools(df, n=20)
    mask = df_bribes["pool_symbol"].astype(str).str.strip().isin([str(p).strip() for p in top_pools])
    df_bribes_display = df_bribes[mask].copy() if mask.any() else df_bribes.copy()
    n = df_bribes_display["pool_symbol"].nunique()
    # Removed info message - filter is already shown in sidebar
elif st.session_state.pool_filter_mode_bribes == "worst20":
    worst_pools = utils.get_worst_pools(df, n=20)
    mask = df_bribes["pool_symbol"].astype(str).str.strip().isin([str(p).strip() for p in worst_pools])
    df_bribes_display = df_bribes[mask].copy() if mask.any() else df_bribes.copy()
    n = df_bribes_display["pool_symbol"].nunique()
    # Removed info message - filter is already shown in sidebar
else:
    df_bribes_display = df_bribes.copy()
    n = df_bribes_display["pool_symbol"].nunique()
    # Removed info message - filter is already shown in sidebar

# Page Header with logout button
col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">💰 Bribes Analysis</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

# Verify pool_col was found
if pool_col is None:
    st.error("❌ Could not identify pool column in bribes data.")
    st.info(f"Available columns: {', '.join(df_bribes.columns.tolist())}")
    st.dataframe(df_bribes.head(5))
    st.stop()


try:
    # Identify bribe-related columns - always use df_bribes (original) for column identification
    # df_bribes_display is used for filtering/display, but column names come from original
    df_to_check = df_bribes
    
    bribe_col = None
    votes_col = None
    bal_col = None

    # Try to find bribe amount column (case-insensitive search)
    # Priority: bribe_amount_usd first (as specified by user)
    df_cols_lower = {col.lower(): col for col in df_to_check.columns}
    for col_lower in ['bribe_amount_usd', 'direct_incentives', 'amount_usdc', 'total_bribes_usd', 'bribe_amount', 'bribes_usd', 'amount_usd', 'bribe', 'bribes', 'amount']:
        if col_lower in df_cols_lower:
            bribe_col = df_cols_lower[col_lower]
            break

    # Try to find votes column (may not exist in this dataset)
    # First check if we have veBAL votes from merge
    if 'vebal_votes' in df_to_check.columns:
        votes_col = 'vebal_votes'
    elif 'votes_received' in df_to_check.columns:
        votes_col = 'votes_received'
    else:
        for col_lower in ['votes', 'total_votes', 'vote_count', 'vote']:
            if col_lower in df_cols_lower:
                votes_col = df_cols_lower[col_lower]
                break

    # BAL column not available in bribes dataset
    # This data would come from the main financial dataset, but we're using only bribes data here
    bal_col = None
    
    # Also check for total_bribes_periodo which might be useful
    total_bribes_col = None
    if 'total_bribes_periodo' in df_to_check.columns:
        total_bribes_col = 'total_bribes_periodo'

    if bribe_col is None:
        st.error("❌ Could not find bribe amount column in the data.")
        st.info(f"Available columns: {', '.join(df_to_check.columns.tolist())}")
        st.dataframe(df_to_check.head(5))
        st.stop()
except Exception as e:
    st.error(f"❌ Error identifying columns: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

try:
    # Verify df_bribes_display has data
    if df_bribes_display.empty:
        st.warning("⚠️ No bribes data available for the selected filter.")
        pool_bribes = pd.DataFrame()
    else:
        # Aggregate bribes data by pool
        agg_dict = {bribe_col: 'sum'}
        # Votes should be 'max' not 'sum' because each gauge has unique vote count
        # If we sum, we're counting votes multiple times for the same gauge
        if votes_col:
            # Only sum if it's not veBAL votes (which are unique per gauge)
            if votes_col == 'vebal_votes':
                agg_dict[votes_col] = 'max'  # Unique per gauge, use max
            else:
                agg_dict[votes_col] = 'sum'  # Other vote types might be cumulative
        if bal_col:
            agg_dict[bal_col] = 'sum'
        # Include total_bribes_periodo if available
        if 'total_bribes_periodo' in df_bribes_display.columns:
            agg_dict['total_bribes_periodo'] = 'max'  # Use max since it's per period
        # Include veBAL votes if available
        if 'vebal_votes' in df_bribes_display.columns:
            agg_dict['vebal_votes'] = 'sum'
        if 'vebal_pct_votes' in df_bribes_display.columns:
            agg_dict['vebal_pct_votes'] = 'mean'  # Average percentage
        if 'vebal_ranking' in df_bribes_display.columns:
            agg_dict['vebal_ranking'] = 'min'
        for c in ['pool_title', 'pool_name']:
            if c in df_bribes_display.columns:
                agg_dict[c] = 'first'
        # Preserve gauge_address and pool_type for display
        if 'gauge_address' in df_bribes_display.columns:
            agg_dict['gauge_address'] = 'first'
        if 'project_contract_address' in df_bribes_display.columns:
            agg_dict['project_contract_address'] = 'first'
        if 'pool_type' in df_bribes_display.columns:
            agg_dict['pool_type'] = 'first'

        # Calculate metrics - aggregate by pool
        if pool_col and pool_col in df_bribes_display.columns:
            pool_bribes = df_bribes_display.groupby(pool_col).agg(agg_dict).reset_index()
        else:
            # Fallback: use pool_match_col if pool_col not available
            if pool_match_col and pool_match_col in df_bribes_display.columns:
                pool_bribes = df_bribes_display.groupby(pool_match_col).agg(agg_dict).reset_index()
                pool_col = pool_match_col  # Update pool_col for later use
            else:
                st.error("❌ Could not find pool column for aggregation.")
                st.info(f"Available columns: {', '.join(df_bribes_display.columns.tolist())}")
                pool_bribes = pd.DataFrame()
except Exception as e:
    st.error(f"❌ Error aggregating data: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

# Calculate derived metrics
if not pool_bribes.empty:
    if votes_col and votes_col in pool_bribes.columns:
        pool_bribes['bribe_per_vote'] = np.where(
            pool_bribes[votes_col] > 0,
            pool_bribes[bribe_col] / pool_bribes[votes_col],
            0
        )

else:
    # Create empty columns for consistency when DataFrame is empty
    if pool_bribes.empty:
        # Create empty DataFrame with proper structure and numeric columns
        empty_cols = [pool_col, bribe_col]
        if votes_col:
            empty_cols.append('bribe_per_vote')
        pool_bribes = pd.DataFrame(columns=empty_cols)
        # Ensure numeric columns have proper dtype
        for col in ['bribe_per_vote']:
            if col in pool_bribes.columns:
                pool_bribes[col] = pool_bribes[col].astype(float)

# No merge with main data - using only bribes and veBAL votes data

# Main Metrics
st.markdown("### 📊 Key Metrics")

col1, col2, col3 = st.columns(3)

total_bribes = pool_bribes[bribe_col].sum() if bribe_col in pool_bribes.columns and not pool_bribes.empty else 0
total_votes = df_bribes_display["votes_received"].sum() if "votes_received" in df_bribes_display.columns else 0
total_vebal_votes = total_votes

with col1:
    st.metric(
        "Total Bribes",
        f"${total_bribes:,.0f}",
        help="Total USD value of all bribes received"
    )

with col2:
    st.metric(
        "Total Votes",
        f"{total_votes:,.0f}",
        help="Total votes received across all pools"
    )

with col3:
    st.metric(
        "veBAL Votes",
        f"{total_vebal_votes:,.0f}",
        help="Total veBAL votes from current voting period"
    )

st.markdown("---")

# Rankings
st.markdown("### 🏆 Pool Rankings")

# Build ranking source from pool_bribes (merged data)
all_pools_for_ranking = None
if not pool_bribes.empty and pool_col in pool_bribes.columns and bribe_col in pool_bribes.columns:
    # Get additional columns: blockchain, gauge_address, version
    cols_to_include = [pool_col, "pool_title", "pool_name", "pool_type", bribe_col]
    if "blockchain" in pool_bribes.columns:
        cols_to_include.append("blockchain")
    if "gauge_address" in pool_bribes.columns:
        cols_to_include.append("gauge_address")
    if "project_contract_address" in pool_bribes.columns:
        cols_to_include.append("project_contract_address")
    
    rr = pool_bribes[cols_to_include].copy()
    rr = rr.rename(columns={pool_col: "pool", bribe_col: "bribe_amount"})
    # Sanitize any URL-like pool labels before display
    def _sanitize_pool_label(val, fallback):
        s = str(val)
        if s.startswith(("http://", "https://")) or "balancer.fi/pools" in s:
            return fallback
        return val
    rr["pool"] = rr.apply(lambda r: _sanitize_pool_label(r.get("pool"), r.get("gauge_address") or r.get("project_contract_address") or r.get("pool")), axis=1)
    if "pool_title" in rr.columns:
        rr["pool_title"] = rr.apply(lambda r: _sanitize_pool_label(r.get("pool_title"), r.get("pool")), axis=1)
    if "pool_name" in rr.columns:
        rr["pool_name"] = rr.apply(lambda r: _sanitize_pool_label(r.get("pool_name"), r.get("pool")), axis=1)
    rr["pool_title"] = rr.get("pool_title", rr["pool"]).fillna(rr["pool"])
    rr["pool_name"] = rr.get("pool_name", rr["pool"]).fillna(rr["pool"])
    
    # Add version and address columns if not present
    if "blockchain" not in rr.columns:
        # Try to get from df_bribes_display
        if not df_bribes_display.empty and "blockchain" in df_bribes_display.columns and "pool_symbol" in df_bribes_display.columns:
            blockchain_map = df_bribes_display.groupby("pool_symbol")["blockchain"].first().to_dict()
            rr["blockchain"] = rr["pool"].map(blockchain_map).fillna("Unknown")
        else:
            rr["blockchain"] = "Unknown"
    
    if "gauge_address" not in rr.columns and "project_contract_address" not in rr.columns:
        # Try to get from df_bribes_display
        if not df_bribes_display.empty and "pool_symbol" in df_bribes_display.columns:
            addr_col_source = "gauge_address" if "gauge_address" in df_bribes_display.columns else "project_contract_address"
            if addr_col_source in df_bribes_display.columns:
                address_map = df_bribes_display.groupby("pool_symbol")[addr_col_source].first().to_dict()
                rr["gauge_address"] = rr["pool"].map(address_map).fillna("")
            else:
                rr["gauge_address"] = ""
        else:
            rr["gauge_address"] = ""
    elif "project_contract_address" in rr.columns and "gauge_address" not in rr.columns:
        rr["gauge_address"] = rr["project_contract_address"]
    
    # Add version column
    if not df_bribes_display.empty and "version" in df_bribes_display.columns and "pool_symbol" in df_bribes_display.columns:
        version_map = df_bribes_display.groupby("pool_symbol")["version"].first().to_dict()
        rr["version"] = rr["pool"].map(version_map).fillna(0).astype(int)
        rr["version_display"] = rr["version"].apply(lambda x: f"V{x}" if x in [2, 3] else "")
    else:
        rr["version_display"] = ""
    
    all_pools_for_ranking = rr

tab1, tab2 = st.tabs(["💰 Top Bribes", "🗳️ veBAL Votes"])

with tab1:
    if all_pools_for_ranking is not None and not all_pools_for_ranking.empty:
        # Show all pools from CSV, even if they don't have data in pool_bribes
        ranking_df = all_pools_for_ranking.copy()
        
        # Use amount_usdc from CSV as base, merge with pool_bribes if available for updated values
        if not pool_bribes.empty and bribe_col in pool_bribes.columns and pool_col in pool_bribes.columns:
            # Create a mapping from pool_bribes
            pool_bribes_dict = {}
            for idx, row in pool_bribes.iterrows():
                pool_key = str(row[pool_col]).upper().strip()
                pool_bribes_dict[pool_key] = row[bribe_col]
            
            # Try to match and update bribe amounts
            def get_bribe_amount(row):
                pool_val = str(row['pool']).upper().strip()
                title_val = str(row.get('pool_title', '')).upper().strip()
                name_val = str(row.get('pool_name', '')).upper().strip()
                
                # Try multiple matching strategies
                if pool_val in pool_bribes_dict:
                    return pool_bribes_dict[pool_val]
                elif title_val in pool_bribes_dict:
                    return pool_bribes_dict[title_val]
                elif name_val in pool_bribes_dict:
                    return pool_bribes_dict[name_val]
                else:
                    return row.get('bribe_amount', 0)
            
            ranking_df['Total Bribes (USD)'] = ranking_df.apply(get_bribe_amount, axis=1)
        else:
            ranking_df['Total Bribes (USD)'] = ranking_df.get('bribe_amount', 0)
        
        # Sort by bribe amount descending
        ranking_df = ranking_df.sort_values('Total Bribes (USD)', ascending=False)
        
        # Generate links for Balancer UI (pool link)
        if 'blockchain' in ranking_df.columns:
            ranking_df['balancer_url'] = ranking_df.apply(
                lambda row: utils.get_balancer_ui_url(
                    row['blockchain'],
                    row.get('project_contract_address') or row.get('gauge_address'),
                    row.get('version', None)
                ),
                axis=1
            )
        

        display_df = ranking_df.copy()
        
        if 'balancer_url' in display_df.columns:
            display_df['pool_label'] = display_df.apply(_safe_pool_label, axis=1)
            display_df['pool_link'] = display_df.apply(
                lambda row: f"{row['balancer_url']}?label={row['pool_label']}"
                if pd.notna(row.get('balancer_url')) and row['balancer_url'] else row['pool_label'],
                axis=1
            )
        else:
            display_df['pool_label'] = display_df.apply(_safe_pool_label, axis=1)
            display_df['pool_link'] = display_df['pool_label']

        if 'blockchain' in display_df.columns:
            display_df['chain_display'] = display_df['blockchain']

        # Address link (gauge_address) with short label - always Etherscan
        def _short_addr(val):
            s = str(val)
            if s.startswith("0x") and len(s) > 10:
                return f"{s[:4]}...{s[-4:]}"
            return s
        if 'gauge_address' in display_df.columns:
            display_df['address_display'] = display_df.apply(
                lambda row: f"https://etherscan.io/address/{row['gauge_address']}?label={_short_addr(row['gauge_address'])}"
                if pd.notna(row.get('gauge_address')) and str(row.get('gauge_address')).strip() != '' else "",
                axis=1
            )
        
        display_df['Total Bribes (USD)'] = display_df['Total Bribes (USD)'].apply(
            lambda x: f"${float(x):,.0f}" if pd.notna(x) and float(x) > 0 else "$0"
        )

        final_cols = ['pool_link']
        final_names = ['Pool']
        if 'chain_display' in display_df.columns:
            final_cols.append('chain_display')
            final_names.append('Chain')
        if 'pool_type' in display_df.columns:
            final_cols.append('pool_type')
            final_names.append('Pool Type')
            
        if 'version_display' in display_df.columns:
            final_cols.append('version_display')
            final_names.append('Version')
            
        final_cols.append('Total Bribes (USD)')
        final_names.append('Total Bribes (USD)')

        if 'address_display' in display_df.columns:
            final_cols.append('address_display')
            final_names.append('Address')

        df_show = display_df[final_cols].copy()
        df_show.columns = final_names
        
        column_config = {}
        
        column_config['Pool'] = st.column_config.LinkColumn(
            'Pool',
            width='medium',
            display_text=r"label=(.*)"
            )
        if 'Chain' in df_show.columns:
            column_config['Chain'] = st.column_config.TextColumn('Chain', width='small')
        if 'Pool Type' in df_show.columns:
            column_config['Pool Type'] = st.column_config.TextColumn('Pool Type', width='small')
            
        if 'Address' in df_show.columns:
            column_config['Address'] = st.column_config.LinkColumn(
                'Address',
                width='small',
                display_text=r"label=(.*)"
            )

        st.dataframe(
            df_show, 
            use_container_width=True, 
            hide_index=True,
            column_config=column_config
        )
    elif bribe_col in pool_bribes.columns and not pool_bribes.empty:
        # Fallback: show from pool_bribes
        bribes_with_data = pool_bribes[pool_bribes[bribe_col] > 0]
        if not bribes_with_data.empty:
            top_bribes = bribes_with_data.nlargest(20, bribe_col)[[pool_col, bribe_col]].copy()
            top_bribes.columns = ['Pool', 'Total Bribes (USD)']
            top_bribes['Total Bribes (USD)'] = top_bribes['Total Bribes (USD)'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(top_bribes, use_container_width=True, hide_index=True)
        else:
            st.info("No pools with bribes data found for the selected filter.")
    else:
        st.info("Bribe amount data not available")

with tab2:
    if all_pools_for_ranking is not None and not all_pools_for_ranking.empty:
        # Show all pools from pool_bribes, merge with veBAL votes from df_bribes_display (Balancer-Tokenomics)
        base_cols = ['pool', 'pool_title', 'pool_name']
        extra_cols = [c for c in ['blockchain', 'project_contract_address', 'gauge_address', 'version', 'pool_type'] if c in all_pools_for_ranking.columns]
        ranking_df = all_pools_for_ranking[base_cols + extra_cols].copy()
        
        # veBAL votes = votes_received in main data. Sum per pool in filtered period, then pct and rank
        vebal_votes_dict = {}
        vebal_pct_dict = {}
        vebal_rank_dict = {}
        vebal_col = 'vebal_votes' if 'vebal_votes' in df_bribes_display.columns else 'votes_received'
        if not df_bribes_display.empty and 'pool_symbol' in df_bribes_display.columns and vebal_col in df_bribes_display.columns:
            pool_vebal = df_bribes_display.groupby('pool_symbol')[vebal_col].sum()
            total_vebal = pool_vebal.sum()
            # Rank by total votes descending (1 = highest)
            pool_rank = pool_vebal.rank(method='min', ascending=False).astype(int)
            for pool_sym in pool_vebal.index:
                key = str(pool_sym).upper().strip()
                if key:
                    vebal_votes_dict[key] = pd.to_numeric(pool_vebal.loc[pool_sym], errors='coerce') if pd.notna(pool_vebal.loc[pool_sym]) else 0
                    vebal_pct_dict[key] = (vebal_votes_dict[key] / total_vebal) if total_vebal and total_vebal > 0 else 0
                    vebal_rank_dict[key] = int(pool_rank.loc[pool_sym]) if pool_sym in pool_rank.index else None
        
        # Match veBAL data: pool column is pool_symbol from pool_bribes
        def get_vebal_votes(row):
            pool_val = str(row['pool']).upper().strip()
            title_val = str(row.get('pool_title', '')).upper().strip()
            name_val = str(row.get('pool_name', '')).upper().strip()
            if pool_val in vebal_votes_dict:
                return vebal_votes_dict[pool_val]
            if title_val in vebal_votes_dict:
                return vebal_votes_dict[title_val]
            if name_val in vebal_votes_dict:
                return vebal_votes_dict[name_val]
            return 0
        
        def get_vebal_pct(row):
            pool_val = str(row['pool']).upper().strip()
            title_val = str(row.get('pool_title', '')).upper().strip()
            name_val = str(row.get('pool_name', '')).upper().strip()
            if pool_val in vebal_pct_dict:
                return vebal_pct_dict[pool_val]
            if title_val in vebal_pct_dict:
                return vebal_pct_dict[title_val]
            if name_val in vebal_pct_dict:
                return vebal_pct_dict[name_val]
            return 0
        
        def get_vebal_rank(row):
            pool_val = str(row['pool']).upper().strip()
            title_val = str(row.get('pool_title', '')).upper().strip()
            name_val = str(row.get('pool_name', '')).upper().strip()
            if pool_val in vebal_rank_dict:
                return vebal_rank_dict[pool_val]
            if title_val in vebal_rank_dict:
                return vebal_rank_dict[title_val]
            if name_val in vebal_rank_dict:
                return vebal_rank_dict[name_val]
            return None
        
        ranking_df['veBAL Votes'] = ranking_df.apply(get_vebal_votes, axis=1)
        ranking_df['Vote Share %'] = ranking_df.apply(get_vebal_pct, axis=1)
        ranking_df['Ranking'] = ranking_df.apply(get_vebal_rank, axis=1)
        
        # Sort by veBAL votes descending
        ranking_df = ranking_df.sort_values('veBAL Votes', ascending=False)
        
        if 'blockchain' in ranking_df.columns:
            ranking_df['balancer_url'] = ranking_df.apply(
                lambda row: utils.get_balancer_ui_url(
                    row['blockchain'],
                    row.get('project_contract_address') or row.get('gauge_address'),
                    row.get('version', None)
                ),
                axis=1
            )
        
        display_df = ranking_df.copy()

        if 'balancer_url' in display_df.columns:
            display_df['pool_display'] = display_df.apply(
                lambda row: f"{row['balancer_url']}?label={_safe_pool_label(row)}" if pd.notna(row.get('balancer_url')) and row['balancer_url'] else _safe_pool_label(row), 
                axis=1
            )
        else:
            display_df['pool_display'] = display_df.apply(_safe_pool_label, axis=1)

        if 'blockchain' in display_df.columns:
            display_df['chain_display'] = display_df['blockchain']

        # Address link (gauge_address) with short label - always Etherscan
        def _short_addr(val):
            s = str(val)
            if s.startswith("0x") and len(s) > 10:
                return f"{s[:4]}...{s[-4:]}"
            return s
        if 'gauge_address' in display_df.columns:
            display_df['address_display'] = display_df.apply(
                lambda row: f"https://etherscan.io/address/{row['gauge_address']}?label={_short_addr(row['gauge_address'])}"
                if pd.notna(row.get('gauge_address')) and str(row.get('gauge_address')).strip() != '' else "",
                axis=1
            )
        
        display_df['veBAL Votes'] = display_df['veBAL Votes'].apply(
            lambda x: f"{float(x):,.0f}" if pd.notna(x) and float(x) > 0 else "0"
        )
        display_df['Vote Share %'] = display_df['Vote Share %'].apply(
            lambda x: f"{float(x)*100:.2f}%" if pd.notna(x) and float(x) > 0 else "0.00%"
        )
        display_df['Ranking'] = display_df['Ranking'].apply(
            lambda x: f"#{int(x)}" if pd.notna(x) else "N/A"
        )
        
        final_cols = ['pool_display']
        final_names = ['Pool']
        
        if 'chain_display' in display_df.columns:
            final_cols.append('chain_display')
            final_names.append('Chain')
        if 'pool_type' in display_df.columns:
            final_cols.append('pool_type')
            final_names.append('Pool Type')
            
        if 'version_display' in display_df.columns:
            final_cols.append('version_display')
            final_names.append('Version')
        
        final_cols.extend(['veBAL Votes', 'Vote Share %', 'Ranking'])
        final_names.extend(['veBAL Votes', 'Vote Share %', 'Ranking'])
        
        if 'address_display' in display_df.columns:
            final_cols.append('address_display')
            final_names.append('Address')
        
        df_show = display_df[final_cols].copy()
        df_show.columns = final_names
        
        column_config = {}
        column_config['Pool'] = st.column_config.LinkColumn(
            'Pool', 
            width='medium',
            display_text=r"label=(.*)"
        )
        
        if 'Chain' in df_show.columns:
            column_config['Chain'] = st.column_config.TextColumn('Chain', width='small')
        if 'Pool Type' in df_show.columns:
            column_config['Pool Type'] = st.column_config.TextColumn('Pool Type', width='small')
            
        if 'Address' in df_show.columns:
            column_config['Address'] = st.column_config.LinkColumn(
                'Address', 
                width='small',
                display_text=r"label=(.*)"
            )
        
        st.dataframe(
            df_show, 
            use_container_width=True, 
            hide_index=True,
            column_config=column_config
        )
        
        # Removed Top Pools by veBAL Votes chart per request
    elif 'vebal_votes' in pool_bribes.columns:
        # Fallback: show from pool_bribes
        vebal_data = pool_bribes[pool_bribes['vebal_votes'].notna() & (pool_bribes['vebal_votes'] > 0)].copy()
        if not vebal_data.empty:
            top_vebal = vebal_data.nlargest(20, 'vebal_votes')[[pool_col, 'vebal_votes', 'vebal_pct_votes', 'vebal_ranking']].copy()
            top_vebal.columns = ['Pool', 'veBAL Votes', 'Vote Share %', 'Ranking']
            top_vebal['veBAL Votes'] = top_vebal['veBAL Votes'].apply(lambda x: f"{x:,.0f}")
            top_vebal['Vote Share %'] = top_vebal['Vote Share %'].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A")
            top_vebal['Ranking'] = top_vebal['Ranking'].apply(lambda x: f"#{int(x)}" if pd.notna(x) else "N/A")
            st.dataframe(top_vebal, use_container_width=True, hide_index=True)
            
            # Removed Top Pools by veBAL Votes chart per request
        else:
            st.info("No veBAL votes data available for the selected pools")
    else:
        st.info("veBAL votes data not available. Please ensure veBAL_votes.csv is in the data folder.")

st.markdown("---")

# Performance by Pool button (shown in all modes)
st.markdown("### 📊 Performance by Pool")

col_btn_perf, col_info = st.columns([1, 4])
with col_btn_perf:
    if st.button("🔍 Show Performance by Pool", key="btn_performance_by_pool"):
        st.session_state.show_performance_by_pool = not st.session_state.show_performance_by_pool
        st.rerun()

if st.session_state.show_performance_by_pool:
    if st.session_state.pool_filter_mode_bribes == 'top20':
        mode_label = "Top"
        category_pools = [str(p) for p in utils.get_top_pools(df, n=20) if pd.notna(p)]
    elif st.session_state.pool_filter_mode_bribes == 'worst20':
        mode_label = "Worst"
        category_pools = [str(p) for p in utils.get_worst_pools(df, n=20) if pd.notna(p)]
    else:
        mode_label = "All"
        if pool_match_col and not df_bribes_display.empty:
            category_pools = df_bribes_display[pool_match_col].unique().tolist()
            category_pools = [str(p) for p in category_pools if pd.notna(p)]
            
            # Sort pools by bribe amount (descending)
            if bribe_col in df_bribes_display.columns:
                pool_bribes_totals = df_bribes_display.groupby(pool_match_col)[bribe_col].sum().sort_values(ascending=False)
                category_pools_sorted = []
                # Add pools with bribes first (sorted by amount)
                for pool in pool_bribes_totals.index:
                    pool_str = str(pool)
                    if pool_str in category_pools:
                        category_pools_sorted.append(pool_str)
                # Add remaining pools (those with 0 or no bribe data)
                for pool in category_pools:
                    if pool not in category_pools_sorted:
                        category_pools_sorted.append(pool)
                category_pools = category_pools_sorted
        else:
            category_pools = []

    st.markdown(f"#### {mode_label} Pools - Individual Performance")

    csv_data = None
    
    # Pagination for "all" mode (when there are many pools)
    items_per_page = 10
    total_pools = len(category_pools)
    
    if st.session_state.pool_filter_mode_bribes == 'all' and total_pools > items_per_page:
        # Pagination controls
        total_pages = (total_pools + items_per_page - 1) // items_per_page
        
        pag_col1, pag_col2, pag_col3, pag_col4 = st.columns([0.2, 0.2, 0.2, 0.4])
        with pag_col1:
            if st.button("◀ Previous", disabled=(st.session_state.performance_page <= 1), key="prev_page_bribes"):
                st.session_state.performance_page = max(1, st.session_state.performance_page - 1)
                st.rerun()
        with pag_col2:
            if st.button("Next ▶", disabled=(st.session_state.performance_page >= total_pages), key="next_page_bribes"):
                st.session_state.performance_page = min(total_pages, st.session_state.performance_page + 1)
                st.rerun()
        with pag_col3:
            st.write(f"Page {st.session_state.performance_page} of {total_pages}")
        with pag_col4:
            st.write(f"Showing {((st.session_state.performance_page - 1) * items_per_page) + 1}-{min(st.session_state.performance_page * items_per_page, total_pools)} of {total_pools} pools")
        
        # Calculate pagination range
        start_idx = (st.session_state.performance_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        paginated_pools = category_pools[start_idx:end_idx]
    else:
        # No pagination needed for top20/worst20 or when there are few pools
        paginated_pools = category_pools
        if st.session_state.pool_filter_mode_bribes == 'all':
            st.info(f"Showing all {total_pools} pools")
    
    for pool in paginated_pools:
        pool_bribe_data = pd.DataFrame()
        # Use pool_bribes (aggregated by pool) for metrics
        if not pool_bribes.empty and pool_col in pool_bribes.columns:
            m = pool_bribes[pool_bribes[pool_col].astype(str).str.upper().str.strip() == pool.upper().strip()]
            if not m.empty:
                pool_bribe_data = m
        if pool_bribe_data.empty and not df_bribes_display.empty:
            for match_col in ['pool_symbol', 'pool_title', 'pool_name']:
                if match_col in df_bribes_display.columns:
                    matches = df_bribes_display[
                        df_bribes_display[match_col].astype(str).str.upper().str.strip() == pool.upper().strip()
                    ]
                    if not matches.empty and bribe_col in matches.columns:
                        agg = {bribe_col: 'sum'}
                        if votes_col and votes_col in matches.columns:
                            agg[votes_col] = 'sum'
                        for c in ['vebal_votes', 'vebal_pct_votes', 'vebal_ranking']:
                            if c in matches.columns:
                                agg[c] = 'mean' if c == 'vebal_pct_votes' else ('min' if c == 'vebal_ranking' else 'sum')
                        pool_bribe_data = matches.groupby(match_col).agg(agg).reset_index()
                        break
        if pool_bribe_data.empty and csv_data is not None and not csv_data.empty:
            csv_match = csv_data[
                csv_data['pool_symbol'].astype(str).str.upper().str.strip() == pool.upper().strip()
            ]
            if not csv_match.empty:
                # Create a minimal pool_bribe_data from CSV
                pool_bribe_data = csv_match.iloc[[0]].copy()
                # Map CSV columns to expected columns - prioritize bribe_amount_usd
                if 'bribe_amount_usd' in pool_bribe_data.columns:
                    pool_bribe_data[bribe_col] = pool_bribe_data['bribe_amount_usd']
                elif 'amount_usdc' in pool_bribe_data.columns:
                    pool_bribe_data[bribe_col] = pool_bribe_data['amount_usdc']
        
        # If still empty, try pool_bribes as fallback
        if pool_bribe_data.empty and not pool_bribes.empty and pool_col in pool_bribes.columns:
            pool_bribe_data = pool_bribes[
                pool_bribes[pool_col].astype(str).str.upper().str.strip() == pool.upper().strip()
            ]
        
        # Show pool data even if empty (to show all pools from category)
        with st.expander(f"📊 {pool}", expanded=False):
            if not pool_bribe_data.empty:
                col_p1, col_p2, col_p3 = st.columns(3)
                
                # Get values from pool_bribe_data
                pool_bribes_val = 0
                if bribe_col in pool_bribe_data.columns:
                    pool_bribes_val = pd.to_numeric(pool_bribe_data[bribe_col].iloc[0], errors='coerce') if pd.notna(pool_bribe_data[bribe_col].iloc[0]) else 0
                elif 'bribe_amount_usd' in pool_bribe_data.columns:
                    pool_bribes_val = pd.to_numeric(pool_bribe_data['bribe_amount_usd'].iloc[0], errors='coerce') if pd.notna(pool_bribe_data['bribe_amount_usd'].iloc[0]) else 0
                elif 'amount_usdc' in pool_bribe_data.columns:
                    pool_bribes_val = pd.to_numeric(pool_bribe_data['amount_usdc'].iloc[0], errors='coerce') if pd.notna(pool_bribe_data['amount_usdc'].iloc[0]) else 0
                
                pool_votes_val = pd.to_numeric(pool_bribe_data[votes_col].iloc[0], errors='coerce') if votes_col and votes_col in pool_bribe_data.columns and pd.notna(pool_bribe_data[votes_col].iloc[0]) else 0
                pool_vebal_votes = pd.to_numeric(pool_bribe_data['vebal_votes'].iloc[0], errors='coerce') if 'vebal_votes' in pool_bribe_data.columns and pd.notna(pool_bribe_data['vebal_votes'].iloc[0]) else 0
                pool_vebal_pct = pd.to_numeric(pool_bribe_data['vebal_pct_votes'].iloc[0], errors='coerce') if 'vebal_pct_votes' in pool_bribe_data.columns and pd.notna(pool_bribe_data['vebal_pct_votes'].iloc[0]) else 0
                pool_vebal_rank = pd.to_numeric(pool_bribe_data['vebal_ranking'].iloc[0], errors='coerce') if 'vebal_ranking' in pool_bribe_data.columns and pd.notna(pool_bribe_data['vebal_ranking'].iloc[0]) else None
                
                with col_p1:
                    st.metric("Total Bribes", f"${pool_bribes_val:,.0f}")
                with col_p2:
                    st.metric("Votes Received", f"{pool_votes_val:,.0f}")
                with col_p3:
                    if pool_vebal_votes > 0:
                        rank_text = f"#{int(pool_vebal_rank)}" if pool_vebal_rank else "N/A"
                        st.metric("veBAL Votes", f"{pool_vebal_votes:,.0f}", delta=f"{pool_vebal_pct*100:.2f}% share", help=f"Ranking: {rank_text}")
                    else:
                        st.metric("veBAL Votes", "N/A", help="No veBAL votes data available")
            else:
                # Show data from CSV if available, even if not in df_bribes_display
                if csv_data is not None and not csv_data.empty:
                    csv_match = csv_data[
                        csv_data['pool_symbol'].astype(str).str.upper().str.strip() == pool.upper().strip()
                    ]
                    if not csv_match.empty:
                        csv_row = csv_match.iloc[0]
                        col_p1, col_p2, col_p3 = st.columns(3)
                        
                        # Prioritize bribe_amount_usd, fallback to amount_usdc
                        pool_bribes_val = csv_row.get('bribe_amount_usd', csv_row.get('amount_usdc', 0))
                        pool_bribes_val = pd.to_numeric(pool_bribes_val, errors='coerce') if pd.notna(pool_bribes_val) else 0
                        
                        with col_p1:
                            st.metric("Total Bribes", f"${pool_bribes_val:,.0f}")
                        with col_p2:
                            st.metric("Votes Received", "N/A", help="No votes data available")
                        with col_p3:
                            st.metric("veBAL Votes", "N/A", help="No veBAL votes data available")
                    else:
                        st.info("No data available for this pool")
                else:
                    st.info("No data available for this pool")

st.markdown("---")

# Visualizations
st.markdown("### 📈 Visualizations")

# Single visualization: Bribes vs veBAL Votes (Dual-Axis Chart)
if 'vebal_votes' in pool_bribes.columns and bribe_col in pool_bribes.columns and not pool_bribes.empty:
        votes_data = pool_bribes[
            (pool_bribes[bribe_col] > 0) & 
            (pool_bribes['vebal_votes'].notna()) & 
            (pool_bribes['vebal_votes'] > 0)
        ].copy()
        if not votes_data.empty:
            # Ensure numeric values
            votes_data['vebal_votes'] = pd.to_numeric(votes_data['vebal_votes'], errors='coerce')
            votes_data = votes_data[votes_data['vebal_votes'].notna() & (votes_data['vebal_votes'] > 0)]
            if not votes_data.empty:
                # Sort by total_bribes_usd in descending order
                votes_data = votes_data.sort_values(bribe_col, ascending=False).reset_index(drop=True)
                
                # Get top pools for readability (top 20 or all if less than 20)
                display_data = votes_data.head(20) if len(votes_data) > 20 else votes_data
                
                # Create dual-axis chart
                fig = go.Figure()
                
                # Add bars for total_bribes_usd (Primary Y-axis, left)
                fig.add_trace(go.Bar(
                    x=display_data[pool_col],
                    y=display_data[bribe_col],
                    name='Total Bribes (USD)',
                    marker_color='#4a90e2',  # Professional blue
                    yaxis='y',
                    hovertemplate='<b>%{x}</b><br>Total Bribes: $%{y:,.0f}<extra></extra>',
                    text=display_data[bribe_col],
                    texttemplate='$%{text:,.0f}',
                    textposition='outside'
                ))
                
                # Add line with markers for vebal_votes (Secondary Y-axis, right)
                fig.add_trace(go.Scatter(
                    x=display_data[pool_col],
                    y=display_data['vebal_votes'],
                    mode='lines+markers',
                    name='veBAL Votes',
                    line=dict(color='#7b8a9a', width=3),
                    marker=dict(
                        size=8,
                        color='#7b8a9a',
                        line=dict(width=1, color='white')
                    ),
                    yaxis='y2',
                    hovertemplate='<b>%{x}</b><br>veBAL Votes: %{y:,.0f}<extra></extra>'
                ))
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    title=dict(text="📊 Bribes vs veBAL Votes: Dual-Axis Comparison", font=dict(color='white', size=18)),
                    xaxis=dict(
                        gridcolor='rgba(255,255,255,0.1)',
                        title='',
                        tickangle=-45,
                        showgrid=False
                    ),
                    yaxis=dict(
                        gridcolor='rgba(255,255,255,0.1)',
                        title=dict(text='Total Bribes (USD)', font=dict(color='#4a90e2')),
                        tickfont=dict(color='#4a90e2'),
                        side='left'
                    ),
                    yaxis2=dict(
                        title=dict(text='veBAL Votes', font=dict(color='#7b8a9a')),
                        overlaying='y',
                        side='right',
                        tickfont=dict(color='#7b8a9a'),
                        gridcolor='rgba(255,255,255,0.05)'
                    ),
                    height=600,
                    hovermode='x unified',
                    legend=dict(
                        bgcolor='rgba(0,0,0,0.5)',
                        font=dict(color='white'),
                        orientation='h',
                        yanchor='bottom',
                        y=1.02,
                        xanchor='right',
                        x=1
                    ),
                    barmode='group'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for votes visualization")
        else:
            st.info("No data available for votes visualization")
else:
    st.info("Votes data not available")

# Top pools bar chart
st.markdown("---")
st.markdown("#### 🏅 Top Pools by Total Bribes")
if bribe_col in pool_bribes.columns and not pool_bribes.empty:
    top_10 = pool_bribes.nlargest(10, bribe_col)
    fig_bar = px.bar(
        top_10,
        x=pool_col,
        y=bribe_col,
        title="Top Pools by Bribe Amount",
        labels={bribe_col: 'Total Bribes (USD)', pool_col: 'Pool'},
        color=bribe_col,
        color_continuous_scale='Viridis'
    )
    fig_bar.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title=dict(font=dict(color='white', size=16)),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Timeline if date column exists
date_col = None
for col in ['day', 'week_date', 'date', 'block_date', 'timestamp', 'week', 'period', 'time']:
    if col in df_bribes.columns:
        date_col = col
        break

if date_col:
    st.markdown("#### 📅 Bribe Timeline")
    if bribe_col in df_bribes_display.columns and not df_bribes_display.empty:
        # Ensure date column is properly formatted (clean any remaining time/UTC strings)
        timeline_data = df_bribes_display.copy()
        if date_col in timeline_data.columns:
            # Clean date strings if they're still strings
            if timeline_data[date_col].dtype == 'object':
                timeline_data[date_col] = timeline_data[date_col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\.\d+\s+UTC', '', regex=True)
                timeline_data[date_col] = timeline_data[date_col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\s+UTC', '', regex=True)
                timeline_data[date_col] = timeline_data[date_col].astype(str).str.replace(r'\s+UTC', '', regex=True)
                timeline_data[date_col] = timeline_data[date_col].astype(str).str.strip()
                timeline_data[date_col] = pd.to_datetime(timeline_data[date_col], errors='coerce')
            else:
                # Ensure it's datetime
                timeline_data[date_col] = pd.to_datetime(timeline_data[date_col], errors='coerce')
            
            # Remove rows with invalid dates
            timeline_data = timeline_data[timeline_data[date_col].notna()].copy()
            
            # Create month column for monthly grouping
            if not timeline_data.empty:
                timeline_data['year_month'] = timeline_data[date_col].dt.to_period('M').dt.to_timestamp()
        
        if not timeline_data.empty:
            # Aggregate by month (total, not by pool)
            timeline_agg = timeline_data.groupby('year_month')[bribe_col].sum().reset_index()
            fig_timeline = px.line(
                timeline_agg,
                x='year_month',
                y=bribe_col,
                title="💰 Total Bribes Over Time (Monthly)",
                labels={bribe_col: 'Total Bribes (USD)', 'year_month': 'Month'},
                markers=True
            )
            
            fig_timeline.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                title=dict(font=dict(color='white', size=16)),
                xaxis=dict(
                    gridcolor='rgba(255,255,255,0.1)',
                    tickfont=dict(size=9)  # Smaller font size for x-axis labels
                ),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                legend=dict(bgcolor='rgba(0,0,0,0.5)')
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("No valid date data available for timeline visualization")
