import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# ------------------------------------------------------------
# CONFIG GENERAL
# ------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Profesional de Vuelos",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Dashboard Profesional de Vuelos")
st.markdown("Análisis de retrasos, rutas, aerolíneas y comportamiento temporal.")

# ------------------------------------------------------------
# CARGA DE DATOS DESDE LA API
# ------------------------------------------------------------

API_URL = "https://grows-affected-villages-folks.trycloudflare.com/data"  # <--- TU URL

@st.cache_data(show_spinner=True)
def load_data():
    resp = requests.get(API_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data)

    # Asegurar columna FlightDate como datetime
    if "FlightDate" in df.columns:
        df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")
    else:
        # fallback por si algún día cambias el endpoint
        if {"Year", "Month"}.issubset(df.columns):
            df["FlightDate"] = pd.to_datetime(
                dict(year=df["Year"], month=df["Month"], day=1),
                errors="coerce"
            )

    # Asegurar numéricas
    for col in ["DepDelay", "ArrDelay", "Distance", "AirTime"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Cancelled / Diverted como int
    for col in ["Cancelled", "Diverted"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df

with st.spinner("Cargando datos desde la API..."):
    df = load_data()

st.success(f"Datos cargados: {len(df):,} registros")
# st.write("Columnas:", list(df.columns))  # <- descomenta si quieres debug

# ------------------------------------------------------------
# SIDEBAR – FILTROS
# ------------------------------------------------------------

st.sidebar.header("🔎 Filtros")

# Filtro por fecha
if "FlightDate" in df.columns:
    min_date = df["FlightDate"].min()
    max_date = df["FlightDate"].max()
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    date_range = None

# Aerolínea
airlines = st.sidebar.multiselect(
    "Aerolínea",
    options=sorted(df["Airline"].dropna().unique()),
    default=None,
)

# Origen / Destino
origins = st.sidebar.multiselect(
    "Aeropuerto de origen",
    options=sorted(df["Origin"].dropna().unique()),
    default=None,
)

destinations = st.sidebar.multiselect(
    "Aeropuerto de destino",
    options=sorted(df["Dest"].dropna().unique()),
    default=None,
)

# Rango de retraso llegada
arr_min = int(df["ArrDelay"].min())
arr_max = int(df["ArrDelay"].max())
delay_range = st.sidebar.slider(
    "Retraso de llegada (min)",
    min_value=arr_min,
    max_value=arr_max,
    value=(0, arr_max),
)

# ------------------------------------------------------------
# APLICAR FILTROS
# ------------------------------------------------------------

df_filtered = df.copy()

# Fecha
if date_range and len(date_range) == 2 and "FlightDate" in df_filtered.columns:
    start_date, end_date = date_range
    df_filtered = df_filtered[
        (df_filtered["FlightDate"] >= pd.to_datetime(start_date)) &
        (df_filtered["FlightDate"] <= pd.to_datetime(end_date))
    ]

# Aerolínea
if airlines:
    df_filtered = df_filtered[df_filtered["Airline"].isin(airlines)]

# Origen / Destino
if origins:
    df_filtered = df_filtered[df_filtered["Origin"].isin(origins)]
if destinations:
    df_filtered = df_filtered[df_filtered["Dest"].isin(destinations)]

# Rango de retraso llegada
df_filtered = df_filtered[
    (df_filtered["ArrDelay"] >= delay_range[0]) &
    (df_filtered["ArrDelay"] <= delay_range[1])
]

st.markdown(f"### Vuelos filtrados: **{len(df_filtered):,}**")

# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

total_vuelos = len(df_filtered)
avg_dep = df_filtered["DepDelay"].mean()
avg_arr = df_filtered["ArrDelay"].mean()
cancelados = df_filtered["Cancelled"].sum()
desviados = df_filtered["Diverted"].sum()

col1.metric("Total de vuelos", f"{total_vuelos:,}")
col2.metric("Retraso promedio salida", f"{avg_dep:,.1f} min")
col3.metric("Retraso promedio llegada", f"{avg_arr:,.1f} min")
col4.metric("Cancelados / Desviados", f"{cancelados} / {desviados}")

# ------------------------------------------------------------
# GRÁFICO 1 – Vuelos por mes
# ------------------------------------------------------------

st.subheader("📅 Vuelos por mes")

if "FlightDate" in df_filtered.columns:
    df_month = (
        df_filtered
        .assign(MonthStr=df_filtered["FlightDate"].dt.to_period("M").astype(str))
        .groupby("MonthStr")
        .size()
        .reset_index(name="Vuelos")
    )

    if not df_month.empty:
        fig1 = px.bar(df_month, x="MonthStr", y="Vuelos",
                      labels={"MonthStr": "Mes", "Vuelos": "Número de vuelos"},
                      title="Vuelos por mes")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No hay datos para este filtro.")
else:
    st.info("No se encontró columna FlightDate para análisis temporal.")

# ------------------------------------------------------------
# GRÁFICO 2 – Retraso por aerolínea
# ------------------------------------------------------------

st.subheader("🛫 Retraso promedio por aerolínea")

df_airline = (
    df_filtered
    .groupby("Airline")["ArrDelay"]
    .mean()
    .reset_index()
    .sort_values("ArrDelay", ascending=False)
)

if not df_airline.empty:
    fig2 = px.bar(
        df_airline.head(20),
        x="Airline",
        y="ArrDelay",
        labels={"ArrDelay": "Retraso llegada (min)", "Airline": "Aerolínea"},
        title="Retraso promedio de llegada por aerolínea (top 20)",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# GRÁFICO 3 – Top rutas
# ------------------------------------------------------------

st.subheader("🗺️ Top 15 rutas más activas")

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
        labels={"Ruta": "Ruta", "Vuelos": "Número de vuelos"},
        title="Top 15 rutas con más vuelos",
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No hay datos para este filtro.")

# ------------------------------------------------------------
# GRÁFICO 4 – Distancia vs Tiempo en aire
# ------------------------------------------------------------

st.subheader("✈️ Distancia vs Tiempo en aire")

df_scatter = df_filtered.dropna(subset=["Distance", "AirTime"])

if not df_scatter.empty:
    sample = df_scatter.sample(min(3000, len(df_scatter)), random_state=42)
    fig4 = px.scatter(
        sample,
        x="Distance",
        y="AirTime",
        color="Airline",
        hover_data=["Origin", "Dest"],
        labels={"Distance": "Distancia (millas)", "AirTime": "Tiempo en aire (min)"},
        title="Relación distancia – tiempo en aire (muestra)",
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No hay datos suficientes para este gráfico.")

# ------------------------------------------------------------
# TABLA DETALLADA + DESCARGA
# ------------------------------------------------------------

st.subheader("📋 Detalle de vuelos (primeros 500 registros)")

st.dataframe(df_filtered.head(500))

csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Descargar CSV filtrado",
    data=csv,
    file_name="vuelos_filtrados.csv",
    mime="text/csv",
)
