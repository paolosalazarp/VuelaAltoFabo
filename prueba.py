import streamlit as st
import pandas as pd
import altair as alt
import requests

st.set_page_config(
    page_title="Dashboard de Vuelos Vuela Alto Fabo",
    layout="wide",
    page_icon="✈️"
)

API_URL = "https://could-earth-labor-late.trycloudflare.com/data"

st.title("✈️ Dashboard Profesional de Vuelos")
st.markdown("Análisis de puntualidad, demoras, cancelaciones y comportamiento por aerolínea y aeropuerto.")

# ----------- CARGA DE DATA ----------------
@st.cache_data
def load_data():
    response = requests.get(API_URL, timeout=10)

    if response.status_code != 200:
        st.error("Error al obtener datos del API.")
        st.stop()

    df = pd.DataFrame(response.json())

    # Conversión segura de fechas
    if "FlightDate" in df.columns:
        df["FlightDate"] = pd.to_datetime(df["FlightDate"], errors="coerce")

    # Rellenar NaN para evitar errores
    df = df.fillna({"DepDelay": 0, "ArrDelay": 0, "Cancelled": 0, "Diverted": 0})

    return df

df = load_data()

# --------------------------- SIDEBAR ---------------------------------
st.sidebar.header("Filtros")
aerolineas = st.sidebar.multiselect("Aerolínea", df["Airline"].unique())
origenes = st.sidebar.multiselect("Aeropuerto Origen", df["Origin"].unique())
destinos = st.sidebar.multiselect("Aeropuerto Destino", df["Dest"].unique())

df_filt = df.copy()

if aerolineas:
    df_filt = df_filt[df_filt["Airline"].isin(aerolineas)]
if origenes:
    df_filt = df_filt[df_filt["Origin"].isin(origenes)]
if destinos:
    df_filt = df_filt[df_filt["Dest"].isin(destinos)]

# --------------------------- KPIs ------------------------------------
col1, col2, col3, col4 = st.columns(4)

prom_dep = df_filt["DepDelay"].mean()
prom_arr = df_filt["ArrDelay"].mean()
cancel_rate = df_filt["Cancelled"].mean() * 100
divert_rate = df_filt["Diverted"].mean() * 100

col1.metric("Retraso Promedio en Despegue", f"{prom_dep:.2f} min")
col2.metric("Retraso Promedio de Llegada", f"{prom_arr:.2f} min")
col3.metric("Tasa de Cancelación", f"{cancel_rate:.2f}%")
col4.metric("Tasa de Desvío", f"{divert_rate:.2f}%")

# --------------------------- ANALISIS 1 -------------------------------
st.subheader("✈️ Puntualidad por Aerolínea")
airline_delay = df_filt.groupby("Airline")["ArrDelay"].mean().reset_index()

chart_delay = (
    alt.Chart(airline_delay)
    .mark_bar()
    .encode(
        x=alt.X("ArrDelay", title="Retraso Promedio (min)"),
        y=alt.Y("Airline", sort="-x", title="Aerolínea"),
        color=alt.Color("ArrDelay", scale=alt.Scale(scheme="blues"))
    )
)

st.altair_chart(chart_delay, use_container_width=True)

# --------------------------- ANALISIS 2 -------------------------------
st.subheader("⏱ Aeropuertos con Mayor Retraso Acumulado")

airport_delay = (
    df_filt.groupby("Origin")["DepDelay"]
    .sum()
    .reset_index()
    .sort_values("DepDelay", ascending=False)
    .head(10)
)

chart_airport = (
    alt.Chart(airport_delay)
    .mark_bar()
    .encode(
        x=alt.X("DepDelay", title="Minutos de Demora Acumulada"),
        y=alt.Y("Origin", sort="-x", title="Aeropuerto"),
        color=alt.Color("DepDelay", scale=alt.Scale(scheme="reds"))
    )
)

st.altair_chart(chart_airport, use_container_width=True)

# --------------------------- ANALISIS 3 -------------------------------
st.subheader("📊 Tasa de Cancelación por Aerolínea")

cancel_by_airline = (
    df_filt.groupby("Airline")["Cancelled"]
    .mean()
    .reset_index()
)

cancel_by_airline["Cancelled"] *= 100

chart_cancel = (
    alt.Chart(cancel_by_airline)
    .mark_bar()
    .encode(
        x=alt.X("Cancelled", title="% Cancelaciones"),
        y=alt.Y("Airline", sort="-x"),
        color=alt.Color("Cancelled", scale=alt.Scale(scheme="oranges"))
    )
)

st.altair_chart(chart_cancel, use_container_width=True)

# --------------------------- RAW DATA --------------------------------
with st.expander("📄 Ver datos crudos"):
    st.dataframe(df_filt)


