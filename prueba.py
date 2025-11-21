# app.py
import streamlit as st
import pyodbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------
st.set_page_config(
    page_title="Dashboard de Vuelos",
    layout="wide",
    page_icon="✈️",
)

st.title("✈️ Dashboard Profesional de Vuelos")

st.markdown(
    """
    Este dashboard muestra el comportamiento de los vuelos:
    retrasos, aerolíneas, rutas, tiempos y más.  
    Usa los filtros de la izquierda para explorar la información.
    """
)

# -----------------------------
# CONEXIÓN A SQL SERVER
# -----------------------------
@st.cache_resource
def get_connection():
    cfg = st.secrets
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={cfg.server};"
        f"DATABASE={cfg.database};"
        f"UID={cfg.username};"
        f"PWD={cfg.password};"
    )
    return conn

# -----------------------------
# CARGA DE DATOS
# -----------------------------
@st.cache_data(show_spinner=True)
def load_data():
    conn = get_connection()

    # OJO: si tus nombres cambian, ajusta este SELECT
    query = """
    SELECT
        f.fact_id,
        df.FlightDate,
        df.[Year],
        df.[Month],
        df.DayOfWeek,
        o.Origin,
        o.OriginCityName,
        o.OriginStateName,
        d.Dest,
        d.DestCityName,
        d.DestStateName,
        a.Airline,
        f.AirTime,
        f.Distance,
        f.DepDelay,
        f.ArrDelay,
        c.Cancelled,
        dv.Diverted
    FROM fact_vuelos f
        INNER JOIN dim_fecha df
            ON f.dim_fecha_id = df.dim_fecha_id
        INNER JOIN dim_origen o
            ON f.dim_origen_id = o.dim_origen_id
        INNER JOIN dim_destino d
            ON f.dim_destino_id = d.dim_destino_id
        INNER JOIN dim_aerolinea a
            ON f.dim_aerolinea_id = a.dim_aerolinea_id
        LEFT JOIN dim_cancelacion c
            ON f.dim_cancelacion_id = c.dim_cancelacion_id
        LEFT JOIN dim_desviacion dv
            ON f.dim_desviacion_id = dv.dim_desviacion_id
    -- TOP opcional para pruebas:
    -- ORDER BY df.FlightDate
    """
    df = pd.read_sql(query, conn)

    # Casting de tipos
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    df["DepDelay"] = pd.to_numeric(df["DepDelay"], errors="coerce")
    df["ArrDelay"] = pd.to_numeric(df["ArrDelay"], errors="coerce")
    df["Distance"] = pd.to_numeric(df["Distance"], errors="coerce")
    df["AirTime"] = pd.to_numeric(df["AirTime"], errors="coerce")

    # Columnas booleanas normalizadas
    if "Cancelled" in df.columns:
        df["Cancelled"] = df["Cancelled"].fillna(0)
    if "Diverted" in df.columns:
        df["Diverted"] = df["Diverted"].fillna(0)

    return df

with st.spinner("Cargando datos de SQL Server..."):
    df = load_data()

# -----------------------------
# SIDEBAR – FILTROS
# -----------------------------
st.sidebar.header("🧪 Filtros")

# Rango de fechas
min_date = df["FlightDate"].min()
max_date = df["FlightDate"].max()

date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Aerolínea
airlines = st.sidebar.multiselect(
    "Aerolínea",
    options=sorted(df["Airline"].dropna().unique()),
    default=sorted(df["Airline"].dropna().unique())[:10],  # para no reventar todo
)

# Origen y destino
origins = st.sidebar.multiselect(
    "Aeropuerto de origen",
    options=sorted(df["Origin"].dropna().unique()),
    default=None
)

destinations = st.sidebar.multiselect(
    "Aeropuerto de destino",
    options=sorted(df["Dest"].dropna().unique()),
    default=None
)

# Filtro por retraso de llegada
max_delay = int(df["ArrDelay"].fillna(0).max())
delay_range = st.sidebar.slider(
    "Rango de retraso de llegada (minutos)",
    min_value=int(df["ArrDelay"].fillna(0).min()),
    max_value=max_delay,
    value=(0, max_delay)
)

# Cancelados / desviados
show_cancelled = st.sidebar.selectbox(
    "Incluir vuelos cancelados",
    ["Todos", "Solo no cancelados", "Solo cancelados"]
)

show_diverted = st.sidebar.selectbox(
    "Incluir vuelos desviados",
    ["Todos", "Solo no desviados", "Solo desviados"]
)

# -----------------------------
# APLICAR FILTROS
# -----------------------------
df_filtered = df.copy()

# Fecha
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[
        (df_filtered["FlightDate"] >= pd.to_datetime(start_date)) &
        (df_filtered["FlightDate"] <= pd.to_datetime(end_date))
    ]

# Aerolínea
if airlines:
    df_filtered = df_filtered[df_filtered["Airline"].isin(airlines)]

# Origen
if origins:
    df_filtered = df_filtered[df_filtered["Origin"].isin(origins)]

# Destino
if destinations:
    df_filtered = df_filtered[df_filtered["Dest"].isin(destinations)]

# Rango de retraso llegada
df_filtered = df_filtered[
    (df_filtered["ArrDelay"] >= delay_range[0]) &
    (df_filtered["ArrDelay"] <= delay_range[1])
]

