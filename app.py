import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Escandallos",
    layout="wide",
    initial_sidebar_state="collapsed", 
    page_icon="🥩"
)

# --- CSS ESTILO POWER BI AVANZADO ---
st.markdown("""
    <style>
        /* Fondo general */
        .stApp { background-color: #F1F5F9; color: #1E293B; }
        
        /* KPIs MODO OSCURO */
        div[data-testid="stMetric"] { 
            background-color: #0F172A !important; /* Azul noche oscuro */
            border-radius: 12px; 
            padding: 20px; 
            border: 1px solid #334155; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); 
        }
        div[data-testid="stMetricValue"] { 
            color: #38BDF8 !important; /* Azul eléctrico brillante */
            font-size: 2.2rem !important; 
            font-weight: 800 !important;
        }
        div[data-testid="stMetricLabel"] { 
            color: #94A3B8 !important; /* Gris claro para el título */
            font-size: 1.1rem !important; 
            font-weight: 600 !important; 
        }

        /* Pestañas */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { background-color: #FFFFFF; border: 1px solid #CBD5E1; color: #475569; border-radius: 6px 6px 0 0; }
        .stTabs [aria-selected="true"] { background-color: #2563EB !important; color: #FFFFFF !important; font-weight: bold; }
        
        /* Textos y Etiquetas de Filtros */
        h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-family: 'Segoe UI', sans-serif; }
        .stMultiSelect label, .stSelectbox label, .stNumberInput label, .stCheckbox label { 
            font-size: 1.05rem !important; 
            font-weight: 600 !important; 
            color: #1E293B !important; 
        }
    </style>
""", unsafe_allow_html=True)

# --- CABECERAS DE TABLAS ---
custom_headers = [
    {'selector': 'th', 'props': [('background-color', '#1E293B'), ('color', '#FFFFFF'), ('font-size', '14px'), ('font-weight', 'bold'), ('text-align', 'center'), ('border-bottom', '2px solid #38BDF8')]},
    {'selector': 'td', 'props': [('font-size', '14px'), ('border-bottom', '1px solid #E2E8F0')]}
]

# --- ENLACES A DATOS ---
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'
SALES_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTlJBcdE77BaiNke-06GxDH8nY7vQ0wm_XgtDaVlF9cDDlFIxIawsTNZHrEPlv3uoVecih6_HRo7gqH/pub?gid=1543847315&single=true&output=csv'
EQUIV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=1911720872&single=true&output=csv'

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def formato_europeo(val, decimales=2, sufijo=""):
    if pd.isna(val) or val == np.inf or val == -np.inf: return "0" + sufijo
    formateado = f"{val:,.{decimales}f}"
    formateado = formateado.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formateado + sufijo

def recalcular_dataframe(df):
    if 'Cantidad(kg)' in df.columns and 'Escandallo' in df.columns:
        df['Total_Kg_Grupo'] = df.groupby('Escandallo')['Cantidad(kg)'].transform('sum')
        df['%_Calculado'] = np.where(df['Total_Kg_Grupo'] > 0, df['Cantidad(kg)'] / df['Total_Kg_Grupo'], 0.0)

    cols_calc = ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']
    if all(c in df.columns for c in cols_calc):
        df['Precio_escandallo_Calculado'] = (df['Precio EXW'] - df['Coste_congelación'] - df['Coste_despiece']) * df['%_Calculado']
    return df

# --- MOTOR DE CASCADA DINÁMICO ---
def procesar_ventas_cascada(df_v, df_esc_completo, mapa_esc_principal, mapa_equiv, esc_to_princ):
    global_avg = {}
    for cod, grp in df_v.groupby('Código'):
        tot_k = grp['Kilos'].sum()
        if tot_k > 0: global_avg[str(cod)] = (grp['Kilos'] * grp['Precio EXW']).sum() / tot_k

    client_avg = {}
    for cli, grp_cli in df_v.groupby('Cliente'):
        cli_str = str(cli)
        client_avg[cli_str] = {}
        for cod, grp_cod in grp_cli.groupby('Código'):
            tot_k = grp_cod['Kilos'].sum()
            if tot_k > 0: client_avg[cli_str][str(cod)] = (grp_cod['Kilos'] * grp_cod['Precio EXW']).sum() / tot_k

    ventas_procesadas = []

    for idx, row in df_v.iterrows():
        cod_vendido = str(row.get('Código', '')).strip()
        precio_cliente = float(row.get('Precio EXW', 0.0) or 0.0)
        kilos_cliente = float(row.get('Kilos', 0.0) or 0.0)
        nombre_cliente = str(row.get('Cliente', 'Desconocido'))
        nombre_articulo = str(row.get('Nombre', ''))

        esc_id = None
        cod_principal_teorico = None
        
        if cod_vendido in mapa_esc_principal:
            esc_id = mapa_esc_principal[cod_vendido]
            cod_principal_teorico = cod_vendido
        elif cod_vendido in mapa_equiv:
            esc_id = mapa_equiv[cod_vendido][0]
            cod_principal_teorico = mapa_equiv[cod_vendido][1]

        df_bloque_esc = pd.DataFrame()
        if esc_id is not None:
            df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id]

        if not df_bloque_esc.empty and cod_principal_teorico is not None:
            fam_temp = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else "Sin clasificar"
            if pd.isna(fam_temp) or str(fam_temp).strip() == "": fam_temp = "Sin clasificar"
            
            precio_cp_unitario_escandallo = 0.0
            
            for _, item in df_bloque_esc.iterrows():
                cod_item = str(item.get('Código', '')).strip()
                pct_item = float(item.get('%_Calculado', 0.0))
                coste_cong = float(item.get('Coste_congelación', 0.0))
                coste_desp = float(item.get('Coste_despiece', 0.0))
                
                if cod_item == cod_principal_teorico:
                    precio_exw_dinamico = precio_cliente
                else:
                    if cod_item in client_avg.get(nombre_cliente, {}):
                        precio_exw_dinamico = client_avg[nombre_cliente][cod_item]
                    elif cod_item in global_avg:
                        precio_exw_dinamico = global_avg[cod_item]
                    else:
                        precio_exw_dinamico = float(item.get('Precio EXW', 0.0))
                
                linea_cp = (precio_exw_dinamico - coste_cong - coste_desp) * pct_item
                precio_cp_unitario_escandallo += linea_cp

            ventas_procesadas.append({
                'Cliente': nombre_cliente, 'Código': cod_vendido, 'Artículo': nombre_articulo,
                'Familia': fam_temp, 'Kilos': kilos_cliente, 'Precio EXW': precio_cliente,
                'Precio_CP_Unitario': precio_cp_unitario_escandallo, 'Precio_CP_Total': precio_cp_unitario_escandallo * kilos_cliente
            })
        else:
            ventas_procesadas.append({
                'Cliente': nombre_cliente, 'Código': cod_vendido, 'Artículo': nombre_articulo,
                'Familia': 'Sin clasificar', 'Kilos': kilos_cliente, 'Precio EXW': precio_cliente,
                'Precio_CP_Unitario': 0.0, 'Precio_CP_Total': 0.0
            })

    return pd.DataFrame(ventas_procesadas), global_avg, client_avg

