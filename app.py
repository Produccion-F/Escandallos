import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def formato_europeo(val, decimales=2, sufijo=""):
    """Transforma números al formato europeo: 1.234,56"""
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

# --- MOTOR DE CASCADA DINÁMICO (CÁLCULO PURO DE ESCANDALLO) ---
def procesar_ventas_cascada(df_v, df_esc_completo, mapa_esc_principal):
    # 1. Pre-calcular Medias Ponderadas Globales (Prioridad 2)
    global_avg = {}
    for cod, grp in df_v.groupby('Código'):
        tot_k = grp['Kilos'].sum()
        if tot_k > 0:
            global_avg[str(cod)] = (grp['Kilos'] * grp['Precio EXW']).sum() / tot_k

    # 2. Pre-calcular Medias Ponderadas del Cliente (Prioridad 1)
    client_avg = {}
    for cli, grp_cli in df_v.groupby('Cliente'):
        cli_str = str(cli)
        client_avg[cli_str] = {}
        for cod, grp_cod in grp_cli.groupby('Código'):
            tot_k = grp_cod['Kilos'].sum()
            if tot_k > 0:
                client_avg[cli_str][str(cod)] = (grp_cod['Kilos'] * grp_cod['Precio EXW']).sum() / tot_k

    ventas_procesadas = []

    # 3. Iterar por cada línea de venta
    for idx, row in df_v.iterrows():
        cod_vendido = str(row.get('Código', '')).strip()
        precio_cliente = float(row.get('Precio EXW', 0.0) or 0.0)
        kilos_cliente = float(row.get('Kilos', 0.0) or 0.0)
        nombre_cliente = str(row.get('Cliente', 'Desconocido'))
        nombre_articulo = str(row.get('Nombre', ''))

        # Si el artículo es un "Principal", calculamos su escandallo completo
        if cod_vendido in mapa_esc_principal:
            esc_id = mapa_esc_principal[cod_vendido]
            df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id]
            
            fam_temp = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else "Sin clasificar"
            if pd.isna(fam_temp) or str(fam_temp).strip() == "": fam_temp = "Sin clasificar"
            
            precio_cp_unitario_escandallo = 0.0
            
            # Fórmula estricta: Suma de [% * (Precio EXW - Costes)]
            for _, item in df_bloque_esc.iterrows():
                cod_item = str(item.get('Código', '')).strip()
                pct_item = float(item.get('%_Calculado', 0.0))
                coste_cong = float(item.get('Coste_congelación', 0.0))
                coste_desp = float(item.get('Coste_despiece', 0.0))
                
                # Asignación del Precio EXW en Cascada
                if cod_item == cod_vendido:
                    # El artículo principal coge el precio real de la factura
                    precio_exw_dinamico = precio_cliente
                else:
                    # Artículos secundarios (Busca prioridad)
                    if cod_item in client_avg.get(nombre_cliente, {}):
                        precio_exw_dinamico = client_avg[nombre_cliente][cod_item] # P1: Cliente
                    elif cod_item in global_avg:
                        precio_exw_dinamico = global_avg[cod_item] # P2: Mercado global
                    else:
                        precio_exw_dinamico = float(item.get('Precio EXW', 0.0)) # P3: Teórico
                
                # Cálculo de la línea
                linea_cp = (precio_exw_dinamico - coste_cong - coste_desp) * pct_item
                precio_cp_unitario_escandallo += linea_cp

            ventas_procesadas.append({
                'Cliente': nombre_cliente,
                'Código': cod_vendido,
                'Artículo': nombre_articulo,
                'Familia': fam_temp,
                'Kilos': kilos_cliente,
                'Precio EXW': precio_cliente,
                'Precio_CP_Unitario': precio_cp_unitario_escandallo,
                'Precio_CP_Total': precio_cp_unitario_escandallo * kilos_cliente
            })
            
        else:
            # Es un artículo secundario vendido suelto (No es principal de ningún escandallo)
            ventas_procesadas.append({
                'Cliente': nombre_cliente,
                'Código': cod_vendido,
                'Artículo': nombre_articulo,
                'Familia': 'Sin clasificar',
                'Kilos': kilos_cliente,
                'Precio EXW': precio_cliente,
                'Precio_CP_Unitario': 0.0, # De momento no calcula CP hasta la próxima fase
                'Precio_CP_Total': 0.0
            })

    return pd.DataFrame(ventas_procesadas)

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

