import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Simulador Pro", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; }
        .stTabs [aria-selected="true"] { background-color: #ffffff; border-top: 3px solid #ff4b4b; }
        .block-container { padding-top: 1rem; }
        h1 { font-size: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- ENLACE ---
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'

# --- FUNCIONES ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError:
        return 0.0

def recalcular_dataframe(df):
    df['Total_Kg_Grupo'] = df.groupby('Escandallo')['Cantidad(kg)'].transform('sum')
    df['%_Calculado'] = np.where(df['Total_Kg_Grupo'] > 0, df['Cantidad(kg)'] / df['Total_Kg_Grupo'], 0.0)
    df['Precio_escandallo_Calculado'] = (df['Precio EXW'] - df['Coste_congelación'] - df['Coste_despiece']) * df['%_Calculado']
    return df

def load_initial_data():
    try:
        # Leemos todo el CSV
        df_raw = pd.read_csv(SHEET_URL)

        # --- EXTRACCIÓN FECHA ACTUALIZACIÓN (CELDA S2) ---
        # En pandas, S2 sería la columna index 18 (S es la 19ª letra) y fila index 0 (fila 2 de excel)
        # Intentamos leerla de forma segura
        last_update = "N/D"
        try:
            # Verificamos si tenemos suficientes columnas
            if df_raw.shape[1] >= 19:
                # iloc[0] es la primera fila de datos (fila 2 excel)
                # iloc[:, 18] es la columna 19 (S)
                val = df_raw.iloc[0, 18]
                if pd.notna(val):
                    last_update = str(val)
        except:
            pass

    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}"); st.stop()

    df_raw.columns = df_raw.columns.str.strip()
    rename_map = {'Coste congelación': 'Coste_congelación', 'Coste despiece': 'Coste_despiece', 'Precio escandallo': 'Precio_escandallo'}
    df_raw.rename(columns=rename_map, inplace=True)

    # Guardamos la fecha de actualización en el dataframe como metadato (en una columna temporal o atributo)
    df_raw._metadata = {'last_update': last_update}

    if 'Cliente' not in df_raw.columns: df_raw['Cliente'] = ""
    else: df_raw['Cliente'] = df_raw['Cliente'].fillna("")
    if 'Fecha' not in df_raw.columns: df_raw['Fecha'] = ""
    if 'Código' in df_raw.columns:
        df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)

    cols_to_clean = ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']
    for col in cols_to_clean:
        if col in df_raw.columns: df_raw[col] = df_raw[col].apply(clean_european_number)

    if 'Coste_congelación' in df_raw.columns: df_raw['Coste_congelación'] = df_raw['Coste_congelación'].fillna(0)
    if 'Coste_despiece' in df_raw.columns: df_raw['Coste_despiece'] = df_raw['Coste_despiece'].fillna(0)
    if 'Familia' in df_raw.columns: df_raw['Familia'] = df_raw['Familia'].fillna("Sin Familia")
    if 'Formato' in df_raw.columns: df_raw['Formato'] = df_raw['Formato'].fillna("Sin Formato")

    if 'Fecha' in df_raw.columns:
        df_raw['Fecha_dt'] = pd.to_datetime(df_raw['Fecha'], dayfirst=True, errors='coerce')
        df_raw['Max_Fecha'] = df_raw.groupby('Escandallo')['Fecha_dt'].transform('max')
        df_raw = df_raw[ (df_raw['Fecha_dt'] == df_raw['Max_Fecha']) | (df_raw['Fecha_dt'].isna()) ].copy()
        df_raw.drop(columns=['Fecha_dt', 'Max_Fecha'], inplace=True)

    return recalcular_dataframe(df_raw), last_update

if 'df_global' not in st.session_state:
    df_data, last_upd = load_initial_data()
    st.session_state.df_global = df_data
    st.session_state.last_update = last_upd

df = st.session_state.df_global
last_update_txt = st.session_state.last_update

# --- ETIQUETAS ---
if 'Tipo' in df.columns:
    df_principales = df[df['Tipo'].str.contains('Principal', case=False, na=False)][['Escandallo', 'Código', 'Nombre']]
else:
    df_principales = df.groupby('Escandallo')[['Código', 'Nombre']].first().reset_index()

df_principales = df_principales.drop_duplicates(subset=['Escandallo'])
df_principales['Texto_Escandallo'] = (
    df_principales['Escandallo'].astype(str) + " | " +
    df_principales['Código'].astype(str) + " | " +
    df_principales['Nombre']
)
mapa_etiquetas = dict(zip(df_principales['Escandallo'], df_principales['Texto_Escandallo']))
df['Filtro_Display'] = df['Escandallo'].map(mapa_etiquetas)


# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Filtros Globales")
    opciones_familia = sorted(df['Familia'].unique()) if 'Familia' in df.columns else []
    sel_familia = st.multiselect("📂 Familia", options=opciones_familia)
    opciones_formato = sorted(df['Formato'].unique()) if 'Formato' in df.columns else []
    sel_formato = st.multiselect("📦 Formato", options=opciones_formato)

    df_temp = df.copy()
    if sel_familia: df_temp = df_temp[df_temp['Familia'].isin(sel_familia)]
    if sel_formato: df_temp = df_temp[df_temp['Formato'].isin(sel_formato)]
    opciones_escandallo = sorted(df_temp['Filtro_Display'].dropna().unique())
    sel_escandallo = st.multiselect("🏷️ Escandallo", options=opciones_escandallo)

# --- APLICAR FILTROS ---
df_filtrado = df.copy()
if sel_familia: df_filtrado = df_filtrado[df_filtrado['Familia'].isin(sel_familia)]
if sel_formato: df_filtrado = df_filtrado[df_filtrado['Formato'].isin(sel_formato)]
if sel_escandallo: df_filtrado = df_filtrado[df_filtrado['Filtro_Display'].isin(sel_escandallo)]

# --- APP ---
c_title, c_info = st.columns([3, 1])
c_title.title("📊 Dashboard de Rentabilidad")
# MOSTRAR ÚLTIMA ACTUALIZACIÓN BAJO TÍTULO
c_title.caption(f"📅 Última actualización de precios: **{last_update_txt}**")

if df_filtrado.empty:
    st.warning("⚠️ No hay datos.")