@st.cache_data(ttl=600)
def load_equiv_data():
    try:
        df_e = pd.read_csv(EQUIV_URL)
        df_e.columns = df_e.columns.str.strip()
        for c in df_e.columns:
            c_up = c.upper()
            if c_up in ['CODIGO', 'CÓDIGO']: df_e.rename(columns={c: 'Código'}, inplace=True)
            elif c_up == 'ESCANDALLO': df_e.rename(columns={c: 'Escandallo'}, inplace=True)
            elif c_up in ['CODIGO PRINCIPAL', 'CÓDIGO PRINCIPAL']: df_e.rename(columns={c: 'Codigo_Principal'}, inplace=True)
            
        if 'Código' in df_e.columns and 'Escandallo' in df_e.columns and 'Codigo_Principal' in df_e.columns:
            df_e['Código'] = df_e['Código'].astype(str).str.replace('.0', '', regex=False).str.strip()
            df_e['Codigo_Principal'] = df_e['Codigo_Principal'].astype(str).str.replace('.0', '', regex=False).str.strip()
            
            mapa_equiv = {}
            for _, row in df_e.iterrows():
                try:
                    val_esc = float(row['Escandallo'])
                    val_esc = int(val_esc) if val_esc.is_integer() else val_esc
                except: val_esc = row['Escandallo']
                mapa_equiv[row['Código']] = (val_esc, row['Codigo_Principal'])
            return mapa_equiv, None
        return {}, "Faltan columnas (Codigo, Escandallo o Codigo Principal) en tu archivo Excel de Equivalencias."
    except Exception as e:
        return {}, f"Error cargando equivalencias: {e}"

@st.cache_data(ttl=600)
def load_initial_data():
    try:
        df_raw = pd.read_csv(SHEET_URL)
    except Exception as e: return None, f"Error: {e}"
    df_raw.columns = df_raw.columns.str.strip()
    rename_map = {'Coste congelación': 'Coste_congelación', 'Coste congelacion': 'Coste_congelación', 'Coste despiece': 'Coste_despiece', 'Precio escandallo': 'Precio_escandallo', 'TIPO': 'Tipo', 'tipo': 'Tipo', 'Fecha': 'Fecha', 'fecha': 'Fecha', 'Cliente': 'Cliente'}
    df_raw.rename(columns={k:v for k,v in rename_map.items() if k in df_raw.columns}, inplace=True)
    if 'Tipo' not in df_raw.columns: df_raw['Tipo'] = ""
    for col in ['Cliente', 'Fecha', 'Familia', 'Formato']:
        if col not in df_raw.columns: df_raw[col] = ""
        else: df_raw[col] = df_raw[col].fillna("")
    if 'Código' in df_raw.columns: df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)
    cols_num = ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']
    for col in cols_num:
        if col in df_raw.columns: df_raw[col] = df_raw[col].apply(clean_european_number)
        else: df_raw[col] = 0.0
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
            if col in df_v.columns: df_v[col] = df_v[col].apply(clean_european_number)
        if 'Código' in df_v.columns: df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
        return df_v, None
    except Exception as e: return None, f"Error cargando ventas: {e}"

# --- CARGA Y ESTADO ---
if 'df_global' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global = data 
    st.session_state.df_global_base = data.copy()
if 'grid_key' not in st.session_state: st.session_state.grid_key = 0

# --- PRE-PROCESAMIENTO DE VENTAS GLOBAL ---
if 'df_proc_global' not in st.session_state:
    df_ventas, err_v = load_sales_data()
    st.session_state.err_v = err_v 
    mapa_equiv, err_e = load_equiv_data()
    if err_e: st.warning(err_e)
    st.session_state.mapa_equivalencias = mapa_equiv
    
    if not err_v and df_ventas is not None and not df_ventas.empty:
        df_ventas = df_ventas[~df_ventas['Cliente'].str.contains('Entradas a Congelar', case=False, na=False)]
        df_esc_completo = st.session_state.df_global_base.copy() 
        mapa_escandallos = {}
        esc_to_princ = {}
        if 'Código' in df_ventas.columns:
            df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)] if 'Tipo' in df_esc_completo.columns else pd.DataFrame()
            if not df_princ.empty:
                df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                df_princ_per_esc = df_princ.drop_duplicates(subset=['Escandallo'], keep='first')
                esc_to_princ = dict(zip(df_princ_per_esc['Escandallo'], df_princ_per_esc['Código'].astype(str)))
                
                df_proc_global, global_avg_base, client_avg_base = procesar_ventas_cascada(df_ventas, df_esc_completo, mapa_escandallos, mapa_equiv, esc_to_princ)
                
                bench_familia = {}
                if not df_proc_global.empty:
                    for fam in df_proc_global['Familia'].unique():
                        if fam != 'Sin clasificar':
                            df_f = df_proc_global[df_proc_global['Familia'] == fam]
                            tk, tr = df_f['Kilos'].sum(), df_f['Precio_CP_Total'].sum()
                            bench_familia[fam] = tr / tk if tk > 0 else 0.0
                            
                st.session_state.df_proc_global = df_proc_global
                st.session_state.global_avg_base = global_avg_base
                st.session_state.client_avg_base = client_avg_base
                st.session_state.bench_familia = bench_familia
                st.session_state.mapa_escandallos = mapa_escandallos
                st.session_state.esc_to_princ = esc_to_princ
                st.session_state.df_ventas_crudas = df_ventas
    else: st.session_state.df_proc_global = pd.DataFrame()

df_global_editable = st.session_state.df_global
df_proc_global = st.session_state.get('df_proc_global', pd.DataFrame())
global_avg_base = st.session_state.get('global_avg_base', {})
client_avg_base = st.session_state.get('client_avg_base', {})
bench_familia = st.session_state.get('bench_familia', {})
mapa_escandallos = st.session_state.get('mapa_escandallos', {})
esc_to_princ = st.session_state.get('esc_to_princ', {})
mapa_equivalencias = st.session_state.get('mapa_equivalencias', {})
df_ventas = st.session_state.get('df_ventas_crudas', pd.DataFrame())
err_v = st.session_state.get('err_v', None)

# --- ETIQUETAS FILTROS GLOBALES ---
try:
    if 'Tipo' in df_global_editable.columns and df_global_editable['Tipo'].str.contains('Principal', case=False, na=False).any():
        mask_p = df_global_editable['Tipo'].str.contains('Principal', case=False, na=False)
        df_principales = df_global_editable[mask_p][['Escandallo', 'Código', 'Nombre']]
    else:
        cols_exist = [c for c in ['Escandallo', 'Código', 'Nombre'] if c in df_global_editable.columns]
        df_principales = df_global_editable.groupby('Escandallo')[cols_exist[1:]].first().reset_index()
except:
    df_principales = df_global_editable[['Escandallo']].drop_duplicates()
    df_principales['Código'] = ""
    df_principales['Nombre'] = ""

df_principales = df_principales.drop_duplicates(subset=['Escandallo'])
df_principales['Texto_Escandallo'] = df_principales['Escandallo'].astype(str) + " | " + df_principales['Código'].astype(str) + " | " + df_principales['Nombre']
mapa_etiquetas = dict(zip(df_principales['Escandallo'], df_principales['Texto_Escandallo']))
df_global_editable['Filtro_Display'] = df_global_editable['Escandallo'].map(mapa_etiquetas)

