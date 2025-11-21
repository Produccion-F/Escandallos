import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Simulador de Rentabilidad",
    page_icon="🥩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DISEÑO VISUAL "EJECUTIVO" (CSS AVANZADO) ---
st.markdown("""
    <style>
        /* 1. FONDO Y TIPOGRAFÍA */
        .stApp {
            background-color: #f4f6f9; /* Gris muy suave, estilo dashboard */
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        
        /* 2. BARRA LATERAL (SIDEBAR) */
        section[data-testid="stSidebar"] {
            background-color: #2c3e50; /* Azul oscuro corporativo */
            color: white;
        }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] label {
            color: #ecf0f1 !important; /* Texto blanco/gris claro */
        }
        
        /* 3. TARJETAS DE MÉTRICAS (KPIs) */
        div[data-testid="stMetric"] {
            background-color: white;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            text-align: center;
        }
        div[data-testid="stMetricLabel"] {
            color: #7f8c8d;
            font-size: 0.9rem;
            font-weight: 600;
        }
        div[data-testid="stMetricValue"] {
            color: #2c3e50;
            font-size: 1.6rem;
            font-weight: bold;
        }

        /* 4. PESTAÑAS MODERNAS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
            padding-bottom: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: white;
            border-radius: 8px;
            padding: 10px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: none;
            font-weight: 600;
            color: #555;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3498db !important; /* Azul brillante activo */
            color: white !important;
        }

        /* 5. TABLAS CON ESTILO CORPORATIVO */
        thead tr th {
            background-color: #34495e !important; /* Cabecera oscura */
            color: white !important;
            font-weight: bold !important;
            text-transform: uppercase;
            font-size: 0.85rem !important;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        /* 6. COLUMNA EDITABLE DESTACADA */
        div[data-testid="stDataEditor"] table tbody tr td[data-testid*="Precio EXW"] {
            background-color: #e8f6f3 !important; /* Verde/Azul muy tenue */
            font-weight: bold;
            color: #16a085;
            border: 1px solid #d1f2eb;
        }
        /* Encabezado de la editable */
        th[aria-label="Precio EXW (Editable)"] {
            background-color: #16a085 !important; /* Verde Esmeralda */
            color: white !important;
        }

        /* Ocultar elementos innecesarios */
        .row_heading.level0, .blank { display:none; }
        
        /* Títulos */
        h1, h2, h3 {
            color: #2c3e50;
            font-weight: 700;
        }
        hr {
            margin-top: 1rem;
            margin-bottom: 1rem;
            border: 0;
            border-top: 1px solid #dfe6e9;
        }
    </style>
""", unsafe_allow_html=True)

# --- ENLACE ---
SHEET_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRtdfgZGMkk10_R_8pFbH2_qbRsFB1JyltIq3t-hJqfEGKJhXMCbjH3Xh0z12AkMgZkRXYt7rLclJ44/pub?gid=0&single=true&output=csv'

# --- FUNCIONES DE NEGOCIO ---
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
        df_raw = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}"); st.stop()

    # Limpieza
    df_raw.columns = df_raw.columns.str.strip()
    rename_map = {'Coste congelación': 'Coste_congelación', 'Coste despiece': 'Coste_despiece', 'Precio escandallo': 'Precio_escandallo'}
    df_raw.rename(columns=rename_map, inplace=True)
    
    for col in ['Cliente', 'Fecha']: 
        if col not in df_raw.columns: df_raw[col] = ""
        else: df_raw[col] = df_raw[col].fillna("")

    if 'Código' in df_raw.columns:
        df_raw['Código'] = df_raw['Código'].astype(str).str.replace('.0', '', regex=False)

    cols_to_clean = ['Cantidad(kg)', 'Coste_despiece', 'Coste_congelación', 'Precio EXW']
    for col in cols_to_clean:
        if col in df_raw.columns: df_raw[col] = df_raw[col].apply(clean_european_number)

    for col in ['Coste_congelación', 'Coste_despiece']:
        if col in df_raw.columns: df_raw[col] = df_raw[col].fillna(0)
    
    for col in ['Familia', 'Formato']:
        if col in df_raw.columns: df_raw[col] = df_raw[col].fillna(f"Sin {col}")

    # FILTRO ÚLTIMA FECHA
    if 'Fecha' in df_raw.columns:
        df_raw['Fecha_dt'] = pd.to_datetime(df_raw['Fecha'], dayfirst=True, errors='coerce')
        df_raw['Max_Fecha'] = df_raw.groupby('Escandallo')['Fecha_dt'].transform('max')
        df_raw = df_raw[ (df_raw['Fecha_dt'] == df_raw['Max_Fecha']) | (df_raw['Fecha_dt'].isna()) ].copy()
        df_raw.drop(columns=['Fecha_dt', 'Max_Fecha'], inplace=True)

    return recalcular_dataframe(df_raw)

