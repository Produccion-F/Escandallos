import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Escandallos", layout="wide", page_icon="🥩")

# --- ESTILOS PERSONALIZADOS (Punto C) ---
st.markdown("""
    <style>
        .main-header { font-size: 2rem; color: #1E293B; font-weight: 700; margin-bottom: 20px; }
        [data-testid="stMetricValue"] { font-size: 1.8rem; color: #0F172A; }
    </style>
""", unsafe_allow_html=True)

# URL de tu Google Sheet (Publicado como CSV)
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'

# --- CARGA DE DATOS OPTIMIZADA (Punto A) ---
@st.cache_data(ttl=600)  # Cache por 10 minutos
def load_data():
    df = pd.read_csv(SHEET_URL)
    df.columns = df.columns.str.strip() # Limpia espacios en nombres de columnas
    
    # Función interna para limpiar números europeos (1.250,50 -> 1250.50)
    def clean_num(x):
        if pd.isna(x) or str(x).strip() == '': return 0.0
        if isinstance(x, (int, float)): return float(x)
        return float(str(x).replace('.', '').replace(',', '.'))

    # Columnas críticas
    cols_to_fix = ['Cantidad(kg)', 'Precio EXW', 'Coste congelación', 'Coste despiece', 'Precio_escandallo_Calculado']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].apply(clean_num)
            
    return df

# --- LÓGICA DE NEGOCIO (Punto B - Intacto) ---
def recalcular_rentabilidad(df):
    # Aquí se mantiene tu lógica actual de cálculo
    df['Total_Kg_Grupo'] = df.groupby('Escandallo')['Cantidad(kg)'].transform('sum')
    df['%_Calculado'] = np.where(df['Total_Kg_Grupo'] > 0, df['Cantidad(kg)'] / df['Total_Kg_Grupo'], 0.0)
    df['Precio_escandallo_Calculado'] = (df['Precio EXW'] - df['Coste congelación'] - df['Coste despiece']) * df['%_Calculado']
    return df

# Inicialización de estado
if 'df_clean' not in st.session_state:
    st.session_state.df_clean = load_data()

df_display = st.session_state.df_clean.copy()

# --- INTERFAZ ---
st.markdown('<p class="main-header">📊 Dashboard de Escandallos y Rentabilidad</p>', unsafe_allow_html=True)

# Filtros en Sidebar
with st.sidebar:
    st.header("Filtros")
    escandallos_sel = st.multiselect("Seleccionar Escandallo", options=sorted(df_display['Escandallo'].unique()))
    articulos_sel = st.multiselect("Seleccionar Artículo", options=sorted(df_display['Artículo'].unique()))

if escandallos_sel:
    df_display = df_display[df_display['Escandallo'].isin(escandallos_sel)]
if articulos_sel:
    df_display = df_display[df_display['Artículo'].isin(articulos_sel)]

# --- TABLA INTERACTIVA (Punto C mejorado) ---
gb = GridOptionsBuilder.from_dataframe(df_display)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
gb.configure_side_bar()
gb.configure_default_column(editable=True, groupable=True)

# Formateo visual de columnas
gb.configure_column("Precio EXW", type=["numericColumn","numberColumnFilter"], valueFormatter="x.toLocaleString() + ' €'")
gb.configure_column("Precio_escandallo_Calculado", type=["numericColumn"], valueFormatter="x.toFixed(2) + ' €'")

# Color según estado (JS para AgGrid)
cellsytle_jscode = JsCode("""
function(params) {
    if (params.value === 'Alta') return {'color': 'white', 'backgroundColor': '#22C55E'};
    if (params.value === 'Media') return {'color': 'black', 'backgroundColor': '#EAB308'};
    if (params.value === 'Baja') return {'color': 'white', 'backgroundColor': '#EF4444'};
}
""")
gb.configure_column("Estado", cellStyle=cellsytle_jscode)

gridOptions = gb.build()

grid_response = AgGrid(
    df_display,
    gridOptions=gridOptions,
    update_mode=GridUpdateMode.MODEL_CHANGED,
    allow_unsafe_jscode=True,
    theme='alpine'
)

# Sincronizar cambios editados
if grid_response['data'] is not None:
    st.session_state.df_clean = pd.DataFrame(grid_response['data'])

st.info("💡 Los cambios realizados en la tabla se mantienen durante la sesión. Para cambios permanentes, actualiza el Google Sheet.")