# --- APP LAYOUT ---
c_title, c_btn = st.columns([4, 1])
c_title.title("📊 Panel de Escandallos y Rentabilidad")
if c_btn.button("🔄 Actualizar todos los datos", type="primary", use_container_width=True):
    st.cache_data.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico (Teórico)", "🏆 Ranking & Simulación", "📈 Panel Ejecutivo (Ventas Reales)"])

# --- FUNCIONES DE ESTILO DE TABLA ZEBRA ---
def zebra_base(row):
    if row.name % 2 == 0: return ['background-color: #F8F9FA; color: #1E293B'] * len(row)
    else: return ['background-color: #DBEAFE; color: #0F172A'] * len(row) # Azul claro contrastante

def style_rows_t1(row):
    tipo_val = row.get('Tipo', '')
    if tipo_val == 'TotalRow': return ['background-color: #064E3B; font-weight: bold; color: #FFFFFF'] * len(row)
    if isinstance(tipo_val, str) and 'principal' in tipo_val.lower(): return ['background-color: #1E40AF; font-weight: bold; color: #FFFFFF'] * len(row)
    return zebra_base(row)

# --- PESTAÑA 1: DETALLE TÉCNICO ---
with tab1:
    st.markdown("#### 🎛️ Filtros Teóricos")
    with st.container(border=True):
        col_t1_1, col_t1_2, col_t1_3 = st.columns(3)
        familias_t1 = sorted(df_global_editable['Familia'].unique()) if 'Familia' in df_global_editable.columns else []
        sel_familia_t1 = col_t1_1.multiselect("📂 Familia", options=familias_t1, key="f_fam_t1")
        formatos_t1 = sorted(df_global_editable['Formato'].unique()) if 'Formato' in df_global_editable.columns else []
        sel_formato_t1 = col_t1_2.multiselect("📦 Formato", options=formatos_t1, key="f_for_t1")
        mask_t1 = pd.Series(True, index=df_global_editable.index)
        if sel_familia_t1: mask_t1 &= df_global_editable['Familia'].isin(sel_familia_t1)
        if sel_formato_t1: mask_t1 &= df_global_editable['Formato'].isin(sel_formato_t1)
        opciones_escandallo_t1 = sorted(df_global_editable[mask_t1]['Filtro_Display'].dropna().unique())
        sel_escandallo_t1 = col_t1_3.multiselect("🏷️ Escandallo", options=opciones_escandallo_t1, key="f_esc_t1")
        if sel_escandallo_t1: mask_t1 &= df_global_editable['Filtro_Display'].isin(sel_escandallo_t1)
        df_t1_filtrado = df_global_editable[mask_t1].copy()

    if df_t1_filtrado.empty:
        st.info("ℹ️ No hay datos teóricos disponibles para los filtros seleccionados.")
    else:
        kpi_data = df_t1_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum()
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Escandallos Mostrados", f"{kpi_data.count()}")
        k2.metric("Media a CP Teórico", f"{formato_europeo(kpi_data.mean(), 2, ' €')}")
        k3.metric("Max a CP Teórico", f"{formato_europeo(kpi_data.max(), 2, ' €')}")
        k4.metric("Min a CP Teórico", f"{formato_europeo(kpi_data.min(), 2, ' €')}")
        st.divider()

        escandallos_unicos = df_t1_filtrado['Escandallo'].unique()
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
        c_pag2.markdown(f"<div style='text-align:center; color:#6B7280; margin-top:10px;'>Mostrando {st.session_state.page * ITEMS_PER_PAGE + 1} - {min((st.session_state.page + 1) * ITEMS_PER_PAGE, total_esc)} de {total_esc}</div>", unsafe_allow_html=True)

        start_idx = st.session_state.page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        escandallos_pagina = escandallos_unicos[start_idx:end_idx]

        for i, esc_id in enumerate(escandallos_pagina):
            df_f = df_t1_filtrado[df_t1_filtrado['Escandallo'] == esc_id].copy()
            titulo = f"Escandallo {esc_id}"
            if 'Filtro_Display' in df_f.columns: titulo = df_f['Filtro_Display'].iloc[0]
            st.markdown(f"#### 🔹 {titulo}", unsafe_allow_html=True)

            cols_ver = ['Cliente', 'Código', 'Nombre', 'Coste_despiece', 'Coste_congelación', '%_Calculado', 'Precio EXW', 'Precio_escandallo_Calculado', 'Tipo']
            cols_exist = [c for c in cols_ver if c in df_f.columns]
            df_v = df_f[cols_exist].copy().reset_index(drop=True)
            if '%_Calculado' in df_v.columns: df_v['%_Calculado'] = df_v['%_Calculado'] * 100

            row_total = {c: None for c in df_v.columns}; row_total['Nombre'] = 'TOTAL'; row_total['Tipo'] = 'TotalRow'
            if '%_Calculado' in df_v: row_total['%_Calculado'] = df_v['%_Calculado'].sum()
            if 'Precio_escandallo_Calculado' in df_v: row_total['Precio_escandallo_Calculado'] = df_v['Precio_escandallo_Calculado'].sum()

            df_fin = pd.concat([df_v, pd.DataFrame([row_total])], ignore_index=True)
            df_fin.rename(columns={'Precio_escandallo_Calculado': 'Precio a CP Teórico'}, inplace=True)

            styled_df = df_fin.style.apply(style_rows_t1, axis=1).format({
                '%_Calculado': lambda x: formato_europeo(x, 2, " %"),
                'Precio EXW': lambda x: formato_europeo(x, 3, " €"),
                'Precio a CP Teórico': lambda x: formato_europeo(x, 4, " €")
            }).set_table_styles(custom_headers)

            st.dataframe(styled_df, column_config={"Tipo": None}, use_container_width=True, hide_index=True)
            st.divider()

