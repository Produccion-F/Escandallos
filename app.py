import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import plotly.express as px
import plotly.graph_objects as go

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
                
        if 'Código' in df_v.columns:
            df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
            
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

            diferencias = df_mod['Precio EXW'] - df_ed['Precio EXW']
            if diferencias.abs().sum() > 0.0001:
                 st.toast("⚡ Guardando cambios...", icon="📊")
                 
                 cambios = df_mod[diferencias.abs() > 0.0001]
                 
                 for i, r in cambios.iterrows():
                    mask = (st.session_state.df_global['Escandallo'] == r['Escandallo']) & (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                    st.session_state.df_global.loc[mask, 'Precio EXW'] = float(r['Precio EXW'])

                 st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
                 
                 st.session_state.grid_key += 1 
                 st.rerun()

    # --- PESTAÑA 3: RENTABILIDAD EJECUTIVA DE CLIENTES ---
    with tab3:
        st.info("💡 **Panel Ejecutivo:** Analiza la rentabilidad real de la 'cesta de compra' de cada cliente y compárala con el precio medio de mercado.")
        
        df_ventas, err_v = load_sales_data()
        
        if err_v:
            st.error(err_v)
        elif df_ventas is not None and not df_ventas.empty:
            df_esc_completo = st.session_state.df_global.copy()
            
            if 'Código' not in df_ventas.columns:
                st.error("🚨 El fichero de ventas no tiene la columna 'Código' requerida. Revisa el Excel de ventas.")
            else:
                if 'Tipo' in df_esc_completo.columns:
                    df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)]
                else:
                    df_princ = pd.DataFrame()
                    
                if not df_princ.empty:
                    df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                    mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                    
                    ventas_procesadas = []
                    
                    for idx, row in df_ventas.iterrows():
                        cod_vendido = str(row.get('Código', '')).strip()
                        precio_cliente = row.get('Precio EXW', 0.0)
                        kilos_cliente = row.get('Kilos', 0.0)
                        nombre_cliente = str(row.get('Cliente', 'Desconocido'))
                        nombre_articulo = str(row.get('Nombre', ''))
                        
                        if pd.isna(precio_cliente): precio_cliente = 0.0
                        if pd.isna(kilos_cliente): kilos_cliente = 0.0
                        
                        rent_unit = 0.0
                        familia_esc = "Sin clasificar"
                        
                        if cod_vendido in mapa_escandallos:
                            esc_id = mapa_escandallos[cod_vendido]
                            df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id].copy()
                            mask_art = df_bloque_esc['Código'].astype(str) == cod_vendido
                            df_bloque_esc.loc[mask_art, 'Precio EXW'] = float(precio_cliente)
                            
                            for c in ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']:
                                if c not in df_bloque_esc.columns: df_bloque_esc[c] = 0.0
                                
                            rentabilidad_lineas = (df_bloque_esc['Precio EXW'] - df_bloque_esc['Coste_congelación'] - df_bloque_esc['Coste_despiece']) * df_bloque_esc['%_Calculado']
                            rent_unit = rentabilidad_lineas.sum()
                            
                            fam_temp = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else ""
                            if pd.notna(fam_temp) and str(fam_temp).strip() != "":
                                familia_esc = fam_temp
                        
                        ventas_procesadas.append({
                            'Cliente': nombre_cliente,
                            'Código': cod_vendido,
                            'Artículo': nombre_articulo,
                            'Familia': familia_esc,
                            'Kilos': float(kilos_cliente),
                            'Rentabilidad_Unit_kg': float(rent_unit),
                            'Rentabilidad_Total': float(rent_unit) * float(kilos_cliente)
                        })
                    
                    df_proc = pd.DataFrame(ventas_procesadas)
                    
                    bench_familia = {}
                    for fam in df_proc['Familia'].unique():
                        df_f = df_proc[df_proc['Familia'] == fam]
                        tot_k = df_f['Kilos'].sum()
                        tot_r = df_f['Rentabilidad_Total'].sum()
                        bench_familia[fam] = tot_r / tot_k if tot_k > 0 else 0.0
                        
                    df_cli = df_proc.groupby('Cliente').agg(
                        Kilos_Totales=('Kilos', 'sum'),
                        Rent_Total=('Rentabilidad_Total', 'sum')
                    ).reset_index()
                    
                    df_cli['Rent_Media_kg'] = np.where(df_cli['Kilos_Totales'] > 0, df_cli['Rent_Total'] / df_cli['Kilos_Totales'], 0.0)
                    
                    def calc_vs_market(cliente):
                        df_c = df_proc[df_proc['Cliente'] == cliente]
                        extra = 0.0
                        for _, r in df_c.iterrows():
                            if r['Kilos'] > 0:
                                mkt_rent = bench_familia.get(r['Familia'], 0.0)
                                diff = r['Rentabilidad_Unit_kg'] - mkt_rent
                                extra += diff * r['Kilos']
                        return extra
                        
                    df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
                    
                    # --- VISUALIZACIÓN: CUADRANTE MÁGICO ---
                    st.subheader("🎯 Cuadrante Mágico: Kilos vs Rentabilidad Media")
                    st.caption("⚠️ *Si ves un error rojo aquí en lugar del gráfico, pulsa **Ctrl + F5** (o Cmd + Shift + R en Mac) para recargar la memoria de tu navegador.*")
                    
                    avg_kilos = df_cli['Kilos_Totales'].mean() if not df_cli.empty else 0
                    avg_rent = df_cli['Rent_Media_kg'].mean() if not df_cli.empty else 0
                    
                    try:
                        fig = px.scatter(
                            df_cli, x='Kilos_Totales', y='Rent_Media_kg',
                            text='Cliente', hover_name='Cliente',
                            size=[max(20, k) for k in df_cli['Kilos_Totales']], 
                            color='Vs_Mercado_Euros', color_continuous_scale='RdYlGn',
                            labels={'Rent_Media_kg': 'Rentabilidad Media (€/kg)', 'Kilos_Totales': 'Volumen Total (kg)'},
                            height=550
                        )
                        fig.add_hline(y=avg_rent, line_dash="dash", line_color="gray", annotation_text="Media de Rentabilidad")
                        fig.add_vline(x=avg_kilos, line_dash="dash", line_color="gray", annotation_text="Media de Volumen")
                        fig.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='DarkSlateGrey')))
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error cargando el gráfico visual (problema de caché): {e}")
                    
                    # --- VISUALIZACIÓN: RANKING EJECUTIVO ---
                    st.subheader("🏆 Ranking Ejecutivo de Desempeño por Cliente")
                    st.write("Selecciona un cliente haciendo clic en su fila para ver su desglose de familias.")
                    
                    gb = GridOptionsBuilder.from_dataframe(df_cli)
                    gb.configure_selection('single', use_checkbox=False)
                    gb.configure_default_column(sortable=True, filter=True)
                    gb.configure_column("Kilos_Totales", header_name="Kg Totales", type=["numericColumn"], valueFormatter="x.toLocaleString()", width=120)
                    gb.configure_column("Rent_Media_kg", header_name="Rent. Media (€/kg)", type=["numericColumn"], precision=4, width=150)
                    
                    js_color = JsCode("""
                    function(params) {
                        if (params.value > 0) return {'color': '#166534', 'backgroundColor': '#DCFCE7', 'fontWeight': 'bold'};
                        if (params.value < 0) return {'color': '#991B1B', 'backgroundColor': '#FEE2E2', 'fontWeight': 'bold'};
                        return null;
                    }
                    """)
                    gb.configure_column("Vs_Mercado_Euros", header_name="Desempeño vs Mercado (€)", cellStyle=js_color, type=["numericColumn"], precision=2, width=200)
                    gb.configure_column("Rent_Total", hide=True)
                    
                    grid_resp = AgGrid(
                        df_cli, gridOptions=gb.build(),
                        theme='alpine', height=350,
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        allow_unsafe_jscode=True,
                        key="grid_ranking_exec"
                    )
                    
                    # --- FIX DE INTERACCIÓN: Manejo robusto de la selección de AgGrid ---
                    selected_rows = grid_resp.get('selected_rows', [])
                    sel_list = []
                    
                    if isinstance(selected_rows, pd.DataFrame):
                        if not selected_rows.empty:
                            sel_list = selected_rows.to_dict('records')
                    elif isinstance(selected_rows, list):
                        sel_list = selected_rows
                        
                    # --- VISUALIZACIÓN: DRILL-DOWN (ZOOM AL CLIENTE) ---
                    if sel_list and len(sel_list) > 0:
                        cliente_sel = sel_list[0].get('Cliente')
                        st.divider()
                        st.subheader(f"🔍 Análisis de Cesta: {cliente_sel}")
                        
                        df_zoom = df_proc[df_proc['Cliente'] == cliente_sel].groupby('Familia').agg(
                            Kilos=('Kilos', 'sum'),
                            Rent_Total=('Rentabilidad_Total', 'sum')
                        ).reset_index()
                        
                        df_zoom['Rent_Cliente'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Rent_Total'] / df_zoom['Kilos'], 0.0)
                        df_zoom['Rent_Mercado'] = df_zoom['Familia'].map(bench_familia)
                        df_zoom['Diferencia_Unitaria'] = df_zoom['Rent_Cliente'] - df_zoom['Rent_Mercado']
                        df_zoom['Extra_Generado'] = df_zoom['Diferencia_Unitaria'] * df_zoom['Kilos']
                        
                        c1, c2 = st.columns([2, 1.5])
                        with c1:
                            try:
                                fig_bar = go.Figure()
                                fig_bar.add_trace(go.Bar(name='Cliente (€/kg)', x=df_zoom['Familia'], y=df_zoom['Rent_Cliente'], marker_color='#2563EB'))
                                fig_bar.add_trace(go.Bar(name='Media Empresa (€/kg)', x=df_zoom['Familia'], y=df_zoom['Rent_Mercado'], marker_color='#94A3B8'))
                                fig_bar.update_layout(title="Comparativa por Familia", barmode='group', height=350)
                                st.plotly_chart(fig_bar, use_container_width=True)
                            except Exception:
                                st.warning("Recarga la página (Ctrl+F5) para ver el gráfico comparativo.")
                            
                        with c2:
                            st.markdown("##### ⚖️ Impacto vs Mercado por Familia")
                            for _, r in df_zoom.iterrows():
                                color = "green" if r['Diferencia_Unitaria'] >= 0 else "red"
                                icon = "🟢" if r['Diferencia_Unitaria'] >= 0 else "🔴"
                                st.markdown(f"**{r['Familia']}** ({r['Kilos']:,.0f} kg)")
                                st.markdown(f"{icon} Diferencia: **{r['Diferencia_Unitaria']:+.4f} €/kg**")
                                st.markdown(f"↳ Impacto económico total: <span style='color:{color}; font-weight:bold'>{r['Extra_Generado']:+.2f} €</span>", unsafe_allow_html=True)
                                st.write("---")
                                
                    # --- GESTIÓN DE HUÉRFANOS ---
                    df_sobrantes = df_proc[df_proc['Familia'] == 'Sin clasificar']
                    if not df_sobrantes.empty:
                        st.divider()
                        with st.expander(f"⚠️ Ver artículos vendidos 'Sin clasificar' ({len(df_sobrantes)} registros sin escandallo asignado)"):
                            st.warning("Estos artículos no han encontrado cruce con los 'Principales' de la Pestaña 1. Se les ha asignado Rentabilidad 0 para no romper los cálculos.")
                            st.dataframe(df_sobrantes[['Código', 'Artículo', 'Cliente', 'Kilos']], use_container_width=True)
                            
                else:
                    st.warning("No hay artículos marcados como 'Principal' en tu fichero de Escandallos original.")
