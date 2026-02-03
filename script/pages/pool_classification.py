import streamlit as st
import utils
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Pool Classification", layout="wide", page_icon="🏷️")

# Check authentication
if not utils.check_authentication():
    st.stop()

utils.inject_css()

# Script para aplicar IDs específicos aos botões
import streamlit.components.v1 as components

components.html("""
<script>
console.log('[Button IDs] Script carregado via components.html (pool_classification.py)!');

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

# Initialize session state - default to 'all' (show everything)
if 'pool_filter_mode_class' not in st.session_state:
    st.session_state.pool_filter_mode_class = 'all'  # Default: show all pools

if 'version_filter_class' not in st.session_state:
    st.session_state.version_filter_class = 'all'  # Default: show all versions

if 'gauge_filter_class' not in st.session_state:
    st.session_state.gauge_filter_class = 'all'  # Default: show all pools

# Version filter at the top of sidebar
utils.show_version_filter('version_filter_class')

# Gauge filter (Gauge / No Gauge)
utils.show_gauge_filter('gauge_filter_class')

# Pool filters at the top of sidebar
utils.show_pool_filters('pool_filter_mode_class')

# Date filter: Year + Quarter (using dynamic filters)
df = utils.show_date_filter_sidebar(df, key_prefix="date_filter_class")

# Apply version filter
df = utils.apply_version_filter(df, 'version_filter_class')

# Apply gauge filter
df = utils.apply_gauge_filter(df, 'gauge_filter_class')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

# Page Header with logout button
col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">Pool Classification Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">From Balancer-All-Tokenomics.csv • Legitimate vs Mercenary • Top/Worst 20 by protocol fees</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

# Add explanation section (same as emission_impact.py)
st.markdown("### 📖 Understanding Pool Classification")

with st.expander("ℹ️ What are Legitimate vs Mercenary Pools?", expanded=False):
    st.markdown("""
    **Legitimate Pools:**
    - Pools that generate positive DAO profit (revenue > bribes)
    - Have good emissions ROI (revenue/bribes > 1.0)
    - Generate meaningful revenue (>$10k) even without bribes
    - Core pools with ROI > 0.7 are typically classified as legitimate
    
    **Mercenary Pools:**
    - Pools that generate negative DAO profit (revenue < bribes)
    - Have poor emissions ROI (revenue/bribes < 0.5)
    - Highly dependent on bribes (>80% of revenue comes from bribes)
    - Generate little to no revenue without bribes
    
    **Undefined Pools:**
    - Pools that don't clearly fit into either category
    - May have no bribes but also low revenue
    - Require further analysis to classify
    
    **Core Pools:**
    - Pools designated as "core" by the protocol
    - Typically receive priority in emissions distribution
    - May have different revenue distribution rules
    
    **Note:** This analysis focuses on bribes (voting incentives). Direct incentives are not considered in this classification.
    """)

st.markdown("---")

# Filter data based on mode
if st.session_state.pool_filter_mode_class == 'top20':
    # Get top 20 pools
    top_pools = utils.get_top_pools(df, n=20)
    top_pools_list = [str(p) for p in top_pools]
    df_display = df[df['pool_symbol'].isin(top_pools_list)].copy()
elif st.session_state.pool_filter_mode_class == 'worst20':
    # Get worst 20 pools
    worst_pools = utils.get_worst_pools(df, n=20)
    worst_pools_list = [str(p) for p in worst_pools]
    df_display = df[df['pool_symbol'].isin(worst_pools_list)].copy()
else:
    # 'all' mode - show everything
    df_display = df.copy()

if 'pool_category' not in df_display.columns:
    st.error("Pool classification not found.")
    st.stop()

category_stats = df_display.groupby('pool_category').agg({
    'pool_symbol': 'nunique',
    'protocol_fee_amount_usd': 'sum',
    'direct_incentives': 'sum',
    'dao_profit_usd': 'sum',
    'bal_emited_votes': 'sum'
}).round(2)

category_stats.columns = ['Pool Count', 'Total Revenue', 'Total Bribes', 'Total DAO Profit', 'Total BAL Emitted']

total_bribes = category_stats['Total Bribes'].sum()
total_bal = category_stats['Total BAL Emitted'].sum()

if total_bribes > 0:
    category_stats['% of Total Bribes'] = (category_stats['Total Bribes'] / total_bribes * 100).round(2)
if total_bal > 0:
    category_stats['% of Total BAL'] = (category_stats['Total BAL Emitted'] / total_bal * 100).round(2)

st.markdown("### 📊 Classification Summary")

col1, col2, col3 = st.columns(3)

with col1:
    legit_count = category_stats.loc['Legitimate', 'Pool Count'] if 'Legitimate' in category_stats.index else 0
    st.metric("Legitimate Pools", f"{legit_count:.0f}")

with col2:
    merc_count = category_stats.loc['Mercenary', 'Pool Count'] if 'Mercenary' in category_stats.index else 0
    st.metric("Mercenary Pools", f"{merc_count:.0f}")

with col3:
    undef_count = category_stats.loc['Undefined', 'Pool Count'] if 'Undefined' in category_stats.index else 0
    st.metric("Undefined Pools", f"{undef_count:.0f}")

st.markdown("---")

# Format monetary columns for display
category_stats_display = category_stats.copy()
for col in ['Total Revenue', 'Total Bribes', 'Total DAO Profit']:
    if col in category_stats_display.columns:
        category_stats_display[col] = category_stats_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")

# Format percentage columns
for col in ['% of Total Bribes', '% of Total BAL']:
    if col in category_stats_display.columns:
        category_stats_display[col] = category_stats_display[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

st.dataframe(category_stats_display, use_container_width=True, hide_index=False)

st.markdown("---")

st.markdown("### 📈 Historical Distribution by Category")

# Ensure block_date is datetime before using .dt accessor
if 'block_date' in df_display.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_display['block_date']):
        df_display['block_date'] = pd.to_datetime(df_display['block_date'], errors='coerce')
    
    # Filter out rows with invalid dates
    df_display_valid = df_display[df_display['block_date'].notna()].copy()
    
    if not df_display_valid.empty:
        df_monthly = df_display_valid.groupby([df_display_valid['block_date'].dt.to_period('M'), 'pool_category']).agg({
            'direct_incentives': 'sum',
            'dao_profit_usd': 'sum'
        }).reset_index()
    else:
        st.warning("No valid date data available for historical distribution.")
        df_monthly = pd.DataFrame()
else:
    st.warning("block_date column not found. Cannot create historical distribution.")
    df_monthly = pd.DataFrame()

if not df_monthly.empty:
    df_monthly['block_date'] = df_monthly['block_date'].astype(str)

    pivot_incentives = df_monthly.pivot(index='block_date', columns='pool_category', values='direct_incentives').fillna(0)
    pivot_profit = df_monthly.pivot(index='block_date', columns='pool_category', values='dao_profit_usd').fillna(0)

    pivot_incentives.index = pd.to_datetime(pivot_incentives.index)
    pivot_profit.index = pd.to_datetime(pivot_profit.index)
else:
    pivot_incentives = pd.DataFrame()
    pivot_profit = pd.DataFrame()

colors = {'Legitimate': '#2ecc71', 'Mercenary': '#e74c3c', 'Undefined': '#95a5a6'}

if pivot_incentives.empty or pivot_profit.empty:
    st.info("No data available for historical distribution charts.")
else:
    # Toggle for percentage view
    if 'show_percentage_bribes' not in st.session_state:
        st.session_state.show_percentage_bribes = False
    
    col_toggle, _ = st.columns([1, 10])
    with col_toggle:
        toggle_text = "%" if not st.session_state.show_percentage_bribes else "Absolute"
        if st.button(toggle_text, key="toggle_bribes_percentage"):
            st.session_state.show_percentage_bribes = not st.session_state.show_percentage_bribes
            st.rerun()
    
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        chart_title = "**Monthly Bribes Distribution**" if not st.session_state.show_percentage_bribes else "**Monthly Bribes Distribution (%)**"
        st.markdown(chart_title)
        
        fig1 = go.Figure()
        
        # Calculate percentages if toggle is on
        if st.session_state.show_percentage_bribes:
            row_sums = pivot_incentives.sum(axis=1)
            # Avoid division by zero
            pivot_incentives_pct = pivot_incentives.div(row_sums.replace(0, 1), axis=0) * 100
            # Set to 0 where row sum was 0
            pivot_incentives_pct.loc[row_sums == 0] = 0
            pivot_incentives_display = pivot_incentives_pct
            yaxis_title = "Percentage (%)"
        else:
            pivot_incentives_display = pivot_incentives
            yaxis_title = ""
        
        for category in pivot_incentives_display.columns:
            # Format hover template based on view mode
            if st.session_state.show_percentage_bribes:
                hovertemplate = f'<b>{category}</b><br>%{{x|%b %Y}}<br>%{{y:,.2f}}%<extra></extra>'
            else:
                hovertemplate = f'<b>{category}</b><br>%{{x|%b %Y}}<br>$%{{y:,.0f}}<extra></extra>'
            
            fig1.add_trace(go.Scatter(
                x=pivot_incentives_display.index,
                y=pivot_incentives_display[category],
                mode='lines',
                name=category,
                line=dict(color=colors.get(category, '#3498db'), width=1.5),
                stackgroup='one',
                hovertemplate=hovertemplate
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
                title=yaxis_title,
                tickfont=dict(size=11, color='#8B95A6'),
                tickformat='.2f' if st.session_state.show_percentage_bribes else ',.0f',
                ticksuffix='%' if st.session_state.show_percentage_bribes else ''
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
        
        st.plotly_chart(fig1, use_container_width=True, key="monthly_incentives")

    with col_chart2:
        st.markdown("**Monthly DAO Profit by Category**")
        
        fig2 = go.Figure()
        
        for category in pivot_profit.columns:
            fig2.add_trace(go.Scatter(
                x=pivot_profit.index,
                y=pivot_profit[category],
                mode='lines',
                name=category,
                line=dict(color=colors.get(category, '#3498db'), width=1.5)
            ))
        
        fig2.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)", line_width=1)
        
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
                title="",
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
        
        st.plotly_chart(fig2, use_container_width=True, key="monthly_profit")

# Show detailed pool analysis when filtering by Top 20 or Worst 20
if st.session_state.pool_filter_mode_class in ['top20', 'worst20']:
    st.markdown("---")
    st.markdown("### 📋 Pools by Category")
    
    # Get list of pools from filtered data
    filtered_pools = sorted(df_display['pool_symbol'].unique().tolist())
    
    for idx, pool in enumerate(filtered_pools):
        pool_data = df_display[df_display['pool_symbol'] == pool]
        if len(pool_data) > 0:
            category = pool_data['pool_category'].iloc[0]
            total_profit = pool_data['dao_profit_usd'].sum()
            total_rev = pool_data['protocol_fee_amount_usd'].sum()
            total_inc = pool_data['direct_incentives'].sum()
            
            with st.expander(f"{pool} ({category})"):
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Total Revenue", f"${total_rev:,.0f}")
                col_p2.metric("Total Bribes", f"${total_inc:,.0f}")
                col_p3.metric("DAO Profit", f"${total_profit:,.0f}")
                
                # Ensure block_date is datetime before grouping
                pool_data_copy = pool_data.copy()
                if 'block_date' in pool_data_copy.columns:
                    if not pd.api.types.is_datetime64_any_dtype(pool_data_copy['block_date']):
                        pool_data_copy['block_date'] = pd.to_datetime(pool_data_copy['block_date'], errors='coerce')
                    pool_data_copy = pool_data_copy[pool_data_copy['block_date'].notna()]
                
                if not pool_data_copy.empty:
                    pool_daily = pool_data_copy.groupby('block_date').agg({
                        'protocol_fee_amount_usd': 'sum',
                        'direct_incentives': 'sum',
                        'dao_profit_usd': 'sum'
                    }).reset_index()
                else:
                    pool_daily = pd.DataFrame(columns=['block_date', 'protocol_fee_amount_usd', 'direct_incentives', 'dao_profit_usd'])
                
                if not pool_daily.empty:
                    fig_pool = go.Figure()
                    fig_pool.add_trace(go.Scatter(
                        x=pool_daily['block_date'],
                        y=pool_daily['protocol_fee_amount_usd'],
                        mode='lines',
                        name='Revenue',
                        line=dict(color='#67A2E1', width=1.5)
                    ))
                    fig_pool.add_trace(go.Scatter(
                        x=pool_daily['block_date'],
                        y=pool_daily['dao_profit_usd'],
                        mode='lines',
                        name='DAO Profit',
                        line=dict(color='#2ecc71', width=1.5)
                    ))
                    
                    fig_pool.update_layout(
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=300,
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
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=1.05,
                        xanchor="left",
                        x=0,
                        font=dict(size=10, color='#8B95A6')
                    )
                    )
                    
                    st.plotly_chart(fig_pool, use_container_width=True, key=f"pool_class_{idx}_{hash(pool)}")
                else:
                    st.info("No valid date data available for this pool.")
