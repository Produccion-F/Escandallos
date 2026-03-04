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
            
            def style_rows(row):
                tipo_val = row.get('Tipo', '')
                if tipo_val == 'TotalRow': return ['background-color: #DCFCE7; font-weight: bold; color: #166534'] * len(row)
                if isinstance(tipo_val, str) and 'principal' in tipo_val.lower(): return ['background-color: #EFF6FF; color: #1E40AF'] * len(row)
                return [''] * len(row)

            styled_df = df_fin.style.apply(style_rows, axis=1).format({
                '%_Calculado': "{:.2f} %",
                'Precio EXW': "{:.3f} €",
                'Precio_escandallo_Calculado': "{:.4f} €"
            })

            st.dataframe(styled_df, column_config={"Tipo": None}, use_container_width=True, hide_index=True)
            st.divider()

    # --- PESTAÑA 2: RANKING ---
    with tab2:
        st.info("💡 Haz doble clic en la columna **Precio EXW** para editar. El recálculo es automático.")

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

        edited_df = st.data_editor(
            df_ed,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", disabled=True),
                "Estado": st.column_config.TextColumn("Estado", disabled=True),
                "Precio EXW": st.column_config.NumberColumn("Precio EXW (Editable)", format="%.3f €", required=True),
                "%/CP": st.column_config.NumberColumn("%/CP", format="%.2f %%", disabled=True),
                "Precio_escandallo_Calculado": st.column_config.NumberColumn("Rentabilidad", format="%.4f €", disabled=True),
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

    # --- PESTAÑA 3: PANEL EJECUTIVO ---
    with tab3:
        st.info("💡 **Panel Ejecutivo:** Analiza la rentabilidad real de la 'cesta de compra' de cada cliente. Haz clic en una fila para ver su desglose.")
        
        df_ventas, err_v = load_sales_data()
        
        if err_v:
            st.error(err_v)
        elif df_ventas is not None and not df_ventas.empty:
            # 1. ELIMINAR CLIENTE ESPECÍFICO
            df_ventas = df_ventas[~df_ventas['Cliente'].str.contains('Entradas a Congelar', case=False, na=False)]
            
            df_esc_completo = st.session_state.df_global.copy()
            
            if 'Código' not in df_ventas.columns:
                st.error("🚨 El fichero de ventas no tiene la columna 'Código'.")
            else:
                df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)] if 'Tipo' in df_esc_completo.columns else pd.DataFrame()
                    
                if not df_princ.empty:
                    df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                    mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                    
                    ventas_procesadas = []
                    
                    for idx, row in df_ventas.iterrows():
                        cod_vendido = str(row.get('Código', '')).strip()
                        precio_cliente = float(row.get('Precio EXW', 0.0) or 0.0)
                        kilos_cliente = float(row.get('Kilos', 0.0) or 0.0)
                        nombre_cliente = str(row.get('Cliente', 'Desconocido'))
                        nombre_articulo = str(row.get('Nombre', ''))
                        
                        rent_unit = 0.0
                        familia_esc = "Sin clasificar"
                        
                        if cod_vendido in mapa_escandallos:
                            esc_id = mapa_escandallos[cod_vendido]
                            df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id].copy()
                            df_bloque_esc.loc[df_bloque_esc['Código'].astype(str) == cod_vendido, 'Precio EXW'] = precio_cliente
                            
                            rentabilidad_lineas = (df_bloque_esc.get('Precio EXW',0) - df_bloque_esc.get('Coste_congelación',0) - df_bloque_esc.get('Coste_despiece',0)) * df_bloque_esc.get('%_Calculado',0)
                            rent_unit = rentabilidad_lineas.sum()
                            fam_temp = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else ""
                            if pd.notna(fam_temp) and str(fam_temp).strip() != "": familia_esc = fam_temp
                        
                        ventas_procesadas.append({
                            'Cliente': nombre_cliente, 'Código': cod_vendido, 'Artículo': nombre_articulo,
                            'Familia': familia_esc, 'Kilos': kilos_cliente,
                            'Rentabilidad_Unit_kg': rent_unit, 'Rentabilidad_Total': rent_unit * kilos_cliente
                        })
                    
                    df_proc = pd.DataFrame(ventas_procesadas)
                    
                    bench_familia = {}
                    for fam in df_proc['Familia'].unique():
                        df_f = df_proc[df_proc['Familia'] == fam]
                        tk, tr = df_f['Kilos'].sum(), df_f['Rentabilidad_Total'].sum()
                        bench_familia[fam] = tr / tk if tk > 0 else 0.0
                        
                    df_cli = df_proc.groupby('Cliente').agg(
                        Kilos_Totales=('Kilos', 'sum'), Rent_Total=('Rentabilidad_Total', 'sum')
                    ).reset_index()
                    df_cli['Rent_Media_kg'] = np.where(df_cli['Kilos_Totales'] > 0, df_cli['Rent_Total'] / df_cli['Kilos_Totales'], 0.0)
                    
                    def calc_vs_market(cliente):
                        df_c = df_proc[df_proc['Cliente'] == cliente]
                        extra = 0.0
                        for _, r in df_c.iterrows():
                            if r['Kilos'] > 0:
                                extra += (r['Rentabilidad_Unit_kg'] - bench_familia.get(r['Familia'], 0.0)) * r['Kilos']
                        return extra
                        
                    df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
                    
                    # --- 2. GRÁFICO CON ALTAIR (Con tooltips y estable) ---
                    st.subheader("🎯 Cuadrante Mágico: Kilos vs Rentabilidad Media")
                    
                    avg_k = df_cli['Kilos_Totales'].mean()
                    avg_r = df_cli['Rent_Media_kg'].mean()
                    
                    base = alt.Chart(df_cli).mark_circle().encode(
                        x=alt.X('Kilos_Totales:Q', title='Volumen Total (kg)'),
                        y=alt.Y('Rent_Media_kg:Q', title='Rentabilidad Media (€/kg)', scale=alt.Scale(zero=False)),
                        size=alt.Size('Rent_Total:Q', legend=None),
                        color=alt.Color('Vs_Mercado_Euros:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Vs Mercado (€)'),
                        tooltip=[
                            alt.Tooltip('Cliente:N', title='Cliente'),
                            alt.Tooltip('Kilos_Totales:Q', format=',.0f', title='Volumen (kg)'),
                            alt.Tooltip('Rent_Media_kg:Q', format='.3f', title='Rentabilidad (€/kg)'),
                            alt.Tooltip('Vs_Mercado_Euros:Q', format='+.2f', title='Valor extra generado (€)')
                        ]
                    )
                    
                    rule_x = alt.Chart(pd.DataFrame({'x': [avg_k]})).mark_rule(color='gray', strokeDash=[5,5]).encode(x='x:Q')
                    rule_y = alt.Chart(pd.DataFrame({'y': [avg_r]})).mark_rule(color='gray', strokeDash=[5,5]).encode(y='y:Q')
                    
                    st.altair_chart(base + rule_x + rule_y, use_container_width=True)
                    
                    # --- 3. RANKING NATIVO CLICKABLE (DRILL-DOWN) ---
                    st.subheader("🏆 Ranking Ejecutivo")
                    
                    def color_vs_market(val):
                        if val > 0: return 'background-color: #DCFCE7; color: #166534; font-weight: bold;'
                        if val < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold;'
                        return ''
                    
                    try:
                        styled_df = df_cli.style.map(color_vs_market, subset=['Vs_Mercado_Euros'])
                    except AttributeError:
                        styled_df = df_cli.style.applymap(color_vs_market, subset=['Vs_Mercado_Euros'])
                    
                    # Añadimos el on_select para que sea clicable como AgGrid
                    event = st.dataframe(
                        styled_df.format({
                            'Kilos_Totales': "{:,.0f} kg",
                            'Rent_Total': "{:,.2f} €",
                            'Rent_Media_kg': "{:.4f} €/kg",
                            'Vs_Mercado_Euros': "{:+.2f} €"
                        }),
                        use_container_width=True, hide_index=True,
                        selection_mode="single-row", on_select="rerun"
                    )
                    
                    # --- ZOOM AL CLIENTE (Basado en la fila pinchada) ---
                    st.divider()
                    
                    # Comprobamos si el usuario ha pinchado alguna fila
                    selected_rows = event.selection.rows
                    if selected_rows:
                        # Extraemos el nombre del cliente de la fila seleccionada
                        cliente_sel = df_cli.iloc[selected_rows[0]]['Cliente']
                        
                        st.subheader(f"🔍 Análisis de Cesta: {cliente_sel}")
                        
                        df_zoom = df_proc[df_proc['Cliente'] == cliente_sel].groupby('Familia').agg(
                            Kilos=('Kilos', 'sum'), Rent_Total=('Rentabilidad_Total', 'sum')
                        ).reset_index()
                        
                        df_zoom['Rent_Cliente'] = np.where(df_zoom['Kilos'] > 0, df_zoom['Rent_Total'] / df_zoom['Kilos'], 0.0)
                        df_zoom['Rent_Mercado'] = df_zoom['Familia'].map(bench_familia)
                        df_zoom['Dif_Unitaria'] = df_zoom['Rent_Cliente'] - df_zoom['Rent_Mercado']
                        df_zoom['Extra_Generado'] = df_zoom['Dif_Unitaria'] * df_zoom['Kilos']
                        
                        c1, c2 = st.columns([2, 1.5])
                        with c1:
                            df_bar = df_zoom[['Familia', 'Rent_Cliente', 'Rent_Mercado']].set_index('Familia')
                            st.bar_chart(df_bar, height=350)
                            
                        with c2:
                            st.markdown("##### ⚖️ Impacto vs Mercado")
                            for _, r in df_zoom.iterrows():
                                color = "green" if r['Dif_Unitaria'] >= 0 else "red"
                                icon = "🟢" if r['Dif_Unitaria'] >= 0 else "🔴"
                                st.markdown(f"**{r['Familia']}** ({r['Kilos']:,.0f} kg)")
                                st.markdown(f"{icon} Diferencia: **{r['Dif_Unitaria']:+.4f} €/kg**")
                                st.markdown(f"↳ Impacto total: <span style='color:{color}; font-weight:bold'>{r['Extra_Generado']:+.2f} €</span>", unsafe_allow_html=True)
                                st.write("---")
                    else:
                        st.info("👆 Haz clic en una fila del ranking de arriba para ver en qué familias gana o pierde valor ese cliente.")
                                
                    # HUÉRFANOS
                    df_sobrantes = df_proc[df_proc['Familia'] == 'Sin clasificar']
                    if not df_sobrantes.empty:
                        st.divider()
                        with st.expander(f"⚠️ Artículos 'Sin clasificar' ({len(df_sobrantes)})"):
                            st.dataframe(df_sobrantes[['Código', 'Artículo', 'Cliente', 'Kilos']], use_container_width=True)
