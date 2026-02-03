import streamlit as st
import utils
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Balancer Tokenomics Analysis",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check authentication
if not utils.check_authentication():
    st.stop()

utils.inject_css()

# Script para aplicar IDs específicos aos botões
import streamlit.components.v1 as components

components.html("""
<script>
console.log('[Button IDs] Script carregado via components.html (home.py)!');

function applyButtonIds() {
    const contexts = [
        { doc: document, name: 'document' },
        { doc: window.parent?.document, name: 'parent' },
        { doc: window.top?.document, name: 'top' }
    ];
    
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
                
                // Aplica IDs que começam com os prefixos corretos
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
                }
            });
        } catch(e) {
            console.error(`[Button IDs] Erro no contexto ${name}:`, e);
        }
    });
}

// Executa imediatamente e após delays
applyButtonIds();
setTimeout(applyButtonIds, 100);
setTimeout(applyButtonIds, 500);
setTimeout(applyButtonIds, 1000);
setInterval(applyButtonIds, 2000);

// Observa mudanças no DOM
if (window.MutationObserver) {
    const observer = new MutationObserver(() => {
        setTimeout(applyButtonIds, 100);
    });
    
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    }
}
</script>
""", height=0)

df = utils.load_data()
if df.empty:
    st.stop()

# Initialize session state - default to 'all' (show everything)
if 'pool_filter_mode' not in st.session_state:
    st.session_state.pool_filter_mode = 'all'  # Default: show all pools

if 'version_filter_home' not in st.session_state:
    st.session_state.version_filter_home = 'all'  # Default: show all versions

if 'gauge_filter_home' not in st.session_state:
    st.session_state.gauge_filter_home = 'all'  # Default: show all pools

# Version filter at the top of sidebar
utils.show_version_filter('version_filter_home')

# Gauge filter (with gauge / without gauge)
utils.show_gauge_filter('gauge_filter_home')

# Pool filters at the top of sidebar (FIRST - before any other sidebar content)
utils.show_pool_filters('pool_filter_mode')

# Date filter: Year + Quarter (using dynamic filters)
df = utils.show_date_filter_sidebar(df, key_prefix="date_filter_home")

# Apply version filter
df = utils.apply_version_filter(df, 'version_filter_home')

# Apply gauge filter
df = utils.apply_gauge_filter(df, 'gauge_filter_home')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")
    df_sim = df.copy()
    # Ensure simulation columns exist even when df is empty
    if 'sim_dao_revenue' not in df_sim.columns:
        df_sim['sim_dao_revenue'] = 0.0
    if 'sim_holders_revenue' not in df_sim.columns:
        df_sim['sim_holders_revenue'] = 0.0
    if 'sim_incentives_revenue' not in df_sim.columns:
        df_sim['sim_incentives_revenue'] = 0.0
    if 'sim_bal_emitted' not in df_sim.columns:
        df_sim['sim_bal_emitted'] = 0.0
else:
    df_sim = utils.run_simulation_sidebar(df)

# Header with logout button
col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">Balancer Tokenomics Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Historical analysis with simulation controls</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

# Filter data based on mode
if st.session_state.pool_filter_mode == 'top20':
    # Get top 20 pools
    top_pools = utils.get_top_pools(df, n=20)
    top_pools_list = [str(p) for p in top_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(top_pools_list)].copy()
    st.info(f"📊 Showing analysis for Top 20 Pools ({len(top_pools_list)} pools)")
elif st.session_state.pool_filter_mode == 'worst20':
    # Get worst 20 pools
    worst_pools = utils.get_worst_pools(df, n=20)
    worst_pools_list = [str(p) for p in worst_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(worst_pools_list)].copy()
    st.info(f"📊 Showing analysis for Worst 20 Pools ({len(worst_pools_list)} pools)")
else:
    # 'all' mode - show everything
    df_display = df_sim.copy()
    total_pools = len(df_sim['pool_symbol'].unique()) if 'pool_symbol' in df_sim.columns else 0
    st.info(f"📊 Showing analysis for all pools ({total_pools} pools)")

total_revenue = df_display['sim_dao_revenue'].sum() + df_display['sim_holders_revenue'].sum() + df_display['sim_incentives_revenue'].sum()
total_dao = df_display['sim_dao_revenue'].sum()
total_holders = df_display['sim_holders_revenue'].sum()
total_incentives = df_display['sim_incentives_revenue'].sum()
# Use simulated BAL from sidebar slider (BAL Emitted per Week × vote share); fallback to raw data when no simulation
total_bal_emitted = df_display['sim_bal_emitted'].sum() if 'sim_bal_emitted' in df_display.columns else df_display['bal_emited_votes'].sum()