# Cancelados
if "Cancelled" in df_filtered.columns:
    if show_cancelled == "Solo no cancelados":
        df_filtered = df_filtered[df_filtered["Cancelled"] == 0]
    elif show_cancelled == "Solo cancelados":
        df_filtered = df_filtered[df_filtered["Cancelled"] == 1]

# Desviados
if "Diverted" in df_filtered.columns:
    if show_diverted == "Solo no desviados":
        df_filtered = df_filtered[df_filtered["Diverted"] == 0]
    elif show_diverted == "Solo desviados":
        df_filtered = df_filtered[df_filtered["Diverted"] == 1]

st.markdown(f"### Resultados filtrados: {len(df_filtered):,} vuelos")

# -----------------------------
# FILA 1 – KPIs
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

total_vuelos = len(df_filtered)
prom_depdelay = df_filtered["DepDelay"].mean()
prom_arrdelay = df_filtered["ArrDelay"].mean()
porc_cancelados = 100 * df_filtered["Cancelled"].sum() / total_vuelos if "Cancelled" in df_filtered.columns and total_vuelos > 0 else 0
porc_desviados = 100 * df_filtered["Diverted"].sum() / total_vuelos if "Diverted" in df_filtered.columns and total_vuelos > 0 else 0

col1.metric("Total de vuelos", f"{total_vuelos:,}")
col2.metric("Retraso promedio salida (min)", f"{prom_depdelay:,.1f}")
col3.metric("Retraso promedio llegada (min)", f"{prom_arrdelay:,.1f}")
col4.metric("% Cancelados / Desviados", f"{porc_cancelados:,.1f}% / {porc_desviados:,.1f}%")

# -----------------------------
# FILA 2 – TIEMPO Y AEROLÍNEAS
# -----------------------------
col5, col6 = st.columns(2)

# Vuelos por mes
df_mes = (
    df_filtered
    .assign(YearMonth=lambda x: x["FlightDate"].dt.to_period("M").astype(str))
    .groupby("YearMonth")
    .agg(Vuelos=("fact_id", "count"),
         RetrasoPromedio=("ArrDelay", "mean"))
    .reset_index()
)

with col5:
    st.subheader("Vuelos por mes")
    if not df_mes.empty:
        fig_mes = px.bar(
            df_mes,
            x="YearMonth",
            y="Vuelos",
            labels={"YearMonth": "Mes", "Vuelos": "Número de vuelos"},
        )
        st.plotly_chart(fig_mes, use_container_width=True)
    else:
        st.info("No hay datos para los filtros seleccionados.")

# Retraso promedio por aerolínea
df_airline = (
    df_filtered
    .groupby("Airline")
    .agg(
        Vuelos=("fact_id", "count"),
        RetrasoLlegada=("ArrDelay", "mean")
    )
    .reset_index()
    .sort_values("Vuelos", ascending=False)
    .head(15)
)

with col6:
    st.subheader("Retraso promedio por aerolínea")
    if not df_airline.empty:
        fig_air = px.bar(
            df_airline,
            x="Airline",
            y="RetrasoLlegada",
            hover_data=["Vuelos"],
            labels={"Airline": "Aerolínea", "RetrasoLlegada": "Retraso promedio llegada (min)"},
        )
        st.plotly_chart(fig_air, use_container_width=True)
    else:
        st.info("No hay datos para los filtros seleccionados.")

# -----------------------------
# FILA 3 – RUTAS
# -----------------------------
st.subheader("Top 15 rutas (Origen → Destino) por cantidad de vuelos")

df_rutas = (
    df_filtered
    .assign(Ruta=lambda x: x["Origin"] + " → " + x["Dest"])
    .groupby("Ruta")
    .agg(
        Vuelos=("fact_id", "count"),
        RetrasoPromedio=("ArrDelay", "mean")
    )
    .reset_index()
    .sort_values("Vuelos", ascending=False)
    .head(15)
)

if not df_rutas.empty:
    fig_rutas = px.bar(
        df_rutas,
        x="Ruta",
        y="Vuelos",
        hover_data=["RetrasoPromedio"],
        labels={"Ruta": "Ruta", "Vuelos": "Número de vuelos"},
    )
    st.plotly_chart(fig_rutas, use_container_width=True)
else:
    st.info("No hay datos para los filtros seleccionados.")

# -----------------------------
# FILA 4 – DISTANCIA vs TIEMPO
# -----------------------------
st.subheader("Relación distancia vs tiempo en aire")

df_scatter = df_filtered.dropna(subset=["Distance", "AirTime"]).copy()
if not df_scatter.empty:
    fig_scatter = px.scatter(
        df_scatter.sample(min(5000, len(df_scatter))),  # para no explotar el navegador
        x="Distance",
        y="AirTime",
        color="Airline",
        size="ArrDelay",
        labels={"Distance": "Distancia (millas)", "AirTime": "Tiempo en aire (min)"},
        hover_data=["Origin", "Dest"]
    )
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.info("No hay datos suficientes para este gráfico.")

# -----------------------------
# TABLA DETALLADA
# -----------------------------
st.subheader("Detalle de vuelos (primeros 500 registros filtrados)")

df_table = df_filtered.sort_values("FlightDate").head(500)
st.dataframe(df_table)

# Botón de descarga
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Descargar datos filtrados (CSV)",
    data=csv,
    file_name="vuelos_filtrados.csv",
    mime="text/csv",
)
