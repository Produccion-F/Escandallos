import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Escandallos",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🥩"
)

# --- CSS ESTILO POWER BI ---
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

# --- FUNCIONES ---
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

    df_calc = recalcular_dataframe(df_raw)
    return df_calc, None

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
                
        # Validar y limpiar la columna Código de forma segura
        if 'Código' in df_v.columns:
            df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
        else:
            # Si no existe en el origen, la creamos vacía para evitar el KeyError
            df_v['Código'] = ""
            
        return df_v, None
    except Exception as e:
        return None, f"Error cargando ventas: {e}"

# --- CARGA Y ESTADO ---
if 'df_global' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global = data

if 'grid_key' not in st.session_state: st.session_state.grid_key = 0

df = st.session_state.df_global

# --- ETIQUETAS FILTROS ---
try:
    if 'Tipo' in df.columns and df['Tipo'].str.contains('Principal', case=False, na=False).any():
        mask_p = df['Tipo'].str.contains('Principal', case=False, na=False)
        df_principales = df[mask_p][['Escandallo', 'Código', 'Nombre']]
    else:
        cols_exist = [c for c in ['Escandallo', 'Código', 'Nombre'] if c in df.columns]
        df_principales = df.groupby('Escandallo')[cols_exist[1:]].first().reset_index()
except:
    df_principales = df[['Escandallo']].drop_duplicates()
    df_principales['Código'] = ""
    df_principales['Nombre'] = ""

df_principales = df_principales.drop_duplicates(subset=['Escandallo'])
df_principales['Texto_Escandallo'] = df_principales['Escandallo'].astype(str) + " | " + df_principales['Código'].astype(str) + " | " + df_principales['Nombre']
mapa_etiquetas = dict(zip(df_principales['Escandallo'], df_principales['Texto_Escandallo']))
df['Filtro_Display'] = df['Escandallo'].map(mapa_etiquetas)

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    st.header("🎛️ Filtros Globales")
    familias = sorted(df['Familia'].unique()) if 'Familia' in df.columns else []
    sel_familia = st.multiselect("📂 Familia", options=familias)
    formatos = sorted(df['Formato'].unique()) if 'Formato' in df.columns else []
    sel_formato = st.multiselect("📦 Formato", options=formatos)

    mask_filtros = pd.Series(True, index=df.index)
    if sel_familia: mask_filtros &= df['Familia'].isin(sel_familia)
    if sel_formato: mask_filtros &= df['Formato'].isin(sel_formato)

    opciones_escandallo = []
    if 'Filtro_Display' in df.columns:
        opciones_escandallo = sorted(df[mask_filtros]['Filtro_Display'].dropna().unique())

    sel_escandallo = st.multiselect("🏷️ Escandallo", options=opciones_escandallo)

    st.markdown("---")
    if st.button("🔄 Resetear Datos Originales", type="primary"):
        st.cache_data.clear()
        data, _ = load_initial_data()
        if data is not None:
            st.session_state.df_global = data
            st.session_state.grid_key += 1
            st.session_state.page = 0
        st.rerun()

if sel_escandallo: mask_filtros &= df['Filtro_Display'].isin(sel_escandallo)
df_filtrado = df[mask_filtros].copy()

# --- APP ---
st.title("📊 Panel de Escandallos y Rentabilidad")

if df_filtrado.empty:
    st.info("ℹ️ No hay datos disponibles para los filtros seleccionados.")
