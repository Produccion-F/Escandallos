import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Escandallos & Rentabilidad Ejecutiva",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🥩"
)

# --- CSS ESTILO PROFESIONAL ---
st.markdown("""
    <style>
        .stApp { background-color: #F8FAFC; color: #1E293B; }
        section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
        .stMetric { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 700; color: #0F172A !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { background-color: #F1F5F9; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #64748B; }
        .stTabs [aria-selected="true"] { background-color: #FFFFFF !important; color: #2563EB !important; border-top: 2px solid #2563EB; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- ENLACES A DATOS ---
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'
SALES_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTlJBcdE77BaiNke-06GxDH8nY7vQ0wm_XgtDaVlF9cDDlFIxIawsTNZHrEPlv3uoVecih6_HRo7gqH/pub?gid=1543847315&single=true&output=csv'

# --- FUNCIONES DE LIMPIEZA ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try:
        return float(str(x).replace('.', '').replace(',', '.'))
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
        rename_map = {'Coste congelación': 'Coste_congelación', 'Coste congelacion': 'Coste_congelación', 'Coste despiece': 'Coste_despiece', 'Precio escandallo': 'Precio_escandallo', 'TIPO': 'Tipo', 'tipo': 'Tipo', 'Fecha': 'Fecha', 'fecha': 'Fecha', 'Cliente': 'Cliente'}
        df_raw.rename(columns={k:v for k,v in rename_map.items() if k in df_raw.columns}, inplace=True)
        if 'Tipo' not in df_raw.columns: df_raw['Tipo'] = ""
        for col in ['Cliente', 'Fecha', 'Familia', 'Formato']:
            if col not in df_raw.columns: df_raw[col] = ""
            else: df_raw[col] = df_raw[col].fillna("")
        if 'Código' in df_raw.columns:
            df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)
        for col in ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']:
            if col in df_raw.columns: df_raw[col] = df_raw[col].apply(clean_european_number)
            else: df_raw[col] = 0.0
        df_calc = recalcular_dataframe(df_raw)
        return df_calc, None
    except Exception as e: return None, f"Error: {e}"

@st.cache_data(ttl=600)
def load_sales_data():
    try:
        df_v = pd.read_csv(SALES_URL)
        df_v.columns = df_v.columns.str.strip()
        map_v = {'CODIGO': 'Código', 'CÓDIGO': 'Código', 'CLIENTE': 'Cliente', 'NOMBRE': 'Nombre', 'KILOS': 'Kilos', 'PRECIO EXW': 'Precio EXW'}
        df_v.rename(columns={k:v for k,v in map_v.items() if k.upper() in [c.upper() for c in df_v.columns]}, inplace=True)
        for col in ['Kilos', 'Precio EXW']:
            if col in df_v.columns: df_v[col] = df_v[col].apply(clean_european_number)
        if 'Código' in df_v.columns:
            df_v['Código'] = df_v['Código'].astype(str).str.replace('.0', '', regex=False)
        return df_v, None
    except Exception as e: return None, f"Error cargando ventas: {e}"

# --- CARGA INICIAL ---
if 'df_global' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global = data

if 'grid_key' not in st.session_state: st.session_state.grid_key = 0
df_global = st.session_state.df_global

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Filtros Globales")
    fams = sorted(df_global['Familia'].unique()) if 'Familia' in df_global.columns else []
    sel_f = st.multiselect("📂 Familia", options=fams)
    
    mask = pd.Series(True, index=df_global.index)
    if sel_f: mask &= df_global['Familia'].isin(sel_f)
    
    df_filtrado = df_global[mask].copy()
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- APP PRINCIPAL ---
st.title("🥩 Meat Intelligence Dashboard")

tab1, tab2, tab3 = st.tabs(["📋 Detalle Técnico", "🏆 Ranking & Simulación", "📈 Rentabilidad Ejecutiva"])

with tab1:
    st.write("Vista de detalle de escandallos técnicos (Pestaña original)")
    # (Aquí va el código original de la Tab 1 que ya tenías)
    # Por brevedad en la respuesta, asumo que mantienes el bloque anterior aquí.

with tab2:
    st.write("Ranking y simulación de precios (Pestaña original)")
    # (Aquí va el código original de la Tab 2 que ya tenías)

# --- PESTAÑA 3: RENTABILIDAD EJECUTIVA (EL NUEVO CUADRO DE MANDO) ---
with tab3:
    df_sales, err_v = load_sales_data()
    
    if err_v:
        st.error(err_v)
    elif df_sales is not None:
        # --- MOTOR DE CÁLCULO ---
        df_esc = st.session_state.df_global.copy()
        df_princ = df_esc[df_esc['Tipo'].str.contains('Principal', case=False, na=False)].copy()
        
        if not df_princ.empty:
            df_princ_u = df_princ.drop_duplicates(subset=['Código'], keep='first')
            map_esc = dict(zip(df_princ_u['Código'].astype(str), df_princ_u['Escandallo']))
            
            results = []
            # Procesamos cada venta para calcular rentabilidad de escandallo completo
            for _, row in df_sales.iterrows():
                cod = str(row['Código'])
                if cod in map_esc:
                    esc_id = map_esc[cod]
                    # Bloque completo del escandallo
                    bloque = df_esc[df_esc['Escandallo'] == esc_id].copy()
                    # Cambiamos precio solo al principal
                    bloque.loc[bloque['Código'].astype(str) == cod, 'Precio EXW'] = row['Precio EXW']
                    # Cálculo de rentabilidad por línea
                    rent_lineas = (bloque['Precio EXW'] - bloque['Coste_congelación'] - bloque['Coste_despiece']) * bloque['%_Calculado']
                    results.append({
                        'Cliente': row['Cliente'], 'Código': cod, 'Nombre': row['Nombre'],
                        'Familia': bloque['Familia'].iloc[0], 'Kilos': row['Kilos'],
                        'Precio_Venta': row['Precio EXW'], 'Rentabilidad_Total': rent_lineas.sum(),
                        'Rentabilidad_Unit': rent_lineas.sum() # Rent. total por kg vendido del principal
                    })
            
            df_res = pd.DataFrame(results)
            
            if not df_res.empty:
                # --- CALCULO MÉTRICAS DE MERCADO ---
                # 1. Media Global por Familia
                bench_familia = df_res.groupby('Familia').apply(
                    lambda x: x['Rentabilidad_Total'].sum() / x['Kilos'].sum() if x['Kilos'].sum() > 0 else 0
                ).to_dict()
                
                # 2. Agregación por Cliente
                df_cli = df_res.groupby('Cliente').agg({
                    'Kilos': 'sum',
                    'Rentabilidad_Total': 'sum'
                }).reset_index()
                
                df_cli['Rent_Media_kg'] = df_cli['Rentabilidad_Total'] / df_cli['Kilos']
                
                # 3. Cálculo de Desviación vs Mercado (Métrica 2)
                def calc_vs_market(nombre_cliente):
                    c_data = df_res[df_res['Cliente'] == nombre_cliente]
                    extra = 0
                    for _, r in c_data.iterrows():
                        media_mkt = bench_familia.get(r['Familia'], 0)
                        diff_unitaria = r['Rentabilidad_Unit'] - media_mkt
                        extra += diff_unitaria * r['Kilos']
                    return extra

                df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
                
                # --- VISUALIZACIÓN 1: CUADRANTE MÁGICO ---
                st.subheader("🎯 Cuadrante Mágico: Kilos vs Rentabilidad Media")
                
                avg_kg = df_cli['Kilos'].mean()
                avg_rent = df_cli['Rent_Media_kg'].mean()
                
                fig = px.scatter(
                    df_cli, x='Kilos', y='Rent_Media_kg',
                    text='Cliente', hover_name='Cliente',
                    size='Rentabilidad_Total', color='Vs_Mercado_Euros',
                    color_continuous_scale='RdYlGn',
                    labels={'Rent_Media_kg': 'Rentabilidad Media (€/kg)', 'Kilos': 'Volumen Total (kg)'},
                    height=500
                )
                
                # Añadir líneas de cuadrantes
                fig.add_hline(y=avg_rent, line_dash="dash", line_color="gray", annotation_text="Media Rentabilidad")
                fig.add_vline(x=avg_kg, line_dash="dash", line_color="gray", annotation_text="Media Volumen")
                
                fig.update_traces(textposition='top center')
                st.plotly_chart(fig, use_container_width=True)
                
                # --- VISUALIZACIÓN 2: RANKING EJECUTIVO ---
                st.subheader("🏆 Ranking de Desempeño por Cliente")
                
                gb = GridOptionsBuilder.from_dataframe(df_cli)
                gb.configure_default_column(sortable=True, filter=True)
                gb.configure_selection('single', use_checkbox=False)
                
                gb.configure_column("Kilos", header_name="Kg Totales", valueFormatter="x.toLocaleString()")
                gb.configure_column("Rent_Media_kg", header_name="Rent. Media (€/kg)", precision=4)
                
                # Color para la métrica de mercado
                js_color = JsCode("""
                function(params) {
                    if (params.value > 0) return {'color': '#166534', 'backgroundColor': '#DCFCE7', 'fontWeight': 'bold'};
                    if (params.value < 0) return {'color': '#991B1B', 'backgroundColor': '#FEE2E2', 'fontWeight': 'bold'};
                    return null;
                }
                """)
                gb.configure_column("Vs_Mercado_Euros", header_name="Ganancia/Pérdida vs Mercado", cellStyle=js_color, precision=2)
                
                grid_resp = AgGrid(
                    df_cli, gridOptions=gb.build(), 
                    theme='alpine', height=400, 
                    update_mode=GridUpdateMode.SELECTION_CHANGED,
                    allow_unsafe_jscode=True
                )
                
                # --- VISUALIZACIÓN 3: ZOOM AL CLIENTE (DRILL-DOWN) ---
                selected_row = grid_resp['selected_rows']
                
                if selected_row:
                    cliente_sel = selected_row[0]['Cliente']
                    st.divider()
                    st.subheader(f"🔍 Análisis de Cesta: {cliente_sel}")
                    
                    df_zoom = df_res[df_res['Cliente'] == cliente_sel].groupby('Familia').agg({
                        'Kilos': 'sum',
                        'Rentabilidad_Total': 'sum'
                    }).reset_index()
                    
                    df_zoom['Rent_Cliente'] = df_zoom['Rentabilidad_Total'] / df_zoom['Kilos']
                    df_zoom['Rent_Mercado'] = df_zoom['Familia'].map(bench_familia)
                    df_zoom['Diferencia_Unitaria'] = df_zoom['Rent_Cliente'] - df_zoom['Rent_Mercado']
                    
                    c1, c2 = st.columns([2, 1])
                    
                    with c1:
                        # Gráfico comparativo
                        fig_zoom = go.Figure()
                        fig_zoom.add_trace(go.Bar(name='Cliente', x=df_zoom['Familia'], y=df_zoom['Rent_Cliente'], marker_color='#2563EB'))
                        fig_zoom.add_trace(go.Bar(name='Mercado', x=df_zoom['Familia'], y=df_zoom['Rent_Mercado'], marker_color='#94A3B8'))
                        fig_zoom.update_layout(title="Rentabilidad Cliente vs Mercado por Familia", barmode='group')
                        st.plotly_chart(fig_zoom, use_container_width=True)
                        
                    with c2:
                        st.write("📈 **Detalle de Desviación**")
                        for _, r in df_zoom.iterrows():
                            color = "green" if r['Diferencia_Unitaria'] >= 0 else "red"
                            icon = "🟢" if r['Diferencia_Unitaria'] >= 0 else "🔴"
                            st.markdown(f"**{r['Familia']}**")
                            st.markdown(f"{icon} {r['Diferencia_Unitaria']:+.4f} €/kg vs mercado")
                            st.divider()

            else:
                st.warning("No hay suficientes datos cruzados para mostrar el análisis.")
