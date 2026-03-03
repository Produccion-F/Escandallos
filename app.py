import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Panel de Escandallos PRO",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🥩"
)

# --- CSS ESTILO POWER BI (Restaurado completo) ---
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

# --- FUNCIONES NUCLEARES ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try: return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError: return 0.0

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
        df_raw.columns = df_raw.columns.str.strip()
        rename_map = {'Coste congelación': 'Coste_congelación', 'Coste despiece': 'Coste_despiece', 'TIPO': 'Tipo'}
        df_raw.rename(columns={k:v for k,v in rename_map.items() if k in df_raw.columns}, inplace=True)
        for col in ['Cliente', 'Fecha', 'Familia', 'Formato', 'Tipo']:
            df_raw[col] = df_raw[col].fillna("").astype(str)
        if 'Código' in df_raw.columns:
            df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)
        for col in ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']:
            df_raw[col] = df_raw[col].apply(clean_european_number)
        return recalcular_dataframe(df_raw), None
    except Exception as e: return None, str(e)

@st.cache_data(ttl=600)
def load_sales_data():
    try:
        df_v = pd.read_csv(SALES_URL)
        df_v.columns = df_v.columns.str.strip()
        rename_map = {'CODIGO': 'Código', 'CÓDIGO': 'Código', 'KILOS': 'Kilos', 'PRECIO EXW': 'Precio EXW'}
        df_v.rename(columns={k:v for k,v in rename_map.items() if k.upper() in rename_map}, inplace=True)
        for col in ['Kilos', 'Precio EXW']:
            if col in df_v.columns: df_v[col] = df_v[col].apply(clean_european_number)
        df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
        return df_v, None
    except Exception as e: return None, str(e)

# --- ESTADO Y FILTROS ---
if 'df_global' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global = data
if 'grid_key' not in st.session_state: st.session_state.grid_key = 0

df = st.session_state.df_global

with st.sidebar:
    st.header("🎛️ Filtros Globales")
    familias = sorted(df['Familia'].unique())
    sel_familia = st.multiselect("📂 Familia", options=familias)
    mask = pd.Series(True, index=df.index)
    if sel_familia: mask &= df['Familia'].isin(sel_familia)
    
    # Buscador de escandallos mejorado
    df_labels = df[mask & df['Tipo'].str.contains('Principal', case=False, na=False)].drop_duplicates('Escandallo')
    mapa_lab = {r['Escandallo']: f"{r['Escandallo']} | {r['Código']} | {r['Nombre']}" for _, r in df_labels.iterrows()}
    df['Filtro_Display'] = df['Escandallo'].map(mapa_lab)
    sel_esc = st.multiselect("🏷️ Escandallo", options=sorted(df[mask]['Filtro_Display'].dropna().unique()))
    
    if st.button("🔄 Resetear Todo", type="primary"):
        st.cache_data.clear()
        st.rerun()

if sel_esc: mask &= df['Filtro_Display'].isin(sel_esc)
df_f = df[mask].copy()

# --- TABS PRINCIPALES ---
tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico", "🏆 Ranking & Simulación", "📈 Rentabilidad Clientes"])

with tab1:
    for esc_id in df_f['Escandallo'].unique()[:5]:
        bloque = df_f[df_f['Escandallo'] == esc_id]
        st.markdown(f"#### 🔹 Escandallo {esc_id}")
        AgGrid(bloque, height=200, theme='alpine', key=f"t1_{esc_id}")

