import streamlit as st
import pyodbc
import pandas as pd

config = st.secrets

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={config.server};"
    f"DATABASE={config.database};"
    f"UID={config.username};"
    f"PWD={config.password};"
)

st.title("Dashboard con SQL Server conectado por Cloudflare Tunnel")

df = pd.read_sql("SELECT TOP 100 * fact_vuelos", conn)

st.dataframe(df)