if 'df_global' not in st.session_state:
    st.session_state.df_global = load_initial_data()

df = st.session_state.df_global

# --- ETIQUETAS INTELIGENTES ---
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


# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🎛️ Panel de Control")
    st.markdown("---")
    
    opciones_familia = sorted(df['Familia'].unique()) if 'Familia' in df.columns else []
    sel_familia = st.multiselect("📂 Familia", options=opciones_familia)
    
    opciones_formato = sorted(df['Formato'].unique()) if 'Formato' in df.columns else []
    sel_formato = st.multiselect("📦 Formato", options=opciones_formato)
    
    # Filtro dinámico de escandallos
    df_temp = df.copy()
    if sel_familia: df_temp = df_temp[df_temp['Familia'].isin(sel_familia)]
    if sel_formato: df_temp = df_temp[df_temp['Formato'].isin(sel_formato)]
    opciones_escandallo = sorted(df_temp['Filtro_Display'].dropna().unique())
    
    st.markdown("---")
    sel_escandallo = st.multiselect("🏷️ Escandallos Específicos", options=opciones_escandallo)
    
    st.markdown("---")
    if st.button("🔄 Resetear Todos los Datos", type="primary"):
        st.cache_data.clear()
        st.session_state.df_global = load_initial_data()
        st.rerun()

# --- APLICACIÓN DE FILTROS ---
df_filtrado = df.copy()
if sel_familia: df_filtrado = df_filtrado[df_filtrado['Familia'].isin(sel_familia)]
if sel_formato: df_filtrado = df_filtrado[df_filtrado['Formato'].isin(sel_formato)]
if sel_escandallo: df_filtrado = df_filtrado[df_filtrado['Filtro_Display'].isin(sel_escandallo)]


# --- CUERPO PRINCIPAL ---

# 1. HEADER EJECUTIVO
st.title("📊 Dashboard de Rentabilidad")
st.markdown(f"**Análisis de costes y simulación de escenarios de precios.** | *Datos actualizados: {pd.Timestamp.now().strftime('%d/%m/%Y')}*")

if df_filtrado.empty:
    st.error("❌ No hay datos que coincidan con los filtros. Por favor, ajusta la selección en la barra lateral.")