# --- PRE-PROCESAMIENTO DE VENTAS GLOBAL ---
df_ventas, err_v = load_sales_data()
df_proc_global = pd.DataFrame()
bench_familia = {}
mapa_escandallos = {}

if not err_v and df_ventas is not None and not df_ventas.empty:
    df_ventas = df_ventas[~df_ventas['Cliente'].str.contains('Entradas a Congelar', case=False, na=False)]
    df_esc_completo = st.session_state.df_global.copy()
    
    if 'Código' in df_ventas.columns:
        df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)] if 'Tipo' in df_esc_completo.columns else pd.DataFrame()
        if not df_princ.empty:
            df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
            mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
            
            # Ejecutamos el Motor Cascada globalmente
            df_proc_global = procesar_ventas_cascada(df_ventas, df_esc_completo, mapa_escandallos)
            
            if not df_proc_global.empty:
                for fam in df_proc_global['Familia'].unique():
                    if fam != 'Sin clasificar':
                        df_f = df_proc_global[df_proc_global['Familia'] == fam]
                        tk, tr = df_f['Kilos'].sum(), df_f['Precio_CP_Total'].sum()
                        bench_familia[fam] = tr / tk if tk > 0 else 0.0

# --- ETIQUETAS FILTROS GLOBALES ---
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
        k2.metric("Media a CP", f"{formato_europeo(kpi_data.mean(), 2, ' €')}")
        k3.metric("Max a CP", f"{formato_europeo(kpi_data.max(), 2, ' €')}")
        k4.metric("Min a CP", f"{formato_europeo(kpi_data.min(), 2, ' €')}")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico", "🏆 Ranking & Simulación", "📈 Panel Ejecutivo (Clientes)"])

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
            df_fin.rename(columns={'Precio_escandallo_Calculado': 'Precio a CP'}, inplace=True)
            
            def style_rows(row):
                tipo_val = row.get('Tipo', '')
                if tipo_val == 'TotalRow': return ['background-color: #DCFCE7; font-weight: bold; color: #166534'] * len(row)
                if isinstance(tipo_val, str) and 'principal' in tipo_val.lower(): return ['background-color: #EFF6FF; color: #1E40AF'] * len(row)
                return [''] * len(row)

            styled_df = df_fin.style.apply(style_rows, axis=1).format({
                '%_Calculado': lambda x: formato_europeo(x, 2, " %"),
                'Precio EXW': lambda x: formato_europeo(x, 3, " €"),
                'Precio a CP': lambda x: formato_europeo(x, 4, " €")
            })

            st.dataframe(styled_df, column_config={"Tipo": None}, use_container_width=True, hide_index=True)
            st.divider()

    # --- PESTAÑA 2: RANKING Y SIMULACIÓN ---
    with tab2:
        st.subheader("🏆 Ranking & Simulación")
        st.info("💡 Haz doble clic en la columna **Precio EXW ✏️** para editar. El recálculo es automático.")

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
            def get_sem(v): return "🟢 Alta" if v >= q66 else ("🟡 Media" if v >= q33 else "🔴 Baja")
            df_final['Estado'] = df_final['Precio_escandallo_Calculado'].apply(get_sem)
        else:
            df_final['Estado'] = "N/D"

        cols_vis = ['Pos', 'Estado', 'Cliente', 'Fecha', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
        cols_final = [c for c in cols_vis if c in df_final.columns] + ['Escandallo']
        df_ed = df_final[cols_final].copy()
        
        df_ed_display = df_ed.copy()
        df_ed_display['%/CP'] = df_ed['%/CP'].apply(lambda x: formato_europeo(x, 2, " %"))
        df_ed_display['Precio_escandallo_Calculado'] = df_ed['Precio_escandallo_Calculado'].apply(lambda x: formato_europeo(x, 4, " €"))

        try:
            styled_ed_display = df_ed_display.style.map(lambda _: 'background-color: #EFF6FF; color: #1D4ED8; font-weight: bold;', subset=['Precio EXW'])
        except AttributeError:
            styled_ed_display = df_ed_display.style.applymap(lambda _: 'background-color: #EFF6FF; color: #1D4ED8; font-weight: bold;', subset=['Precio EXW'])

        edited_df = st.data_editor(
            styled_ed_display,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", disabled=True),
                "Estado": st.column_config.TextColumn("Estado", disabled=True),
                "Precio EXW": st.column_config.NumberColumn("Precio EXW ✏️", required=True),
                "%/CP": st.column_config.TextColumn("%/CP", disabled=True),
                "Precio_escandallo_Calculado": st.column_config.TextColumn("Precio a CP", disabled=True),
                "Escandallo": None
            },
            disabled=["Pos", "Estado", "Cliente", "Fecha", "Código", "Nombre", "%/CP", "Precio_escandallo_Calculado", "Escandallo"],
            hide_index=True, use_container_width=True, key=f"editor_nativo_{st.session_state.grid_key}"
        )

        diferencias = edited_df['Precio EXW'] - df_ed['Precio EXW']
        if diferencias.abs().sum() > 0.0001:
             st.toast("⚡ Guardando cambios...", icon="📊")
             cambios = edited_df[diferencias.abs() > 0.0001]
             for i, r in cambios.iterrows():
                mask = (st.session_state.df_global['Escandallo'] == r['Escandallo']) & (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                st.session_state.df_global.loc[mask, 'Precio EXW'] = float(r['Precio EXW'])
             st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
             st.session_state.grid_key += 1 
             st.rerun()
             
        st.divider()
        st.subheader("📋 Escandallos reales por clientes (Métricas de Cascada)")
        st.write("Datos cruzados aplicando la fórmula directa del escandallo con los precios de venta dinámicos.")
        
        if not df_proc_global.empty:
            df_proc_filtrado = df_proc_global[df_proc_global['Familia'] != 'Sin clasificar'].copy()
            
            mask_proc = pd.Series(True, index=df_proc_filtrado.index)
            if sel_familia: mask_proc &= df_proc_filtrado['Familia'].isin(sel_familia)
            if sel_formato or sel_escandallo:
                codigos_filtrados = df_filtrado['Código'].astype(str).unique()
                mask_proc &= df_proc_filtrado['Código'].astype(str).isin(codigos_filtrados)
                
            df_proc_filtrado = df_proc_filtrado[mask_proc].copy()
            
            if not df_proc_filtrado.empty:
                df_raw_disp = df_proc_filtrado[['Cliente', 'Código', 'Artículo', 'Familia', 'Kilos', 'Precio EXW', 'Precio_CP_Unitario']].copy()
                df_raw_disp.rename(columns={'Precio_CP_Unitario': 'Precio a CP'}, inplace=True)
                
                def color_cp_manual(val):
                    if not isinstance(val, (int, float)): return ''
                    if val <= 0: return 'background-color: #FEE2E2; color: #991B1B;'
                    elif val >= 1.5: return 'background-color: #DCFCE7; color: #166534;'
                    return ''

                try:
                    styled_raw = df_raw_disp.style.map(color_cp_manual, subset=['Precio a CP'])
                except AttributeError:
                    styled_raw = df_raw_disp.style.applymap(color_cp_manual, subset=['Precio a CP'])

                styled_raw = styled_raw.format({
                    'Kilos': lambda x: formato_europeo(x, 2, " kg"),
                    'Precio EXW': lambda x: formato_europeo(x, 3, " €"),
                    'Precio a CP': lambda x: formato_europeo(x, 4, " €/kg")
                })
                
                st.dataframe(styled_raw, use_container_width=True, hide_index=True)
            else:
                st.warning("No hay datos de ventas cruzadas para los filtros seleccionados.")
        else:
            st.warning("No hay datos de ventas cruzadas para mostrar la tabla bruta.")

    # --- PESTAÑA 3: PANEL EJECUTIVO ---
    with tab3:
        st.info("💡 **Panel Ejecutivo:** Analiza el Precio a CP real de la cesta de cada cliente frente al mercado, aplicando el cálculo de escandallo con precios dinámicos.")
        
        if err_v:
            st.error(err_v)
        elif not df_proc_global.empty:
            st.markdown("#### 🎛️ Filtros de Análisis")
            col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
            
            df_proc_validos = df_proc_global[df_proc_global['Familia'] != 'Sin clasificar']
            all_clients = sorted(df_proc_validos['Cliente'].unique()) if not df_proc_validos.empty else []
            
            buscador = col_f1.text_input("🔍 Auto-seleccionar cadena (Ej: Escribe 'COVI' o 'DIA')")
            clientes_preseleccionados = [c for c in all_clients if buscador.lower() in c.lower()] if buscador else []
            
            sel_clients = col_f1.multiselect("🏢 Clientes (Selecciona uno o varios)", all_clients, default=clientes_preseleccionados)
            agrupar_cadena = col_f1.checkbox("🔗 Agrupar clientes seleccionados como una 'Cadena'", value=bool(buscador))
            
            fams_disp = sorted(df_proc_validos['Familia'].unique()) if not df_proc_validos.empty else []
            sel_fams = col_f2.multiselect("📂 Familias", fams_disp)
            
            arts_disp = sorted(df_proc_validos['Artículo'].unique()) if not df_proc_validos.empty else []
            sel_arts = col_f3.multiselect("🏷️ Artículos", arts_disp)
            
            if sel_clients and agrupar_cadena:
                nombre_grupo = "GRUPO: " + " + ".join([c[:10] for c in sel_clients[:2]]) + ("..." if len(sel_clients)>2 else "")
                df_ventas_grupo = df_ventas.copy()
                df_ventas_grupo.loc[df_ventas_grupo['Cliente'].isin(sel_clients), 'Cliente'] = nombre_grupo
                
                df_proc_full = procesar_ventas_cascada(df_ventas_grupo, st.session_state.df_global, mapa_escandallos)
                df_proc = df_proc_full[df_proc_full['Cliente'] == nombre_grupo].copy()
            else:
                df_proc = df_proc_global.copy()
                if sel_clients: df_proc = df_proc[df_proc['Cliente'].isin(sel_clients)]
            
            df_proc = df_proc[df_proc['Familia'] != 'Sin clasificar']
            
            if sel_fams: df_proc = df_proc[df_proc['Familia'].isin(sel_fams)]
            if sel_arts: df_proc = df_proc[df_proc['Artículo'].isin(sel_arts)]
                    
            if df_proc.empty:
                st.warning("No hay datos para la combinación de filtros seleccionada.")
            else:
                df_cli = df_proc.groupby('Cliente').agg(
                    Kilos_Totales=('Kilos', 'sum'),
                    Precio_CP_Total=('Precio_CP_Total', 'sum')
                ).reset_index()
                
                df_cli['Precio_Medio_CP'] = np.where(df_cli['Kilos_Totales'] > 0, df_cli['Precio_CP_Total'] / df_cli['Kilos_Totales'], 0.0)
                
                def calc_vs_market(cliente):
                    df_c = df_proc[df_proc['Cliente'] == cliente]
                    extra = 0.0
                    for _, r in df_c.iterrows():
                        if r['Kilos'] > 0:
                            extra += (r['Precio_CP_Unitario'] - bench_familia.get(r['Familia'], 0.0)) * r['Kilos']
                    return extra
                    
                df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
                
                df_cli['Kilos_Disp'] = df_cli['Kilos_Totales'].apply(lambda x: formato_europeo(x, 0, " kg"))
                df_cli['Precio_Medio_CP_Disp'] = df_cli['Precio_Medio_CP'].apply(lambda x: formato_europeo(x, 4, " €/kg"))
                df_cli['Extra_Disp'] = df_cli['Vs_Mercado_Euros'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €"))
                df_cli['Extra_kg'] = np.where(df_cli['Kilos_Totales']>0, df_cli['Vs_Mercado_Euros'] / df_cli['Kilos_Totales'], 0)
                df_cli['Extra_kg_Disp'] = df_cli['Extra_kg'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 4, " €/kg"))

                st.divider()
                st.subheader("🎯 Cuadrante Mágico: Volumen vs Precio Medio a CP")
                
                avg_k = df_cli['Kilos_Totales'].mean()
                avg_r = df_cli['Precio_Medio_CP'].mean()
                
                base = alt.Chart(df_cli).mark_circle().encode(
                    x=alt.X('Kilos_Totales:Q', 
                            title='Volumen Vendido (kg)', 
                            axis=alt.Axis(format=',.0f', labelExpr="replace(datum.label, ',', '.')")),
                    y=alt.Y('Precio_Medio_CP:Q', 
                            title='Precio Medio a CP (€/kg)', 
                            scale=alt.Scale(zero=False),
                            axis=alt.Axis(format='.2f', labelExpr="replace(datum.label, '.', ',')")),
                    size=alt.Size('Precio_CP_Total:Q', legend=None),
                    color=alt.Color('Vs_Mercado_Euros:Q', 
                                    scale=alt.Scale(scheme='redyellowgreen'), 
                                    title='Vs Mercado (€)',
                                    legend=alt.Legend(format=',.0f', labelExpr="replace(datum.label, ',', '.')")),
                    tooltip=[
                        alt.Tooltip('Cliente:N', title='Cliente'),
                        alt.Tooltip('Kilos_Disp:N', title='Volumen'),
                        alt.Tooltip('Precio_Medio_CP_Disp:N', title='Precio Medio a CP'),
                        alt.Tooltip('Extra_Disp:N', title='Extra generado'),
                        alt.Tooltip('Extra_kg_Disp:N', title='Extra por kg')
                    ]
                )
                
                rule_x = alt.Chart(pd.DataFrame({'x': [avg_k]})).mark_rule(color='gray', strokeDash=[5,5]).encode(x='x:Q')
                rule_y = alt.Chart(pd.DataFrame({'y': [avg_r]})).mark_rule(color='gray', strokeDash=[5,5]).encode(y='y:Q')
                
                st.altair_chart(base + rule_x + rule_y, use_container_width=True)
                
                st.subheader("🏆 Ranking Ejecutivo")
                
                def color_vs_market(val):
                    if val > 0: return 'background-color: #DCFCE7; color: #166534; font-weight: bold;'
                    if val < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
                    return ''
                
                df_rank_display = df_cli[['Cliente', 'Kilos_Totales', 'Precio_Medio_CP', 'Vs_Mercado_Euros']].copy()
                df_rank_display.rename(columns={'Kilos_Totales': 'Kilos'}, inplace=True)

                try:
                    styled_df = df_rank_display.style.map(color_vs_market, subset=['Vs_Mercado_Euros'])
                except AttributeError:
                    styled_df = df_rank_display.style.applymap(color_vs_market, subset=['Vs_Mercado_Euros'])
                
                event = st.dataframe(
                    styled_df.format({
                        'Kilos': lambda x: formato_europeo(x, 0, " kg"),
                        'Precio_Medio_CP': lambda x: formato_europeo(x, 4, " €/kg"),
                        'Vs_Mercado_Euros': lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €")
                    }),
                    use_container_width=True, hide_index=True,
                    selection_mode="single-row", on_select="rerun"
                )
                
                st.divider()
                
                selected_rows = event.selection.rows
                if selected_rows:
                    cliente_sel = df_cli.iloc[selected_rows[0]]['Cliente']
                    
                    st.subheader(f"🔍 Análisis de Cesta: {cliente_sel}")
                    
                    df_zoom = df_proc[df_proc['Cliente'] == cliente_sel].groupby('Familia').agg(
                        Kilos=('Kilos', 'sum'),
                        Precio_CP_Total=('Precio_CP_Total', 'sum')
                    ).reset_index()
                    
                    df_zoom['Precio_CP_Cliente'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Precio_CP_Total'] / df_zoom['Kilos'], 0.0)
                    df_zoom['Precio_CP_Mercado'] = df_zoom['Familia'].map(bench_familia)
                    df_zoom['Dif_Unitaria'] = df_zoom['Precio_CP_Cliente'] - df_zoom['Precio_CP_Mercado']
                    df_zoom['Extra_Generado'] = df_zoom['Dif_Unitaria'] * df_zoom['Kilos']
                    
                    df_chart = df_zoom[['Familia', 'Precio_CP_Cliente', 'Precio_CP_Mercado']].melt(id_vars='Familia', var_name='Métrica', value_name='Precio a CP (€/kg)')
                    df_chart['Métrica'] = df_chart['Métrica'].replace({'Precio_CP_Cliente': 'Cliente', 'Precio_CP_Mercado': 'Media Mercado'})
                    df_chart['Precio_Disp'] = df_chart['Precio a CP (€/kg)'].apply(lambda x: formato_europeo(x, 4, " €/kg"))
                    
                    bar_chart = alt.Chart(df_chart).mark_bar().encode(
                        x=alt.X('Métrica:N', title=None, axis=alt.Axis(labels=False, ticks=False)),
                        y=alt.Y('Precio a CP (€/kg):Q', 
                                axis=alt.Axis(format='.2f', labelExpr="replace(datum.label, '.', ',')")),
                        color=alt.Color('Métrica:N', scale=alt.Scale(range=['#2563EB', '#94A3B8']), legend=alt.Legend(orient='top', title=None)),
                        column=alt.Column('Familia:N', header=alt.Header(title=None, labelOrient='bottom')),
                        tooltip=['Familia', 'Métrica', alt.Tooltip('Precio_Disp:N', title='Precio a CP')]
                    ).properties(
                        width=alt.Step(50), 
                        height=250
                    ).configure_view(stroke='transparent')
                    
                    st.altair_chart(bar_chart, use_container_width=False)
                    
                    st.markdown("##### 📦 Desglose por Familia y Artículos Principales")
                    for _, r in df_zoom.iterrows():
                        color = "green" if r['Dif_Unitaria'] >= 0 else "red"
                        icon = "🟢" if r['Dif_Unitaria'] >= 0 else "🔴"
                        
                        kilos_fmt = formato_europeo(r['Kilos'], 0, " kg")
                        extra_fmt = ("+" if r['Extra_Generado']>0 else "") + formato_europeo(r['Extra_Generado'], 2, " €")
                        
                        with st.expander(f"{icon} {r['Familia']} | {kilos_fmt} | Impacto vs Mercado: {extra_fmt}"):
                            
                            col_m1, col_m2, col_m3 = st.columns(3)
                            col_m1.metric("Precio a CP Cliente", f"{formato_europeo(r['Precio_CP_Cliente'], 4, ' €/kg')}")
                            col_m2.metric("Precio a CP Mercado", f"{formato_europeo(r['Precio_CP_Mercado'], 4, ' €/kg')}")
                            
                            dif_sign = "+" if r['Dif_Unitaria']>0 else ""
                            col_m3.metric("Diferencia Unitaria", f"{dif_sign}{formato_europeo(r['Dif_Unitaria'], 4, ' €/kg')}")
                            
                            st.markdown(f"**Artículos principales comprados:**")
                            df_arts = df_proc[(df_proc['Cliente'] == cliente_sel) & (df_proc['Familia'] == r['Familia'])].copy()
                            
                            df_arts['Ingreso_EXW'] = df_arts['Kilos'] * df_arts['Precio EXW']
                            df_arts_grouped = df_arts.groupby(['Código', 'Artículo']).agg(
                                Kilos=('Kilos', 'sum'),
                                Ingreso_EXW=('Ingreso_EXW', 'sum')
                            ).reset_index()
                            
                            df_arts_grouped['Precio EXW Medio'] = np.where(df_arts_grouped['Kilos'] > 0, df_arts_grouped['Ingreso_EXW'] / df_arts_grouped['Kilos'], 0)
                            df_arts_grouped.drop(columns=['Ingreso_EXW'], inplace=True)
                            
                            st.dataframe(
                                df_arts_grouped.style.format({
                                    'Kilos': lambda x: formato_europeo(x, 0, " kg"),
                                    'Precio EXW Medio': lambda x: formato_europeo(x, 3, " €")
                                }),
                                use_container_width=True, hide_index=True
                            )
                else:
                    st.info("👆 Haz clic en una fila del ranking de arriba para ver el desglose detallado de ese cliente.")
                            
                st.divider()
                
                # --- HUÉRFANOS ---
                if sel_clients and agrupar_cadena:
                    df_sobrantes = df_proc_full[(df_proc_full['Cliente'] == nombre_grupo) & (df_proc_full['Familia'] == 'Sin clasificar')]
                else:
                    df_sobrantes = df_proc_global[(df_proc_global['Cliente'].isin(sel_clients if sel_clients else all_clients)) & (df_proc_global['Familia'] == 'Sin clasificar')]
                
                if not df_sobrantes.empty:
                    with st.expander(f"⚠️ Artículos 'Sin clasificar' ({len(df_sobrantes)})"):
                        st.warning("Artículos vendidos sueltos que no constan como 'Principales' en la matriz de escandallos.")
                        st.dataframe(
                            df_sobrantes[['Código', 'Artículo', 'Cliente', 'Kilos', 'Precio EXW']].style.format({
                                'Kilos': lambda x: formato_europeo(x, 2, " kg"),
                                'Precio EXW': lambda x: formato_europeo(x, 3, " €")
                            }),
                            use_container_width=True, hide_index=True
                        )
