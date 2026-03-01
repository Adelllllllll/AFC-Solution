import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import os

# ─────────────────────────────────────────────
# 1. PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AFC Executive Dashboard",
    page_icon="🍗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 2. CUSTOM STYLING (Gris clair pour la Sidebar)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Sans:wght@400;500;700&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, .stMarkdown h1, .stMarkdown h2 { font-family: 'Syne', sans-serif !important; }

/* Dashboard Title */
.main-title { font-family: 'Syne', sans-serif; font-size: 1.8rem; font-weight: 700; color: #111827; margin-bottom: 0; padding-bottom: 0; }
.main-subtitle { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #4b5563; margin-top: 4px; }

/* KPI Cards */
.kpi-card { 
    background: #ffffff; border-radius: 12px; padding: 16px 12px; 
    border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
    display: flex; flex-direction: column; justify-content: center; align-items: flex-start;
    height: 100%; min-height: 110px;
}
.kpi-label { font-size: 0.7rem; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; line-height: 1.2; }
.kpi-value { font-family: 'Syne', sans-serif; font-size: 1.4rem; font-weight: 700; color: #111827; line-height: 1; margin: 0; }
.kpi-delta { font-size: 0.75rem; color: #059669; margin-top: 8px; font-weight: 600; }

/* --------------------------------------------------- */
/* SIDEBAR - NOUVEAU THEME GRIS CLAIR                  */
/* --------------------------------------------------- */
[data-testid="stSidebar"] { 
    background-color: #f8fafc !important; /* Gris très clair */
    border-right: 1px solid #e2e8f0; 
}
/* Titres de la sidebar en sombre */
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { 
    color: #0f172a !important; 
}
/* Paragraphes normaux de la sidebar */
[data-testid="stSidebar"] .stMarkdown p { 
    color: #334155 !important; 
}
/* Labels (titres des filtres) */
[data-testid="stSidebar"] label p { 
    color: #475569 !important; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; 
}
/* Style spécifique pour le texte des cases à cocher (Checkboxes) */
[data-testid="stSidebar"] .stCheckbox label p { 
    text-transform: none !important; font-weight: 500 !important; color: #1e293b !important; font-size: 0.85rem !important; 
}
/* On laisse Streamlit gérer les couleurs internes des menus déroulants automatiquement */

/* Tab styling */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #f1f5f9; padding: 4px; border-radius: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; padding: 6px 16px; font-weight: 500; font-size: 0.9rem; color: #475569 !important; }
.stTabs [aria-selected="true"] { color: #0f172a !important; background: #ffffff !important; box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important; font-weight: 700 !important; }

/* Insight Boxes */
.insight-box { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; }
.insight-box p { margin: 0; font-size: 0.85rem; color: #1e40af; }
.warn-box { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; }
.warn-box p { margin: 0; font-size: 0.85rem; color: #92400e; }
.success-box { background: #d1fae5; border-left: 4px solid #059669; padding: 12px 16px; border-radius: 4px; margin-bottom: 16px; }
.success-box p { margin: 0; font-size: 0.85rem; color: #065f46; }

.section-header { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 2px; }
.section-sub { font-size: 0.85rem; color: #64748b; margin-bottom: 16px; }
.divider { border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

BRAND_COLORS = ["#e85d04", "#f48c06", "#faa307", "#1d3557", "#457b9d", "#a8dadc", "#6d6875"]
CHART_TEMPLATE = "plotly_white"

# ─────────────────────────────────────────────
# 3. DATABASE CONNECTION & SQL VIEWS
# ─────────────────────────────────────────────
DB_USER     = os.getenv("POSTGRES_USER",     "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
DB_PORT     = os.getenv("POSTGRES_PORT",     "5432")
DB_NAME     = os.getenv("POSTGRES_DB",       "airflow")

@st.cache_resource
def get_engine():
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)

@st.cache_data(ttl=60)
def load_data_from_views(_engine):
    # Utilisation de st.status pour éviter le chargement infini visuel
    with st.status("📡 Connexion aux services de données...", expanded=True) as status:
        st.write("Vérification des vues SQL analytiques...")
        
        # Chargement séquentiel pour identifier précisément où ça bloque
        st.write("Chargement des ventes par pays...")
        df_country = pd.read_sql("SELECT * FROM view_sales_by_country", _engine)
        df_country['sale_date'] = pd.to_datetime(df_country['sale_date'])
        
        st.write("Analyse des sentiments IA...")
        df_campaign = pd.read_sql("SELECT * FROM view_campaign_feedback_stats", _engine)
        df_campaign['feedback_date'] = pd.to_datetime(df_campaign['feedback_date'])
        
        st.write("Calcul des KPIs globaux...")
        df_global = pd.read_sql("SELECT * FROM view_global_kpi", _engine)
        df_global['date'] = pd.to_datetime(df_global['date'])
        
        status.update(label="✅ Données prêtes !", state="complete", expanded=False)
    
    return df_country, df_campaign, df_global

# --- LOGIQUE DE FALLBACK ---
try:
    engine = get_engine()
    df_country, df_campaign, df_global = load_data_from_views(engine)
except Exception as e:
    st.error("### ❌ Données non disponibles")
    st.markdown(f"""
    Le Dashboard ne peut pas afficher les graphiques car les **vues SQL analytiques** sont manquantes ou vides.
    
    **Pour résoudre ce problème, suivez ces étapes :**
    1. Vérifiez que vous avez bien poussé les données avec le script `api_pusher`.
    2. Allez sur **Airflow** ([http://localhost:8081](http://localhost:8081)).
    3. Lancez votre **DAG principal** manuellement.
    4. **ATTENDEZ** que toutes les tâches soient de couleur **verte** (cela crée les vues SQL).
    5. Une fois le DAG terminé, rafraîchissez cette page.
    
    *Détail technique : {e}*
    """)
    st.stop() # Arrête l'exécution du reste du dashboard

# ─────────────────────────────────────────────
# 4. SIDEBAR FILTERS (NOUVELLES CHECKBOXES)
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍗 AFC Dashboard")
    st.markdown("---")

    if not df_country.empty:
        min_date = df_country['sale_date'].min()
        max_date = df_country['sale_date'].max()
    else:
        min_date = pd.to_datetime("2024-01-01")
        max_date = pd.to_datetime("today")

    date_preset = st.selectbox(
        "Date Range",
        ["All time", "Last 30 days", "Last 90 days", "Last 6 months", "Current year"],
        index=0,
    )

    if date_preset == "Last 30 days":
        date_range = (max_date - pd.Timedelta(days=30), max_date)
    elif date_preset == "Last 90 days":
        date_range = (max_date - pd.Timedelta(days=90), max_date)
    elif date_preset == "Last 6 months":
        date_range = (max_date - pd.Timedelta(days=180), max_date)
    elif date_preset == "Current year":
        date_range = (pd.to_datetime(f"{max_date.year}-01-01"), max_date)
    else:
        date_range = (min_date, max_date)

    # Sélection des pays par Cases à cocher
    all_countries = sorted(df_country['country'].dropna().unique()) if not df_country.empty else []
    
    with st.expander("🌍 COUNTRIES", expanded=True):
        col_c1, col_c2 = st.columns(2)
        if col_c1.button("Select All", key="btn_all_c"):
            for c in all_countries: st.session_state[f"chk_c_{c}"] = True
        if col_c2.button("Clear", key="btn_clr_c"):
            for c in all_countries: st.session_state[f"chk_c_{c}"] = False
            
        selected_countries = []
        for country in all_countries:
            # Initialisation de la case à True par défaut si elle n'existe pas en session
            if f"chk_c_{country}" not in st.session_state:
                st.session_state[f"chk_c_{country}"] = True
            if st.checkbox(country, key=f"chk_c_{country}"):
                selected_countries.append(country)

    # Sélection des produits par Cases à cocher
    all_products = sorted(df_country['product'].dropna().unique()) if not df_country.empty else []
    
    with st.expander("🍗 PRODUCTS", expanded=True):
        col_p1, col_p2 = st.columns(2)
        if col_p1.button("Select All", key="btn_all_p"):
            for p in all_products: st.session_state[f"chk_p_{p}"] = True
        if col_p2.button("Clear", key="btn_clr_p"):
            for p in all_products: st.session_state[f"chk_p_{p}"] = False
            
        selected_products = []
        for product in all_products:
            # Initialisation de la case à True par défaut si elle n'existe pas en session
            if f"chk_p_{product}" not in st.session_state:
                st.session_state[f"chk_p_{product}"] = True
            if st.checkbox(product, key=f"chk_p_{product}"):
                selected_products.append(product)

    agg_freq_label = st.selectbox("Time Aggregation", ["Daily", "Weekly", "Monthly"], index=2)
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "MS"}
    pd_freq = freq_map[agg_freq_label]

    top_n = st.slider("Top N (charts)", min_value=3, max_value=20, value=7)

    st.markdown("---")
    st.caption("Armoric Fried Chicken · Executive BI")


# ─────────────────────────────────────────────
# 5. APPLY FILTERS (SUR LES VUES SQL)
# ─────────────────────────────────────────────
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date = end_date = pd.to_datetime(date_range)

if not df_country.empty:
    mask_country = (
        (df_country['sale_date'] >= start_date) &
        (df_country['sale_date'] <= end_date) &
        (df_country['country'].isin(selected_countries)) &
        (df_country['product'].isin(selected_products))
    )
    fs = df_country[mask_country].copy()
else:
    fs = df_country.copy()

if not df_campaign.empty:
    mask_campaign = (
        (df_campaign['feedback_date'] >= start_date) &
        (df_campaign['feedback_date'] <= end_date) &
        (df_campaign['product'].isin(selected_products))
    )
    fc_feedbacks = df_campaign[mask_campaign].copy()
else:
    fc_feedbacks = df_campaign.copy()

if not df_global.empty:
    mask_global = (
        (df_global['date'] >= start_date) &
        (df_global['date'] <= end_date) &
        (df_global['product'].isin(selected_products))
    )
    fc = df_global[mask_global & df_global['campaign_id'].notna()].copy()
else:
    fc = df_global.copy()

# ─────────────────────────────────────────────
# 6. HEADER & KPI ROW
# ─────────────────────────────────────────────
st.markdown(
    '<p class="main-title">🍗 Armoric Fried Chicken — Executive Dashboard</p>'
    '<p class="main-subtitle">Sales performance, campaign intelligence & Sentiment Analysis · All figures in USD</p>',
    unsafe_allow_html=True
)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

total_revenue  = fs['total_revenue'].sum() if not fs.empty else 0
total_units    = fs['total_sold'].sum() if not fs.empty else 0
avg_order_val  = total_revenue / total_units if total_units > 0 else 0
active_markets = fs['country'].nunique() if not fs.empty else 0
top_product    = fs.groupby('product')['total_revenue'].sum().idxmax() if not fs.empty else "—"
active_camps   = fc['campaign_id'].nunique() if not fc.empty else 0

avg_sentiment_pct = (fc_feedbacks['avg_sentiment'].mean() * 100) if not fc_feedbacks.empty else 0

def kpi_card(label, value, note=""):
    note_html = f'<p class="kpi-delta">{note}</p>' if note else ""
    return f"""
    <div class="kpi-card">
        <p class="kpi-label">{label}</p>
        <p class="kpi-value">{value}</p>
        {note_html}
    </div>
    """

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.markdown(kpi_card("Total Revenue",    f"${total_revenue:,.0f}"), unsafe_allow_html=True)
col2.markdown(kpi_card("Units Sold",       f"{total_units:,}"),       unsafe_allow_html=True)
col3.markdown(kpi_card("Avg Order Value",  f"${avg_order_val:,.0f}"), unsafe_allow_html=True)
col4.markdown(kpi_card("Active Markets",   f"{active_markets}"),      unsafe_allow_html=True)
col5.markdown(kpi_card("Top Product",      top_product),              unsafe_allow_html=True)
col6.markdown(kpi_card("Customer Sentiment", f"{avg_sentiment_pct:.1f}%"), unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)
# ─────────────────────────────────────────────
# 8. TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "💰  Sales Performance",
    "📣  Campaign Impact & AI",
    "🌍  Market & Product Deep Dive",
])

# ══════════════════════════════════════════════
# TAB 1 – SALES PERFORMANCE (Basé sur la Vue Pays)
# ══════════════════════════════════════════════
with tab1:
    if fs.empty:
        st.info("No sales data for current filters.")
    else:
        # ── Revenue over time ──────────────────
        st.markdown('<p class="section-header">Revenue Trend</p>'
                    '<p class="section-sub">How is overall revenue evolving?</p>',
                    unsafe_allow_html=True)

        trend = (
            fs.set_index('sale_date')
            .resample(pd_freq)['total_revenue']
            .sum()
            .reset_index()
        )
        fig_trend = px.area(
            trend, x='sale_date', y='total_revenue',
            labels={'sale_date': 'Date', 'total_revenue': 'Revenue (USD)'},
            color_discrete_sequence=[BRAND_COLORS[0]],
            template=CHART_TEMPLATE,
        )
        fig_trend.update_traces(fill='tozeroy', line_width=2)
        fig_trend.update_layout(
            height=280, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title=None, yaxis_title="Revenue (USD)",
            font_family="DM Sans",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Product performance + Country revenue ─
        colA, colB = st.columns([3, 2])

        with colA:
            st.markdown('<p class="section-header">Top Products by Revenue</p>'
                        '<p class="section-sub">Which products drive the most value?</p>',
                        unsafe_allow_html=True)

            prod_rev = (
                fs.groupby('product')
                .agg(revenue=('total_revenue', 'sum'), units=('total_sold', 'sum'))
                .reset_index()
                .sort_values('revenue', ascending=True)
                .tail(top_n)
            )
            fig_prod = px.bar(
                prod_rev, y='product', x='revenue', orientation='h',
                color='revenue', color_continuous_scale=['#faa307', '#e85d04'],
                text=prod_rev['revenue'].apply(lambda v: f"${v:,.0f}"),
                template=CHART_TEMPLATE,
                labels={'revenue': 'Revenue (USD)', 'product': ''},
            )
            fig_prod.update_traces(textposition='outside', cliponaxis=False)
            fig_prod.update_coloraxes(showscale=False)
            fig_prod.update_layout(
                height=320, margin=dict(l=0, r=80, t=10, b=0),
                font_family="DM Sans",
            )
            st.plotly_chart(fig_prod, use_container_width=True)

            total = prod_rev['revenue'].sum()
            top = prod_rev.iloc[-1]
            share = top['revenue'] / total * 100 if total else 0
            st.markdown(
                f'<div class="insight-box"><p>📌 <strong>{top["product"]}</strong> generates '
                f'<strong>{share:.0f}%</strong> of revenue among selected products — '
                f'your highest-performing SKU.</p></div>',
                unsafe_allow_html=True
            )

        with colB:
            st.markdown('<p class="section-header">Revenue by Country</p>'
                        '<p class="section-sub">Where are sales strongest?</p>',
                        unsafe_allow_html=True)

            country_rev = (
                fs.groupby('country')['total_revenue'].sum()
                .reset_index()
                .sort_values('total_revenue', ascending=False)
                .head(top_n)
            )
            fig_geo = px.bar(
                country_rev, x='country', y='total_revenue',
                color='country', color_discrete_sequence=BRAND_COLORS,
                text=country_rev['total_revenue'].apply(lambda v: f"${v/1e3:.0f}k"),
                template=CHART_TEMPLATE,
                labels={'total_revenue': 'Revenue (USD)', 'country': ''},
            )
            fig_geo.update_traces(textposition='outside', cliponaxis=False)
            fig_geo.update_layout(
                showlegend=False, height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                font_family="DM Sans",
            )
            st.plotly_chart(fig_geo, use_container_width=True)

            if not country_rev.empty:
                top_country = country_rev.iloc[0]
                share_c = top_country['total_revenue'] / country_rev['total_revenue'].sum() * 100
                st.markdown(
                    f'<div class="success-box"><p>🌍 <strong>{top_country["country"]}</strong> leads '
                    f'with <strong>{share_c:.0f}%</strong> of total revenue in the selected period.</p></div>',
                    unsafe_allow_html=True
                )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Monthly heatmap ──────────────────────
        st.markdown('<p class="section-header">Revenue Heatmap — Product × Month</p>'
                    '<p class="section-sub">Which products are seasonal? Where are the gaps?</p>',
                    unsafe_allow_html=True)

        heat_df = fs.copy()
        heat_df['month'] = heat_df['sale_date'].dt.to_period('M').astype(str)
        pivot = heat_df.groupby(['product', 'month'])['total_revenue'].sum().unstack(fill_value=0)

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale=["#fff7ed", "#fed7aa", "#e85d04"],
            aspect='auto',
            template=CHART_TEMPLATE,
            labels=dict(x="Month", y="Product", color="Revenue"),
        )
        fig_heat.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=0),
            font_family="DM Sans", coloraxis_colorbar_title="USD",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Raw data ────────────────────────────
        with st.expander("📋 View raw sales data"):
            st.dataframe(
                fs.sort_values('sale_date', ascending=False).reset_index(drop=True),
                use_container_width=True,
            )
            st.download_button(
                "⬇ Download CSV", fs.to_csv(index=False),
                file_name="filtered_sales.csv", mime="text/csv",
            )

# ══════════════════════════════════════════════
# TAB 2 – CAMPAIGN IMPACT & AI (Basé sur la Vue Globale)
# ══════════════════════════════════════════════
with tab2:
    if fc.empty:
        st.info("No campaign data for selected products in this date range.")
    else:
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
            'padding:10px 16px;margin-bottom:20px;display:flex;align-items:center;gap:10px;">'
            '<span style="font-size:1rem;">🤖</span>'
            '<span style="font-size:0.82rem;color:#475569;">'
            '<strong style="color:#1e293b;">AI NLP Integration:</strong> '
            'Customer sentiments are dynamically analyzed. The chart below cross-references sales revenue with AI sentiment scores to identify if happier customers drive higher sales.'
            '</span></div>',
            unsafe_allow_html=True
        )

        # ── AI Sentiment Trend vs. Sales Volume ──
        st.markdown('<p class="section-header">AI Sentiment Analysis vs Sales Trend</p>'
                    '<p class="section-sub">Dynamic correlation: Evaluating how qualitative customer perception influences daily transaction volume.</p>',
                    unsafe_allow_html=True)
        
        # 1. Extracting Revenue Trend from Sales view
        rev_trend = (
            fs.groupby(pd.Grouper(key='sale_date', freq=pd_freq))['total_revenue']
            .sum().reset_index()
        )

        # 2. Extracting Sentiment Trend from Feedback view (Excluding null days to avoid bias)
        sent_trend = (
            fc_feedbacks.groupby(pd.Grouper(key='feedback_date', freq=pd_freq))['avg_sentiment']
            .mean().reset_index()
        )
        
        # 3. Synchronizing data on time axis for visualization
        corr_data = rev_trend.merge(
            sent_trend, left_on='sale_date', right_on='feedback_date', how='left'
        )
        
        # Creating the heatmap bar chart
        fig_corr = px.bar(
            corr_data, x='sale_date', y='total_revenue', color='avg_sentiment',
            color_continuous_scale=["#dc2626", "#fbbf24", "#10b981"], # Red (Negative) -> Green (Positive)
            range_color=[0, 1], # Normalizing AI score from 0.0 to 1.0
            template=CHART_TEMPLATE,
            labels={'sale_date': 'Timeline', 'total_revenue': 'Revenue (USD)', 'avg_sentiment': 'Mean Sentiment'}
        )

        # Applying Executive Dashboard styling
        fig_corr.update_layout(
            height=320, 
            margin=dict(l=0, r=0, t=10, b=0), 
            font_family="DM Sans",
            coloraxis_colorbar=dict(
                title="AI Score",
                tickformat=".0%", # Displays as percentage (e.g. 50%)
                thickness=15
            ),
            xaxis_title=None
        )
        st.plotly_chart(fig_corr, use_container_width=True)


        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # Agrégation par Campagne
        camp_agg = fc.groupby(['campaign_id', 'product']).agg(
            total_revenue=('total_revenue', 'sum'), 
            total_sold=('total_sold', 'sum')
        ).reset_index()


        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Top campaigns by revenue (Horizontal - Pleine largeur) ─────────────
        st.markdown('<p class="section-header">Top Campaigns by Attributed Revenue</p>'
                    '<p class="section-sub">Which campaigns generate the most sales, and how are they perceived?</p>',
                    unsafe_allow_html=True)

        # 1. Extracting total revenue per campaign and keeping the Top N
        top_camps_rev = camp_agg.groupby('campaign_id')['total_revenue'].sum().reset_index()
        top_camps_rev = top_camps_rev.sort_values('total_revenue', ascending=True).tail(top_n)
        
        # 2. Merging with AI Sentiment scores to enable heatmap coloring
        sentiment_stats = df_campaign.groupby('campaign_id')['avg_sentiment'].mean().reset_index()
        top_camps = top_camps_rev.merge(sentiment_stats, on='campaign_id', how='left')
        
        # 3. Generating the bar chart with thermal color scale (Red to Green)
        fig_camps = px.bar(
            top_camps, y='campaign_id', x='total_revenue', orientation='h',
            color='avg_sentiment',
            color_continuous_scale=["#dc2626", "#fbbf24", "#10b981"], # Red -> Yellow -> Green
            range_color=[0, 1], # Normalizing AI score
            text=top_camps['total_revenue'].apply(lambda v: f"${v/1e3:.1f}k"),
            template=CHART_TEMPLATE,
            labels={'total_revenue': 'Revenue (USD)', 'campaign_id': '', 'avg_sentiment': 'Mean Sentiment'},
        )
        fig_camps.update_traces(textposition='outside', cliponaxis=False)
        fig_camps.update_layout(
            height=340, margin=dict(l=0, r=40, t=10, b=0), font_family="DM Sans",
            coloraxis_colorbar=dict(title="AI Score", tickformat=".0%", thickness=15)
        )
        st.plotly_chart(fig_camps, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Revenue by product via campaigns (Lollipop - Pleine largeur) ────
        st.markdown('<p class="section-header">Campaign-Attributed Revenue by Product</p>'
                    '<p class="section-sub">Which products benefit most?</p>',
                    unsafe_allow_html=True)

        prod_camp_rev = camp_agg.groupby('product')['total_revenue'].sum().reset_index().sort_values('total_revenue', ascending=True)
        
        fig_pc = go.Figure()
        for i, row in prod_camp_rev.iterrows():
            fig_pc.add_trace(go.Scatter(
                x=[0, row['total_revenue']], y=[row['product'], row['product']],
                mode='lines', line=dict(color="#cbd5e1", width=3), showlegend=False, hoverinfo='skip'
            ))
            fig_pc.add_trace(go.Scatter(
                x=[row['total_revenue']], y=[row['product']],
                mode='markers+text', marker=dict(color=BRAND_COLORS[1], size=14),
                text=[f"${row['total_revenue']/1e3:.1f}k"], textposition="middle right",
                showlegend=False, name=row['product']
            ))
            
        fig_pc.update_layout(
            template=CHART_TEMPLATE, height=340, margin=dict(l=0, r=60, t=10, b=0),
            xaxis=dict(showgrid=True, title="Revenue (USD)"), yaxis=dict(title=""),
            font_family="DM Sans"
        )
        st.plotly_chart(fig_pc, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)


        # ── Campaign density per product ────────
        st.markdown('<p class="section-header">Campaign Density vs. Revenue per Product</p>'
                    '<p class="section-sub">Do products with more campaigns earn more?</p>',
                    unsafe_allow_html=True)

        prod_summary = camp_agg.groupby('product').agg(
            total_revenue=('total_revenue', 'sum'),
            total_sold=('total_sold', 'sum'),
            num_campaigns=('campaign_id', 'nunique')
        ).reset_index()
        prod_summary['rev_per_camp'] = prod_summary['total_revenue'] / prod_summary['num_campaigns']

        fig_bubble = px.scatter(
            prod_summary, x='num_campaigns', y='total_revenue',
            size='total_sold', color='product', text='product',
            color_discrete_sequence=BRAND_COLORS, template=CHART_TEMPLATE,
            labels={'num_campaigns': 'Number of Campaigns', 'total_revenue': 'Total Revenue (USD)', 'total_sold': 'Units Sold', 'product': 'Product'},
        )
        
        max_sold = prod_summary['total_sold'].max() if not prod_summary.empty else 1
        max_sold = max_sold if max_sold > 0 else 1 

        fig_bubble.update_traces(
            textposition='top center',
            marker=dict(sizemode='area', sizeref=2. * max_sold / (40. ** 2)),
        )
        fig_bubble.update_layout(
            height=380, margin=dict(l=0, r=0, t=10, b=0),
            font_family="DM Sans", showlegend=False,
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

        if not prod_summary.empty:
            most_eff = prod_summary.sort_values('rev_per_camp', ascending=False).iloc[0]
            least_eff = prod_summary.sort_values('rev_per_camp').iloc[0]
            st.markdown(
                f'<div class="success-box"><p>🏆 <strong>{most_eff["product"]}</strong> delivers '
                f'<strong>${most_eff["rev_per_camp"]:,.0f}</strong> revenue per campaign.</p></div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="warn-box"><p>⚠️ <strong>{least_eff["product"]}</strong> earns only '
                f'<strong>${least_eff["rev_per_camp"]:,.0f}</strong> per campaign.</p></div>',
                unsafe_allow_html=True
            )

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── 1. Macro Correlation: Sentiment vs. Revenue by PRODUCT ──
        st.markdown('<p class="section-header">Macro View: AI Sentiment vs. Revenue per Product</p>'
                    '<p class="section-sub">Which products combine high financial performance and high customer satisfaction?</p>',
                    unsafe_allow_html=True)

        # Revenue and Sentiment aggregated at the PRODUCT level
        prod_revenue_stats = fc.groupby('product')['total_revenue'].sum().reset_index()
        prod_sentiment_stats = df_campaign.groupby('product')['avg_sentiment'].mean().reset_index()
        prod_stats = prod_revenue_stats.merge(prod_sentiment_stats, on='product')

        fig_prod_bubble = px.scatter(
            prod_stats, x='avg_sentiment', y='total_revenue', size='total_revenue', 
            color='product', hover_name='product', text='product', 
            color_discrete_sequence=BRAND_COLORS, template=CHART_TEMPLATE,
            labels={'avg_sentiment': 'Mean AI Sentiment (0.0 - 1.0)', 'total_revenue': 'Total Revenue (USD)', 'product': 'Product'}
        )

        fig_prod_bubble.update_traces(
            textposition='top center',
            marker=dict(
                sizemode='area', 
                sizeref=2. * prod_stats['total_revenue'].max() / (60. ** 2) if not prod_stats.empty else 1,
                line=dict(width=1, color='white') 
            )
        )

        fig_prod_bubble.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=0), font_family="DM Sans", showlegend=False,
            xaxis=dict(gridcolor='#f1f5f9', zeroline=False, range=[-0.05, 1.05]), 
            yaxis=dict(gridcolor='#f1f5f9', zeroline=False)
        )

        # Magic Quadrant lines for Products
        if not prod_stats.empty:
            fig_prod_bubble.add_vline(x=prod_stats['avg_sentiment'].mean(), line_dash="dash", line_color="#94a3b8", annotation_text="Avg Sentiment")
            fig_prod_bubble.add_hline(y=prod_stats['total_revenue'].mean(), line_dash="dash", line_color="#94a3b8", annotation_text="Avg Revenue")

        st.plotly_chart(fig_prod_bubble, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── 2. Micro Correlation: Campaign Satisfaction Drill-down ──

        st.markdown('<p class="section-header">Micro View: Campaign Satisfaction Drill-down</p>'
                    '<p class="section-sub">Select a specific product to rank its campaigns by AI Customer Satisfaction.</p>',
                    unsafe_allow_html=True)

        # 1. Le selectbox pour choisir le produit
        selected_prod = st.selectbox("🎯 Select Product to analyze:", all_products, index=0)

        # 2. On filtre les données pour ce produit
        drill_data = camp_agg[camp_agg['product'] == selected_prod].copy()

        # On a besoin des sentiments (on refait la jointure avec df_campaign)
        sentiment_drill = df_campaign[df_campaign['product'] == selected_prod].groupby('campaign_id')['avg_sentiment'].mean().reset_index()
        drill_data = drill_data.merge(sentiment_drill, on='campaign_id', how='left').fillna(0)

        # NOUVEAU : On trie par SATISFACTION décroissante (les meilleures campagnes en premier)
        drill_data = drill_data.sort_values('avg_sentiment', ascending=False)
        
        # On prépare le texte en pourcentage pour l'affichage
        drill_data['sentiment_text'] = drill_data['avg_sentiment'].apply(lambda v: f"{v*100:.1f}%")

        # 3. Le Bar Chart Vertical
        fig_drill = px.bar(
            drill_data, 
            x='campaign_id', 
            y='avg_sentiment',
            color='avg_sentiment',
            # Échelle de couleurs : Rouge (Négatif) -> Jaune (Neutre) -> Vert (Positif)
            color_continuous_scale=["#ef4444", "#fcd34d", "#10b981"],
            range_color=[0, 1],
            text='sentiment_text',
            labels={'campaign_id': 'Campaign', 'avg_sentiment': 'AI Sentiment Score'},
            template=CHART_TEMPLATE
        )

        # On place le pourcentage juste au-dessus de la barre
        fig_drill.update_traces(textposition='outside', cliponaxis=False)
        
        fig_drill.update_layout(
            height=400, 
            margin=dict(l=0, r=0, t=20, b=0),
            font_family="DM Sans",
            # On monte l'axe Y à 1.15 (115%) pour laisser de la place au texte au-dessus des barres
            yaxis=dict(tickformat=".0%", range=[0, 1.15], title="AI Sentiment (%)"), 
            xaxis=dict(type='category', title=""), 
            coloraxis_colorbar=dict(
                title="NLP Score",
                tickformat=".0%" 
            )
        )
        st.plotly_chart(fig_drill, use_container_width=True)


        
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── 3. Campaign Health Portfolio (Executive Summary) ──
        st.markdown('<p class="section-header">Campaign Portfolio Health</p>'
                    '<p class="section-sub">Overall classification of campaigns based on AI satisfaction thresholds.</p>',
                    unsafe_allow_html=True)

        # 1. On récupère la moyenne de sentiment pour toutes les campagnes affichées
        health_stats = df_campaign[df_campaign['product'].isin(selected_products)].groupby('campaign_id')['avg_sentiment'].mean().reset_index()

        # 2. Fonction de classification (Thresholds)
        def categorize_sentiment(score):
            if score >= 0.70: return "Excellent (≥70%)"
            elif score >= 0.40: return "Average (40-69%)"
            else: return "Critical (<40%)"

        if not health_stats.empty:
            health_stats['Health'] = health_stats['avg_sentiment'].apply(categorize_sentiment)
            health_dist = health_stats['Health'].value_counts().reset_index()
            health_dist.columns = ['Health Category', 'Number of Campaigns']

            # 3. Couleurs strictes pour la lecture exécutive
            color_map = {
                "Excellent (≥70%)": "#10b981", # Vert
                "Average (40-69%)": "#fbbf24", # Jaune/Orange
                "Critical (<40%)": "#ef4444"   # Rouge
            }

            fig_health = px.pie(
                health_dist, names='Health Category', values='Number of Campaigns',
                color='Health Category', color_discrete_map=color_map,
                hole=0.6, template=CHART_TEMPLATE
            )

            # 4. Design du Donut avec texte central
            fig_health.update_traces(
                textinfo='percent+value', 
                textfont_size=14,
                hovertemplate="<b>%{label}</b><br>Campaigns: %{value}<br>Share: %{percent}<extra></extra>"
            )
            
            fig_health.update_layout(
                height=380, margin=dict(l=0, r=0, t=10, b=0), font_family="DM Sans",
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                annotations=[dict(text='Portfolio<br>Health', x=0.5, y=0.5, font_size=18, font_weight="bold", showarrow=False)]
            )

            st.plotly_chart(fig_health, use_container_width=True)
        else:
            st.info("No data to display portfolio health.")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)


        
        # ── Revenue per campaign table ───────────
        st.markdown('<p class="section-header">Campaign Performance Table</p>', unsafe_allow_html=True)
        
        # 1. Agrégation financière de base
        display_camp = camp_agg.groupby('campaign_id').agg({
            'total_revenue': 'sum', 
            'total_sold': 'sum', 
            'product': 'first'
        }).reset_index()

        # 2. Récupération du sentiment moyen (depuis df_campaign pour la précision)
        sentiment_for_table = df_campaign.groupby('campaign_id')['avg_sentiment'].mean().reset_index()
        
        # 3. Jointure des deux tables
        display_camp = display_camp.merge(sentiment_for_table, on='campaign_id', how='left').fillna(0)
        
        # 4. Tri par revenu décroissant
        display_camp = display_camp.sort_values('total_revenue', ascending=False)
        
        # 5. Renommage des colonnes
        display_camp.columns = ['Campaign ID', 'Total Revenue (USD)', 'Units Sold', 'Product', 'AI Sentiment']
        
        # 6. Formatage visuel pour le tableau
        display_camp['Total Revenue (USD)'] = display_camp['Total Revenue (USD)'].apply(lambda v: f"${v:,.0f}")
        display_camp['Units Sold'] = display_camp['Units Sold'].apply(lambda v: f"{v:,}")
        display_camp['AI Sentiment'] = display_camp['AI Sentiment'].apply(lambda v: f"{v*100:.1f}%")
        
        # Affichage
        st.dataframe(display_camp, use_container_width=True, height=280)

# ══════════════════════════════════════════════
# TAB 3 – MARKET & PRODUCT DEEP DIVE (Basé sur la Vue Pays)
# ══════════════════════════════════════════════
with tab3:
    if fs.empty:
        st.info("No data available for current filters.")
    else:
        colP, colC = st.columns([2, 3])

        # ── Product revenue share (treemap) ─────
        with colP:
            st.markdown('<p class="section-header">Product Revenue Share</p>'
                        '<p class="section-sub">Portfolio composition at a glance.</p>',
                        unsafe_allow_html=True)

            prod_share = fs.groupby('product')['total_revenue'].sum().reset_index()
            fig_tree = px.treemap(
                prod_share, path=['product'], values='total_revenue',
                color='total_revenue', color_continuous_scale=["#fed7aa", "#e85d04"],
                template=CHART_TEMPLATE,
            )
            fig_tree.update_traces(textinfo='label+percent entry')
            fig_tree.update_coloraxes(showscale=False)
            fig_tree.update_layout(
                height=360, margin=dict(l=0, r=0, t=10, b=0), font_family="DM Sans",
            )
            st.plotly_chart(fig_tree, use_container_width=True)

        # ── Country × Product revenue matrix ────
        with colC:
            st.markdown('<p class="section-header">Country × Product Revenue Matrix</p>'
                        '<p class="section-sub">Where do specific products perform best?</p>',
                        unsafe_allow_html=True)

            matrix = fs.groupby(['country', 'product'])['total_revenue'].sum().unstack(fill_value=0)
            fig_mat = px.imshow(
                matrix, color_continuous_scale=["#fff7ed", "#fed7aa", "#c44b04"],
                aspect='auto', template=CHART_TEMPLATE,
                labels=dict(x="Product", y="Country", color="Revenue"),
            )
            fig_mat.update_layout(
                height=360, margin=dict(l=0, r=0, t=10, b=0),
                font_family="DM Sans", xaxis_tickangle=-30,
            )
            st.plotly_chart(fig_mat, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Units sold by country over time ─────
        st.markdown('<p class="section-header">Units Sold by Country Over Time</p>'
                    '<p class="section-sub">Track market momentum across geographies.</p>',
                    unsafe_allow_html=True)

        timeline_c = (
            fs.set_index('sale_date')
            .groupby([pd.Grouper(freq=pd_freq), 'country'])['total_sold']
            .sum().reset_index()
        )
        timeline_c.columns = ['date', 'country', 'units']

        fig_tl_c = px.line(
            timeline_c, x='date', y='units', color='country',
            color_discrete_sequence=BRAND_COLORS, template=CHART_TEMPLATE,
            labels={'date': 'Date', 'units': 'Units Sold', 'country': 'Country'},
        )
        fig_tl_c.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=0),
            font_family="DM Sans", legend=dict(orientation='h', yanchor='bottom', y=-0.35),
        )
        st.plotly_chart(fig_tl_c, use_container_width=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ── Product volume trend ────────────────
        st.markdown('<p class="section-header">Product Volume Over Time</p>'
                    '<p class="section-sub">Which products are trending up or declining?</p>',
                    unsafe_allow_html=True)

        timeline_p = (
            fs.set_index('sale_date')
            .groupby([pd.Grouper(freq=pd_freq), 'product'])['total_sold']
            .sum().reset_index()
        )
        timeline_p.columns = ['date', 'product', 'units']

        fig_tl_p = px.area(
            timeline_p, x='date', y='units', color='product',
            color_discrete_sequence=BRAND_COLORS, template=CHART_TEMPLATE,
            labels={'date': 'Date', 'units': 'Units Sold', 'product': 'Product'},
        )
        fig_tl_p.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=0),
            font_family="DM Sans", legend=dict(orientation='h', yanchor='bottom', y=-0.35),
        )
        st.plotly_chart(fig_tl_p, use_container_width=True)

# ─────────────────────────────────────────────
# 9. FOOTER
# ─────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align:center;font-size:0.75rem;color:#9ca3af;">'
    'N.D.A.I · Armoric Fried Chicken · Executive Business Intelligence · Internal Use Only'
    '</p>',
    unsafe_allow_html=True,
)