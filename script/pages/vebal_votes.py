import streamlit as st
import utils
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

st.set_page_config(page_title="veBAL Votes", layout="wide", page_icon="🗳️")
if not utils.check_authentication():
    st.stop()

utils.inject_css()
import streamlit.components.v1 as components

components.html("""
<script>
console.log('[Button IDs] Script carregado via components.html (vebal_votes.py)!');

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
            
            const numberInputs = doc.querySelectorAll('input[type="number"]');
            numberInputs.forEach((input) => {
                input.style.cursor = 'pointer';
            });
            
            const selectboxes = doc.querySelectorAll('div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child');
            selectboxes.forEach((select) => {
                if (!select.hasAttribute('data-styled')) {
                    select.setAttribute('data-styled', 'true');
                    select.style.background = 'linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%)';
                    select.style.border = '1.5px solid rgba(103, 162, 225, 0.45)';
                    select.style.boxShadow = '0 3px 12px rgba(103, 162, 225, 0.15)';
                    select.style.borderRadius = '12px';
                    select.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                    select.style.position = 'relative';
                    select.style.overflow = 'hidden';
                    select.style.display = 'flex';
                    select.style.alignItems = 'center';
                    select.style.cursor = 'pointer';
                    select.style.animation = 'sidebarSaltinho 0.35s ease-out both';
                    const shimmer = document.createElement('div');
                    shimmer.style.cssText = `
                        content: '';
                        position: absolute;
                        top: 0;
                        left: -100%;
                        width: 100%;
                        height: 100%;
                        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
                        transition: left 0.6s ease;
                        pointer-events: none;
                        z-index: 1;
                    `;
                    select.appendChild(shimmer);
                    const borderGlow = document.createElement('div');
                    borderGlow.style.cssText = `
                        content: '';
                        position: absolute;
                        inset: 0;
                        border-radius: 12px;
                        padding: 1.5px;
                        background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2));
                        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
                        -webkit-mask-composite: xor;
                        mask-composite: exclude;
                        opacity: 0;
                        transition: opacity 0.3s;
                        pointer-events: none;
                        z-index: 0;
                    `;
                    select.appendChild(borderGlow);
                    select.addEventListener('mouseenter', function() {
                        this.style.background = 'linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%)';
                        this.style.borderColor = 'rgba(103, 162, 225, 0.7)';
                        this.style.transform = 'translateY(-3px) scale(1.02)';
                        this.style.boxShadow = '0 6px 20px rgba(103, 162, 225, 0.3)';
                        shimmer.style.left = '100%';
                        borderGlow.style.opacity = '1';
                    });
                    
                    select.addEventListener('mouseleave', function() {
                        this.style.background = 'linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%)';
                        this.style.borderColor = 'rgba(103, 162, 225, 0.45)';
                        this.style.transform = 'translateY(0) scale(1)';
                        this.style.boxShadow = '0 3px 12px rgba(103, 162, 225, 0.15)';
                        shimmer.style.left = '-100%';
                        borderGlow.style.opacity = '0';
                    });
                    
                    select.addEventListener('mousedown', function() {
                        this.style.transform = 'translateY(-1px) scale(1.01)';
                        this.style.boxShadow = '0 3px 12px rgba(103, 162, 225, 0.2)';
                    });
                    
                    select.addEventListener('mouseup', function() {
                        this.style.transform = 'translateY(-3px) scale(1.02)';
                        this.style.boxShadow = '0 6px 20px rgba(103, 162, 225, 0.3)';
                    });
                    const textContainer = select.querySelector('div:first-child');
                    if (textContainer) {
                        textContainer.style.flex = '1';
                        textContainer.style.minWidth = '0';
                        textContainer.style.textAlign = 'center';
                        textContainer.style.display = 'flex';
                        textContainer.style.justifyContent = 'center';
                        textContainer.style.alignItems = 'center';
                    }
                }
            });
        } catch(e) {
            console.error(`[Button IDs] Erro no contexto ${name}:`, e);
        }
    });
}
applyButtonIds();
setTimeout(applyButtonIds, 100);
setTimeout(applyButtonIds, 500);
setTimeout(applyButtonIds, 1000);
setInterval(applyButtonIds, 2000);
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

df_main = utils.load_data()
if df_main.empty:
    st.error("❌ No data. Ensure `Balancer-All-Tokenomics.csv` is in `data/`.")
    st.stop()

if 'pool_filter_mode_votes' not in st.session_state:
    st.session_state.pool_filter_mode_votes = 'all'  

if 'version_filter_votes' not in st.session_state:
    st.session_state.version_filter_votes = 'all'  

if 'gauge_filter_votes' not in st.session_state:
    st.session_state.gauge_filter_votes = 'all'  

utils.show_version_filter('version_filter_votes')

utils.show_gauge_filter('gauge_filter_votes')

utils.show_pool_filters('pool_filter_mode_votes')

df_main = utils.show_date_filter_sidebar(df_main, key_prefix="date_filter_votes")

df_main = utils.apply_version_filter(df_main, 'version_filter_votes')

df_main = utils.apply_gauge_filter(df_main, 'gauge_filter_votes')

if df_main.empty:
    st.warning("No data in selected period. Adjust Year/Quarter or select «All».")

df_votes = utils.get_votes_by_pool_from_main_df(df_main)
if df_votes.empty:
    st.error("❌ No votes data in Balancer-Tokenomics (missing votes_received or pool_symbol).")
    st.stop()

df_display = df_votes.copy()
has_pool_symbol = 'pool_symbol' in df_display.columns

if st.session_state.pool_filter_mode_votes == 'top20':
    if has_pool_symbol and not df_main.empty:
        top_pools = utils.get_top_pools(df_main, n=20)
        top_list = [str(p).strip() for p in top_pools if pd.notna(p)]
        df_filtered = df_display[df_display['pool_symbol'].astype(str).str.strip().isin(top_list)].copy()
        if len(df_filtered) > 0:
            df_display = df_filtered
            st.info(f"📊 Top 20 Pools by protocol fees ({len(df_display)} pools, from Balancer-Tokenomics)")
        else:
            st.info(f"📊 Showing all ({len(df_display)} pools)")
    else:
        st.info(f"📊 Showing all ({len(df_display)} pools)")
elif st.session_state.pool_filter_mode_votes == 'worst20':
    if has_pool_symbol and not df_main.empty:
        worst_pools = utils.get_worst_pools(df_main, n=20)
        worst_list = [str(p).strip() for p in worst_pools if pd.notna(p)]
        df_filtered = df_display[df_display['pool_symbol'].astype(str).str.strip().isin(worst_list)].copy()
        if len(df_filtered) > 0:
            df_display = df_filtered
            st.info(f"📊 Worst 20 Pools by protocol fees ({len(df_display)} pools, from Balancer-Tokenomics)")
        else:
            st.info(f"📊 Showing all ({len(df_display)} pools)")
    else:
        st.info(f"📊 Showing all ({len(df_display)} pools)")
else:
    st.info(f"📊 Showing all ({len(df_display)} pools)")

total_gauges = len(df_display)

col_title, col_logout = st.columns([1, 0.1])
with col_title:
    st.markdown('<div class="page-title">🗳️ veBAL Votes Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">From Balancer-All-Tokenomics.csv • Votes by pool (votes_received) • Top/Worst 20 by protocol fees</div>', unsafe_allow_html=True)
with col_logout:
    utils.show_logout_button()

st.markdown("---")

st.markdown("### 📊 Key Metrics")

col1, col2, col3, col4 = st.columns(4)

total_votes = df_display['votes'].sum()
total_gauges = len(df_display)
top_gauge_votes = df_display['votes'].max()
top_gauge_pct = df_display['pct_votes'].max() * 100

with col1:
    st.metric("Total Votes", f"{total_votes:,.0f}", help="Total votes across all gauges")

with col2:
    st.metric("Total Gauges", f"{total_gauges:,}", help="Number of gauges receiving votes")

with col3:
    st.metric("Top Gauge Votes", f"{top_gauge_votes:,.0f}", help="Highest vote count for a single gauge")

with col4:
    st.metric("Top Gauge Share", f"{top_gauge_pct:.2f}%", help="Percentage of total votes for top gauge")

st.markdown("---")

st.markdown("### 🏆 Gauge Rankings")

tab1, tab2, tab3 = st.tabs(["📊 Top Gauges", "🥧 Vote Share", "📋 Full Table"])

with tab1:
    st.markdown("#### Top 20 Gauges by Votes")
    n_gauges = st.slider("Number of top gauges to display", 10, 50, 20, 5)
    top_n = df_display.nlargest(n_gauges, 'votes')
    
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=top_n['symbol_clean'].iloc[::-1], 
            x=top_n['votes'].iloc[::-1],
            orientation='h',
            marker=dict(
                color=top_n['votes'].iloc[::-1],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title=dict(text="Votes", font=dict(color='white')),
                    tickfont=dict(color='white')
                )
            ),
            text=[f"{v:,.0f}" for v in top_n['votes'].iloc[::-1]],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Votes: %{x:,.0f}<br>Share: %{customdata:.2f}%<extra></extra>',
            customdata=top_n['pct_votes'].iloc[::-1] * 100
        ))
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(font=dict(color='white', size=16)),
            xaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                title=dict(text="Votes", font=dict(color='#8B95A6'))
            ),
            yaxis=dict(
                gridcolor='rgba(255,255,255,0.1)',
                title="",
                tickfont=dict(size=10)
            ),
            height=600,
            margin=dict(l=200, r=50, t=20, b=50),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_chart2:
        st.markdown("**Top 5 Gauges**")
        top_5 = df_display.nlargest(5, 'votes')
        for idx, row in top_5.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 3px solid #67A2E1;">
                    <div style="font-weight: 600; color: #67A2E1; font-size: 0.9rem;">#{int(row['ranking'])} {row['symbol_clean'][:30]}</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: white; margin-top: 0.3rem;">{row['votes']:,.0f}</div>
                    <div style="font-size: 0.8rem; color: #8B95A6; margin-top: 0.2rem;">{row['pct_votes']*100:.2f}% share</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Table
    st.markdown("#### Detailed Rankings")
    top_n_display = top_n[['ranking', 'symbol_clean', 'votes', 'pct_votes']].copy()
    top_n_display['votes'] = top_n_display['votes'].apply(lambda x: f"{x:,.0f}")
    top_n_display['pct_votes'] = top_n_display['pct_votes'].apply(lambda x: f"{x*100:.2f}%")
    top_n_display.columns = ['Rank', 'Gauge', 'Votes', 'Share %']
    st.dataframe(top_n_display, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("#### Vote Share Visualization")
    
    n_top_pie = st.slider("Number of top gauges for pie chart", 5, 20, 10, 1)
    
    col_pie1, col_pie2 = st.columns(2)
    
    with col_pie1:
        top_n_pie = df_display.nlargest(n_top_pie, 'votes')
        others_votes = df_display['votes'].sum() - top_n_pie['votes'].sum()
        
        pie_data = top_n_pie.copy()
        if others_votes > 0:
            others_row = pd.DataFrame({
                'symbol_clean': ['Others'],
                'votes': [others_votes],
                'pct_votes': [others_votes / df_display['votes'].sum()]
            })
            pie_data = pd.concat([pie_data, others_row], ignore_index=True)
        
        fig_pie = px.pie(
            pie_data,
            values='votes',
            names='symbol_clean',
            title=f"Vote Share - Top {n_top_pie} Gauges",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Votes: %{value:,.0f}<br>Share: %{percent}<extra></extra>'
        )
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(font=dict(color='white', size=16)),
            legend=dict(
                bgcolor='rgba(0,0,0,0.5)',
                font=dict(size=10),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.1
            )
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_pie2:
        top_n_treemap = df_display.nlargest(15, 'votes')
        fig_treemap = px.treemap(
            top_n_treemap,
            path=['symbol_clean'],
            values='votes',
            title=f"Vote Distribution - Top 15 Gauges",
            color='votes',
            color_continuous_scale='Viridis'
        )
        fig_treemap.update_traces(
            textinfo='label+value+percent parent',
            hovertemplate='<b>%{label}</b><br>Votes: %{value:,.0f}<br>Share: %{percentParent:.2f}%<extra></extra>'
        )
        fig_treemap.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title=dict(font=dict(color='white', size=16))
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
    st.markdown("#### Cumulative Vote Distribution")
    df_sorted = df_display.sort_values('votes', ascending=False).copy()
    df_sorted['cumulative_pct'] = (df_sorted['votes'].cumsum() / df_sorted['votes'].sum() * 100)
    df_sorted['rank'] = range(1, len(df_sorted) + 1)
    
    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=df_sorted['rank'],
        y=df_sorted['cumulative_pct'],
        mode='lines',
        name='Cumulative %',
        line=dict(color='#67A2E1', width=2),
        fill='tozeroy',
        fillcolor='rgba(103, 162, 225, 0.1)',
        hovertemplate='Rank: %{x}<br>Cumulative: %{y:.2f}%<extra></extra>'
    ))
    
    # Add reference lines
    for pct in [25, 50, 75, 90]:
        rank_at_pct = df_sorted[df_sorted['cumulative_pct'] <= pct]['rank'].max()
        if not pd.isna(rank_at_pct):
            fig_cum.add_vline(
                x=rank_at_pct,
                line_dash="dash",
                line_color="rgba(255,255,255,0.3)",
                annotation_text=f"{pct}%",
                annotation_position="top"
            )
    
    fig_cum.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        title=dict(text="Cumulative Vote Percentage by Rank", font=dict(color='white', size=16)),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            title=dict(text="Gauge Rank", font=dict(color='#8B95A6'))
        ),
        yaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            title=dict(text="Cumulative % of Votes", font=dict(color='#8B95A6'))
        ),
        height=400,
        showlegend=False
    )
    st.plotly_chart(fig_cum, use_container_width=True)

with tab3:
    st.markdown("#### Full Gauge Rankings")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        search_term = st.text_input("🔍 Search pool id or gauge address", placeholder="Type pool id or gauge address...", key="search_gauge")
    
    with col_filter2:
        min_votes = st.number_input("Minimum votes", min_value=0.0, value=0.0, step=1000.0, key="min_votes")
    
    with col_filter3:
        min_share = st.number_input("Minimum share (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="min_share")
    
    display_df = df_display.copy()
    
    if search_term:
        mask_project = display_df['project_contract_address'].str.contains(search_term, case=False, na=False) if 'project_contract_address' in display_df.columns else False
        mask_gauge = display_df['gauge_address'].str.contains(search_term, case=False, na=False) if 'gauge_address' in display_df.columns else False
        display_df = display_df[mask_project | mask_gauge]
    
    if min_votes > 0:
        display_df = display_df[display_df['votes'] >= min_votes]
    
    if min_share > 0:
        display_df = display_df[display_df['pct_votes'] * 100 >= min_share]
    col_sort1, col_sort2 = st.columns(2)
    with col_sort1:
        sort_by = st.selectbox("Sort by", ['votes', 'ranking', 'pct_votes'], index=0, key="sort_by")
    with col_sort2:
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True, index=0, key="sort_order")
    
    display_df = display_df.sort_values(sort_by, ascending=(sort_order == "Ascending"))
    display_table = display_df[['ranking', 'symbol_clean', 'votes', 'pct_votes']].copy()
    display_table['votes'] = display_table['votes'].apply(lambda x: f"{x:,.0f}")
    display_table['pct_votes'] = display_table['pct_votes'].apply(lambda x: f"{x*100:.2f}%")
    display_table.columns = ['Rank', 'Pool', 'Votes', 'Share %']
    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
        height=600
    )
    st.caption(f"Showing {len(display_table)} of {len(df_display)} gauges")
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name=f'vebal_votes_filtered_{len(display_df)}.csv',
        mime='text/csv'
    )

st.markdown("---")

st.markdown("### 💡 Insights & Analysis")

col_insight1, col_insight2 = st.columns(2)

with col_insight1:
    st.markdown("#### 📊 Concentration Analysis")
    top_5_pct = (df_display.nlargest(5, 'votes')['votes'].sum() / total_votes * 100)
    top_10_pct = (df_display.nlargest(10, 'votes')['votes'].sum() / total_votes * 100)
    top_20_pct = (df_display.nlargest(20, 'votes')['votes'].sum() / total_votes * 100)
    
    st.metric("Top 5 Gauges Share", f"{top_5_pct:.1f}%")
    st.metric("Top 10 Gauges Share", f"{top_10_pct:.1f}%")
    st.metric("Top 20 Gauges Share", f"{top_20_pct:.1f}%")
    df_sorted_votes = df_display.sort_values('votes', ascending=True)
    n = len(df_sorted_votes)
    cumsum = df_sorted_votes['votes'].cumsum()
    gini = (2 * sum((i + 1) * v for i, v in enumerate(df_sorted_votes['votes']))) / (n * total_votes) - (n + 1) / n
    
    st.metric("Gini Coefficient", f"{gini:.3f}", help="0 = perfect equality, 1 = perfect inequality")
    
    if top_10_pct > 50:
        st.error("⚠️ **High concentration**: Top 10 gauges control majority of votes")
    elif top_10_pct > 30:
        st.warning("⚖️ **Moderate concentration** in top gauges")
    else:
        st.success("✅ Votes are relatively distributed")

with col_insight2:
    st.markdown("#### 🎯 Power Distribution")
    df_sorted_power = df_display.sort_values('votes', ascending=False)
    cumsum_power = df_sorted_power['votes'].cumsum()
    
    for target_pct in [50, 80, 90]:
        target_votes = total_votes * (target_pct / 100)
        n_gauges = len(cumsum_power[cumsum_power <= target_votes])
        if n_gauges == 0:
            n_gauges = 1
        st.metric(
            f"Gauges controlling {target_pct}%",
            f"{n_gauges}",
            help=f"Number of top gauges needed to control {target_pct}% of votes"
        )
    hhi = sum((df_display['pct_votes'] * 100) ** 2)
    st.metric("HHI Index", f"{hhi:.0f}", help="Higher HHI = more concentration (0-10000 scale)")
    
    if hhi > 2500:
        st.error("🔴 **High market concentration** (HHI > 2500)")
    elif hhi > 1500:
        st.warning("🟡 **Moderate concentration** (HHI 1500-2500)")
    else:
        st.success("🟢 **Low concentration** (HHI < 1500)")

