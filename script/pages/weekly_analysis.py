import streamlit as st
import utils
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Weekly Analysis", layout="wide", page_icon="📅")

# Check authentication
if not utils.check_authentication():
    st.stop()

utils.inject_css()

# Script para aplicar IDs específicos aos botões
import streamlit.components.v1 as components

components.html("""
<script>
console.log('[Button IDs] Script carregado via components.html (weekly_analysis.py)!');

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
                } else if (text === '%' || text === 'Absolute' || textLower === '%' || textLower === 'absolute') {
                    if (!button.id || button.id !== 'btn_toggle_percentage') {
                        button.id = 'btn_toggle_percentage';
                        button.classList.add('performance-button-fallback');
                        button.setAttribute('data-button-type', 'toggle');
                        
                        // Apply all inline styles directly (maximum priority)
                        const styles = {
                            'width': 'auto',
                            'min-width': '100px',
                            'max-width': '140px',
                            'height': '36px',
                            'padding': '0.5rem 1rem',
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
    st.error("❌ Unable to load data.")
    st.stop()

if 'pool_filter_mode_weekly' not in st.session_state:
    st.session_state.pool_filter_mode_weekly = 'all'  # Default: show all pools

if 'version_filter_weekly' not in st.session_state:
    st.session_state.version_filter_weekly = 'all'  # Default: show all versions

if 'gauge_filter_weekly' not in st.session_state:
    st.session_state.gauge_filter_weekly = 'all'  # Default: show all pools

# Version filter at the top of sidebar
utils.show_version_filter('version_filter_weekly')

# Gauge filter (Gauge / No Gauge)
utils.show_gauge_filter('gauge_filter_weekly')

# Pool filters at the top of sidebar (FIRST - before any other sidebar content)
utils.show_pool_filters('pool_filter_mode_weekly')

# Date filter: Year + Quarter (using dynamic filters)
df = utils.show_date_filter_sidebar(df, key_prefix="date_filter_weekly")

# Apply version filter
df = utils.apply_version_filter(df, 'version_filter_weekly')

# Apply gauge filter
df = utils.apply_gauge_filter(df, 'gauge_filter_weekly')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

# Don't run simulation sidebar - we use bal_emited_votes directly from data (same as emission_impact page)
df_sim = df.copy()

# Ensure block_date is datetime (needed for temporal charts)
if 'block_date' in df_sim.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_sim['block_date']):
        df_sim['block_date'] = pd.to_datetime(df_sim['block_date'], errors='coerce')

# Ensure we have bal_emited_votes (same column used in home page)
if 'bal_emited_votes' not in df_sim.columns:
    df_sim['bal_emited_votes'] = 0

st.sidebar.markdown("---")
st.sidebar.markdown("### 📉 Emission Reduction Scenario")

# Custom reduction percentage input (number input for direct value entry)
reduction_pct = st.sidebar.number_input(
    "BAL Emission Reduction (%)",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=5.0,
    help="Enter the percentage reduction in BAL emissions (e.g., 50 means 50% reduction, keeping 50% of emissions). Start with 0 for baseline."
)

reduction_factor = (100 - reduction_pct) / 100  # Convert to factor (50% reduction = 0.5 factor)

# Toggle for core pools only
core_only = st.sidebar.checkbox(
    "Allow emissions only for Core Pools",
    value=False,
    help="If enabled, only core pools will receive emissions. Non-core pools will have zero emissions."
)

# Page Header with logout button
col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">Weekly Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Weekly aggregation of emissions, votes, and distribution patterns</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

# Filter data based on mode
if st.session_state.pool_filter_mode_weekly == 'top20':
    # Get top 20 pools
    top_pools = utils.get_top_pools(df, n=20)
    top_pools_list = [str(p) for p in top_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(top_pools_list)].copy()
elif st.session_state.pool_filter_mode_weekly == 'worst20':
    # Get worst 20 pools
    worst_pools = utils.get_worst_pools(df, n=20)
    worst_pools_list = [str(p) for p in worst_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(worst_pools_list)].copy()
else:
    # 'all' mode - show everything
    df_display = df_sim.copy()

if 'pool_category' not in df_display.columns:
    df_display['pool_category'] = 'Undefined'
else:
    df_display['pool_category'] = df_display['pool_category'].fillna('Undefined').astype(str)
if 'direct_incentives' not in df_display.columns:
    df_display['direct_incentives'] = 0.0

# Ensure block_date is datetime before using .dt accessor
if 'block_date' in df_display.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_display['block_date']):
        df_display['block_date'] = pd.to_datetime(df_display['block_date'], errors='coerce')

# Apply emission reduction scenario (same as emission_impact page)
df_scenario = utils.calculate_emission_reduction_impact(df_display, reduction_factor, core_only=core_only)

df_scenario['week'] = df_scenario['block_date'].dt.to_period('W').dt.start_time

df_weekly = df_scenario.groupby(['week', 'pool_category']).agg({
    'reduced_bal_emitted': 'sum' if 'reduced_bal_emitted' in df_scenario.columns else 'bal_emited_votes',
    'reduced_incentives': 'sum' if 'reduced_incentives' in df_scenario.columns else 'direct_incentives',
    'votes_received': 'sum' if 'votes_received' in df_scenario.columns else 0,
    'protocol_fee_amount_usd': 'sum',
    'dao_profit_usd': 'sum'
}).reset_index()

# Rename columns for consistency
if 'reduced_bal_emitted' in df_weekly.columns:
    df_weekly['bal_emited_votes'] = df_weekly['reduced_bal_emitted']
    df_weekly = df_weekly.drop(columns=['reduced_bal_emitted'])
if 'reduced_incentives' in df_weekly.columns:
    df_weekly['direct_incentives'] = df_weekly['reduced_incentives']
    df_weekly = df_weekly.drop(columns=['reduced_incentives'])

weekly_totals = df_weekly.groupby('week').agg({
    'bal_emited_votes': 'sum',
    'direct_incentives': 'sum'
}).reset_index()

df_weekly = df_weekly.merge(
    weekly_totals,
    on='week',
    suffixes=('', '_total')
)

df_weekly['pct_of_weekly_emissions'] = np.where(
    df_weekly['bal_emited_votes_total'] > 0,
    (df_weekly['bal_emited_votes'] / df_weekly['bal_emited_votes_total'] * 100).round(2),
    0
)

st.markdown("### 📊 Weekly Summary")

summary_stats = df_weekly.groupby('pool_category').agg({
    'bal_emited_votes': 'sum',
    'direct_incentives': 'sum',
    'week': 'nunique'
}).round(2)

summary_stats.columns = ['Total BAL Emitted', 'Total USD Value', 'Weeks Active']

# Format monetary column for display
summary_stats_display = summary_stats.copy()
if 'Total USD Value' in summary_stats_display.columns:
    summary_stats_display['Total USD Value'] = summary_stats_display['Total USD Value'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")

st.dataframe(summary_stats_display, use_container_width=True, hide_index=False)

st.markdown("---")

st.markdown("### 📈 Weekly Trends")

pivot_weekly = df_weekly.pivot(index='week', columns='pool_category', values='bal_emited_votes').fillna(0)
pivot_weekly_incentives = df_weekly.pivot(index='week', columns='pool_category', values='direct_incentives').fillna(0)

colors = {'Legitimate': '#2ecc71', 'Sustainable': '#3498db', 'Mercenary': '#e74c3c', 'Undefined': '#95a5a6'}

# Initialize session state for toggles
if 'show_weekly_bal_percentage' not in st.session_state:
    st.session_state.show_weekly_bal_percentage = False
if 'show_weekly_incentives_percentage' not in st.session_state:
    st.session_state.show_weekly_incentives_percentage = False

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # Toggle for percentage view
    col_toggle1, _ = st.columns([1, 10])
    with col_toggle1:
        toggle_text1 = "%" if not st.session_state.show_weekly_bal_percentage else "Absolute"
        if st.button(toggle_text1, key="toggle_weekly_bal_percentage"):
            st.session_state.show_weekly_bal_percentage = not st.session_state.show_weekly_bal_percentage
            st.rerun()
    
    chart_title1 = "**Weekly BAL Emissions by Category**" if not st.session_state.show_weekly_bal_percentage else "**Weekly BAL Emissions by Category (%)**"
    st.markdown(chart_title1)
    
    # Calculate percentages if toggle is on
    if st.session_state.show_weekly_bal_percentage:
        row_sums = pivot_weekly.sum(axis=1)
        pivot_weekly_pct = pivot_weekly.div(row_sums.replace(0, 1), axis=0) * 100
        pivot_weekly_pct.loc[row_sums == 0] = 0
        data_to_plot1 = pivot_weekly_pct
        yaxis_title1 = "Percentage (%)"
        hovertemplate_suffix1 = "%"
    else:
        data_to_plot1 = pivot_weekly
        yaxis_title1 = ""
        hovertemplate_suffix1 = " BAL"
    
    fig1 = go.Figure()
    
    for category in data_to_plot1.columns:
        fig1.add_trace(go.Scatter(
            x=data_to_plot1.index,
            y=data_to_plot1[category],
            mode='lines',
            name=category,
            line=dict(color=colors.get(category, '#3498db'), width=1.5),
            stackgroup='one',
            hovertemplate=f'<b>{category}</b><br>%{{x|%b %d, %Y}}<br>%{{y:,.2f}}{hovertemplate_suffix1}<extra></extra>'
        ))
    
    fig1.update_layout(
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
            title=yaxis_title1,
            tickfont=dict(size=11, color='#8B95A6'),
            tickformat='.2f' if st.session_state.show_weekly_bal_percentage else ',.0f',
            ticksuffix='%' if st.session_state.show_weekly_bal_percentage else ''
        ),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.05,
            xanchor="left",
            x=0,
            font=dict(size=11, color='#8B95A6')
        )
    )
    
    st.plotly_chart(fig1, use_container_width=True, key="weekly_bal_emissions")

with col_chart2:
    # Toggle for percentage view
    col_toggle2, _ = st.columns([1, 10])
    with col_toggle2:
        toggle_text2 = "%" if not st.session_state.show_weekly_incentives_percentage else "Absolute"
        if st.button(toggle_text2, key="toggle_weekly_incentives_percentage"):
            st.session_state.show_weekly_incentives_percentage = not st.session_state.show_weekly_incentives_percentage
            st.rerun()
    
    chart_title2 = "**Weekly Incentives Distribution (USD)**" if not st.session_state.show_weekly_incentives_percentage else "**Weekly Incentives Distribution (%)**"
    st.markdown(chart_title2)
    
    # Calculate percentages if toggle is on
    if st.session_state.show_weekly_incentives_percentage:
        row_sums = pivot_weekly_incentives.sum(axis=1)
        pivot_weekly_incentives_pct = pivot_weekly_incentives.div(row_sums.replace(0, 1), axis=0) * 100
        pivot_weekly_incentives_pct.loc[row_sums == 0] = 0
        data_to_plot2 = pivot_weekly_incentives_pct
        yaxis_title2 = "Percentage (%)"
        hovertemplate_suffix2 = "%"
    else:
        data_to_plot2 = pivot_weekly_incentives
        yaxis_title2 = ""
        hovertemplate_suffix2 = " USD"
    
    fig2 = go.Figure()
    
    for category in data_to_plot2.columns:
        fig2.add_trace(go.Scatter(
            x=data_to_plot2.index,
            y=data_to_plot2[category],
            mode='lines',
            name=category,
            line=dict(color=colors.get(category, '#3498db'), width=1.5),
            stackgroup='one',
            hovertemplate=f'<b>{category}</b><br>%{{x|%b %d, %Y}}<br>%{{y:,.2f}}{hovertemplate_suffix2}<extra></extra>'
        ))
    
    fig2.update_layout(
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
            title=yaxis_title2,
            tickfont=dict(size=11, color='#8B95A6'),
            tickformat='.2f' if st.session_state.show_weekly_incentives_percentage else ',.0f',
            ticksuffix='%' if st.session_state.show_weekly_incentives_percentage else ''
        ),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.05,
            xanchor="left",
            x=0,
            font=dict(size=11, color='#8B95A6')
        )
    )
    
    st.plotly_chart(fig2, use_container_width=True, key="weekly_incentives")

# Show individual pool analysis only when Top 20 or Worst 20 filter is active
if st.session_state.pool_filter_mode_weekly in ['top20', 'worst20']:
    filtered_pools = sorted(df_display['pool_symbol'].unique())
    
    if len(filtered_pools) > 0:
        st.markdown("---")
        st.markdown("### 📋 Pools Weekly Analysis")
        
        for idx, pool in enumerate(filtered_pools):
            pool_weekly = df_weekly[df_weekly['week'].isin(
                df_display[df_display['pool_symbol'] == pool]['week'].unique()
            )]
        
        if len(pool_weekly) > 0:
            with st.expander(f"{pool}"):
                pool_weekly_summary = pool_weekly.groupby('week').agg({
                    'bal_emited_votes': 'sum',
                    'direct_incentives': 'sum'
                }).reset_index()
                
                fig_pool = utils.create_minimalist_chart(
                    pool_weekly_summary['week'],
                    pool_weekly_summary['bal_emited_votes'],
                    'BAL Emitted',
                    '#67A2E1',
                    height=300
                )
                st.plotly_chart(fig_pool, use_container_width=True, key=f"weekly_pool_{idx}_{hash(pool)}")

st.markdown("---")

st.markdown("### 📋 Weekly Distribution Table")

display_columns = ['week', 'pool_category', 'bal_emited_votes', 'direct_incentives', 'pct_of_weekly_emissions']
df_display_table = df_weekly[display_columns].copy()
df_display_table.columns = ['Week', 'Category', 'BAL Emitted', 'Incentives (USD)', '% of Weekly Emissions']
df_display_table = df_display_table.sort_values(['Week', 'Category'])

# Format monetary and percentage columns
if 'Incentives (USD)' in df_display_table.columns:
    df_display_table['Incentives (USD)'] = df_display_table['Incentives (USD)'].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
if '% of Weekly Emissions' in df_display_table.columns:
    df_display_table['% of Weekly Emissions'] = df_display_table['% of Weekly Emissions'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

st.dataframe(df_display_table, use_container_width=True, hide_index=True)
