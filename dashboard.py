import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import os

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="N.D.A.I Dashboard", page_icon="🍗", layout="wide")
st.title("🍗 Tableau de Bord N.D.A.I - Armoric Fried Chicken")
st.markdown("*Plateforme hybride d'analyse des Ventes et du Sentiment Client*")
st.markdown("---")

# --- 2. CONNEXION À LA BASE DE DONNÉES ---
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "airflow")

@st.cache_resource
def get_engine():
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)

engine = get_engine()

# --- 3. CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=60)
def load_data():
    df_country = pd.read_sql("SELECT * FROM view_sales_by_country", engine)
    df_campaign = pd.read_sql("SELECT * FROM view_campaign_feedback_stats", engine)
    df_global = pd.read_sql("SELECT * FROM view_global_kpi", engine)

    df_country['sale_date'] = pd.to_datetime(df_country['sale_date'])
    df_campaign['feedback_date'] = pd.to_datetime(df_campaign['feedback_date'])
    df_global['date'] = pd.to_datetime(df_global['date'])
    return df_country, df_campaign, df_global

try:
    df_country, df_campaign, df_global = load_data()

    # --- 4. BARRE LATÉRALE (FILTRES DYNAMIQUES) ---
    st.sidebar.header("🔍 Filtres Globaux")

    # Date range selector with presets
    min_date = df_global['date'].min()
    max_date = df_global['date'].max()
    date_preset = st.sidebar.selectbox("Période prédéfinie", ["Personnalisée", "30 derniers jours", "90 derniers jours", "6 derniers mois", "Année en cours"], index=0)

    if date_preset == "Personnalisée":
        date_range = st.sidebar.date_input("Période", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        if date_preset == "30 derniers jours":
            date_range = (max_date - pd.Timedelta(days=30), max_date)
        elif date_preset == "90 derniers jours":
            date_range = (max_date - pd.Timedelta(days=90), max_date)
        elif date_preset == "6 derniers mois":
            date_range = (max_date - pd.Timedelta(days=180), max_date)
        else:
            date_range = (pd.to_datetime(f"{max_date.year}-01-01"), max_date)

    # Country / Product filters with search
    all_countries = sorted(df_country['country'].dropna().unique())
    selected_countries = st.sidebar.multiselect("Pays", all_countries, default=all_countries)

    all_products = sorted(df_global['product'].dropna().unique())
    selected_products = st.sidebar.multiselect("Produits", all_products, default=all_products)

    # Aggregation and top-N options
    agg_freq = st.sidebar.selectbox("Agrégation temporelle", ["D (Daily)", "W (Weekly)", "M (Monthly)"], index=0)
    top_n = st.sidebar.slider("Top N produits / campagnes", min_value=3, max_value=50, value=10)

    # Quick search for campaigns
    search_campaign = st.sidebar.text_input("Rechercher campagne (ID)")

    # --- 5. APPLICATION DES FILTRES ---
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    mask_country = (
        (df_country['sale_date'] >= start_date) &
        (df_country['sale_date'] <= end_date) &
        (df_country['country'].isin(selected_countries)) &
        (df_country['product'].isin(selected_products))
    )
    filtered_country = df_country[mask_country].copy()

    mask_campaign = (
        (df_campaign['feedback_date'] >= start_date) &
        (df_campaign['feedback_date'] <= end_date) &
        (df_campaign['product'].isin(selected_products))
    )
    filtered_campaign = df_campaign[mask_campaign].copy()

    if search_campaign:
        filtered_campaign = filtered_campaign[filtered_campaign['campaign_id'].str.contains(search_campaign, case=False, na=False)]

    mask_global = (
        (df_global['date'] >= start_date) &
        (df_global['date'] <= end_date) &
        (df_global['product'].isin(selected_products))
    )
    filtered_global = df_global[mask_global].copy()

    # --- 6. KPIS DYNAMIQUES ---
    st.header("📊 Vue d'Ensemble")
    col1, col2, col3, col4 = st.columns(4)

    total_rev = filtered_country['total_revenue'].sum()
    total_sold = filtered_country['total_sold'].sum()
    avg_sent = (filtered_campaign['avg_sentiment'].mean() * 100) if not filtered_campaign.empty else 0
    total_reviews = filtered_campaign['reviews_count'].sum()

    col1.metric("Chiffre d'Affaires", f"{total_rev:,.0f} $")
    col2.metric("Produits Vendus", f"{int(total_sold):,}")
    col3.metric("Satisfaction Globale", f"{avg_sent:.1f} %")
    col4.metric("Nombre d'Avis Reçus", f"{int(total_reviews):,}")

    st.markdown("---")

    # --- 7. NAVIGATION PAR ONGLETS ---
    tab1, tab2, tab3 = st.tabs(["💰 Ventes & Géo", "📣 Marketing & Campagnes", "🧠 Analyse Corrélationnelle"])

    # Helper: resample
    def resample_df(df, date_col, value_col, freq):
        if df.empty:
            return df
        df = df.set_index(pd.to_datetime(df[date_col]))
        return df.resample(freq).agg({value_col: 'sum'}).reset_index()

    # Map aggregation to pandas freq
    freq_map = {"D (Daily)": 'D', "W (Weekly)": 'W', "M (Monthly)": 'M'}
    pd_freq = freq_map.get(agg_freq, 'D')

    # ONGLET 1 : VENTES
    with tab1:
        st.subheader("Évolution du Chiffre d'Affaires")
        if not filtered_country.empty:
            sales_timeline = filtered_country.groupby('sale_date')["total_revenue"].sum().reset_index()
            fig_line = px.line(sales_timeline, x='sale_date', y='total_revenue', title='Chiffre d\'affaires dans le temps', markers=True)
            fig_line.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_line, use_container_width=True)

            colA, colB = st.columns((2,1))
            with colA:
                st.subheader("Top produits")
                prod_rank = filtered_country.groupby('product')["total_sold"].sum().reset_index().sort_values('total_sold', ascending=False).head(top_n)
                fig_prod = px.bar(prod_rank, x='product', y='total_sold', title=f'Top {top_n} produits', text='total_sold')
                fig_prod.update_layout(xaxis={'categoryorder':'total descending'}, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_prod, use_container_width=True)

            with colB:
                st.subheader("Répartition géographique")
                country_rank = filtered_country.groupby('country')["total_revenue"].sum().reset_index().sort_values('total_revenue', ascending=False).head(20)
                fig_country = px.pie(country_rank, names='country', values='total_revenue', title='CA par pays')
                st.plotly_chart(fig_country, use_container_width=True)

            st.markdown("---")
            st.subheader("Table de détail ventes")
            st.dataframe(filtered_country.sort_values(by='sale_date', ascending=False).reset_index(drop=True), use_container_width=True)
            csv = filtered_country.to_csv(index=False)
            st.download_button("Télécharger ventes (CSV)", csv, file_name='filtered_sales.csv', mime='text/csv')
        else:
            st.info("Aucune donnée de vente pour ces filtres.")

    # ONGLET 2 : MARKETING
    with tab2:
        st.subheader("Performance des Campagnes Publicitaires")
        if not filtered_campaign.empty:
            camp_perf = filtered_campaign.groupby('campaign_id')["avg_sentiment"].mean().reset_index()
            camp_perf['avg_sentiment_pct'] = camp_perf['avg_sentiment'] * 100
            camp_perf = camp_perf.sort_values('avg_sentiment_pct', ascending=False).head(top_n)

            fig_camp = px.bar(camp_perf, x='campaign_id', y='avg_sentiment_pct', color='avg_sentiment_pct', title=f'Top {top_n} campagnes par satisfaction', text='avg_sentiment_pct')
            fig_camp.update_layout(xaxis={'categoryorder':'total descending'}, yaxis_title='Satisfaction (%)')
            st.plotly_chart(fig_camp, use_container_width=True)

            st.subheader("Détail des retours")
            st.dataframe(filtered_campaign.sort_values(by='reviews_count', ascending=False).reset_index(drop=True), use_container_width=True)
            st.download_button("Télécharger retours (CSV)", filtered_campaign.to_csv(index=False), file_name='filtered_campaigns.csv', mime='text/csv')
        else:
            st.info("Aucune donnée marketing pour ces filtres.")

    # ONGLET 3 : CORRÉLATION
    with tab3:
        st.subheader("Impact de la satisfaction client sur le Chiffre d'Affaires")
        if not filtered_global.empty:
            fig_scatter = px.scatter(filtered_global, x='sentiment_score', y='total_revenue', color='product', size='total_sold', hover_data=['date', 'product'], title='Corrélation Sentiment vs CA')
            fig_scatter.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_scatter, use_container_width=True)

            st.subheader("Table de fusion (ventes + avis)")
            st.dataframe(filtered_global.sort_values(by='date', ascending=False).reset_index(drop=True), use_container_width=True)
            st.download_button("Télécharger fusion (CSV)", filtered_global.to_csv(index=False), file_name='global_kpi.csv', mime='text/csv')
        else:
            st.info("Pas assez de données pour établir une corrélation.")

except Exception as e:
    st.error(f"Erreur d'exécution : {e}")
