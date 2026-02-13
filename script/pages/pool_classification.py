import streamlit as st
import utils
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Pool Classification", layout="wide", page_icon="🏷️")

if not utils.check_authentication():
    st.stop()

utils.inject_css()

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

utils.show_data_source_badge()
utils.show_data_load_debug()

if 'pool_filter_mode_class' not in st.session_state:
    st.session_state.pool_filter_mode_class = 'all'  

if 'version_filter_class' not in st.session_state:
    st.session_state.version_filter_class = 'all'  

if 'gauge_filter_class' not in st.session_state:
    st.session_state.gauge_filter_class = 'all'  

utils.show_version_filter('version_filter_class')

utils.show_gauge_filter('gauge_filter_class')

utils.show_pool_filters('pool_filter_mode_class')

df = utils.show_date_filter_sidebar(df, key_prefix="date_filter_class")

df = utils.apply_version_filter(df, 'version_filter_class')

df = utils.apply_gauge_filter(df, 'gauge_filter_class')

if df.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">Pool Classification Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Legitimate / Sustainable / Mercenary / Undefined • Top/Worst 20 by DAO profit</div>', unsafe_allow_html=True)
    utils.show_data_source_inline()
with col_logout:
    utils.show_logout_button()

st.markdown("---")

st.markdown("### 📖 Understanding Pool Classification")

KNOWN_CATS = ['Legitimate', 'Sustainable', 'Mercenary', 'Undefined']


def _map_pool_cat(x):
    """Normalize pool_category to a known category."""
    if pd.isna(x) or x is None or str(x).strip().lower() in ('', 'nan'):
        return 'Undefined'
    s = str(x).strip()
    return s if s in KNOWN_CATS else 'Undefined'


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

if st.session_state.pool_filter_mode_class == 'top20':
    top_pools = utils.get_top_pools(df, n=20)
    top_pools_list = [str(p) for p in top_pools]
    df_display = df[df['pool_symbol'].isin(top_pools_list)].copy()
elif st.session_state.pool_filter_mode_class == 'worst20':
    worst_pools = utils.get_worst_pools(df, n=20)
    worst_pools_list = [str(p) for p in worst_pools]
    df_display = df[df['pool_symbol'].isin(worst_pools_list)].copy()
else:
    df_display = df.copy()

if 'pool_category' not in df_display.columns:
    st.error("Pool classification not found.")
    st.stop()
df_display = df_display.copy()
df_display['pool_category'] = df_display['pool_category'].apply(_map_pool_cat)
agg_dict = {
    'pool_symbol': 'nunique',
    'protocol_fee_amount_usd': 'sum',
    'direct_incentives': 'sum',
    'dao_profit_usd': 'sum',
}
if 'bal_emited_votes' in df_display.columns:
    agg_dict['bal_emited_votes'] = 'sum'

category_stats = df_display.groupby('pool_category').agg(agg_dict).round(2)
col_map = {
    'pool_symbol': 'Pool Count',
    'protocol_fee_amount_usd': 'Total Revenue',
    'direct_incentives': 'Total Incentives',
    'dao_profit_usd': 'Total DAO Profit',
    'bal_emited_votes': 'Total BAL Emitted'
}
category_stats = category_stats.rename(columns=col_map)
category_stats = category_stats.reindex(KNOWN_CATS, fill_value=0).fillna(0)
if 'Total BAL Emitted' in category_stats.columns:
    total_bal = category_stats['Total BAL Emitted'].sum()
    if total_bal > 0:
        category_stats['% of Total BAL'] = (category_stats['Total BAL Emitted'] / total_bal * 100).round(2)
    else:
        category_stats['% of Total BAL'] = 0.0
total_bribes = category_stats['Total Incentives'].sum()
if total_bribes > 0:
    category_stats['% of Total Incentives'] = (category_stats['Total Incentives'] / total_bribes * 100).round(2)
else:
    category_stats['% of Total Incentives'] = 0.0

st.markdown("### 📊 Classification Summary")

def _count(cat):
    return category_stats.loc[cat, 'Pool Count'] if cat in category_stats.index else 0
active_cats = [c for c in KNOWN_CATS if _count(c) > 0]
if active_cats:
    cols = st.columns(len(active_cats))
    for i, cat in enumerate(active_cats):
        with cols[i]:
            st.metric(f"{cat} Pools", f"{_count(cat):.0f}")
else:
    st.info("No pool data in selected filters.")

st.markdown("---")

category_stats_display = category_stats.loc[active_cats].copy() if active_cats else category_stats.copy()
for col in ['Total Revenue', 'Total Bribes', 'Total DAO Profit']:
    if col in category_stats_display.columns:
        category_stats_display[col] = category_stats_display[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "$0")
for col in ['% of Total Bribes', '% of Total BAL']:
    if col in category_stats_display.columns:
        category_stats_display[col] = category_stats_display[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

st.dataframe(category_stats_display, use_container_width=True, hide_index=False)


st.markdown("---")

st.markdown("### 📈 Historical Distribution by Category")
if 'block_date' in df_display.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_display['block_date']):
        df_display['block_date'] = pd.to_datetime(df_display['block_date'], errors='coerce')
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
    chart_cats = [c for c in KNOWN_CATS if c in pivot_incentives.columns]
    if chart_cats:
        for c in chart_cats:
            if c not in pivot_profit.columns:
                pivot_profit[c] = 0
        pivot_incentives = pivot_incentives[chart_cats]
        pivot_profit = pivot_profit[chart_cats]

    pivot_incentives.index = pd.to_datetime(pivot_incentives.index)
    pivot_profit.index = pd.to_datetime(pivot_profit.index)
else:
    pivot_incentives = pd.DataFrame()
    pivot_profit = pd.DataFrame()

colors = {'Legitimate': '#2ecc71', 'Sustainable': '#3498db', 'Mercenary': '#e74c3c', 'Undefined': '#95a5a6'}

if pivot_incentives.empty or pivot_profit.empty:
    st.info("No data available for historical distribution charts.")
else:
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
        if st.session_state.show_percentage_bribes:
            row_sums = pivot_incentives.sum(axis=1)
            pivot_incentives_pct = pivot_incentives.div(row_sums.replace(0, 1), axis=0) * 100
            pivot_incentives_pct.loc[row_sums == 0] = 0
            pivot_incentives_display = pivot_incentives_pct
            yaxis_title = "Percentage (%)"
        else:
            pivot_incentives_display = pivot_incentives
            yaxis_title = ""
        
        for category in pivot_incentives_display.columns:
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
if st.session_state.pool_filter_mode_class in ['top20', 'worst20']:
    st.markdown("---")
    st.markdown("### 📋 Pools by Category")
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