col1, col2, col3, col4 = st.columns(4)

num_weeks = df_display.attrs.get("num_weeks")

help_dao = (
    "Revenue allocated to the DAO from protocol fees.\n\n"
    "**How it is calculated:**\n"
    "1. Remaining revenue = Total protocol fee − (Protocol fee % from sidebar)\n"
    "2. Per pool: DAO Share % (sidebar) × remaining revenue — Non-Core and Core have distinct %\n"
    "3. Sum over all pools\n"
    "4. Multiply by emission factor: (1 − Decrease %) × (1 + Increase %)"
)
help_holders = (
    "Revenue allocated to veBAL Holders.\n\n"
    "**How it is calculated:**\n"
    "1. Remaining revenue = Total protocol fee − (Protocol fee % from sidebar)\n"
    "2. Per pool: Holders Share % (sidebar) × remaining revenue\n"
    "3. Sum over all pools\n"
    "4. Multiply by emission factor: (1 − Decrease %) × (1 + Increase %)"
)
help_incentives = (
    "Revenue allocated to incentives/bribes (Core pools only).\n\n"
    "**How it is calculated:**\n"
    "1. Remaining revenue = Total protocol fee − (Protocol fee % from sidebar)\n"
    "2. Per Core pool: Incentives/Bribes % (sidebar) × remaining revenue\n"
    "3. Sum over all pools\n"
    "4. Multiply by emission factor: (1 − Decrease %) × (1 + Increase %)"
)
help_bal = (
    "Total BAL emitted in the period (simulated and scaled).\n\n"
    "**How it is calculated:**\n"
    "1. Base BAL/week = Total BAL in period data ÷ number of weeks"
    + (f" ({num_weeks:.0f} wk)" if num_weeks is not None else "")
    + "\n"
    "2. Factor = (1 − Decrease %) × (1 + Increase %)\n"
    "3. Distribution per pool by vote_share (votes_received)\n"
    "4. Total = sum of sim_bal_emitted (scaled to match raw sum × factor)"
)

with col1:
    st.metric("DAO Revenue", f"${total_dao:,.0f}", help=help_dao)

with col2:
    st.metric("Holders Revenue", f"${total_holders:,.0f}", help=help_holders)

with col3:
    st.metric("Incentives Revenue", f"${total_incentives:,.0f}", help=help_incentives)

with col4:
    st.metric("Total BAL Emitted", f"{total_bal_emitted:,.0f}", help=help_bal)

st.markdown("---")

st.markdown("### 📈 Revenue Distribution Over Time")

# Check if required columns exist and if we have data
if df_display.empty or 'block_date' not in df_display.columns:
    st.warning("No data available for charts.")
