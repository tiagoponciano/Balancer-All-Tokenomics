import streamlit as st
import utils
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Emission Impact Analysis", layout="wide", page_icon="📉")

# Check authentication
if not utils.check_authentication():
    st.stop()

utils.inject_css()

# Script para aplicar IDs específicos aos botões
import streamlit.components.v1 as components

components.html("""
<script>
console.log('[Button IDs] Script carregado via components.html (emission_impact.py)!');

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
                            'min-width': '80px',
                            'max-width': '120px',
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

# Initialize session state - default to 'all' (show everything)
if 'pool_filter_mode_emission' not in st.session_state:
    st.session_state.pool_filter_mode_emission = 'all'  # Default: show all pools
if 'version_filter_emission' not in st.session_state:
    st.session_state.version_filter_emission = 'all'  # Default: show all versions
if 'gauge_filter_emission' not in st.session_state:
    st.session_state.gauge_filter_emission = 'all'  # Default: show all pools
if 'show_core_percentage' not in st.session_state:
    st.session_state.show_core_percentage = False  # Default: show absolute values
if 'show_legit_mercenary_percentage' not in st.session_state:
    st.session_state.show_legit_mercenary_percentage = False  # Default: show absolute values

# Version filter at the top of sidebar
utils.show_version_filter('version_filter_emission')

# Gauge filter (Gauge / No Gauge)
utils.show_gauge_filter('gauge_filter_emission')

# Pool filters at the top of sidebar (FIRST - before any other sidebar content)
utils.show_pool_filters('pool_filter_mode_emission')

# Date filter: Year + Quarter (using dynamic filters)
df = utils.show_date_filter_sidebar(df, key_prefix="date_filter_emission")

# Apply version filter
df = utils.apply_version_filter(df, 'version_filter_emission')

# Apply gauge filter
df = utils.apply_gauge_filter(df, 'gauge_filter_emission')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

# Don't run simulation sidebar - we use bal_emited_votes directly from data (same as home page)
# This page focuses on emission reduction scenarios, not revenue distribution simulation
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
    st.markdown('<div class="page-title">Emission Reduction Impact Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Simulate emission reduction scenarios and analyze impact on legitimate vs mercenary pools</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

# Explanation section at the beginning
st.markdown("### 📖 Understanding Pool Classification")

with st.expander("ℹ️ What are Legitimate, Sustainable, Mercenary and Undefined Pools?", expanded=False):
    st.markdown("""
    **Legitimate Pools:**
    - Top pools: high DAO profit (>$5k), ROI > 1.5x, low incentive dependency (<50%), or core pools with ROI > 1.2x
    - No incentives: revenue > $15k
    
    **Sustainable Pools:**
    - Positive but not elite: DAO profit ≥ 0, aggregate ROI ≥ 1.0
    - No incentives: revenue > 0 but ≤ $15k
    
    **Mercenary Pools:**
    - Zero revenue, or ROI < 0.5, or negative DAO profit, or incentive dependency > 80%, or revenue < $5k
    
    **Undefined Pools:**
    - Don't clearly fit other categories (e.g. no incentives and no revenue)
    
    **Core Pools:** Designated as "core" by the protocol; may receive priority in emissions.
    """)

st.markdown("---")

# Filter data based on mode
if st.session_state.pool_filter_mode_emission == 'top20':
    # Get top 20 pools
    top_pools = utils.get_top_pools(df, n=20)
    top_pools_list = [str(p) for p in top_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(top_pools_list)].copy()
elif st.session_state.pool_filter_mode_emission == 'worst20':
    # Get worst 20 pools
    worst_pools = utils.get_worst_pools(df, n=20)
    worst_pools_list = [str(p) for p in worst_pools]
    df_display = df_sim[df_sim['pool_symbol'].isin(worst_pools_list)].copy()
else:
    # 'all' mode - show everything
    df_display = df_sim.copy()

# When "Allow emissions only for Core Pools" is on, filter the entire page to core pools only
if core_only and 'is_core_pool' in df_display.columns:
    core_mask = pd.to_numeric(df_display['is_core_pool'], errors='coerce').fillna(0).astype(int) == 1
    df_display = df_display.loc[core_mask].copy()
    if df_display.empty:
        st.warning("No core pools in the selected filters. Adjust filters or turn off «Allow emissions only for Core Pools».")
        st.stop()

# Apply scenario (reduction % + core-only) so emission sections reflect the filters
df_scenario = utils.calculate_emission_reduction_impact(df_display, reduction_factor, core_only=core_only)
# Column to use for emissions in breakdowns: scenario (reduced + core-only) so filters are visible
bal_col = 'reduced_bal_emitted' if 'reduced_bal_emitted' in df_scenario.columns else 'bal_emited_votes'
df_emissions = df_scenario.copy()
df_emissions[bal_col] = df_scenario['reduced_bal_emitted'] if 'reduced_bal_emitted' in df_scenario.columns else df_scenario['bal_emited_votes']

# Ensure pool_category exists and has no NaN (groupby with NaN index breaks metric lookup)
if 'pool_category' not in df_emissions.columns:
    df_emissions['pool_category'] = 'Undefined'
else:
    df_emissions['pool_category'] = (
        df_emissions['pool_category'].astype(str).str.strip().replace('', 'Undefined').replace('nan', 'Undefined')
    )
df_emissions['pool_category'] = df_emissions['pool_category'].fillna('Undefined').replace('', 'Undefined')

# ============================================================================
# EMISSIONS ANALYSIS: LEGITIMATE VS MERCENARY
# ============================================================================
st.markdown("### 📊 Emissions Analysis by Pool Category")
if reduction_pct > 0 or core_only:
    st.caption(f"Showing scenario: {reduction_pct}% reduction" + (" • Core pools only" if core_only else ""))

# Aggregate emissions by pool category (uses scenario emissions when reduction/core-only set)
emissions_by_category = df_emissions.groupby('pool_category').agg({
    bal_col: 'sum',
    'pool_symbol': 'nunique'
}).round(2)
emissions_by_category.columns = ['Total BAL Emitted', 'Pool Count']

# Build category totals by mapping any index value to our 4 known categories (avoids index lookup issues)
KNOWN_CATS = ['Legitimate', 'Sustainable', 'Mercenary', 'Undefined']
cat_totals = {c: 0.0 for c in KNOWN_CATS}
cat_counts = {c: 0 for c in KNOWN_CATS}
for idx, row in emissions_by_category.iterrows():
    key = str(idx).strip() if pd.notna(idx) and idx is not None else 'Undefined'
    if not key or key.lower() == 'nan':
        key = 'Undefined'
    if key not in KNOWN_CATS:
        key = 'Undefined'
    cat_totals[key] += float(row['Total BAL Emitted'])
    cat_counts[key] += int(row['Pool Count'])

total_emissions = sum(cat_totals.values())
if total_emissions > 0:
    cat_pcts = {c: (cat_totals[c] / total_emissions * 100) for c in KNOWN_CATS}
else:
    cat_pcts = {c: 0.0 for c in KNOWN_CATS}

# Rebuild emissions_by_category for the detailed table (index = known categories)
emissions_by_category = pd.DataFrame({
    'Total BAL Emitted': [cat_totals[c] for c in KNOWN_CATS],
    'Pool Count': [cat_counts[c] for c in KNOWN_CATS],
    'Percentage': [cat_pcts[c] for c in KNOWN_CATS]
}, index=KNOWN_CATS)

# Display aggregated values (5 columns: Legitimate, Sustainable, Mercenary, Undefined, Total)
col1, col2, col3, col4, col5 = st.columns(5)

legitimate_emissions, legitimate_pct = cat_totals['Legitimate'], cat_pcts['Legitimate']
sustainable_emissions, sustainable_pct = cat_totals['Sustainable'], cat_pcts['Sustainable']
mercenary_emissions, mercenary_pct = cat_totals['Mercenary'], cat_pcts['Mercenary']
undefined_emissions, undefined_pct = cat_totals['Undefined'], cat_pcts['Undefined']

with col1:
    st.metric("Legitimate Emissions", f"{legitimate_emissions:,.0f} BAL", f"{legitimate_pct:.1f}%", help="Total BAL emitted to legitimate pools")
with col2:
    st.metric("Sustainable Emissions", f"{sustainable_emissions:,.0f} BAL", f"{sustainable_pct:.1f}%", help="Total BAL emitted to sustainable pools")
with col3:
    st.metric("Mercenary Emissions", f"{mercenary_emissions:,.0f} BAL", f"{mercenary_pct:.1f}%", help="Total BAL emitted to mercenary pools")
with col4:
    st.metric("Undefined Emissions", f"{undefined_emissions:,.0f} BAL", f"{undefined_pct:.1f}%", help="Total BAL emitted to undefined pools")
with col5:
    st.metric("Total Emissions", f"{total_emissions:,.0f} BAL", help="Total BAL emitted across all pools")

# Display detailed table
st.markdown("#### 📋 Detailed Breakdown")
emissions_display = emissions_by_category.copy()
emissions_display['Total BAL Emitted'] = emissions_display['Total BAL Emitted'].apply(lambda x: f"{x:,.0f}")
emissions_display['Percentage'] = emissions_display['Percentage'].apply(lambda x: f"{x:.2f}%")
st.dataframe(emissions_display, use_container_width=True, hide_index=False)

# Temporal chart for emissions by category
col_chart_title_legit, col_toggle_legit = st.columns([1, 0.15])
with col_chart_title_legit:
    st.markdown("#### 📈 Emissions Over Time by Category")
with col_toggle_legit:
    # Button text changes based on current state
    button_text_legit = "Absolute" if st.session_state.show_legit_mercenary_percentage else "%"
    if st.button(button_text_legit, key="toggle_legit_mercenary_percentage", use_container_width=True):
        st.session_state.show_legit_mercenary_percentage = not st.session_state.show_legit_mercenary_percentage
        st.rerun()
    
    show_percentage_legit = st.session_state.show_legit_mercenary_percentage

# Prepare temporal data - ensure block_date is datetime (use df_emissions for scenario-aware chart)
df_emissions_chart = df_emissions.copy()
if 'block_date' in df_emissions_chart.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_emissions_chart['block_date']):
        df_emissions_chart['block_date'] = pd.to_datetime(df_emissions_chart['block_date'], errors='coerce')
    df_emissions_chart['month'] = df_emissions_chart['block_date'].dt.to_period('M').dt.start_time
else:
    st.warning("block_date column not found. Cannot create temporal chart.")
    df_emissions_chart['month'] = pd.NaT

# Map pool_category to our 4 known categories before groupby (for correct chart breakdown)
def _map_pool_cat(x):
    if pd.isna(x) or x is None or str(x).strip().lower() in ('', 'nan'):
        return 'Undefined'
    s = str(x).strip()
    return s if s in KNOWN_CATS else 'Undefined'
df_emissions_chart['pool_category'] = df_emissions_chart['pool_category'].apply(_map_pool_cat)

emissions_temporal = df_emissions_chart.groupby(['month', 'pool_category']).agg({
    bal_col: 'sum'
}).reset_index()

# Pivot for chart - ensure all 4 categories as columns in fixed order
pivot_emissions = emissions_temporal.pivot(index='month', columns='pool_category', values=bal_col).fillna(0)
for c in KNOWN_CATS:
    if c not in pivot_emissions.columns:
        pivot_emissions[c] = 0
pivot_emissions = pivot_emissions[KNOWN_CATS]

# Normalize to percentage if toggle is on
if show_percentage_legit:
    # Calculate percentage for each month
    row_sums = pivot_emissions.sum(axis=1)
    pivot_emissions_pct = pivot_emissions.div(row_sums.replace(0, 1), axis=0) * 100
    # Set to 0 where row sum was 0
    pivot_emissions_pct.loc[row_sums == 0] = 0
    data_to_plot_legit = pivot_emissions_pct
    yaxis_title_legit = "Percentage (%)"
    hovertemplate_suffix_legit = "%"
else:
    data_to_plot_legit = pivot_emissions
    yaxis_title_legit = "BAL Emitted"
    hovertemplate_suffix_legit = " BAL"

# Create area chart
fig_legit_mercenary = go.Figure()

colors = {
    'Legitimate': '#2ecc71',
    'Sustainable': '#3498db',
    'Mercenary': '#e74c3c',
    'Undefined': '#95a5a6'
}

for category in data_to_plot_legit.columns:
    fig_legit_mercenary.add_trace(go.Scatter(
        x=data_to_plot_legit.index,
        y=data_to_plot_legit[category],
        mode='lines',
        name=category,
        fill='tonexty' if category != data_to_plot_legit.columns[0] else 'tozeroy',
        stackgroup='one',
        line=dict(color=colors.get(category, '#3498db'), width=1.5),
        hovertemplate=f'<b>{category}</b><br>%{{x|%b %Y}}<br>%{{y:,.2f}}{hovertemplate_suffix_legit}<extra></extra>'
    ))

fig_legit_mercenary.update_layout(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    height=450,
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
        title=dict(text=yaxis_title_legit, font=dict(size=12, color='#8B95A6')),
        tickfont=dict(size=11, color='#8B95A6'),
        tickformat='.2f' if show_percentage_legit else ',.0f',
        ticksuffix='%' if show_percentage_legit else ''
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

st.plotly_chart(fig_legit_mercenary, use_container_width=True, key="emissions_legit_mercenary")

st.markdown("---")

# ============================================================================
# EMISSIONS ANALYSIS: CORE VS NON-CORE POOLS
# ============================================================================
st.markdown("### 📊 Emissions Analysis: Core Pools vs Non-Core Pools")
if core_only:
    st.caption("Showing scenario: emissions only for core pools (non-core = 0).")

# Aggregate emissions by core pool status (uses scenario so core-only filter is visible)
emissions_by_core = df_emissions.groupby('is_core_pool').agg({
    bal_col: 'sum',
    'pool_symbol': 'nunique'
}).round(2)
# Map index values safely
mapping = {1: 'Core Pools', 0: 'Non-Core Pools'}
emissions_by_core.index = [mapping.get(x, f'Unknown ({x})') for x in emissions_by_core.index]
emissions_by_core.columns = ['Total BAL Emitted', 'Pool Count']

# Calculate percentages
total_emissions_core = emissions_by_core['Total BAL Emitted'].sum()
if total_emissions_core > 0:
    emissions_by_core['Percentage'] = (emissions_by_core['Total BAL Emitted'] / total_emissions_core * 100).round(2)
else:
    emissions_by_core['Percentage'] = 0

# Display aggregated values
col1, col2, col3 = st.columns(3)

core_emissions = emissions_by_core.loc['Core Pools', 'Total BAL Emitted'] if 'Core Pools' in emissions_by_core.index else 0
core_pct = emissions_by_core.loc['Core Pools', 'Percentage'] if 'Core Pools' in emissions_by_core.index else 0
noncore_emissions = emissions_by_core.loc['Non-Core Pools', 'Total BAL Emitted'] if 'Non-Core Pools' in emissions_by_core.index else 0
noncore_pct = emissions_by_core.loc['Non-Core Pools', 'Percentage'] if 'Non-Core Pools' in emissions_by_core.index else 0

with col1:
    st.metric(
        "Core Pools Emissions",
        f"{core_emissions:,.0f} BAL",
        f"{core_pct:.1f}%",
        help="Total BAL emitted to core pools"
    )

with col2:
    st.metric(
        "Non-Core Pools Emissions",
        f"{noncore_emissions:,.0f} BAL",
        f"{noncore_pct:.1f}%",
        help="Total BAL emitted to non-core pools"
    )

with col3:
    st.metric(
        "Total Emissions",
        f"{total_emissions_core:,.0f} BAL",
        help="Total BAL emitted across all pools"
    )

# Display detailed table
st.markdown("#### 📋 Detailed Breakdown")
emissions_core_display = emissions_by_core.copy()
emissions_core_display['Total BAL Emitted'] = emissions_core_display['Total BAL Emitted'].apply(lambda x: f"{x:,.0f}")
emissions_core_display['Percentage'] = emissions_core_display['Percentage'].apply(lambda x: f"{x:.2f}%")
st.dataframe(emissions_core_display, use_container_width=True, hide_index=False)

# Temporal chart for emissions by core status
col_chart_title, col_toggle = st.columns([1, 0.15])
with col_chart_title:
    st.markdown("#### 📈 Emissions Over Time: Core vs Non-Core Pools")
with col_toggle:
    # Button text changes based on current state
    button_text = "Absolute" if st.session_state.show_core_percentage else "%"
    if st.button(button_text, key="toggle_core_percentage", use_container_width=True):
        st.session_state.show_core_percentage = not st.session_state.show_core_percentage
        st.rerun()
    
    show_percentage = st.session_state.show_core_percentage

# Prepare temporal data (use df_emissions_chart which has month and scenario emissions)
emissions_temporal_core = df_emissions_chart.groupby(['month', 'is_core_pool']).agg({
    bal_col: 'sum'
}).reset_index()
mapping_core = {1: 'Core Pools', 0: 'Non-Core Pools'}
emissions_temporal_core['is_core_pool'] = emissions_temporal_core['is_core_pool'].apply(lambda x: mapping_core.get(x, f'Unknown ({x})'))

# Pivot for chart
pivot_emissions_core = emissions_temporal_core.pivot(index='month', columns='is_core_pool', values=bal_col).fillna(0)

# Normalize to percentage if toggle is on
if show_percentage:
    # Calculate percentage for each month
    pivot_emissions_core_pct = pivot_emissions_core.div(pivot_emissions_core.sum(axis=1), axis=0) * 100
    pivot_emissions_core_pct = pivot_emissions_core_pct.fillna(0)
    data_to_plot = pivot_emissions_core_pct
    yaxis_title = "Percentage (%)"
    hovertemplate_suffix = "%"
else:
    data_to_plot = pivot_emissions_core
    yaxis_title = "BAL Emitted"
    hovertemplate_suffix = " BAL"

# Create area chart
fig_core_noncore = go.Figure()

core_colors = {
    'Core Pools': '#67A2E1',
    'Non-Core Pools': '#E9A97B'
}

for pool_type in data_to_plot.columns:
    fig_core_noncore.add_trace(go.Scatter(
        x=data_to_plot.index,
        y=data_to_plot[pool_type],
        mode='lines',
        name=pool_type,
        fill='tonexty' if pool_type != data_to_plot.columns[0] else 'tozeroy',
        stackgroup='one',
        line=dict(color=core_colors.get(pool_type, '#3498db'), width=1.5),
        hovertemplate=f'<b>{pool_type}</b><br>%{{x|%b %Y}}<br>%{{y:,.2f}}{hovertemplate_suffix}<extra></extra>'
    ))

fig_core_noncore.update_layout(
    template='plotly_dark',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    height=450,
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
        title=dict(text=yaxis_title, font=dict(size=12, color='#8B95A6')),
        tickfont=dict(size=11, color='#8B95A6')
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

st.plotly_chart(fig_core_noncore, use_container_width=True, key="emissions_core_noncore")

st.markdown("---")

# ============================================================================
# CURRENT STATE (BASELINE) - Existing section
# ============================================================================
st.markdown("### 📊 Current State (Baseline)")

# Normalize pool_category for baseline (same mapping as KPIs/chart)
df_baseline = df_display.copy()
if 'pool_category' not in df_baseline.columns:
    df_baseline['pool_category'] = 'Undefined'
else:
    df_baseline['pool_category'] = df_baseline['pool_category'].apply(
        lambda x: 'Undefined' if (pd.isna(x) or x is None or str(x).strip().lower() in ('', 'nan'))
        else (str(x).strip() if str(x).strip() in KNOWN_CATS else 'Undefined')
    )
baseline = df_baseline.groupby('pool_category').agg({
    'bal_emited_votes': 'sum',
    'direct_incentives': 'sum',
    'protocol_fee_amount_usd': 'sum',
    'dao_profit_usd': 'sum'
}).round(2)
baseline.columns = ['BAL Emitted', 'Total Incentives', 'Total Revenue', 'Total DAO Profit']
# Ensure all 4 categories in baseline (reindex, fill 0)
baseline = baseline.reindex(KNOWN_CATS, fill_value=0).fillna(0)

# Format monetary columns
baseline_display = baseline.copy()
for col in ['Total Incentives', 'Total Revenue', 'Total DAO Profit']:
    if col in baseline_display.columns:
        baseline_display[col] = baseline_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")

st.dataframe(baseline_display, use_container_width=True, hide_index=False)

st.markdown("---")

# Build scenario name based on settings
scenario_name = f"{reduction_pct}% BAL Emission Reduction"
if core_only:
    scenario_name += " (Core Pools Only)"

st.markdown(f"### 📈 Impact Analysis: {scenario_name}")

# Calculate impact with new parameters
df_scenario = utils.calculate_emission_reduction_impact(df_display, reduction_factor, core_only=core_only)

# Normalize pool_category for scenario summary (same mapping as baseline)
df_scenario_norm = df_scenario.copy()
if 'pool_category' not in df_scenario_norm.columns:
    df_scenario_norm['pool_category'] = 'Undefined'
else:
    df_scenario_norm['pool_category'] = df_scenario_norm['pool_category'].apply(
        lambda x: 'Undefined' if (pd.isna(x) or x is None or str(x).strip().lower() in ('', 'nan'))
        else (str(x).strip() if str(x).strip() in KNOWN_CATS else 'Undefined')
    )
agg_dict = {
    'reduced_incentives': 'sum',
    'protocol_fee_amount_usd': 'sum',
    'new_dao_profit': 'sum',
    'direct_incentives': 'sum'
}
if 'bal_emited_votes' in df_scenario_norm.columns:
    agg_dict['bal_emited_votes'] = 'sum'
if 'reduced_bal_emitted' in df_scenario_norm.columns:
    agg_dict['reduced_bal_emitted'] = 'sum'

scenario_summary = df_scenario_norm.groupby('pool_category').agg(agg_dict).round(2)
# Ensure all 4 categories (reindex, fill 0)
scenario_summary = scenario_summary.reindex(KNOWN_CATS, fill_value=0).fillna(0)

# Calculate additional metrics
if 'reduced_bal_emitted' in scenario_summary.columns and 'bal_emited_votes' in scenario_summary.columns:
    scenario_summary['bal_reduction'] = scenario_summary['bal_emited_votes'] - scenario_summary['reduced_bal_emitted']
else:
    scenario_summary['bal_reduction'] = 0

scenario_summary['incentive_reduction'] = scenario_summary['direct_incentives'] - scenario_summary['reduced_incentives']
scenario_summary['profit_change'] = scenario_summary['new_dao_profit'] - baseline['Total DAO Profit']
base_dao = baseline['Total DAO Profit'].replace(0, 1)  # avoid division by zero
scenario_summary['profit_change_pct'] = (scenario_summary['profit_change'] / base_dao * 100).round(2).fillna(0).replace([float('inf'), -float('inf')], 0)

# Rename columns based on what actually exists
column_mapping = {}
if 'reduced_incentives' in scenario_summary.columns:
    column_mapping['reduced_incentives'] = 'Reduced Incentives'
if 'protocol_fee_amount_usd' in scenario_summary.columns:
    column_mapping['protocol_fee_amount_usd'] = 'Total Revenue'
if 'new_dao_profit' in scenario_summary.columns:
    column_mapping['new_dao_profit'] = 'New DAO Profit'
if 'direct_incentives' in scenario_summary.columns:
    column_mapping['direct_incentives'] = 'Original Incentives'
# Removed 'Reduced BAL' column as requested
if 'bal_emited_votes' in scenario_summary.columns:
    column_mapping['bal_emited_votes'] = 'Original BAL'
if 'bal_reduction' in scenario_summary.columns:
    column_mapping['bal_reduction'] = 'BAL Reduction'
if 'incentive_reduction' in scenario_summary.columns:
    column_mapping['incentive_reduction'] = 'Incentive Reduction'
if 'profit_change' in scenario_summary.columns:
    column_mapping['profit_change'] = 'Profit Change'
if 'profit_change_pct' in scenario_summary.columns:
    column_mapping['profit_change_pct'] = 'Profit Change %'

scenario_summary = scenario_summary.rename(columns=column_mapping)

# Format monetary columns for display (keep reduced_bal_emitted in scenario_summary for comparison chart)
scenario_summary_display = scenario_summary.copy()
if 'reduced_bal_emitted' in scenario_summary_display.columns:
    scenario_summary_display = scenario_summary_display.drop(columns=['reduced_bal_emitted'])
monetary_cols = ['Reduced Incentives', 'Total Revenue', 'New DAO Profit', 'Original Incentives', 'Incentive Reduction', 'Profit Change']
for col in monetary_cols:
    if col in scenario_summary_display.columns:
        scenario_summary_display[col] = scenario_summary_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")

# Format percentage column
if 'Profit Change %' in scenario_summary_display.columns:
    scenario_summary_display['Profit Change %'] = scenario_summary_display['Profit Change %'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

st.dataframe(scenario_summary_display, use_container_width=True, hide_index=False)

st.markdown("### 📊 Comparison Chart: Baseline vs Scenario")

# Build comparison data
comparison_data = []
for category in baseline.index:
    comparison_data.append({
        'Category': category,
        'Baseline': baseline.loc[category, 'Total DAO Profit'],
        'Scenario': scenario_summary.loc[category, 'New DAO Profit'] if category in scenario_summary.index else 0
    })

df_comparison = pd.DataFrame(comparison_data)

if len(df_comparison) > 0:
    fig1 = go.Figure()
    
    color_baseline = '#67A2E1'
    color_scenario = '#E9A97B'
    
    fig1.add_trace(go.Bar(
        name='Baseline',
        x=df_comparison['Category'],
        y=df_comparison['Baseline'],
        marker=dict(color=color_baseline, line=dict(width=0)),
        marker_line_width=0
    ))
    
    fig1.add_trace(go.Bar(
        name=scenario_name,
        x=df_comparison['Category'],
        y=df_comparison['Scenario'],
        marker=dict(color=color_scenario, line=dict(width=0)),
        marker_line_width=0
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
            title="DAO Profit (USD)",
            tickfont=dict(size=11, color='#8B95A6')
        ),
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.05,
            xanchor="left",
            x=0,
            font=dict(size=11, color='#8B95A6')
        )
    )
    
    st.plotly_chart(fig1, use_container_width=True, key="emission_comparison")

    # Comparison chart: Baseline vs Scenario – BAL Emitted (same layout, Y = emissions)
    comparison_emissions = []
    for category in baseline.index:
        scenario_bal = scenario_summary.loc[category, 'reduced_bal_emitted'] if category in scenario_summary.index and 'reduced_bal_emitted' in scenario_summary.columns else 0
        comparison_emissions.append({
            'Category': category,
            'Baseline': baseline.loc[category, 'BAL Emitted'],
            'Scenario': scenario_bal
        })
    df_comparison_emissions = pd.DataFrame(comparison_emissions)

    if len(df_comparison_emissions) > 0:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name='Baseline',
            x=df_comparison_emissions['Category'],
            y=df_comparison_emissions['Baseline'],
            marker=dict(color=color_baseline, line=dict(width=0)),
            marker_line_width=0
        ))
        fig2.add_trace(go.Bar(
            name=scenario_name,
            x=df_comparison_emissions['Category'],
            y=df_comparison_emissions['Scenario'],
            marker=dict(color=color_scenario, line=dict(width=0)),
            marker_line_width=0
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
                title="BAL Emitted",
                tickfont=dict(size=11, color='#8B95A6')
            ),
            barmode='group',
            legend=dict(
                orientation="h",
                yanchor="top",
                y=1.05,
                xanchor="left",
                x=0,
                font=dict(size=11, color='#8B95A6')
            )
        )
        st.plotly_chart(fig2, use_container_width=True, key="emission_comparison_emissions")

# Show detailed pool analysis when filtering by Top 20 or Worst 20
if st.session_state.pool_filter_mode_emission in ['top20', 'worst20']:
    st.markdown("---")
    st.markdown("### 📋 Pools Impact Analysis")
    
    # Get list of pools from filtered data
    filtered_pools = sorted(df_display['pool_symbol'].unique().tolist())
    
    for idx, pool in enumerate(filtered_pools):
        pool_data = df_display[df_display['pool_symbol'] == pool]
        if len(pool_data) > 0:
            with st.expander(f"{pool}"):
                baseline_pool = pool_data['dao_profit_usd'].sum()
                baseline_bal = pool_data['bal_emited_votes'].sum()
                baseline_inc = pool_data['direct_incentives'].sum()
                
                col_base1, col_base2, col_base3 = st.columns(3)
                col_base1.metric("Baseline DAO Profit", f"${baseline_pool:,.0f}")
                col_base2.metric("Baseline BAL Emitted", f"{baseline_bal:,.0f}")
                col_base3.metric("Baseline Incentives", f"${baseline_inc:,.0f}")
                
                st.markdown("---")
                
                # Use current scenario settings
                df_scenario = utils.calculate_emission_reduction_impact(pool_data, reduction_factor, core_only=core_only)
                new_profit = df_scenario['new_dao_profit'].sum()
                profit_change = new_profit - baseline_pool
                
                reduced_bal = df_scenario['reduced_bal_emitted'].sum() if 'reduced_bal_emitted' in df_scenario.columns else baseline_bal * reduction_factor
                bal_reduction = baseline_bal - reduced_bal
                
                reduced_inc = df_scenario['reduced_incentives'].sum()
                inc_reduction = baseline_inc - reduced_inc
                
                st.markdown(f"**{scenario_name}**")
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("New DAO Profit", f"${new_profit:,.0f}", f"${profit_change:,.0f}")
                with col_s2:
                    st.metric("Reduced BAL", f"{reduced_bal:,.0f}", f"-{bal_reduction:,.0f}")
                with col_s3:
                    st.metric("Reduced Incentives", f"${reduced_inc:,.0f}", f"-${inc_reduction:,.0f}")
                
                if idx < len(filtered_pools) - 1:
                    st.markdown("---")