else:
    # KPIs
    df_rank_kpi = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Escandallos", f"{df_rank_kpi.count()}")
    c2.metric("Rentabilidad Media", f"{df_rank_kpi.mean():.2f} €")
    c3.metric("Rentabilidad Max", f"{df_rank_kpi.max():.2f} €")
    st.divider()

    tab1, tab2 = st.tabs(["📋 Detalle", "🏆 Ranking Comparativo"])

    # --- PESTAÑA 1: DETALLE ---
    with tab1:
        escandallos_a_mostrar = df_filtrado['Escandallo'].unique()
        for i, esc_id in enumerate(escandallos_a_mostrar):
            df_f = df_filtrado[df_filtrado['Escandallo'] == esc_id].copy()
            fecha_str = df_f['Fecha'].iloc[0] if 'Fecha' in df_f.columns else "-"
            titulo = df_f['Filtro_Display'].iloc[0] if 'Filtro_Display' in df_f.columns else f"Escandallo {esc_id}"

            st.subheader(f"🔹 {titulo} (📅 {fecha_str})")

            # Necesitamos la columna 'Tipo' para pintar de azul los principales, la añadimos aunque la ocultemos luego
            cols = ['Cliente', 'Código', 'Nombre', 'Coste_despiece', 'Coste_congelación', '%_Calculado', 'Precio EXW', 'Precio_escandallo_Calculado', 'Tipo']
            df_v = df_f[[c for c in cols if c in df_f.columns]].copy()

            if '%_Calculado' in df_v.columns: df_v['%_Calculado'] = df_v['%_Calculado'] * 100

            ft = {c: None for c in df_v.columns}; ft['Nombre'] = 'TOTAL'; ft['Tipo'] = 'TotalRow' # Marca especial para fila total
            if '%_Calculado' in df_v: ft['%_Calculado'] = df_v['%_Calculado'].sum()
            if 'Precio_escandallo_Calculado' in df_v: ft['Precio_escandallo_Calculado'] = df_v['Precio_escandallo_Calculado'].sum()

            df_fin = pd.concat([df_v, pd.DataFrame([ft])], ignore_index=True)

            # --- AG-GRID DETALLE ---
            gb = GridOptionsBuilder.from_dataframe(df_fin)

            # Ocultamos columna Tipo (solo la usamos para lógica de colores)
            gb.configure_column("Tipo", hide=True)

            # Alineación izquierda forzada para todo
            gb.configure_default_column(type=["leftAligned"])

            gb.configure_column("Código", width=100)
            gb.configure_column("Nombre", width=300)
            gb.configure_column("%_Calculado", header_name="%", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' %'", precision=2, width=90)
            gb.configure_column("Precio EXW", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=3, width=110)
            gb.configure_column("Precio_escandallo_Calculado", header_name="Rentabilidad", type=["numericColumn"], valueFormatter="x.toLocaleString() + ' €'", precision=4, width=120)
            gb.configure_column("Coste_despiece", header_name="C. Desp", width=100)
            gb.configure_column("Coste_congelación", header_name="C. Cong", width=100)

            # JS para Colores:
            # 1. Fila TOTAL -> Verde
            # 2. Fila 'Principal' (según columna Tipo) -> Azul Claro
            # 3. Alineación izquierda siempre
            row_style_jscode = JsCode("""
            function(params) {
                if (params.data.Tipo === 'TotalRow') {
                    return {'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'color': 'darkgreen'};
                }
                if (params.data.Tipo && params.data.Tipo.includes('Principal')) {
                    return {'backgroundColor': '#e3f2fd', 'color': '#0d47a1'}; /* Azul claro para Principal */
                }
                return {};
            }
            """)
            gb.configure_grid_options(getRowStyle=row_style_jscode)

            gridOptions = gb.build()

            AgGrid(
                df_fin,
                gridOptions=gridOptions,
                height=300,
                fit_columns_on_grid_load=True,  # <--- ESTO AJUSTA AL ANCHO DE PANTALLA
                theme='alpine',
                allow_unsafe_jscode=True
            )

            if i < len(escandallos_a_mostrar) - 1: st.divider()

    # --- PESTAÑA 2: RANKING ---
    with tab2:
        st.info("💡 Edita la columna **AZUL** (doble clic).")

        df_rank = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()

        cols_info = ['Escandallo', 'Código', 'Nombre', '%_Calculado', 'Precio EXW', 'Cliente', 'Fecha']
        if 'Tipo' in df_filtrado.columns:
            try:
                df_pr_raw = df_filtrado[df_filtrado['Tipo'].str.contains('Principal', case=False, na=False)][cols_info]
            except:
                df_pr_raw = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()
        else:
            df_pr_raw = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()

        df_suma_pct = df_pr_raw.groupby('Escandallo')['%_Calculado'].sum().reset_index()
        df_info_first = df_pr_raw.groupby('Escandallo')[['Código', 'Nombre', 'Cliente', 'Fecha', 'Precio EXW']].first().reset_index()
        df_pr_con = pd.merge(df_info_first, df_suma_pct, on='Escandallo')

        df_final = pd.merge(df_rank, df_pr_con, on='Escandallo').sort_values('Precio_escandallo_Calculado', ascending=False)
        df_final['Pos'] = range(1, len(df_final)+1)
        df_final['%/CP'] = df_final['%_Calculado'] * 100

        if not df_final.empty:
            q33 = df_final['Precio_escandallo_Calculado'].quantile(0.33)
            q66 = df_final['Precio_escandallo_Calculado'].quantile(0.66)
            def get_semaforo_txt(valor):
                if valor >= q66: return "Alta"
                elif valor >= q33: return "Media"
                else: return "Baja"
            df_final['Estado'] = df_final['Precio_escandallo_Calculado'].apply(get_semaforo_txt)
        else:
            df_final['Estado'] = "N/D"

        cols_show = ['Pos', 'Estado', 'Cliente', 'Fecha', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
        cols_data = cols_show + ['Escandallo']
        df_ed = df_final[cols_data].copy()

        gb = GridOptionsBuilder.from_dataframe(df_ed)
        gb.configure_column("Escandallo", hide=True)
        gb.configure_column("Pos", width=60, pinned='left')

        # Alineación izquierda para todo
        gb.configure_default_column(type=["leftAligned"])

        semaforo_jscode = JsCode("""
        function(params) {
            if (params.value == 'Alta') {
                return {'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': 'bold', 'textAlign': 'center'};
            } else if (params.value == 'Media') {
                return {'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': 'bold', 'textAlign': 'center'};
            } else {
                return {'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': 'bold', 'textAlign': 'center'};
            }
        }
        """)
        gb.configure_column("Estado", cellStyle=semaforo_jscode, width=90)
        gb.configure_column("Cliente", width=120)
        gb.configure_column("Fecha", width=100)
        gb.configure_column("Nombre", width=250)

        precio_editable_jscode = JsCode("""
        function(params) {
            return {'backgroundColor': '#e3f2fd', 'color': '#0044cc', 'fontWeight': 'bold'};
        }
        """)
        gb.configure_column("Precio EXW", editable=True, cellStyle=precio_editable_jscode, type=["numericColumn"], precision=3, width=110)

        gb.configure_column("%/CP", type=["numericColumn"], precision=2, valueFormatter="x.toLocaleString() + ' %'", width=90)
        gb.configure_column("Precio_escandallo_Calculado", header_name="Rentabilidad Final", type=["numericColumn"], precision=4, valueFormatter="x.toLocaleString() + ' €'")

        gridOptions = gb.build()

        response = AgGrid(
            df_ed,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            height=500,
            theme='alpine',
            fit_columns_on_grid_load=True # <--- AJUSTE ANCHO PANTALLA
        )

        df_modificado = pd.DataFrame(response['data'])

        if not df_modificado.empty and abs(df_modificado['Precio EXW'].sum() - df_ed['Precio EXW'].sum()) > 0.0001:
             st.toast("🔄 Recalculando...", icon="🚀")
             for i, r in df_modificado.iterrows():
                esc_id_real = r['Escandallo']
                mask = (st.session_state.df_global['Escandallo'] == esc_id_real) & \
                       (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                st.session_state.df_global.loc[mask, 'Precio EXW'] = r['Precio EXW']

             st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
             st.rerun()

        if st.button("Resetear Datos Originales"):
            st.cache_data.clear()
            st.session_state.df_global, st.session_state.last_update = load_initial_data()
            st.rerun()