else:
    # Ensure simulation columns exist
    required_cols = ['sim_dao_revenue', 'sim_holders_revenue', 'sim_incentives_revenue']
    for col in required_cols:
        if col not in df_display.columns:
            df_display[col] = 0.0
    
    # Fill NaN values with 0 before aggregation
    df_display['sim_dao_revenue'] = df_display['sim_dao_revenue'].fillna(0)
    df_display['sim_holders_revenue'] = df_display['sim_holders_revenue'].fillna(0)
    df_display['sim_incentives_revenue'] = df_display['sim_incentives_revenue'].fillna(0)
    
    # Ensure block_date is datetime and normalized
    if 'block_date' in df_display.columns:
        if not pd.api.types.is_datetime64_any_dtype(df_display['block_date']):
            df_display['block_date'] = pd.to_datetime(df_display['block_date'], format='mixed', utc=True, errors='coerce')
            df_display['block_date'] = pd.to_datetime(df_display['block_date']).dt.normalize()
        else:
            df_display['block_date'] = pd.to_datetime(df_display['block_date']).dt.normalize()
    
    # Filter rows with valid block_date and group by month
    df_with_block_date = df_display[df_display['block_date'].notna()].copy()
    
    if len(df_with_block_date) > 0:
        # Create month column for grouping
        df_with_block_date['year_month'] = df_with_block_date['block_date'].dt.to_period('M').dt.to_timestamp()
        
        # Group by month
        df_monthly = df_with_block_date.groupby('year_month').agg({
            'sim_dao_revenue': 'sum',
            'sim_holders_revenue': 'sum',
            'sim_incentives_revenue': 'sum'
        }).reset_index()
        
        # Check if we have any data after grouping
        if df_monthly.empty or (df_monthly['sim_dao_revenue'].sum() == 0 and df_monthly['sim_holders_revenue'].sum() == 0 and df_monthly['sim_incentives_revenue'].sum() == 0):
            st.info("No revenue data available for the selected period.")
        else:
            col_chart1, col_chart2, col_chart3 = st.columns(3)

            with col_chart1:
                st.markdown("**DAO Revenue**")
                fig_dao = go.Figure()
                fig_dao.add_trace(go.Bar(
                    x=df_monthly['year_month'],
                    y=df_monthly['sim_dao_revenue'],
                    name='DAO',
                    marker_color='#67A2E1'
                ))
                fig_dao.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=350,
                    margin=dict(l=40, r=20, t=20, b=40),
                    xaxis=dict(
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(255,255,255,0.1)',
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.05)',
                        showline=False,
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    hovermode='x unified',
                    showlegend=False
                )
                st.plotly_chart(fig_dao, use_container_width=True, key="dao_revenue")

            with col_chart2:
                st.markdown("**Holders Revenue**")
                fig_holders = go.Figure()
                fig_holders.add_trace(go.Bar(
                    x=df_monthly['year_month'],
                    y=df_monthly['sim_holders_revenue'],
                    name='Holders',
                    marker_color='#E9A97B'
                ))
                fig_holders.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=350,
                    margin=dict(l=40, r=20, t=20, b=40),
                    xaxis=dict(
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(255,255,255,0.1)',
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.05)',
                        showline=False,
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    hovermode='x unified',
                    showlegend=False
                )
                st.plotly_chart(fig_holders, use_container_width=True, key="holders_revenue")

            with col_chart3:
                st.markdown("**Incentives Revenue**")
                fig_incentives = go.Figure()
                fig_incentives.add_trace(go.Bar(
                    x=df_monthly['year_month'],
                    y=df_monthly['sim_incentives_revenue'],
                    name='Incentives',
                    marker_color='#B1ACF1'
                ))
                fig_incentives.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=350,
                    margin=dict(l=40, r=20, t=20, b=40),
                    xaxis=dict(
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(255,255,255,0.1)',
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(255,255,255,0.05)',
                        showline=False,
                        title="",
                        tickfont=dict(size=10, color='#8B95A6')
                    ),
                    hovermode='x unified',
                    showlegend=False
                )
                st.plotly_chart(fig_incentives, use_container_width=True, key="incentives_revenue")

st.markdown("---")

st.markdown("### 📊 Comparison")

# Group data by month for monthly comparison
if df_display.empty or 'block_date' not in df_display.columns:
    st.warning("No data available for comparison chart.")
else:
    # Ensure simulation columns exist
    required_cols = ['sim_dao_revenue', 'sim_holders_revenue']
    for col in required_cols:
        if col not in df_display.columns:
            df_display[col] = 0.0
    
    # Fill NaN values with 0
    df_display['sim_dao_revenue'] = df_display['sim_dao_revenue'].fillna(0)
    df_display['sim_holders_revenue'] = df_display['sim_holders_revenue'].fillna(0)
    
    # Ensure block_date is datetime
    if 'block_date' in df_display.columns:
        if not pd.api.types.is_datetime64_any_dtype(df_display['block_date']):
            df_display['block_date'] = pd.to_datetime(df_display['block_date'], format='mixed', utc=True, errors='coerce')
            df_display['block_date'] = pd.to_datetime(df_display['block_date']).dt.normalize()
        else:
            df_display['block_date'] = pd.to_datetime(df_display['block_date']).dt.normalize()
    
    # Filter rows with valid block_date
    df_with_dates = df_display[df_display['block_date'].notna()].copy()
    
    if len(df_with_dates) > 0:
        # Create month column for grouping
        df_with_dates['year_month'] = df_with_dates['block_date'].dt.to_period('M').dt.to_timestamp()
        
        # Group by month
        df_monthly = df_with_dates.groupby('year_month').agg({
            'sim_dao_revenue': 'sum',
            'sim_holders_revenue': 'sum'
        }).reset_index()
        
        # Check if we have data
        if df_monthly.empty or (df_monthly['sim_dao_revenue'].sum() == 0 and df_monthly['sim_holders_revenue'].sum() == 0):
            st.info("No revenue data available for comparison.")
        else:
            # Create comparison bar chart
            fig_comparison = go.Figure()
            
            # Add DAO Revenue bars
            fig_comparison.add_trace(go.Bar(
                x=df_monthly['year_month'],
                y=df_monthly['sim_dao_revenue'],
                name='DAO Revenue',
                marker_color='#67A2E1'
            ))
            
            # Add Holders (veBAL) Revenue bars
            fig_comparison.add_trace(go.Bar(
                x=df_monthly['year_month'],
                y=df_monthly['sim_holders_revenue'],
                name='veBAL Revenue',
                marker_color='#E9A97B'
            ))
            
            fig_comparison.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                margin=dict(l=40, r=20, t=20, b=40),
                xaxis=dict(
                    showgrid=False,
                    showline=True,
                    linecolor='rgba(255,255,255,0.1)',
                    title="",
                    tickfont=dict(size=11, color='#8B95A6')
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='rgba(255,255,255,0.05)',
                    showline=False,
                    title="",
                    tickfont=dict(size=11, color='#8B95A6')
                ),
                hovermode='x unified',
                barmode='group',  # Grouped bars for comparison
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=1.05,
                    xanchor="left",
                    x=0,
                    font=dict(size=11, color='#8B95A6')
                )
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True, key="revenue_comparison")
    else:
        st.info("No data with valid dates available for comparison.")