# --- PESTAÑA 2: RANKING Y SIMULACIÓN ---
with tab2:
    st.subheader("🏆 Simulador Teórico de Precios")
    st.info("💡 Haz doble clic en la columna **Precio EXW ✏️** para simular y editar. (Esto no afecta a las ventas reales de abajo).")

    st.markdown("#### 🎛️ Filtros del Simulador Teórico")
    with st.container(border=True):
        col_t2_1, col_t2_2, col_t2_3 = st.columns(3)
        familias_t2_sim = sorted(df_global_editable['Familia'].unique()) if 'Familia' in df_global_editable.columns else []
        sel_familia_t2_sim = col_t2_1.multiselect("📂 Familia", options=familias_t2_sim, key="f_fam_t2_sim")
        formatos_t2_sim = sorted(df_global_editable['Formato'].unique()) if 'Formato' in df_global_editable.columns else []
        sel_formato_t2_sim = col_t2_2.multiselect("📦 Formato", options=formatos_t2_sim, key="f_for_t2_sim")
        mask_t2_sim = pd.Series(True, index=df_global_editable.index)
        if sel_familia_t2_sim: mask_t2_sim &= df_global_editable['Familia'].isin(sel_familia_t2_sim)
        if sel_formato_t2_sim: mask_t2_sim &= df_global_editable['Formato'].isin(sel_formato_t2_sim)
        opciones_escandallo_t2_sim = sorted(df_global_editable[mask_t2_sim]['Filtro_Display'].dropna().unique())
        sel_escandallo_t2_sim = col_t2_3.multiselect("🏷️ Escandallo", options=opciones_escandallo_t2_sim, key="f_esc_t2_sim")
        if sel_escandallo_t2_sim: mask_t2_sim &= df_global_editable['Filtro_Display'].isin(sel_escandallo_t2_sim)
        df_sim_filtrado = df_global_editable[mask_t2_sim].copy()

    if df_sim_filtrado.empty:
        st.warning("No hay datos teóricos para los filtros seleccionados.")
    else:
        df_rank = df_sim_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()
        cols_info = ['Escandallo', 'Código', 'Nombre', '%_Calculado', 'Precio EXW']
        cols_info = [c for c in cols_info if c in df_sim_filtrado.columns]

        try:
            if 'Tipo' in df_sim_filtrado.columns and df_sim_filtrado['Tipo'].str.contains('Principal', case=False, na=False).any():
                df_pr = df_sim_filtrado[df_sim_filtrado['Tipo'].str.contains('Principal', case=False, na=False)][cols_info]
            else: df_pr = df_sim_filtrado.groupby('Escandallo')[cols_info].first().reset_index()
        except: df_pr = df_sim_filtrado.groupby('Escandallo')[cols_info].first().reset_index()

        df_suma = df_pr.groupby('Escandallo')['%_Calculado'].sum().reset_index()
        cols_desc = [c for c in cols_info if c != '%_Calculado' and c != 'Escandallo']
        df_desc = df_pr.groupby('Escandallo')[cols_desc].first().reset_index()

        df_final = pd.merge(df_rank, df_suma, on='Escandallo')
        df_final = pd.merge(df_final, df_desc, on='Escandallo').sort_values('Precio_escandallo_Calculado', ascending=False).reset_index(drop=True)

        df_final['Pos'] = range(1, len(df_final)+1)
        df_final['%/CP'] = df_final['%_Calculado'] * 100

        if not df_final.empty:
            q33, q66 = df_final['Precio_escandallo_Calculado'].quantile([0.33, 0.66])
            def get_sem(v): return "🟢 Alta" if v >= q66 else ("🟡 Media" if v >= q33 else "🔴 Baja")
            df_final['Estado'] = df_final['Precio_escandallo_Calculado'].apply(get_sem)
        else: df_final['Estado'] = "N/D"

        cols_vis = ['Pos', 'Estado', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
        cols_final = [c for c in cols_vis if c in df_final.columns] + ['Escandallo']
        df_ed = df_final[cols_final].copy()
        
        df_ed_display = df_ed.copy()
        df_ed_display['%/CP'] = df_ed['%/CP'].apply(lambda x: formato_europeo(x, 2, " %"))
        df_ed_display['Precio_escandallo_Calculado'] = df_ed['Precio_escandallo_Calculado'].apply(lambda x: formato_europeo(x, 4, " €"))

        # Aplicamos Zebra y sobreescribimos la celda editable
        styled_ed_display = df_ed_display.style.apply(zebra_base, axis=1)
        try: styled_ed_display = styled_ed_display.map(lambda _: 'background-color: #FEF08A; color: #075985; font-weight: bold;', subset=['Precio EXW'])
        except AttributeError: styled_ed_display = styled_ed_display.applymap(lambda _: 'background-color: #FEF08A; color: #075985; font-weight: bold;', subset=['Precio EXW'])
        
        styled_ed_display = styled_ed_display.set_table_styles(custom_headers)

        edited_df = st.data_editor(
            styled_ed_display,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", disabled=True),
                "Estado": st.column_config.TextColumn("Estado", disabled=True),
                "Precio EXW": st.column_config.NumberColumn("Precio EXW ✏️", required=True),
                "%/CP": st.column_config.TextColumn("%/CP", disabled=True),
                "Precio_escandallo_Calculado": st.column_config.TextColumn("Precio a CP Simulado", disabled=True),
                "Escandallo": None
            },
            disabled=["Pos", "Estado", "Código", "Nombre", "%/CP", "Precio_escandallo_Calculado", "Escandallo"],
            hide_index=True, use_container_width=True, key=f"editor_nativo_{st.session_state.grid_key}"
        )

        diferencias = edited_df['Precio EXW'] - df_ed['Precio EXW']
        if diferencias.abs().sum() > 0.0001:
             st.toast("⚡ Guardando simulación...", icon="📊")
             cambios = edited_df[diferencias.abs() > 0.0001]
             for i, r in cambios.iterrows():
                mask = (st.session_state.df_global['Escandallo'] == r['Escandallo']) & (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                st.session_state.df_global.loc[mask, 'Precio EXW'] = float(r['Precio EXW'])
             st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
             st.session_state.grid_key += 1 
             st.rerun()
         
    st.divider()
    
    # --- TABLA REAL LISTA MAESTRA ---
    st.subheader("📋 Escandallos Reales por Cliente (Lista Maestra)")
    st.write("Ventas reales calculadas con precios de mercado dinámicos. Haz clic en una fila para auditar su receta.")
    
    if not df_proc_global.empty:
        st.markdown("#### 🎛️ Filtros de Ventas Reales")
        with st.container(border=True):
            col_f2_1, col_f2_2, col_f2_3 = st.columns(3)
            df_proc_validos_t2 = df_proc_global[df_proc_global['Familia'] != 'Sin clasificar']
            
            clientes_t2 = sorted(df_proc_global['Cliente'].unique()) if not df_proc_global.empty else []
            sel_clientes_t2 = col_f2_1.multiselect("🏢 Cliente", options=clientes_t2, key="f_cli_t2")
            fams_t2 = sorted(df_proc_validos_t2['Familia'].unique()) if not df_proc_validos_t2.empty else []
            sel_familia_t2 = col_f2_2.multiselect("📂 Familia", options=fams_t2, key="f_fam_t2")
            arts_t2 = sorted(df_proc_validos_t2['Artículo'].unique()) if not df_proc_validos_t2.empty else []
            sel_arts_t2 = col_f2_3.multiselect("🏷️ Artículo", options=arts_t2, key="f_art_t2")
            
        df_proc_filtrado_t2 = df_proc_validos_t2.copy()
        if sel_clientes_t2: df_proc_filtrado_t2 = df_proc_filtrado_t2[df_proc_filtrado_t2['Cliente'].isin(sel_clientes_t2)]
        if sel_familia_t2: df_proc_filtrado_t2 = df_proc_filtrado_t2[df_proc_filtrado_t2['Familia'].isin(sel_familia_t2)]
        if sel_arts_t2: df_proc_filtrado_t2 = df_proc_filtrado_t2[df_proc_filtrado_t2['Artículo'].isin(sel_arts_t2)]
        
        if not df_proc_filtrado_t2.empty:
            df_master = df_proc_filtrado_t2.groupby(['Cliente', 'Familia', 'Código', 'Artículo']).agg(
                Kilos=('Kilos', 'sum'), Ingreso_EXW=('Precio_CP_Total', 'sum'), Precio_CP_Unitario=('Precio_CP_Unitario', 'first')
            ).reset_index()
            
            df_arts_master = df_proc_filtrado_t2.copy()
            df_arts_master['Ing_EXW'] = df_arts_master['Kilos'] * df_arts_master['Precio EXW']
            df_exw_master = df_arts_master.groupby(['Cliente', 'Familia', 'Código', 'Artículo']).agg(
                Ing_EXW=('Ing_EXW', 'sum'), Kilos=('Kilos', 'sum')
            ).reset_index()
            df_exw_master['Precio EXW'] = np.where(df_exw_master['Kilos']>0, df_exw_master['Ing_EXW']/df_exw_master['Kilos'], 0)
            
            df_master = pd.merge(df_master, df_exw_master[['Cliente', 'Código', 'Precio EXW']], on=['Cliente', 'Código'], how='left')
            df_master.rename(columns={'Precio_CP_Unitario': 'Precio a CP'}, inplace=True)
            df_master_disp = df_master[['Cliente', 'Familia', 'Código', 'Artículo', 'Kilos', 'Precio EXW', 'Precio a CP']].reset_index(drop=True)
            
            styled_master = df_master_disp.style.apply(zebra_base, axis=1).format({
                'Kilos': lambda x: formato_europeo(x, 0, " kg"),
                'Precio EXW': lambda x: formato_europeo(x, 3, " €"),
                'Precio a CP': lambda x: formato_europeo(x, 4, " €/kg")
            }).set_table_styles(custom_headers)

            event_master = st.dataframe(
                styled_master, use_container_width=True, hide_index=True,
                selection_mode="single-row", on_select="rerun", key="table_master_t2"
            )
            
            # --- TRAZABILIDAD TABLA MAESTRA ---
            if len(event_master.selection.rows) > 0:
                row_idx = event_master.selection.rows[0]
                sel_cli = str(df_master_disp.iloc[row_idx]['Cliente'])
                sel_cod = str(df_master_disp.iloc[row_idx]['Código'])
                sel_exw = float(df_master_disp.iloc[row_idx]['Precio EXW'])
                sel_art = str(df_master_disp.iloc[row_idx]['Artículo'])
                
                st.markdown(f"###### 🔎 Trazabilidad del Escandallo: {sel_cod} - {sel_art} (Cliente: {sel_cli})")
                
                esc_id = None; cod_principal_teorico = None; es_equivalencia = False
                if sel_cod in mapa_escandallos:
                    esc_id = mapa_escandallos[sel_cod]
                    cod_principal_teorico = sel_cod
                elif sel_cod in mapa_equivalencias:
                    esc_id = mapa_equivalencias[sel_cod][0]
                    cod_principal_teorico = mapa_equivalencias[sel_cod][1]
                    es_equivalencia = True
                
                if esc_id is not None and cod_principal_teorico is not None:
                    df_bloque_esc = st.session_state.df_global_base[st.session_state.df_global_base['Escandallo'] == esc_id]
                    
                    breakdown_data = []
                    for _, item in df_bloque_esc.iterrows():
                        cod_item = str(item.get('Código', '')).strip()
                        pct_item = float(item.get('%_Calculado', 0.0))
                        coste_cong = float(item.get('Coste_congelación', 0.0))
                        coste_desp = float(item.get('Coste_despiece', 0.0))
                        
                        if cod_item == cod_principal_teorico:
                            precio_aplicado = sel_exw; disp_cod = sel_cod
                            origen = "📍 Venta principal (Equivalencia)" if es_equivalencia else "📍 Venta principal (Esta factura)"
                            disp_name = f"{sel_art} (Equivalencia)" if es_equivalencia else item.get('Nombre', '')
                        else:
                            disp_cod = cod_item; disp_name = item.get('Nombre', '')
                            if cod_item in client_avg_base.get(sel_cli, {}):
                                precio_aplicado = client_avg_base[sel_cli][cod_item]; origen = "🥇 Venta a este cliente (P1)"
                            elif cod_item in global_avg_base:
                                precio_aplicado = global_avg_base[cod_item]; origen = "🥈 Media del mercado (P2)"
                            else:
                                precio_aplicado = float(item.get('Precio EXW', 0.0)); origen = "🥉 Precio teórico (P3)"
                        
                        linea_cp = (precio_aplicado - coste_cong - coste_desp) * pct_item
                        breakdown_data.append({
                            'Código': disp_cod, 'Artículo': disp_name, '% Rendimiento': pct_item * 100, 
                            'Origen del Precio': origen, 'Precio Aplicado': precio_aplicado,
                            'Coste Despiece': coste_desp, 'Coste Cong.': coste_cong, 'Aportación a CP': linea_cp
                        })
                        
                    df_breakdown = pd.DataFrame(breakdown_data).reset_index(drop=True)
                    def style_breakdown(row):
                        if row['Código'] == sel_cod: return ['background-color: #1E3A8A; font-weight: bold; color: #FFFFFF;'] * len(row)
                        return zebra_base(row)
                        
                    st.dataframe(
                        df_breakdown.style.apply(style_breakdown, axis=1).format({
                            '% Rendimiento': lambda x: formato_europeo(x, 2, " %"), 'Precio Aplicado': lambda x: formato_europeo(x, 3, " €"),
                            'Coste Despiece': lambda x: formato_europeo(x, 3, " €"), 'Coste Cong.': lambda x: formato_europeo(x, 3, " €"),
                            'Aportación a CP': lambda x: formato_europeo(x, 4, " €/kg")
                        }).set_table_styles(custom_headers), use_container_width=True, hide_index=True
                    )
                else: st.info("Este artículo no está registrado como 'Principal' ni como 'Equivalencia' en ningún escandallo.")
        else: st.info("ℹ️ Este cliente solo ha comprado artículos que no están mapeados. Revisa la tabla inferior de 'Sobrantes' en la pestaña Panel Ejecutivo.")

# --- PESTAÑA 3: PANEL EJECUTIVO ---
with tab3:
    if err_v: st.error(err_v)
    elif not df_proc_global.empty:
        st.markdown("#### 🎛️ Filtros de Análisis y Segmentación")
        with st.container(border=True):
            col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
            df_proc_validos = df_proc_global[df_proc_global['Familia'] != 'Sin clasificar']
            all_clients = sorted(df_proc_global['Cliente'].unique()) if not df_proc_global.empty else []
            buscador = col_f1.text_input("🔍 Auto-seleccionar cadena (Ej: Escribe 'COVI' o 'DIA')")
            clientes_preseleccionados = [c for c in all_clients if buscador.lower() in c.lower()] if buscador else []
            sel_clients = col_f1.multiselect("🏢 Clientes (Selecciona uno o varios)", all_clients, default=clientes_preseleccionados)
            agrupar_cadena = col_f1.checkbox("🔗 Agrupar clientes seleccionados como una 'Cadena'", value=bool(buscador))
            fams_disp = sorted(df_proc_validos['Familia'].unique()) if not df_proc_validos.empty else []
            sel_fams = col_f2.multiselect("📂 Familias", fams_disp)
            arts_disp = sorted(df_proc_validos['Artículo'].unique()) if not df_proc_validos.empty else []
            sel_arts = col_f3.multiselect("🏷️ Artículos", arts_disp)
            
            st.markdown("##### 🔢 Filtros Numéricos (KPIs)")
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                vol_op = st.selectbox("📊 Filtro por Volumen (kg)", ["-- Desactivado --", "Mayor o igual a (>=)", "Menor o igual a (<=)", "Entre"])
                if vol_op == "Mayor o igual a (>=)": min_kilos = st.number_input("Mínimo (kg)", value=1000, step=100)
                elif vol_op == "Menor o igual a (<=)": max_kilos = st.number_input("Máximo (kg)", value=5000, step=100)
                elif vol_op == "Entre":
                    c1, c2 = st.columns(2)
                    min_kilos = c1.number_input("Mínimo (kg)", value=1000, step=100)
                    max_kilos = c2.number_input("Máximo (kg)", value=5000, step=100)
            with col_n2:
                ben_op = st.selectbox("💶 Filtro por Beneficio (€/kg)", ["-- Desactivado --", "Mayor o igual a (>=)", "Menor o igual a (<=)", "Entre"])
                if ben_op == "Mayor o igual a (>=)": min_ben = st.number_input("Mínimo (€/kg)", value=0.0, step=0.1)
                elif ben_op == "Menor o igual a (<=)": max_ben = st.number_input("Máximo (€/kg)", value=0.0, step=0.1)
                elif ben_op == "Entre":
                    c3, c4 = st.columns(2)
                    min_ben = c3.number_input("Mínimo (€/kg)", value=-1.0, step=0.1)
                    max_ben = c4.number_input("Máximo (€/kg)", value=2.0, step=0.1)
        
        if sel_clients and agrupar_cadena:
            nombre_grupo = "GRUPO: " + " + ".join([c[:10] for c in sel_clients[:2]]) + ("..." if len(sel_clients)>2 else "")
            df_ventas_grupo = df_ventas.copy()
            df_ventas_grupo.loc[df_ventas_grupo['Cliente'].isin(sel_clients), 'Cliente'] = nombre_grupo
            df_proc_full, global_avg_active, client_avg_active = procesar_ventas_cascada(df_ventas_grupo, st.session_state.df_global_base, mapa_escandallos, mapa_equivalencias, esc_to_princ)
            df_proc = df_proc_full[df_proc_full['Cliente'] == nombre_grupo].copy()
        else:
            df_proc = df_proc_global.copy()
            global_avg_active = global_avg_base
            client_avg_active = client_avg_base
            if sel_clients: df_proc = df_proc[df_proc['Cliente'].isin(sel_clients)]
        
        df_proc_kpi = df_proc[df_proc['Familia'] != 'Sin clasificar']
        if sel_fams: df_proc_kpi = df_proc_kpi[df_proc_kpi['Familia'].isin(sel_fams)]
        if sel_arts: df_proc_kpi = df_proc_kpi[df_proc_kpi['Artículo'].isin(sel_arts)]
                
        if df_proc_kpi.empty:
            st.info("ℹ️ Los artículos de este cliente (o filtros) no coinciden con ningún escandallo. Por favor, revisa el desplegable inferior de 'Artículos Sin clasificar'.")
        else:
            df_cli = df_proc_kpi.groupby('Cliente').agg(Kilos_Totales=('Kilos', 'sum'), Precio_CP_Total=('Precio_CP_Total', 'sum')).reset_index()
            df_cli['Precio_Medio_CP'] = np.where(df_cli['Kilos_Totales'] > 0, df_cli['Precio_CP_Total'] / df_cli['Kilos_Totales'], 0.0)
            
            def calc_vs_market(cliente):
                df_c = df_proc_kpi[df_proc_kpi['Cliente'] == cliente]
                extra = 0.0
                for _, r in df_c.iterrows():
                    if r['Kilos'] > 0: extra += (r['Precio_CP_Unitario'] - bench_familia.get(r['Familia'], 0.0)) * r['Kilos']
                return extra
                
            df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
            df_cli['Beneficio_kg'] = np.where(df_cli['Kilos_Totales']>0, df_cli['Vs_Mercado_Euros'] / df_cli['Kilos_Totales'], 0.0)
            
            if vol_op == "Mayor o igual a (>=)": df_cli = df_cli[df_cli['Kilos_Totales'] >= min_kilos]
            elif vol_op == "Menor o igual a (<=)": df_cli = df_cli[df_cli['Kilos_Totales'] <= max_kilos]
            elif vol_op == "Entre": df_cli = df_cli[(df_cli['Kilos_Totales'] >= min_kilos) & (df_cli['Kilos_Totales'] <= max_kilos)]

            if ben_op == "Mayor o igual a (>=)": df_cli = df_cli[df_cli['Beneficio_kg'] >= min_ben]
            elif ben_op == "Menor o igual a (<=)": df_cli = df_cli[df_cli['Beneficio_kg'] <= max_ben]
            elif ben_op == "Entre": df_cli = df_cli[(df_cli['Beneficio_kg'] >= min_ben) & (df_cli['Beneficio_kg'] <= max_ben)]

            if df_cli.empty:
                st.warning("No hay clientes que cumplan con los filtros numéricos (Volumen o Beneficio) establecidos.")
            else:
                st.divider()
                st.markdown("### 📊 Indicadores de Rendimiento")
                
                clientes_filtrados = df_cli['Cliente'].tolist()
                df_proc_kpi_filtered = df_proc_kpi[df_proc_kpi['Cliente'].isin(clientes_filtrados)]
                
                kpi_kilos_totales = df_cli['Kilos_Totales'].sum()
                kpi_beneficio_abs = df_cli['Vs_Mercado_Euros'].sum()
                kpi_beneficio_kg = kpi_beneficio_abs / kpi_kilos_totales if kpi_kilos_totales > 0 else 0.0
                kpi_cp_medio = df_cli['Precio_CP_Total'].sum() / kpi_kilos_totales if kpi_kilos_totales > 0 else 0.0
                ingreso_exw_tot = (df_proc_kpi_filtered['Kilos'] * df_proc_kpi_filtered['Precio EXW']).sum()
                kpi_exw_medio = ingreso_exw_tot / kpi_kilos_totales if kpi_kilos_totales > 0 else 0.0
                
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Precio Medio EXW", f"{formato_europeo(kpi_exw_medio, 3, ' €')}")
                k2.metric("Precio Medio a CP", f"{formato_europeo(kpi_cp_medio, 4, ' €')}")
                k3.metric("Beneficio €/kg", f"{('+' if kpi_beneficio_kg>0 else '')}{formato_europeo(kpi_beneficio_kg, 4, ' €/kg')}")
                k4.metric("Beneficio absoluto (€)", f"{('+' if kpi_beneficio_abs>0 else '')}{formato_europeo(kpi_beneficio_abs, 2, ' €')}")

                df_cli['Kilos_Disp'] = df_cli['Kilos_Totales'].apply(lambda x: formato_europeo(x, 0, " kg"))
                df_cli['Precio_Medio_CP_Disp'] = df_cli['Precio_Medio_CP'].apply(lambda x: formato_europeo(x, 4, " €/kg"))
                df_cli['Beneficio_Abs_Disp'] = df_cli['Vs_Mercado_Euros'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €"))
                df_cli['Beneficio_kg_Disp'] = df_cli['Beneficio_kg'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 4, " €/kg"))

                st.divider()
                st.subheader("🎯 Gráfico de rentabilidad de cliente")
                
                avg_k = df_cli['Kilos_Totales'].mean()
                avg_b = df_cli['Beneficio_kg'].mean()
                
                base = alt.Chart(df_cli).mark_circle().encode(
                    x=alt.X('Kilos_Totales:Q', title='Volumen Vendido (kg)', axis=alt.Axis(format=',.0f', labelExpr="replace(datum.label, ',', '.')")),
                    y=alt.Y('Beneficio_kg:Q', title='Beneficio €/kg', scale=alt.Scale(zero=False), axis=alt.Axis(format='.2f', labelExpr="replace(datum.label, '.', ',')")),
                    size=alt.Size('Precio_CP_Total:Q', legend=None),
                    color=alt.Color('Beneficio_kg:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Beneficio €/kg', legend=alt.Legend(format=',.2f', labelExpr="replace(datum.label, '.', ',')")),
                    tooltip=[alt.Tooltip('Cliente:N', title='Cliente'), alt.Tooltip('Kilos_Disp:N', title='Volumen'), alt.Tooltip('Precio_Medio_CP_Disp:N', title='Precio Medio a CP'), alt.Tooltip('Beneficio_kg_Disp:N', title='Beneficio €/kg'), alt.Tooltip('Beneficio_Abs_Disp:N', title='Beneficio absoluto (€)')]
                )
                rule_x = alt.Chart(pd.DataFrame({'x': [avg_k]})).mark_rule(color='gray', strokeDash=[5,5]).encode(x='x:Q')
                rule_y = alt.Chart(pd.DataFrame({'y': [avg_b]})).mark_rule(color='gray', strokeDash=[5,5]).encode(y='y:Q')
                st.altair_chart(base + rule_x + rule_y, use_container_width=True)
                
                st.subheader("🏆 Ranking Ejecutivo")
                
                def color_vs_market(val):
                    if val > 0: return 'background-color: #DCFCE7; color: #166534; font-weight: bold;'
                    if val < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
                    return ''
                
                df_rank_display = df_cli[['Cliente', 'Kilos_Totales', 'Precio_Medio_CP', 'Beneficio_kg', 'Vs_Mercado_Euros']].copy().reset_index(drop=True)
                df_rank_display.rename(columns={'Kilos_Totales': 'Kilos', 'Precio_Medio_CP': 'Precio Medio a CP', 'Beneficio_kg': 'Beneficio €/kg', 'Vs_Mercado_Euros': 'Beneficio absoluto (€)'}, inplace=True)

                styled_rank = df_rank_display.style.apply(zebra_base, axis=1)
                try: styled_rank = styled_rank.map(color_vs_market, subset=['Beneficio absoluto (€)'])
                except AttributeError: styled_rank = styled_rank.applymap(color_vs_market, subset=['Beneficio absoluto (€)'])
                
                event = st.dataframe(
                    styled_rank.format({
                        'Kilos': lambda x: formato_europeo(x, 0, " kg"), 'Precio Medio a CP': lambda x: formato_europeo(x, 4, " €/kg"),
                        'Beneficio €/kg': lambda x: ("+" if x>0 else "") + formato_europeo(x, 4, " €/kg"), 'Beneficio absoluto (€)': lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €")
                    }).set_table_styles(custom_headers), use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun"
                )
                
                st.divider()
                
                selected_rows = event.selection.rows
                if selected_rows:
                    cliente_sel = df_cli.iloc[selected_rows[0]]['Cliente']
                    st.subheader(f"🔍 Análisis de Cesta: {cliente_sel}")
                    df_zoom = df_proc_kpi[df_proc_kpi['Cliente'] == cliente_sel].groupby('Familia').agg(Kilos=('Kilos', 'sum'), Precio_CP_Total=('Precio_CP_Total', 'sum')).reset_index()
                    df_zoom['Precio_CP_Cliente'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Precio_CP_Total'] / df_zoom['Kilos'], 0.0)
                    df_zoom['Precio_CP_Mercado'] = df_zoom['Familia'].map(bench_familia)
                    df_zoom['Dif_Unitaria'] = df_zoom['Precio_CP_Cliente'] - df_zoom['Precio_CP_Mercado']
                    df_zoom['Extra_Generado'] = df_zoom['Dif_Unitaria'] * df_zoom['Kilos']
                    
                    df_chart = df_zoom[['Familia', 'Precio_CP_Cliente', 'Precio_CP_Mercado']].melt(id_vars='Familia', var_name='Métrica', value_name='Precio a CP')
                    df_chart['Métrica'] = df_chart['Métrica'].replace({'Precio_CP_Cliente': 'Cliente', 'Precio_CP_Mercado': 'Media Mercado'})
                    df_chart['Precio_Disp'] = df_chart['Precio a CP'].apply(lambda x: formato_europeo(x, 4, " €/kg"))
                    
                    bar_chart = alt.Chart(df_chart).mark_bar().encode(
                        x=alt.X('Métrica:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
                        y=alt.Y('Precio a CP:Q', axis=alt.Axis(format='.2f', labelExpr="replace(datum.label, '.', ',')")),
                        color=alt.Color('Métrica:N', scale=alt.Scale(range=['#2563EB', '#94A3B8']), legend=alt.Legend(orient='top', title=None)),
                        column=alt.Column('Familia:N', header=alt.Header(title=None, labelOrient='bottom')),
                        tooltip=['Familia', 'Métrica', alt.Tooltip('Precio_Disp:N', title='Precio a CP')]
                    ).properties(width=alt.Step(50), height=250).configure_view(stroke='transparent')
                    st.altair_chart(bar_chart, use_container_width=False)
                    
                    st.markdown("##### 📦 Desglose por Familia y Artículos Principales")
                    for _, r in df_zoom.iterrows():
                        color = "green" if r['Dif_Unitaria'] >= 0 else "red"
                        icon = "🟢" if r['Dif_Unitaria'] >= 0 else "🔴"
                        kilos_fmt = formato_europeo(r['Kilos'], 0, " kg")
                        extra_fmt = ("+" if r['Extra_Generado']>0 else "") + formato_europeo(r['Extra_Generado'], 2, " €")
                        
                        with st.expander(f"{icon} {r['Familia']} | {kilos_fmt} | Beneficio absoluto: {extra_fmt}"):
                            col_m1, col_m2, col_m3 = st.columns(3)
                            col_m1.metric("Precio a CP Cliente", f"{formato_europeo(r['Precio_CP_Cliente'], 4, ' €/kg')}")
                            col_m2.metric("Precio a CP Mercado", f"{formato_europeo(r['Precio_CP_Mercado'], 4, ' €/kg')}")
                            dif_sign = "+" if r['Dif_Unitaria']>0 else ""
                            col_m3.metric("Beneficio €/kg", f"{dif_sign}{formato_europeo(r['Dif_Unitaria'], 4, ' €/kg')}")
                            
                            st.markdown(f"**Artículos principales comprados (Haz clic en una fila para ver la trazabilidad de su escandallo):**")
                            df_arts = df_proc_kpi[(df_proc_kpi['Cliente'] == cliente_sel) & (df_proc_kpi['Familia'] == r['Familia'])].copy()
                            df_arts['Ingreso_EXW'] = df_arts['Kilos'] * df_arts['Precio EXW']
                            df_arts_grouped = df_arts.groupby(['Código', 'Artículo']).agg(
                                Kilos=('Kilos', 'sum'), Ingreso_EXW=('Ingreso_EXW', 'sum'), Precio_CP_Unitario=('Precio_CP_Unitario', 'first')
                            ).reset_index()
                            df_arts_grouped['Precio EXW Medio'] = np.where(df_arts_grouped['Kilos'] > 0, df_arts_grouped['Ingreso_EXW'] / df_arts_grouped['Kilos'], 0)
                            df_arts_grouped.drop(columns=['Ingreso_EXW'], inplace=True)
                            df_arts_grouped.rename(columns={'Precio_CP_Unitario': 'Precio a CP'}, inplace=True)
                            
                            styled_arts = df_arts_grouped.style.apply(zebra_base, axis=1).format({
                                'Kilos': lambda x: formato_europeo(x, 0, " kg"), 'Precio EXW Medio': lambda x: formato_europeo(x, 3, " €"),
                                'Precio a CP': lambda x: formato_europeo(x, 4, " €/kg")
                            }).set_table_styles(custom_headers)

                            table_key = f"arts_{cliente_sel}_{r['Familia']}"
                            event_arts = st.dataframe(styled_arts, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key=table_key)
                            
                            # --- TRAZABILIDAD ---
                            if len(event_arts.selection.rows) > 0:
                                row_idx = event_arts.selection.rows[0]
                                selected_code = str(df_arts_grouped.iloc[row_idx]['Código'])
                                selected_exw = float(df_arts_grouped.iloc[row_idx]['Precio EXW Medio'])
                                selected_name = str(df_arts_grouped.iloc[row_idx]['Artículo'])
                                
                                st.markdown(f"###### 🔎 Trazabilidad del Escandallo: {selected_code} - {selected_name}")
                                
                                esc_id = None; cod_principal_teorico = None; es_equivalencia = False
                                if selected_code in mapa_escandallos:
                                    esc_id = mapa_escandallos[selected_code]
                                    cod_principal_teorico = selected_code
                                elif selected_code in mapa_equivalencias:
                                    esc_id = mapa_equivalencias[selected_code][0]
                                    cod_principal_teorico = mapa_equivalencias[selected_code][1]
                                    es_equivalencia = True
                                
                                if esc_id is not None and cod_principal_teorico is not None:
                                    df_bloque_esc = st.session_state.df_global_base[st.session_state.df_global_base['Escandallo'] == esc_id]
                                    
                                    breakdown_data = []
                                    for _, item in df_bloque_esc.iterrows():
                                        cod_item = str(item.get('Código', '')).strip()
                                        pct_item = float(item.get('%_Calculado', 0.0))
                                        coste_cong = float(item.get('Coste_congelación', 0.0))
                                        coste_desp = float(item.get('Coste_despiece', 0.0))
                                        
                                        if cod_item == cod_principal_teorico:
                                            precio_aplicado = selected_exw; disp_cod = selected_code
                                            origen = "📍 Venta principal (Equivalencia)" if es_equivalencia else "📍 Venta principal (Esta factura)"
                                            disp_name = f"{selected_name} (Equivalencia)" if es_equivalencia else item.get('Nombre', '')
                                        else:
                                            disp_cod = cod_item; disp_name = item.get('Nombre', '')
                                            if cod_item in client_avg_active.get(cliente_sel, {}):
                                                precio_aplicado = client_avg_active[cliente_sel][cod_item]; origen = "🥇 Venta a este cliente (P1)"
                                            elif cod_item in global_avg_active:
                                                precio_aplicado = global_avg_active[cod_item]; origen = "🥈 Media del mercado (P2)"
                                            else:
                                                precio_aplicado = float(item.get('Precio EXW', 0.0)); origen = "🥉 Precio teórico (P3)"
                                        
                                        linea_cp = (precio_aplicado - coste_cong - coste_desp) * pct_item
                                        breakdown_data.append({
                                            'Código': disp_cod, 'Artículo': disp_name, '% Rendimiento': pct_item * 100, 
                                            'Origen del Precio': origen, 'Precio Aplicado': precio_aplicado,
                                            'Coste Despiece': coste_desp, 'Coste Cong.': coste_cong, 'Aportación a CP': linea_cp
                                        })
                                        
                                    df_breakdown = pd.DataFrame(breakdown_data).reset_index(drop=True)
                                    def style_breakdown(row):
                                        if row['Código'] == selected_code: return ['background-color: #1E3A8A; font-weight: bold; color: #FFFFFF;'] * len(row)
                                        return zebra_base(row)
                                        
                                    st.dataframe(
                                        df_breakdown.style.apply(style_breakdown, axis=1).format({
                                            '% Rendimiento': lambda x: formato_europeo(x, 2, " %"), 'Precio Aplicado': lambda x: formato_europeo(x, 3, " €"),
                                            'Coste Despiece': lambda x: formato_europeo(x, 3, " €"), 'Coste Cong.': lambda x: formato_europeo(x, 3, " €"),
                                            'Aportación a CP': lambda x: formato_europeo(x, 4, " €/kg")
                                        }).set_table_styles(custom_headers), use_container_width=True, hide_index=True
                                    )
                                else: st.info("Este artículo no está registrado como 'Principal' ni como 'Equivalencia'.")
                else: st.info("👆 Haz clic en una fila del ranking de arriba para ver el desglose detallado de ese cliente.")
                            
        st.divider()
        
        # --- HUÉRFANOS ---
        if sel_clients and agrupar_cadena: df_sobrantes = df_proc[(df_proc['Cliente'] == nombre_grupo) & (df_proc['Familia'] == 'Sin clasificar')]
        else: df_sobrantes = df_proc_global[(df_proc_global['Cliente'].isin(sel_clients if sel_clients else all_clients)) & (df_proc_global['Familia'] == 'Sin clasificar')]
        
        if not df_sobrantes.empty:
            with st.expander(f"⚠️ Artículos 'Sin clasificar' ({len(df_sobrantes)})"):
                st.warning("Artículos vendidos sueltos que no constan como 'Principales' en la matriz de escandallos ni equivalencias.")
                df_sob_disp = df_sobrantes[['Código', 'Artículo', 'Cliente', 'Kilos', 'Precio EXW']].reset_index(drop=True)
                st.dataframe(
                    df_sob_disp.style.apply(zebra_base, axis=1).format({
                        'Kilos': lambda x: formato_europeo(x, 2, " kg"), 'Precio EXW': lambda x: formato_europeo(x, 3, " €")
                    }).set_table_styles(custom_headers), use_container_width=True, hide_index=True
                )
