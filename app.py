import streamlit as st
import pandas as pd
import numpy as np
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
        st.info("💡 Edita la columna **AZUL** y pulsa Enter.")

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

        response = AgGrid(df_ed, gridOptions=gb.build(), update_mode=GridUpdateMode.VALUE_CHANGED, allow_unsafe_jscode=True, height=600, theme='alpine', fit_columns_on_grid_load=True, key=f"ranking_grid_{st.session_state.grid_key}")

        df_mod = pd.DataFrame(response['data'])
        if not df_mod.empty and "Precio EXW" in df_mod.columns:
            df_mod['Precio EXW'] = pd.to_numeric(df_mod['Precio EXW'], errors='coerce').fillna(0.0)
            df_ed['Precio EXW'] = pd.to_numeric(df_ed['Precio EXW'], errors='coerce').fillna(0.0)

            if abs(df_mod['Precio EXW'].sum() - df_ed['Precio EXW'].sum()) > 0.0001:
                 st.toast("⚡ Recalculando...", icon="📊")
                 for i, r in df_mod.iterrows():
                    mask = (st.session_state.df_global['Escandallo'] == r['Escandallo']) & (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                    st.session_state.df_global.loc[mask, 'Precio EXW'] = float(r['Precio EXW'])

                 st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
                 st.session_state.grid_key += 1
                 st.rerun()

    # --- PESTAÑA 3: RENTABILIDAD DE CLIENTES (CORREGIDA: ESCANDALLO COMPLETO) ---
    with tab3:
        st.info("💡 Rentabilidad calculada simulando el precio de venta del cliente sobre todo el escandallo.")
        
        df_ventas, err_v = load_sales_data()
        
        if err_v:
            st.error(err_v)
        elif df_ventas is not None and not df_ventas.empty:
            df_esc_completo = st.session_state.df_global.copy()
            
            # 1. Crear un mapa para saber qué "Código Principal" pertenece a qué "Escandallo"
            if 'Tipo' in df_esc_completo.columns:
                df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)]
            else:
                df_princ = pd.DataFrame()
                
            if not df_princ.empty:
                # Tomamos el primer escandallo donde el código sea principal
                df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                
                df_ventas['Código'] = df_ventas['Código'].astype(str)
                
                ventas_match = []
                ventas_sobrantes = []
                
                # 2. Recorrer ventas y recalcular el bloque entero de escandallo
                for idx, row in df_ventas.iterrows():
                    cod_vendido = row['Código']
                    precio_cliente = row['Precio EXW'] if pd.notna(row['Precio EXW']) else 0.0
                    
                    if cod_vendido in mapa_escandallos:
                        esc_id = mapa_escandallos[cod_vendido]
                        
                        # Aislamos TODAS las filas de este escandallo
                        df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id].copy()
                        
                        # Cambiamos el Precio EXW SOLO para el artículo vendido
                        mask_art = df_bloque_esc['Código'].astype(str) == cod_vendido
                        df_bloque_esc.loc[mask_art, 'Precio EXW'] = precio_cliente
                        
                        # Recalculamos matemáticamente todo el bloque
                        for c in ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']:
                            if c not in df_bloque_esc.columns: df_bloque_esc[c] = 0.0
                            
                        rentabilidad_lineas = (df_bloque_esc['Precio EXW'] - df_bloque_esc['Coste_congelación'] - df_bloque_esc['Coste_despiece']) * df_bloque_esc['%_Calculado']
                        
                        # La rentabilidad real es la suma de todo el escandallo modificado
                        rentabilidad_total_escandallo = rentabilidad_lineas.sum()
                        familia_esc = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else ""
                        
                        # Guardamos los resultados
                        row_dict = row.to_dict()
                        row_dict['Familia'] = familia_esc
                        row_dict['Rentabilidad'] = rentabilidad_total_escandallo
                        row_dict['Nº Escandallo Usado'] = esc_id
                        ventas_match.append(row_dict)
                    else:
                        ventas_sobrantes.append(row.to_dict())
                
                df_match = pd.DataFrame(ventas_match)
                df_sobrantes = pd.DataFrame(ventas_sobrantes)
                
                # 3. Mostrar Resultados Coincidentes
                if not df_match.empty:
                    # Renombrar columnas para la visualización
                    disp_cols = {}
                    if 'Nombre' in df_match.columns: disp_cols['Nombre'] = 'Artículo'
                    if 'Cliente' in df_match.columns: disp_cols['Cliente'] = 'Cliente'
                    if 'Familia' in df_match.columns: disp_cols['Familia'] = 'Familia'
                    if 'Precio EXW' in df_match.columns: disp_cols['Precio EXW'] = 'Precio EXW Cliente'
                    disp_cols['Rentabilidad'] = 'Rentabilidad (Corte Primario)'
                    disp_cols['Nº Escandallo Usado'] = 'Nº Escandallo Usado'
                    
                    df_match_disp = df_match.rename(columns=disp_cols)
                    
                    st.markdown("##### 🎛️ Filtros de Rentabilidad (Solo afectan a esta pestaña)")
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
                
                # 4. Tabla de Sobrantes (Camino B)
                st.divider()
                st.markdown("### ⚠️ Artículos Sobrantes (No encontrados como 'Principales')")
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