with tab2:
    st.subheader("🏆 Ranking e Hipótesis de Precios")
    df_rank = df_f.groupby('Escandallo').agg({'Precio_escandallo_Calculado': 'sum', 'Código': 'first', 'Nombre': 'first', 'Precio EXW': 'first'}).reset_index()
    df_rank = df_rank.sort_values('Precio_escandallo_Calculado', ascending=False)
    
    gb = GridOptionsBuilder.from_dataframe(df_rank)
    gb.configure_column("Precio EXW", editable=True, cellStyle={'backgroundColor': '#EFF6FF', 'color': '#1E40AF', 'fontWeight': 'bold'})
    gb.configure_column("Precio_escandallo_Calculado", header_name="Rentabilidad", type=["numericColumn"], precision=4)
    
    res = AgGrid(df_rank, gridOptions=gb.build(), update_mode=GridUpdateMode.VALUE_CHANGED, theme='alpine', key=f"rank_{st.session_state.grid_key}")
    
    # Lógica de simulación (la que se perdió antes)
    df_mod = pd.DataFrame(res['data'])
    if not df_mod.empty:
        diff = df_mod['Precio EXW'].sum() - df_rank['Precio EXW'].sum()
        if abs(diff) > 0.001:
            for _, row in df_mod.iterrows():
                m = (st.session_state.df_global['Escandallo'] == row['Escandallo']) & (st.session_state.df_global['Tipo'].str.contains('Principal', case=False))
                st.session_state.df_global.loc[m, 'Precio EXW'] = row['Precio EXW']
            st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
            st.session_state.grid_key += 1
            st.rerun()

with tab3:
    st.header("📈 Cuadro de Mando de Clientes")
    vnt, err_v = load_sales_data()
    if vnt is not None:
        # Cruce de datos blindado
        df_esc = st.session_state.df_global.copy()
        df_p = df_esc[df_esc['Tipo'].str.contains('Principal', case=False)]
        mapa_e = dict(zip(df_p['Código'].astype(str), df_p['Escandallo']))
        
        vnt['Esc_ID'] = vnt['Código'].astype(str).map(mapa_e)
        match = vnt.dropna(subset=['Esc_ID']).copy()
        
        # CÁLCULO DE RENTABILIDAD REAL (Ponderado por kilos)
        profit_list = []
        for _, r in match.iterrows():
            blq = df_esc[df_esc['Escandallo'] == r['Esc_ID']].copy()
            blq.loc[blq['Código'].astype(str) == str(r['Código']), 'Precio EXW'] = r['Precio EXW']
            unit_profit = ((blq['Precio EXW'] - blq['Coste_congelación'] - blq['Coste_despiece']) * blq['%_Calculado']).sum()
            profit_list.append(unit_profit * r['Kilos'])
        
        match['Profit_Total'] = profit_list
        
        # Agrupación por Cliente
        cli = match.groupby('Cliente').agg({'Kilos': 'sum', 'Profit_Total': 'sum'}).reset_index()
        cli['Rent_Media'] = np.where(cli['Kilos'] > 0, cli['Profit_Total'] / cli['Kilos'], 0)
        
        # --- NIVEL 1: GRÁFICO ---
        fig = px.scatter(cli, x='Kilos', y='Rent_Media', text='Cliente', size='Kilos', color='Rent_Media',
                         title="Cuadrante: Volumen vs Rentabilidad Real", color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
        
        # --- NIVEL 2: TABLA ---
        st.subheader("🏆 Desempeño por Cliente")
        gb_cli = GridOptionsBuilder.from_dataframe(cli[['Cliente', 'Kilos', 'Rent_Media']])
        gb_cli.configure_selection(selection_mode='single')
        gb_cli.configure_column("Rent_Media", header_name="Rent. Media (€/kg)", precision=3)
        
        grid_cli = AgGrid(cli, gridOptions=gb_cli.build(), theme='alpine', update_mode=GridUpdateMode.SELECTION_CHANGED, key="grid_cli_final")
        
        # --- NIVEL 3: ZOOM (Blindado contra NoneType) ---
        sel = grid_cli.get('selected_rows')
        if sel is not None:
            # Manejo de versiones de AgGrid (algunas devuelven lista, otras DataFrame)
            c_sel = sel.iloc[0]['Cliente'] if isinstance(sel, pd.DataFrame) and not sel.empty else (sel[0]['Cliente'] if isinstance(sel, list) and len(sel) > 0 else None)
            
            if c_sel:
                st.success(f"Detalle de Familias para: {c_sel}")
                det = match[match['Cliente'] == c_sel].groupby('Código').agg({'Kilos': 'sum', 'Profit_Total': 'sum'}).reset_index()
                st.dataframe(det)
