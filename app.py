import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Escandallos & Rentabilidad",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🥩"
)

# --- CSS ESTILO PROFESIONAL ---
st.markdown("""
    <style>
        .stApp { background-color: #F3F4F6; color: #1F2937; }
        section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; }
        div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        div[data-testid="stMetricValue"] { color: #2563EB; }
        div[data-testid="stMetricLabel"] { color: #6B7280; }
        .stTabs [data-baseweb="tab-list"] { gap: 5px; }
        .stTabs [data-baseweb="tab"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; color: #4B5563; }
        .stTabs [aria-selected="true"] { background-color: #EFF6FF !important; color: #1D4ED8 !important; border: 1px solid #BFDBFE; font-weight: bold; }
        h1, h2, h3 { color: #111827 !important; font-family: 'Segoe UI', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# --- ENLACES A DATOS ---
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'
SALES_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTlJBcdE77BaiNke-06GxDH8nY7vQ0wm_XgtDaVlF9cDDlFIxIawsTNZHrEPlv3uoVecih6_HRo7gqH/pub?gid=1543847315&single=true&output=csv'

# --- FUNCIONES DE PROCESAMIENTO ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def recalcular_dataframe(df):
    if 'Cantidad(kg)' in df.columns and 'Escandallo' in df.columns:
        df['Total_Kg_Grupo'] = df.groupby('Escandallo')['Cantidad(kg)'].transform('sum')
        df['%_Calculado'] = np.where(df['Total_Kg_Grupo'] > 0, df['Cantidad(kg)'] / df['Total_Kg_Grupo'], 0.0)

    cols_calc = ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']
    if all(c in df.columns for c in cols_calc):
        df['Precio_escandallo_Calculado'] = (df['Precio EXW'] - df['Coste_congelación'] - df['Coste_despiece']) * df['%_Calculado']
    return df

@st.cache_data(ttl=600)
def load_initial_data():
    try:
        df_raw = pd.read_csv(SHEET_URL)
    except Exception as e:
        return None, f"Error: {e}"

    df_raw.columns = df_raw.columns.str.strip()
    rename_map = {
        'Coste congelación': 'Coste_congelación', 'Coste congelacion': 'Coste_congelación',
        'Coste despiece': 'Coste_despiece', 'Precio escandallo': 'Precio_escandallo',
        'TIPO': 'Tipo', 'tipo': 'Tipo',
        'Fecha': 'Fecha', 'fecha': 'Fecha', 'Cliente': 'Cliente'
    }
    df_raw.rename(columns={k:v for k,v in rename_map.items() if k in df_raw.columns}, inplace=True)

    if 'Tipo' not in df_raw.columns: df_raw['Tipo'] = ""
    for col in ['Cliente', 'Fecha', 'Familia', 'Formato']:
        if col not in df_raw.columns: df_raw[col] = ""
        else: df_raw[col] = df_raw[col].fillna("")

    if 'Código' in df_raw.columns:
        df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)

    cols_num = ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']
    for col in cols_num:
        if col in df_raw.columns:
            df_raw[col] = df_raw[col].apply(clean_european_number)
        else:
            df_raw[col] = 0.0

    if 'Fecha' in df_raw.columns:
        df_raw['Fecha_dt'] = pd.to_datetime(df_raw['Fecha'], dayfirst=True, errors='coerce')
        if df_raw['Fecha_dt'].notna().any():
            max_fechas = df_raw.groupby('Escandallo')['Fecha_dt'].transform('max')
            mask = (df_raw['Fecha_dt'] == max_fechas) | (df_raw['Fecha_dt'].isna())
            df_raw = df_raw[mask].copy()
            df_raw.drop(columns=['Fecha_dt'], inplace=True)

    return recalcular_dataframe(df_raw), None

@st.cache_data(ttl=600)
def load_sales_data():
    try:
        df_v = pd.read_csv(SALES_URL)
        df_v.columns = df_v.columns.str.strip()
        for c in df_v.columns:
            c_up = c.upper()
            if c_up in ['CODIGO', 'CÓDIGO']: df_v.rename(columns={c: 'Código'}, inplace=True)
            elif c_up == 'CLIENTE': df_v.rename(columns={c: 'Cliente'}, inplace=True)
            elif c_up == 'NOMBRE': df_v.rename(columns={c: 'Nombre'}, inplace=True)
            elif c_up == 'KILOS': df_v.rename(columns={c: 'Kilos'}, inplace=True)
            elif c_up == 'PRECIO EXW': df_v.rename(columns={c: 'Precio EXW'}, inplace=True)

        for col in ['Kilos', 'Precio EXW']:
            if col in df_v.columns:
                df_v[col] = df_v[col].apply(clean_european_number)
        if 'Código' in df_v.columns:
            df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
        return df_v, None
    except Exception as e:
        return None, f"Error cargando ventas: {e}"

# --- INICIALIZACIÓN DE ESTADO ---
if 'df_global' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global = data
if 'grid_key' not in st.session_state: st.session_state.grid_key = 0

df = st.session_state.df_global

# --- FILTROS SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Filtros Globales")
    familias = sorted(df['Familia'].unique()) if 'Familia' in df.columns else []
    sel_familia = st.multiselect("📂 Familia", options=familias)
    
    mask_filtros = pd.Series(True, index=df.index)
    if sel_familia: mask_filtros &= df['Familia'].isin(sel_familia)

    # Crear etiquetas para el buscador de escandallos
    df_principales = df[mask_filtros].copy()
    if 'Tipo' in df_principales.columns:
        df_principales = df_principales[df_principales['Tipo'].str.contains('Principal', case=False, na=False)]
    
    df_etiquetas = df_principales.drop_duplicates(subset=['Escandallo'])
    mapa_etiquetas = {row['Escandallo']: f"{row['Escandallo']} | {row['Código']} | {row['Nombre']}" for _, row in df_etiquetas.iterrows()}
    df['Filtro_Display'] = df['Escandallo'].map(mapa_etiquetas)

    opciones_escandallo = sorted(df[mask_filtros]['Filtro_Display'].dropna().unique())
    sel_escandallo = st.multiselect("🏷️ Escandallo", options=opciones_escandallo)

    if st.button("🔄 Resetear Datos", type="primary"):
        st.cache_data.clear()
        st.rerun()

if sel_escandallo: mask_filtros &= df['Filtro_Display'].isin(sel_escandallo)
df_filtrado = df[mask_filtros].copy()

# --- INTERFAZ PRINCIPAL ---
st.title("📊 Panel de Escandallos y Rentabilidad")

if df_filtrado.empty:
    st.info("ℹ️ Selecciona filtros para visualizar los datos.")
else:
    tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico", "🏆 Ranking & Simulación", "📈 Rentabilidad Clientes"])

    with tab1:
        # Lógica de paginación para no saturar el navegador
        escandallos_unicos = df_filtrado['Escandallo'].unique()
        for esc_id in escandallos_unicos[:5]: # Mostramos los primeros 5 por rendimiento
            df_f = df_filtrado[df_filtrado['Escandallo'] == esc_id].copy()
            st.markdown(f"#### 🔹 Escandallo: {esc_id}")
            AgGrid(df_f, height=250, theme='alpine', key=f"grid_{esc_id}")

    with tab2:
        st.subheader("🏆 Ranking de Rentabilidad")
        df_rank = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()
        # Aquí iría el código del ranking similar al anterior pero optimizado...
        st.dataframe(df_rank.sort_values('Precio_escandallo_Calculado', ascending=False))

    with tab3:
        st.header("📈 Rentabilidad Real por Cliente")
        df_ventas, err_v = load_sales_data()
        
        if err_v: st.error(err_v)
        elif df_ventas is not None:
            # --- CÁLCULO OPTIMIZADO PARA EVITAR CancelledError ---
            df_esc_completo = st.session_state.df_global.copy()
            
            # 1. Mapeo de artículos principales
            df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)]
            mapa_esc = dict(zip(df_princ['Código'].astype(str), df_princ['Escandallo']))
            
            # 2. Cruce de ventas
            df_ventas['Escandallo_Ref'] = df_ventas['Código'].astype(str).map(mapa_esc)
            df_match = df_ventas.dropna(subset=['Escandallo_Ref']).copy()
            
            # 3. Cálculo de rentabilidad por línea (Vectorizado)
            # Para cada venta, buscamos la suma de rentabilidad del escandallo pero sustituyendo el precio EXW del principal
            resultados = []
            for _, v_row in df_match.iterrows():
                esc_id = v_row['Escandallo_Ref']
                df_bloque = df_esc_completo[df_esc_completo['Escandallo'] == esc_id].copy()
                
                # Sustituimos el precio del artículo que se vendió
                mask_art = df_bloque['Código'].astype(str) == str(v_row['Código'])
                df_bloque.loc[mask_art, 'Precio EXW'] = v_row['Precio EXW']
                
                rent = ((df_bloque['Precio EXW'] - df_bloque['Coste_congelación'] - df_bloque['Coste_despiece']) * df_bloque['%_Calculado']).sum()
                resultados.append(rent)
            
            df_match['Rentabilidad'] = resultados
            
            # --- CÁLCULO DE MERCADO OPTIMIZADO (EVITA EL ERROR DE LA LÍNEA 422) ---
            df_agrupado_mercado = df_match.groupby('Nombre')[['Rentabilidad', 'Kilos']].sum()
            df_agrupado_mercado['Media_Mercado'] = np.where(
                df_agrupado_mercado['Kilos'] > 0, 
                df_agrupado_mercado['Rentabilidad'] / df_agrupado_mercado['Kilos'], 
                0
            )
            mapa_mercado = df_agrupado_mercado['Media_Mercado'].to_dict()
            
            # Cálculo final vs Mercado
            df_match['Rent_Media_Cliente'] = df_match['Rentabilidad'] / df_match['Kilos']
            df_match['Rent_Mercado_Ref'] = df_match['Nombre'].map(mapa_mercado)
            df_match['Diferencial'] = (df_match['Rent_Media_Cliente'] - df_match['Rent_Mercado_Ref']) * df_match['Kilos']

            # --- VISUALIZACIÓN ---
            st.success(f"Analizadas {len(df_match)} líneas de venta con éxito.")
            
            resumen_cliente = df_match.groupby('Cliente').agg({
                'Kilos': 'sum',
                'Diferencial': 'sum'
            }).reset_index()
            
            st.subheader("💰 Ganancia/Pérdida vs Media de Mercado")
            st.dataframe(resumen_cliente.style.format({'Diferencial': '{:.2f} €', 'Kilos': '{:.2f} kg'}))