st.markdown("---")

# Show detailed analysis when filtering by Top 20 or Worst 20
if st.session_state.pool_filter_mode in ['top20', 'worst20']:
    st.markdown("---")
    st.markdown("### 📋 Pools Detailed Analysis")
    
    pool_summary = df_display.groupby('pool_symbol').agg({
        'sim_dao_revenue': 'sum',
        'sim_holders_revenue': 'sum',
        'sim_incentives_revenue': 'sum',
        'sim_bal_emitted': 'sum',
        'protocol_fee_amount_usd': 'sum',
        'direct_incentives': 'sum',
        'dao_profit_usd': 'sum',
        'pool_category': 'first'
    }).round(2)
    
    pool_summary.columns = ['DAO Revenue', 'Holders Revenue', 'Incentives Revenue', 'BAL Emitted', 'Total Revenue', 'Total Incentives', 'DAO Profit', 'Category']
    
    # Format monetary columns for display
    pool_summary_display = pool_summary.copy()
    monetary_cols = ['DAO Revenue', 'Holders Revenue', 'Incentives Revenue', 'Total Revenue', 'Total Incentives', 'DAO Profit']
    for col in monetary_cols:
        if col in pool_summary_display.columns:
            pool_summary_display[col] = pool_summary_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
    
    st.dataframe(pool_summary_display, use_container_width=True, hide_index=False)
    
    st.markdown("---")
    st.markdown("### 📊 Individual Pool Analysis")
    
    # Get list of pools from filtered data
    filtered_pools = sorted(df_display['pool_symbol'].unique().tolist())
    
    for idx, pool in enumerate(filtered_pools):
        pool_data = df_display[df_display['pool_symbol'] == pool]
        if len(pool_data) > 0:
            category = pool_data['pool_category'].iloc[0] if 'pool_category' in pool_data.columns else 'Unknown'
            
            with st.expander(f"🔍 {pool} ({category})", expanded=False):
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                
                with col_p1:
                    st.metric("Total Revenue", f"${pool_data['protocol_fee_amount_usd'].sum():,.0f}")
                with col_p2:
                    st.metric("DAO Revenue", f"${pool_data['sim_dao_revenue'].sum():,.0f}")
                with col_p3:
                    st.metric("Holders Revenue", f"${pool_data['sim_holders_revenue'].sum():,.0f}")
                with col_p4:
                    st.metric("Incentives Revenue", f"${pool_data['sim_incentives_revenue'].sum():,.0f}")
                
                col_p5, col_p6, col_p7 = st.columns(3)
                with col_p5:
                    bal_emitted = pool_data['sim_bal_emitted'].sum() if 'sim_bal_emitted' in pool_data.columns else pool_data['bal_emited_votes'].sum()
                    st.metric("BAL Emitted", f"{bal_emitted:,.0f}")
                with col_p6:
                    st.metric("Total Incentives", f"${pool_data['direct_incentives'].sum():,.0f}")
                with col_p7:
                    st.metric("DAO Profit", f"${pool_data['dao_profit_usd'].sum():,.0f}")