else:
    if 'Precio_escandallo_Calculado' in df_filtrado.columns:
        kpi_data = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Escandallos (Global)", f"{kpi_data.count()}")
        k2.metric("Media", f"{kpi_data.mean():.2f} €")
        k3.metric("Max", f"{kpi_data.max():.2f} €")
        k4.metric("Min", f"{kpi_data.min():.2f} €")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico", "🏆 Ranking & Simulación", "📈 Rent. de clientes"])

    # --- PESTAÑA 1: DETALLE TÉCNICO ---
    with tab1:
        escandallos_unicos = df_filtrado['Escandallo'].unique()
        total_esc = len(escandallos_unicos)

        ITEMS_PER_PAGE = 3
        if 'page' not in st.session_state: st.session_state.page = 0
        if st.session_state.page * ITEMS_PER_PAGE >= total_esc: st.session_state.page = 0

        c_pag1, c_pag2, c_pag3 = st.columns([1, 4, 1])
        if c_pag1.button("◀️ Anterior") and st.session_state.page > 0:
            st.session_state.page -= 1
            st.rerun()
        if c_pag3.button("Siguiente ▶️") and (st.session_state.page + 1) * ITEMS_PER_PAGE < total_esc:
            st.session_state.page += 1
            st.rerun()

        c_pag2.markdown(f"<div style='text-align:center; color:#6B7280'>Mostrando {st.session_state.page * ITEMS_PER_PAGE + 1} - {min((st.session_state.page + 1) * ITEMS_PER_PAGE, total_esc)} de {total_esc}</div>", unsafe_allow_html=True)

        start_idx = st.session_state.page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        escandallos_pagina = escandallos_unicos[start_idx:end_idx]

        for i, esc_id in enumerate(escandallos_pagina):
            df_f = df_filtrado[df_filtrado['Escandallo'] == esc_id].copy()
            titulo = f"Escandallo {esc_id}"
            if 'Filtro_Display' in df_f.columns: titulo = df_f['Filtro_Display'].iloc[0]
            fecha = df_f['Fecha'].iloc[0] if 'Fecha' in df_f.columns else ""

            st.markdown(f"#### 🔹 {titulo} <span style='color:#6B7280; font-size:0.8em'>| {fecha}</span>", unsafe_allow_html=True)

            cols_ver = ['Cliente', 'Código', 'Nombre', 'Coste_despiece', 'Coste_congelación', '%_Calculado', 'Precio EXW', 'Precio_escandallo_Calculado', 'Tipo']
            cols_exist = [c for c in cols_ver if c in df_f.columns]
            df_v = df_f[cols_exist].copy()
            if '%_Calculado' in df_v.columns: df_v['%_Calculado'] = df_v['%_Calculado'] * 100

            row_total = {c: None for c in df_v.columns}; row_total['Nombre'] = 'TOTAL'; row_total['Tipo'] = 'TotalRow'
            if '%_Calculado' in df_v: row_total['%_Calculado'] = df_v['%_Calculado'].sum()
            if 'Precio_escandallo_Calculado' in df_v: row_total['Precio_escandallo_Calculado'] = df_v['Precio_escandallo_Calculado'].sum()

            df_fin = pd.concat([df_v, pd.DataFrame([row_total])], ignore_index=True)

            gb = GridOptionsBuilder.from_dataframe(df_fin)
            gb.configure_column("Tipo", hide=True)
            gb.configure_default_column(type=["leftAligned"])

            if "%_Calculado" in df_fin: gb.configure_column("%_Calculado", header_name="%", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' %'", precision=2)
            if "Precio EXW" in df_fin: gb.configure_column("Precio EXW", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=3)
            if "Precio_escandallo_Calculado" in df_fin: gb.configure_column("Precio_escandallo_Calculado", header_name="Rentabilidad", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=4)

            row_style_js = JsCode("""
            function(params) {
                if (params.data.Tipo === 'TotalRow') { return {'fontWeight': 'bold', 'backgroundColor': '#DCFCE7', 'color': '#166534'}; }
                if (params.data.Tipo && String(params.data.Tipo).toLowerCase().includes('principal')) { return {'backgroundColor': '#EFF6FF', 'color': '#1E40AF'}; }
                return {'textAlign': 'left'};
            }
            """)
            gb.configure_grid_options(getRowStyle=row_style_js)

            AgGrid(df_fin, gridOptions=gb.build(), height=300, fit_columns_on_grid_load=True, theme='alpine', allow_unsafe_jscode=True, key=f"det_grid_{esc_id}_{st.session_state.grid_key}")
            st.divider()

    # --- PESTAÑA 2: RANKING ---
    with tab2:
        st.info("💡 Edita la columna **AZUL** y pulsa Enter. El recálculo ahora es rápido y estable.")

        df_rank = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()

        cols_info = ['Escandallo', 'Código', 'Nombre', '%_Calculado', 'Precio EXW', 'Cliente', 'Fecha']
        cols_info = [c for c in cols_info if c in df_filtrado.columns]

        try:
            if 'Tipo' in df_filtrado.columns and df_filtrado['Tipo'].str.contains('Principal', case=False, na=False).any():
                df_pr = df_filtrado[df_filtrado['Tipo'].str.contains('Principal', case=False, na=False)][cols_info]
            else:
                df_pr = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()
        except:
            df_pr = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()

        df_suma = df_pr.groupby('Escandallo')['%_Calculado'].sum().reset_index()

        cols_desc = [c for c in cols_info if c != '%_Calculado' and c != 'Escandallo']
        df_desc = df_pr.groupby('Escandallo')[cols_desc].first().reset_index()

        df_final = pd.merge(df_rank, df_suma, on='Escandallo')
        df_final = pd.merge(df_final, df_desc, on='Escandallo').sort_values('Precio_escandallo_Calculado', ascending=False)

        df_final['Pos'] = range(1, len(df_final)+1)
        df_final['%/CP'] = df_final['%_Calculado'] * 100

        if not df_final.empty:
            q33, q66 = df_final['Precio_escandallo_Calculado'].quantile([0.33, 0.66])
            def get_sem(v): return "Alta" if v >= q66 else ("Media" if v >= q33 else "Baja")
            df_final['Estado'] = df_final['Precio_escandallo_Calculado'].apply(get_sem)
        else:
            df_final['Estado'] = "N/D"

        cols_vis = ['Pos', 'Estado', 'Cliente', 'Fecha', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
        cols_final = [c for c in cols_vis if c in df_final.columns] + ['Escandallo']
        df_ed = df_final[cols_final].copy()

        gb = GridOptionsBuilder.from_dataframe(df_ed)
        gb.configure_column("Escandallo", hide=True)
        if "Pos" in df_ed: gb.configure_column("Pos", width=60, pinned='left')
        gb.configure_default_column(type=["leftAligned"])

        js_sem = JsCode("""function(params) {
            if (params.value === 'Alta') return {'backgroundColor': '#DCFCE7', 'color': '#166534', 'textAlign': 'center', 'fontWeight': 'bold', 'borderRadius': '4px'};
            if (params.value === 'Media') return {'backgroundColor': '#FEF9C3', 'color': '#854D0E', 'textAlign': 'center', 'fontWeight': 'bold', 'borderRadius': '4px'};
            return {'backgroundColor': '#FEE2E2', 'color': '#991B1B', 'textAlign': 'center', 'fontWeight': 'bold', 'borderRadius': '4px'};
        }""")
        if "Estado" in df_ed: gb.configure_column("Estado", cellStyle=js_sem, width=100)

        js_edit = JsCode("""function(params) { return {'backgroundColor': '#EFF6FF', 'color': '#1D4ED8', 'fontWeight': 'bold', 'border': '1px solid #BFDBFE'}; }""")
        if "Precio EXW" in df_ed: gb.configure_column("Precio EXW", editable=True, cellStyle=js_edit, type=["numericColumn"], precision=3, width=120)

        if "%/CP" in df_ed: gb.configure_column("%/CP", type=["numericColumn"], precision=2, valueFormatter="x.toLocaleString() + ' %'", width=90)
        if "Precio_escandallo_Calculado" in df_ed: gb.configure_column("Precio_escandallo_Calculado", header_name="Rentabilidad", type=["numericColumn"], precision=4, valueFormatter="x.toLocaleString() + ' €'", sort='desc')

        response = AgGrid(
            df_ed, 
            gridOptions=gb.build(), 
            update_mode=GridUpdateMode.VALUE_CHANGED, 
            allow_unsafe_jscode=True, 
            height=600, 
            theme='alpine', 
            fit_columns_on_grid_load=True, 
            key=f"ranking_grid_{st.session_state.grid_key}"
        )

        df_mod = pd.DataFrame(response['data'])
        if not df_mod.empty and "Precio EXW" in df_mod.columns:
            df_mod['Precio EXW'] = pd.to_numeric(df_mod['Precio EXW'], errors='coerce').fillna(0.0)
            df_ed['Precio EXW'] = pd.to_numeric(df_ed['Precio EXW'], errors='coerce').fillna(0.0)

            # ✨ OPTIMIZACIÓN SEGURA ✨
            diferencias = df_mod['Precio EXW'] - df_ed['Precio EXW']
            if diferencias.abs().sum() > 0.0001:
                 st.toast("⚡ Guardando cambios...", icon="📊")
                 
                 # Filtramos SOLO la fila cambiada (esto le da velocidad)
                 cambios = df_mod[diferencias.abs() > 0.0001]
                 
                 for i, r in cambios.iterrows():
                    mask = (st.session_state.df_global['Escandallo'] == r['Escandallo']) & (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                    st.session_state.df_global.loc[mask, 'Precio EXW'] = float(r['Precio EXW'])

                 # Recalculamos con la función rápida global
                 st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
                 
                 # 🔥 LA CLAVE QUE EVITA EL BUCLE INFINITO 🔥
                 st.session_state.grid_key += 1 
                 st.rerun()

    # --- PESTAÑA 3: RENTABILIDAD DE CLIENTES ---
    with tab3:
        st.info("💡 Rentabilidad calculada simulando el precio de venta del cliente sobre todo el escandallo.")
        
        df_ventas, err_v = load_sales_data()
        
        if err_v:
            st.error(err_v)
        elif df_ventas is not None and not df_ventas.empty:
            df_esc_completo = st.session_state.df_global.copy()
            
            if 'Tipo' in df_esc_completo.columns:
                df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)]
            else:
                df_princ = pd.DataFrame()
                
            if not df_princ.empty:
                df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                
                df_ventas['Código'] = df_ventas['Código'].astype(str)
                
                ventas_match = []
                ventas_sobrantes = []
                
                for idx, row in df_ventas.iterrows():
                    # Usamos .get() que es una forma segura de pedir un dato. 
                    cod_vendido = str(row.get('Código', ''))
                    
                    # Hacemos lo mismo con el precio por precaución
                    precio_raw = row.get('Precio EXW', 0.0)
                    precio_cliente = precio_raw if pd.notna(precio_raw) else 0.0
                    
                    if cod_vendido in mapa_escandallos:
                        esc_id = mapa_escandallos[cod_vendido]
                        
                        df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id].copy()
                        
                        mask_art = df_bloque_esc['Código'].astype(str) == cod_vendido
                        df_bloque_esc.loc[mask_art, 'Precio EXW'] = precio_cliente
                        
                        for c in ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']:
                            if c not in df_bloque_esc.columns: df_bloque_esc[c] = 0.0
                            
                        rentabilidad_lineas = (df_bloque_esc['Precio EXW'] - df_bloque_esc['Coste_congelación'] - df_bloque_esc['Coste_despiece']) * df_bloque_esc['%_Calculado']
                        
                        rentabilidad_total_escandallo = rentabilidad_lineas.sum()
                        familia_esc = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else ""
                        
                        row_dict = row.to_dict()
                        row_dict['Familia'] = familia_esc
                        row_dict['Rentabilidad'] = rentabilidad_total_escandallo
                        row_dict['Nº Escandallo Usado'] = esc_id
                        ventas_match.append(row_dict)
                    else:
                        ventas_sobrantes.append(row.to_dict())
                
                df_match = pd.DataFrame(ventas_match)
                df_sobrantes = pd.DataFrame(ventas_sobrantes)
                
                if not df_match.empty:
                    # ---> NUEVO DASHBOARD EJECUTIVO <---
                    
                    # 1. Aseguramos Kilos como número para cálculos
                    df_match['Kilos'] = pd.to_numeric(df_match['Kilos'], errors='coerce').fillna(0)

                    # 2. Calculamos la rentabilidad media del Mercado (por Artículo)
                    mercado_art = df_match.groupby('Nombre').apply(
                        lambda x: x['Rentabilidad'].sum() / x['Kilos'].sum() if x['Kilos'].sum() > 0 else 0
                    ).to_dict()

                    # 3. Calculamos la "Rentabilidad Esperada a precio de Mercado" para cada venta
                    df_match['Rent_Mercado_Total'] = df_match.apply(lambda r: mercado_art.get(r['Nombre'], 0) * r['Kilos'], axis=1)

                    # 4. Agrupamos por Cliente para los KPI globales
                    df_kpi_cli = df_match.groupby('Cliente').agg(
                        Kilos_Totales=('Kilos', 'sum'),
                        Rentabilidad_Total=('Rentabilidad', 'sum'),
                        Rent_Mercado_Total_Cli=('Rent_Mercado_Total', 'sum')
                    ).reset_index()

                    df_kpi_cli['Rentabilidad_Media_KG'] = np.where(df_kpi_cli['Kilos_Totales'] > 0, df_kpi_cli['Rentabilidad_Total'] / df_kpi_cli['Kilos_Totales'], 0)
                    df_kpi_cli['Diferencia_Mercado'] = df_kpi_cli['Rentabilidad_Total'] - df_kpi_cli['Rent_Mercado_Total_Cli']

                    # --- NIVEL 1: CUADRANTE MÁGICO ---
                    st.markdown("### 🎯 Nivel 1: Cuadrante Mágico de Clientes")
                    media_kilos = df_kpi_cli['Kilos_Totales'].mean()
                    media_rent = df_kpi_cli['Rentabilidad_Media_KG'].mean()

                    fig = px.scatter(
                        df_kpi_cli, x='Kilos_Totales', y='Rentabilidad_Media_KG',
                        text='Cliente', size='Kilos_Totales', color='Diferencia_Mercado',
                        color_continuous_scale=px.colors.diverging.RdYlGn,
                        hover_data=['Rentabilidad_Total', 'Diferencia_Mercado'],
                        labels={'Kilos_Totales': 'Volumen (Kilos)', 'Rentabilidad_Media_KG': 'Rentabilidad Media (€/kg)', 'Diferencia_Mercado': 'vs Mercado (€)'}
                    )
                    fig.add_hline(y=media_rent, line_dash="dash", line_color="gray", annotation_text="Media Rentabilidad")
                    fig.add_vline(x=media_kilos, line_dash="dash", line_color="gray", annotation_text="Media Volumen")
                    fig.update_traces(textposition='top center')
                    fig.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig, use_container_width=True)

                    st.divider()

                    # --- NIVEL 2: RANKING DE DESEMPEÑO ---
                    st.markdown("### 🏆 Nivel 2: Ranking de Desempeño por Cliente")
                    st.info("💡 Haz clic en una fila para ver el detalle por Familia abajo.")

                    gb_dash = GridOptionsBuilder.from_dataframe(df_kpi_cli[['Cliente', 'Kilos_Totales', 'Rentabilidad_Media_KG', 'Diferencia_Mercado']])
                    gb_dash.configure_selection(selection_mode='single', use_checkbox=False)
                    gb_dash.configure_column('Kilos_Totales', header_name="Volumen Kilos", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' kg'", precision=2)
                    gb_dash.configure_column('Rentabilidad_Media_KG', header_name="Rent. Media (€/kg)", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €/kg'", precision=3)

                    js_sem_mercado = JsCode("""function(params) {
                        if (params.value > 0) return {'color': '#166534', 'fontWeight': 'bold'};
                        if (params.value < 0) return {'color': '#991B1B', 'fontWeight': 'bold'};
                        return {'color': '#4B5563'};
                    }""")
                    gb_dash.configure_column('Diferencia_Mercado', header_name="Ganancia/Pérdida vs Mercado", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=2, cellStyle=js_sem_mercado)

                    grid_response = AgGrid(
                        df_kpi_cli, gridOptions=gb_dash.build(), theme='alpine', height=300,
                        fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
                        update_mode=GridUpdateMode.SELECTION_CHANGED, key="grid_ranking_cli"
                    )

                    st.divider()

                    # --- NIVEL 3: ZOOM AL CLIENTE ---
                    st.markdown("### 🔍 Nivel 3: Zoom al Cliente (Detalle por Familia)")
                    
                    # Manejo seguro de la selección de AgGrid
                    selected_rows = grid_response.get('selected_rows', [])
                    cliente_sel = None
                    
                    if isinstance(selected_rows, pd.DataFrame):
                        if not selected_rows.empty:
                            cliente_sel = selected_rows.iloc[0]['Cliente']
                    elif len(selected_rows) > 0:
                        cliente_sel = selected_rows[0].get('Cliente')

                    if cliente_sel:
                        st.success(f"Mostrando detalle para: **{cliente_sel}**")

                        df_cli_detalle = df_match[df_match['Cliente'] == cliente_sel].copy()

                        # Agrupar por Familia
                        df_zoom = df_cli_detalle.groupby('Familia').agg(
                            Kilos=('Kilos', 'sum'),
                            Rentabilidad_Total=('Rentabilidad', 'sum'),
                            Rent_Mercado_Total=('Rent_Mercado_Total', 'sum')
                        ).reset_index()

                        df_zoom['Rentabilidad_KG'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Rentabilidad_Total'] / df_zoom['Kilos'], 0)
                        df_zoom['Rentabilidad_Mercado_KG'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Rent_Mercado_Total'] / df_zoom['Kilos'], 0)
                        df_zoom['Dif_vs_Mercado_KG'] = df_zoom['Rentabilidad_KG'] - df_zoom['Rentabilidad_Mercado_KG']

                        gb_zoom = GridOptionsBuilder.from_dataframe(df_zoom[['Familia', 'Kilos', 'Rentabilidad_KG', 'Dif_vs_Mercado_KG']])
                        gb_zoom.configure_column('Kilos', type=["numericColumn"], valueFormatter="x.toLocaleString() + ' kg'", precision=2)
                        gb_zoom.configure_column('Rentabilidad_KG', type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €/kg'", precision=3)
                        
                        js_zoom_sem = JsCode("""function(params) {
                            if (params.value > 0) return {'color': '#166534', 'fontWeight': 'bold', 'backgroundColor': '#DCFCE7'};
                            if (params.value < 0) return {'color': '#991B1B', 'fontWeight': 'bold', 'backgroundColor': '#FEE2E2'};
                            return {};
                        }""")
                        gb_zoom.configure_column('Dif_vs_Mercado_KG', header_name="+/- vs Mercado (€/kg)", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=3, cellStyle=js_zoom_sem)

                        AgGrid(df_zoom, gridOptions=gb_zoom.build(), theme='alpine', height=250, fit_columns_on_grid_load=True, allow_unsafe_jscode=True, key="grid_zoom_cli")
                    else:
                        st.info("👆 Selecciona un cliente en la tabla superior para ver su detalle por familia.")

                    # ---> FIN NUEVO DASHBOARD <---
                    
                    st.divider()
                    
                    # --- TABLAS ANTIGUAS OCULTAS ---
                    with st.expander("🗄️ Ver Datos Originales en Bruto"):
                        disp_cols = {}
                        if 'Nombre' in df_match.columns: disp_cols['Nombre'] = 'Artículo'
                        if 'Cliente' in df_match.columns: disp_cols['Cliente'] = 'Cliente'
                        if 'Familia' in df_match.columns: disp_cols['Familia'] = 'Familia'
                        if 'Precio EXW' in df_match.columns: disp_cols['Precio EXW'] = 'Precio EXW Cliente'
                        disp_cols['Rentabilidad'] = 'Rentabilidad (Corte Primario)'
                        disp_cols['Nº Escandallo Usado'] = 'Nº Escandallo Usado'
                        
                        df_match_disp = df_match.rename(columns=disp_cols)
                        
                        st.markdown("##### 🎛️ Filtros de Rentabilidad Bruta")
                        f1, f2, f3 = st.columns(3)
                        
                        familias_t3 = sorted(df_match_disp['Familia'].dropna().unique()) if 'Familia' in df_match_disp.columns else []
                        sel_fam_t3 = f1.multiselect("📂 Familia", options=familias_t3, key="f_fam_t3")
                        
                        articulos_t3 = sorted(df_match_disp['Artículo'].dropna().unique()) if 'Artículo' in df_match_disp.columns else []
                        sel_art_t3 = f2.multiselect("🏷️ Artículo", options=articulos_t3, key="f_art_t3")
                        
                        clientes_t3 = sorted(df_match_disp['Cliente'].dropna().unique()) if 'Cliente' in df_match_disp.columns else []
                        sel_cli_t3 = f3.multiselect("🏢 Cliente", options=clientes_t3, key="f_cli_t3")
                        
                        mask_t3 = pd.Series(True, index=df_match_disp.index)
                        if sel_fam_t3: mask_t3 &= df_match_disp['Familia'].isin(sel_fam_t3)
                        if sel_art_t3: mask_t3 &= df_match_disp['Artículo'].isin(sel_art_t3)
                        if sel_cli_t3: mask_t3 &= df_match_disp['Cliente'].isin(sel_cli_t3)
                        
                        df_final_t3 = df_match_disp[mask_t3][list(disp_cols.values())]
                        
                        st.markdown("### ✅ Rentabilidad por Artículo/Cliente")
                        gb3 = GridOptionsBuilder.from_dataframe(df_final_t3)
                        gb3.configure_default_column(type=["leftAligned"], filter=True, sortable=True)
                        if 'Precio EXW Cliente' in df_final_t3:
                            gb3.configure_column('Precio EXW Cliente', type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=3)
                        if 'Rentabilidad (Corte Primario)' in df_final_t3:
                            gb3.configure_column('Rentabilidad (Corte Primario)', type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=4)
                        
                        AgGrid(df_final_t3, gridOptions=gb3.build(), theme='alpine', height=400, fit_columns_on_grid_load=True, key="grid_match_t3")
                else:
                    st.warning("No se encontraron coincidencias entre las ventas y los artículos 'Principales' de tus escandallos.")
                
                # --- SOBRANTES TAMBIÉN DENTRO DEL EXPANDER O ABAJO ---
                with st.expander("⚠️ Ver Artículos Sobrantes (Sin escandallo)"):
                    if not df_sobrantes.empty:
                        cols_sobrantes = ['Código', 'Nombre', 'Cliente', 'Precio EXW', 'Kilos']
                        cols_sobrantes = [c for c in cols_sobrantes if c in df_sobrantes.columns]
                        df_sob_disp = df_sobrantes[cols_sobrantes]
                        
                        gb_sob = GridOptionsBuilder.from_dataframe(df_sob_disp)
                        gb_sob.configure_default_column(filter=True, sortable=True)
                        AgGrid(df_sob_disp, gridOptions=gb_sob.build(), theme='alpine', height=300, fit_columns_on_grid_load=True, key="grid_sob_t3")
                        
                        csv_sob = df_sob_disp.to_csv(index=False).encode('utf-8')
                        st.download_button(label="📥 Descargar Sobrantes a CSV/Excel", data=csv_sob, file_name='articulos_sobrantes.csv', mime='text/csv')
                    else:
                        st.success("¡Excelente! Todos los artículos vendidos tienen un escandallo principal asociado.")
            else:
                st.warning("No hay artículos marcados como 'Principal' en tu fichero de Escandallos original.")