else:
    # 2. FILA DE KPIs (Métricas Ejecutivas)
    # Calculamos métricas globales del conjunto filtrado para mostrarlas arriba
    
    # Pre-cálculo de totales para el ranking
    df_kpi_rank = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum()
    avg_rentabilidad = df_kpi_rank.mean()
    top_rentabilidad = df_kpi_rank.max()
    total_escandallos = df_kpi_rank.count()
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Escandallos Analizados", f"{total_escandallos}")
    col_kpi2.metric("Rentabilidad Media", f"{avg_rentabilidad:.3f} €")
    col_kpi3.metric("Rentabilidad Máxima", f"{top_rentabilidad:.3f} €")
    # Un indicador visual simple de estado
    col_kpi4.metric("Estado General", "Activo", delta="Simulación ON")
    
    st.markdown("---")

    # 3. PESTAÑAS
    tab1, tab2 = st.tabs(["📋 Detalle Técnico por Escandallo", "🏆 Ranking & Simulación"])

    # --- PESTAÑA 1: DETALLE ---
    with tab1:
        escandallos_a_mostrar = df_filtrado['Escandallo'].unique()
        
        for i, esc_id in enumerate(escandallos_a_mostrar):
            df_f = df_filtrado[df_filtrado['Escandallo'] == esc_id].copy()
            
            # Metadatos para el título
            fecha_str = df_f['Fecha'].iloc[0] if 'Fecha' in df_f.columns else "-"
            titulo = df_f['Filtro_Display'].iloc[0] if 'Filtro_Display' in df_f.columns else f"Escandallo {esc_id}"
            cliente = df_f['Cliente'].iloc[0] if 'Cliente' in df_f.columns else ""
            
            # Caja contenedora visual
            with st.container():
                c_tit, c_fecha = st.columns([3, 1])
                c_tit.markdown(f"### 🥩 {titulo}")
                if cliente: c_tit.caption(f"Cliente: **{cliente}**")
                c_fecha.markdown(f"**Fecha:** {fecha_str}")

                cols = ['Cliente', 'Código', 'Nombre', 'Coste_despiece', 'Coste_congelación', '%_Calculado', 'Precio EXW', 'Precio_escandallo_Calculado']
                df_v = df_f[[c for c in cols if c in df_f.columns]].copy()
                
                # Corrección Visual Porcentaje
                if '%_Calculado' in df_v.columns: df_v['%_Calculado'] = df_v['%_Calculado'] * 100

                # Fila Total
                ft = {c: None for c in df_v.columns}
                ft['Nombre'] = 'TOTAL'
                if '%_Calculado' in df_v: ft['%_Calculado'] = df_v['%_Calculado'].sum()
                if 'Precio_escandallo_Calculado' in df_v: ft['Precio_escandallo_Calculado'] = df_v['Precio_escandallo_Calculado'].sum()
                
                df_fin = pd.concat([df_v, pd.DataFrame([ft])], ignore_index=True)

                # Función de formateo manual para evitar "None"
                def fmt_num(x, pattern):
                    if pd.isna(x) or x is None: return ""
                    return pattern.format(x)

                format_dict = {
                    "%_Calculado": lambda x: fmt_num(x, "{:.2f} %"),
                    "Precio EXW": lambda x: fmt_num(x, "{:.3f} €"),
                    "Precio_escandallo_Calculado": lambda x: fmt_num(x, "{:.4f} €"),
                    "Coste_despiece": lambda x: fmt_num(x, "{:.3f} €"),
                    "Coste_congelación": lambda x: fmt_num(x, "{:.3f} €")
                }

                # Estilo Fila Total
                def estilo_t1(row):
                    s = [''] * len(row)
                    if row['Nombre'] == 'TOTAL':
                        s = ['font-weight: bold; background-color: #f8f9fa'] * len(row)
                        if 'Precio_escandallo_Calculado' in row.index:
                            idx = row.index.get_loc('Precio_escandallo_Calculado')
                            s[idx] += '; background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb'
                    return s

                col_cfg = {
                    "Código": st.column_config.TextColumn("Código"),
                    "%_Calculado": st.column_config.Column("%"),
                    "Precio EXW": st.column_config.Column("Precio EXW"),
                    "Precio_escandallo_Calculado": st.column_config.Column("P. Escandallo"),
                    "Coste_despiece": st.column_config.Column("C. Desp"),
                    "Coste_congelación": st.column_config.Column("C. Cong")
                }

                st.dataframe(
                    df_fin.style.format(format_dict).apply(estilo_t1, axis=1),
                    column_config=col_cfg,
                    use_container_width=True, 
                    hide_index=True
                )
            
            st.markdown("<br>", unsafe_allow_html=True) # Espacio

    # --- PESTAÑA 2: RANKING ---
    with tab2:
        st.markdown("""
        <div style="background-color: #e8f6f3; padding: 10px; border-radius: 5px; border-left: 5px solid #16a085; margin-bottom: 15px;">
            <strong>💡 Modo Simulación:</strong> Modifica los valores de la columna <em>'Precio EXW (Editable)'</em>. La tabla se reordenará automáticamente según la nueva rentabilidad.
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Datos Base
        df_rank = df_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()
        
        # 2. Info Principal
        cols_info = ['Escandallo', 'Código', 'Nombre', '%_Calculado', 'Precio EXW', 'Cliente', 'Fecha']
        if 'Tipo' in df_filtrado.columns:
            try:
                df_pr_raw = df_filtrado[df_filtrado['Tipo'].str.contains('Principal', case=False, na=False)][cols_info]
            except:
                df_pr_raw = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()
        else:
            df_pr_raw = df_filtrado.groupby('Escandallo')[cols_info].first().reset_index()
            
        # 3. Consolidación (Suma % de todos los principales)
        df_suma_pct = df_pr_raw.groupby('Escandallo')['%_Calculado'].sum().reset_index()
        df_info_first = df_pr_raw.groupby('Escandallo')[['Código', 'Nombre', 'Cliente', 'Fecha', 'Precio EXW']].first().reset_index()
        df_pr_con = pd.merge(df_info_first, df_suma_pct, on='Escandallo')
        
        # 4. Merge Final y Orden
        df_final = pd.merge(df_rank, df_pr_con, on='Escandallo').sort_values('Precio_escandallo_Calculado', ascending=False)
        df_final['Pos'] = [f"{i}º" for i in range(1, len(df_final)+1)]
        df_final['%/CP'] = df_final['%_Calculado'] * 100

        # 5. Semáforo
        if not df_final.empty:
            q33 = df_final['Precio_escandallo_Calculado'].quantile(0.33)
            q66 = df_final['Precio_escandallo_Calculado'].quantile(0.66)
            def get_semaforo(valor):
                if valor >= q66: return "🟢 Alta" 
                elif valor >= q33: return "🟡 Media" 
                else: return "🔴 Baja" 
            df_final['Estado'] = df_final['Precio_escandallo_Calculado'].apply(get_semaforo)
        else:
            df_final['Estado'] = ""

        # 6. Configuración Editor
        cols_show = ['Pos', 'Estado', 'Cliente', 'Fecha', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
        df_ed = df_final[cols_show].copy()

        conf_ed = {
            "Pos": st.column_config.TextColumn("Pos", width="small", disabled=True),
            "Estado": st.column_config.TextColumn("KPI", width="small", disabled=True),
            "Cliente": st.column_config.TextColumn("Cliente", disabled=True),
            "Fecha": st.column_config.TextColumn("Fecha", disabled=True),
            "Código": st.column_config.TextColumn("Cód", disabled=True),
            "Nombre": st.column_config.TextColumn("Artículo Principal", disabled=True),
            "%/CP": st.column_config.NumberColumn("%/CP", format="%.2f %%", disabled=True),
            
            # Barra de Progreso
            "Precio_escandallo_Calculado": st.column_config.ProgressColumn(
                "Rentabilidad Total", 
                format="%.4f €", 
                min_value=0, 
                max_value=df_final['Precio_escandallo_Calculado'].max() if not df_final.empty else 10
            ),
            # Columna Editable Destacada
            "Precio EXW": st.column_config.NumberColumn(
                "Precio EXW (Editable)",
                format="%.3f €",
                step=0.01,
                required=True
            )
        }

        edited = st.data_editor(
            df_ed,
            column_config=conf_ed,
            use_container_width=True,
            hide_index=True,
            key="ranking_ed",
            height=(len(df_ed) + 1) * 35 + 50 # Altura dinámica
        )

        # 7. Lógica de Guardado (Write-back)
        if not edited.equals(df_ed):
            for i, r in edited.iterrows():
                esc_id_real = df_final.iloc[i]['Escandallo']
                mask = (st.session_state.df_global['Escandallo'] == esc_id_real) & \
                       (st.session_state.df_global['Código'].astype(str) == str(r['Código']))
                st.session_state.df_global.loc[mask, 'Precio EXW'] = r['Precio EXW']
                
            st.session_state.df_global = recalcular_dataframe(st.session_state.df_global)
            st.rerun()
