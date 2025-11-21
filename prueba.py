import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Profesional de Vuelos",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Dashboard Profesional de Vuelos")
st.markdown("Análisis de retrasos, rutas, aerolíneas y comportamiento temporal.")

# ------------------------------------------------------------
# CARGA DE DATOS DESDE LA API FASTAPI
# ------------------------------------------------------------

API_URL = "https://grows-affected-villages-folks.trycloudflare.com/data"  # ← TU URL AQUÍ

@st.cache_data(show_spinner=True)
def load_data():
    r = requests.get(API_URL, timeout=60)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
    return df

with st.spinner("Cargando datos..."):
    df = load_data()

st.success(f"Datos cargados: {len(df):,} registros")

# ------------------------------------------------------------
# SIDEBAR – FILTROS
# ------------------------------------------------------------

st.sidebar.header("🔎 Filtros")

# Fechas
min_date, max_date = df["FlightDate"].min(), df["FlightDate"].max()
date_range = st.sidebar.date_input("Rango de fechas", (min_date, max_date))

# Aerolínea
airlines = st.sidebar.multiselect(
    "Aerolínea",
    sorted(df["Airline"].dropna().unique())
)

# Origen / Destino
origins = st.sidebar.multiselect(
    "Aeropuerto de origen",
    sorted(df["Origin"].dropna().unique())
)

destinations = st.sidebar.multiselect(
    "Aeropuerto de destino",
    sorted(df["Dest"].dropna().unique())
)

# Rango de retraso
delay_range = st.sidebar.slider(
    "Retraso llegada (min)",
    int(df["ArrDelay"].min()),
    int(df["ArrDelay"].max()),
    (0, int(df["ArrDelay"].max()))
)

# ------------------------------------------------------------
# APLICAR FILTROS
# ------------------------------------------------------------

df_filtered = df.copy()

# Fecha
if len(date_range) == 2:
    start, end = date_range
    df_filtered = df_filtered[
        (df_filtered["FlightDate"] >= pd.to_datetime(start)) &
        (df_filtered["FlightDate"] <= pd.to_datetime(end))
    ]

if airlines:
    df_filtered = df_filtered[df_filtered["Airline"].isin(airlines)]

if origins:
    df_filtered = df_filtered[df_filtered["Origin"].isin(origins)]

if destinations:
    df_filtered = df_filtered[df_filtered["Dest"].isin(destinations)]

df_filtered = df_filtered[
    (df_filtered["ArrDelay"] >= delay_range[0]) &
    (df_filtered["ArrDelay"] <= delay_range[1])
]

st.markdown(f"### Resultados filtrados: **{len(df_filtered):,}** vuelos")

# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

total_vuelos = len(df_filtered)
avg_dep = df_filtered["DepDelay"].mean()
avg_arr = df_filtered["ArrDelay"].mean()
cancelados = df_filtered["Cancelled"].sum()
desviados = df_filtered["Diverted"].sum()

col1.metric("Total vuelos", f"{total_vuelos:,}")
col2.metric("Retraso promedio salida", f"{avg_dep:,.1f} min")
col3.metric("Retraso promedio llegada", f"{avg_arr:,.1f} min")
col4.metric("Cancelados / Desviados", f"{cancelados} / {desviados}")

# ------------------------------------------------------------
# GRÁFICO 1 – Vuelos por mes
# ------------------------------------------------------------

st.subheader("📅 Vuelos por mes")

df_month = (
    df_filtered
    .assign(Month=df_filtered["FlightDate"].dt.to_period("M").astype(str))
    .groupby("Month")
    .size()
    .reset_index(name="Vuelos")
)

if not df_month.empty:
    fig1 = px.bar(df_month, x="Month", y="Vuelos", title="Vuelos por mes")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# GRÁFICO 2 – Retraso por aerolínea
# ------------------------------------------------------------

st.subheader("🛫 Retraso promedio por aerolínea")

df_airline = (
    df_filtered.groupby("Airline")["ArrDelay"]
    .mean()
    .reset_index()
    .sort_values("ArrDelay", ascending=False)
)

if not df_airline.empty:
    fig2 = px.bar(
        df_airline,
        x="Airline",
        y="ArrDelay",
        title="Retraso promedio de llegada por aerolínea",
        labels={"ArrDelay": "Retraso (min)"}
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# GRÁFICO 3 – Top rutas
# ------------------------------------------------------------

st.subheader("🗺️ Top rutas con más vuelos")

df_routes = (
    df_filtered
    .assign(Ruta=df_filtered["Origin"] + " → " + df_filtered["Dest"])
    .groupby("Ruta")
    .size()
    .reset_index(name="Vuelos")
    .sort_values("Vuelos", ascending=False)
    .head(15)
)

if not df_routes.empty:
    fig3 = px.bar(
        df_routes,
        x="Ruta",
        y="Vuelos",
        title="Top 15 rutas más activas",
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# GRÁFICO 4 – Distancia vs Tiempo en Aire
# ------------------------------------------------------------

st.subheader("✈️ Relación: Distancia vs Tiempo en Aire")

df_scatter = df_filtered.dropna(subset=["Distance", "AirTime"])

if not df_scatter.empty:
    fig4 = px.scatter(
        df_scatter.sample(min(3000, len(df_scatter))),  # para no saturar
        x="Distance",
        y="AirTime",
        color="Airline",
        hover_data=["Origin", "Dest"],
        title="Distancia vs Tiempo en Aire",
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# TABLA DETALLADA
# ------------------------------------------------------------

st.subheader("📋 Detalle de vuelos")

st.dataframe(df_filtered.head(500))

csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar CSV filtrado",
    csv,
    "vuelos_filtrados.csv",
    "text/csv"
)
