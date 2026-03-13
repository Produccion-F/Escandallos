import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import json
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Escandallos",
    layout="wide",
    initial_sidebar_state="collapsed", 
    page_icon="🥩"
)

# --- CSS GENERAL (+20% TAMAÑO) ---
st.markdown("""
    <style>
        .stApp { background-color: #E2E8F0; color: #1E293B; }
        
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #FFFFFF; 
            border: 1px solid #CBD5E1; 
            color: #475569; 
            border-radius: 6px 6px 0 0; 
            font-size: 1.2rem !important; 
            padding: 10px 20px !important;
        }
        .stTabs [aria-selected="true"] { background-color: #2563EB !important; color: #FFFFFF !important; font-weight: bold; }
        
        h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-family: 'Segoe UI', sans-serif; }
        
        .stMultiSelect label p, .stSelectbox label p, .stNumberInput label p, .stCheckbox label p { 
            font-size: 1.1rem !important; 
            font-weight: 700 !important; 
            color: #1E40AF !important; 
        }
    </style>
""", unsafe_allow_html=True)

# --- AUTENTICACIÓN (LOGIN) ---
def check_password():
    """Verifica si el usuario ha introducido la contraseña correcta."""
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown("""
            <div style='background-color: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); text-align: center; border: 1px solid #CBD5E1;'>
                <h2 style='color: #1E293B; margin-bottom: 5px;'>🔒 Acceso Restringido</h2>
                <p style='color: #64748B; font-size: 1.1rem; margin-bottom: 25px;'>Introduce la contraseña para acceder al Panel de Escandallos</p>
            </div>
        """, unsafe_allow_html=True)
        
        password = st.text_input("Contraseña", type="password", label_visibility="collapsed", placeholder="Contraseña...")
        
        if st.button("Entrar al Panel", type="primary", use_container_width=True):
            if password == "comerprod26":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Contraseña incorrecta. Inténtalo de nuevo.")
                
    return False

if not check_password():
    st.stop()


# =====================================================================
# MOTOR DE CONEXIÓN SEGURA A GOOGLE SHEETS
# =====================================================================

@st.cache_resource
def get_gspread_client():
    try:
        creds_secret = st.secrets["google_credentials"]
        # Si el usuario pegó el JSON tal cual, Streamlit lo puede interpretar como string o diccionario
        if isinstance(creds_secret, str):
            creds_dict = json.loads(creds_secret)
        else:
            creds_dict = dict(creds_secret)
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"🚨 Error en la configuración de la clave de Google: {e}")
        st.stop()

def load_sheet_df(url):
    """Extrae la información de Google Sheets usando el enlace real."""
    client = get_gspread_client()
    # Extraer el GID (Identificador de la pestaña)
    gid = 0
    if "gid=" in url:
        gid = url.split("gid=")[-1].split("&")[0]
        
    try:
        sheet = client.open_by_url(url)
        ws = sheet.get_worksheet_by_id(int(gid))
        data = ws.get_all_values()
        
        if not data:
            return pd.DataFrame()
        
        # Convierte los datos brutos en un DataFrame de Pandas usando la primera fila como cabecera
        return pd.DataFrame(data[1:], columns=data[0])
    except Exception as e:
        raise Exception(f"No se pudo acceder a la hoja. ¿Has compartido el Excel con el correo del Robot? Detalle técnico: {e}")

# --- ENLACES REALES DE DATOS PRIVADOS ---
VENTAS_URL = 'https://docs.google.com/spreadsheets/d/1kyiTFjTl-XxkwhYQlm6FjMbnZWhNR4-AtW3iFj2qXzs/edit?gid=1543847315#gid=1543847315'
BASE_URL = 'https://docs.google.com/spreadsheets/d/1nGSUQGspPnvkkSD0qmlYqhhfXAEAqbN1vm5DTPhaDkM/edit?gid=0#gid=0'
EQUIV_URL = 'https://docs.google.com/spreadsheets/d/1nGSUQGspPnvkkSD0qmlYqhhfXAEAqbN1vm5DTPhaDkM/edit?gid=1911720872#gid=1911720872'

# =====================================================================

# --- FUNCIONES DE DIBUJADO DE KPIs ---
def render_kpi(titulo, valor, color_texto="#38BDF8"):
    return f"""
    <div style="background-color: #1E293B; border-radius: 8px; padding: 20px; border: 1px solid #0F172A; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); text-align: center; margin-bottom: 15px;">
        <p style="color: #FFFFFF; font-size: 1.2rem; font-weight: 600; margin: 0 0 10px 0; font-family: sans-serif;">{titulo}</p>
        <p style="color: {color_texto}; font-size: 2.4rem; font-weight: 800; margin: 0; font-family: sans-serif;">{valor}</p>
    </div>
    """

# --- FUNCIONES DE LIMPIEZA Y FORMATO ---
def clean_european_number(x):
    if pd.isna(x) or str(x).strip() == '': return 0.0
    if isinstance(x, (int, float)): return float(x)
    try: return float(str(x).replace('.', '').replace(',', '.'))
    except ValueError: return 0.0

def formato_europeo(val, decimales=2, sufijo=""):
    if pd.isna(val) or val == np.inf or val == -np.inf: return "0" + sufijo
    formateado = f"{val:,.{decimales}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return formateado + sufijo

def recalcular_dataframe(df):
    if 'Cantidad(kg)' in df.columns and 'Escandallo' in df.columns:
        df['Total_Kg_Grupo'] = df.groupby('Escandallo')['Cantidad(kg)'].transform('sum')
        df['%_Calculado'] = np.where(df['Total_Kg_Grupo'] > 0, df['Cantidad(kg)'] / df['Total_Kg_Grupo'], 0.0)

    cols_calc = ['Precio EXW', 'Coste_congelación', 'Coste_despiece', '%_Calculado']
    if all(c in df.columns for c in cols_calc):
        df['Precio_escandallo_Calculado'] = (df['Precio EXW'] - df['Coste_congelación'] - df['Coste_despiece']) * df['%_Calculado']
    return df

# --- MOTOR MRP ---
def procesar_ventas_cascada(df_v, df_esc_completo, mapa_esc_principal, mapa_equiv, esc_to_princ):
    df_v_agrupado = df_v.groupby(['Cliente', 'Código', 'Nombre']).agg({'Kilos': 'sum', 'Precio EXW': 'mean'}).reset_index()
    
    global_avg = {}
    for cod, grp in df_v_agrupado.groupby('Código'):
        tot_k = grp['Kilos'].sum()
        if tot_k > 0: global_avg[str(cod)] = (grp['Kilos'] * grp['Precio EXW']).sum() / tot_k

    client_avg = {}
    banco_kilos = {} 
    
    for cli, grp_cli in df_v_agrupado.groupby('Cliente'):
        cli_str = str(cli)
        client_avg[cli_str] = {}
        banco_kilos[cli_str] = {}
        for _, row in grp_cli.iterrows():
            cod = str(row['Código'])
            client_avg[cli_str][cod] = row['Precio EXW']
            banco_kilos[cli_str][cod] = {'kilos': float(row['Kilos']), 'precio': float(row['Precio EXW']), 'nombre': str(row['Nombre'])}

    ventas_procesadas = []

    for _, row in df_v_agrupado.iterrows():
        cli = str(row['Cliente'])
        cod_vendido = str(row['Código']).strip()
        kilos_cliente = float(row['Kilos'])
        precio_cliente = float(row['Precio EXW'])
        nombre_articulo = str(row['Nombre'])

        esc_id = None
        cod_principal_teorico = None
        
        if cod_vendido in mapa_esc_principal:
            esc_id = mapa_esc_principal[cod_vendido]
            cod_principal_teorico = cod_vendido
        elif cod_vendido in mapa_equiv:
            esc_id = mapa_equiv[cod_vendido][0]
            cod_principal_teorico = mapa_equiv[cod_vendido][1]

        if esc_id is not None and cod_principal_teorico is not None:
            df_bloque_esc = df_esc_completo[df_esc_completo['Escandallo'] == esc_id]
            if not df_bloque_esc.empty:
                fam_temp = df_bloque_esc['Familia'].iloc[0] if 'Familia' in df_bloque_esc.columns else "Sin clasificar"
                if pd.isna(fam_temp) or str(fam_temp).strip() == "": fam_temp = "Sin clasificar"
                
                fila_principal = df_bloque_esc[df_bloque_esc['Código'].astype(str) == cod_principal_teorico]
                pct_principal = fila_principal['%_Calculado'].iloc[0] if not fila_principal.empty else 0.0
                kilos_cp = (kilos_cliente / pct_principal) if pct_principal > 0 else 0.0
                
                precio_cp_unitario = 0.0
                
                for _, item in df_bloque_esc.iterrows():
                    cod_item = str(item['Código']).strip()
                    pct_item = float(item['%_Calculado'])
                    coste_cong = float(item.get('Coste_congelación', 0.0))
                    coste_desp = float(item.get('Coste_despiece', 0.0))
                    
                    if cod_item == cod_principal_teorico: 
                        precio_exw_dinamico = precio_cliente
                        codigo_a_consumir = cod_vendido 
                    else:
                        codigo_a_consumir = cod_item
                        if cod_item in client_avg.get(cli, {}): precio_exw_dinamico = client_avg[cli][cod_item]
                        elif cod_item in global_avg: precio_exw_dinamico = global_avg[cod_item]
                        else: precio_exw_dinamico = float(item.get('Precio EXW', 0.0))
                    
                    precio_cp_unitario += (precio_exw_dinamico - coste_cong - coste_desp) * pct_item
                    
                    if cli in banco_kilos and codigo_a_consumir in banco_kilos[cli]:
                        banco_kilos[cli][codigo_a_consumir]['kilos'] -= (kilos_cp * pct_item)

                ventas_procesadas.append({
                    'Cliente': cli, 'Código': cod_vendido, 'Artículo': nombre_articulo,
                    'Familia': fam_temp, 'Kilos': kilos_cliente, 'Kilos_CP': kilos_cp,
                    'Precio EXW': precio_cliente, 'Precio_CP_Unitario': precio_cp_unitario,
                    'Precio_CP_Total': precio_cp_unitario * kilos_cp
                })

    sobrantes = []
    for cli, codigos in banco_kilos.items():
        for cod, data in codigos.items():
            if data['kilos'] > 0.01: 
                sobrantes.append({
                    'Cliente': cli, 'Código': cod, 'Artículo': data['nombre'],
                    'Familia': 'Sin clasificar', 'Kilos': data['kilos'], 'Kilos_CP': 0.0,
                    'Precio EXW': data['precio'], 'Precio_CP_Unitario': 0.0, 'Precio_CP_Total': 0.0
                })

    df_final = pd.DataFrame(ventas_procesadas)
    if sobrantes:
        df_final = pd.concat([df_final, pd.DataFrame(sobrantes)], ignore_index=True)

    return df_final, global_avg, client_avg

@st.cache_data(ttl=600)
def load_equiv_data():
    try:
        df_e = load_sheet_df(EQUIV_URL)
        if df_e.empty: return {}, "El archivo de Equivalencias está vacío."
        
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
        return {}, "Faltan columnas clave (Código, Escandallo, Codigo Principal) en Equivalencias."
    except Exception as e:
        return {}, f"Error cargando equivalencias: {e}"

@st.cache_data(ttl=600)
def load_initial_data():
    try: 
        df_raw = load_sheet_df(BASE_URL)
        if df_raw.empty: return None, "La base de datos principal está vacía."
    except Exception as e: 
        return None, f"Error conectando a Base de Datos: {e}"
        
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
        df_v = load_sheet_df(VENTAS_URL)
        if df_v.empty: return pd.DataFrame(), None
        
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
if 'df_global_base' not in st.session_state:
    data, err = load_initial_data()
    if err: st.error(err); st.stop()
    st.session_state.df_global_base = data.copy()
if 'grid_key' not in st.session_state: st.session_state.grid_key = 0

# --- PRE-PROCESAMIENTO Y GENERACIÓN DEL SIMULADOR ---
if 'df_proc_global' not in st.session_state or 'df_simulador' not in st.session_state:
    df_ventas, err_v = load_sales_data()
    st.session_state.err_v = err_v 
    mapa_equiv, err_e = load_equiv_data()
    if err_e: st.warning(err_e)
    st.session_state.mapa_equivalencias = mapa_equiv
    
    global_avg_base = {}
    client_avg_base = {}
    bench_familia = {}
    mapa_escandallos = {}
    esc_to_princ = {}
    
    if not err_v and df_ventas is not None and not df_ventas.empty:
        df_ventas = df_ventas[~df_ventas['Cliente'].str.contains('Entradas a Congelar', case=False, na=False)]
        df_esc_completo = st.session_state.df_global_base.copy() 
        
        if 'Código' in df_ventas.columns:
            df_princ = df_esc_completo[df_esc_completo['Tipo'].str.contains('Principal', case=False, na=False)] if 'Tipo' in df_esc_completo.columns else pd.DataFrame()
            if not df_princ.empty:
                df_princ_unique = df_princ.drop_duplicates(subset=['Código'], keep='first')
                mapa_escandallos = dict(zip(df_princ_unique['Código'].astype(str), df_princ_unique['Escandallo']))
                df_princ_per_esc = df_princ.drop_duplicates(subset=['Escandallo'], keep='first')
                esc_to_princ = dict(zip(df_princ_per_esc['Escandallo'], df_princ_per_esc['Código'].astype(str)))
                
                df_proc_global, global_avg_base, client_avg_base = procesar_ventas_cascada(df_ventas, df_esc_completo, mapa_escandallos, mapa_equiv, esc_to_princ)
                
                if not df_proc_global.empty:
                    for fam in df_proc_global['Familia'].unique():
                        if fam != 'Sin clasificar':
                            df_f = df_proc_global[df_proc_global['Familia'] == fam]
                            tk, tr = df_f['Kilos_CP'].sum(), df_f['Precio_CP_Total'].sum()
                            bench_familia[fam] = tr / tk if tk > 0 else 0.0
                            
                st.session_state.df_proc_global = df_proc_global
                st.session_state.global_avg_base = global_avg_base
                st.session_state.client_avg_base = client_avg_base
                st.session_state.bench_familia = bench_familia
                st.session_state.mapa_escandallos = mapa_escandallos
                st.session_state.esc_to_princ = esc_to_princ
                st.session_state.df_ventas_crudas = df_ventas
                
                df_sim = st.session_state.df_global_base.copy()
                df_sim['ORIGEN_PRECIO'] = 'Teórico'
                for idx, row in df_sim.iterrows():
                    cod = str(row['Código'])
                    if cod in global_avg_base:
                        df_sim.at[idx, 'Precio EXW'] = float(global_avg_base[cod])
                        df_sim.at[idx, 'ORIGEN_PRECIO'] = 'Venta Real'
                df_sim = recalcular_dataframe(df_sim)
                st.session_state.df_simulador = df_sim
                
    else: 
        st.session_state.df_proc_global = pd.DataFrame()
        st.session_state.df_simulador = st.session_state.df_global_base.copy()

# RECUPERACIÓN DE VARIABLES
df_proc_global = st.session_state.get('df_proc_global', pd.DataFrame())
df_simulador = st.session_state.get('df_simulador', st.session_state.get('df_global_base', pd.DataFrame()).copy())
df_global_base = st.session_state.get('df_global_base', pd.DataFrame())
global_avg_base = st.session_state.get('global_avg_base', {})
client_avg_base = st.session_state.get('client_avg_base', {})
bench_familia = st.session_state.get('bench_familia', {})
mapa_escandallos = st.session_state.get('mapa_escandallos', {})
esc_to_princ = st.session_state.get('esc_to_princ', {})
mapa_equivalencias = st.session_state.get('mapa_equivalencias', {})
df_ventas = st.session_state.get('df_ventas_crudas', pd.DataFrame())
err_v = st.session_state.get('err_v', None)

# --- ETIQUETAS FILTROS GLOBALES ---
if not df_global_base.empty:
    if 'Tipo' in df_global_base.columns and df_global_base['Tipo'].str.contains('Principal', case=False, na=False).any():
        df_principales = df_global_base[df_global_base['Tipo'].str.contains('Principal', case=False, na=False)][['Escandallo', 'Código', 'Nombre']]
    else:
        df_principales = df_global_base.groupby('Escandallo')[['Escandallo', 'Código', 'Nombre']].first().reset_index()
    
    df_principales = df_principales.drop_duplicates(subset=['Escandallo'])
    df_principales['Texto_Escandallo'] = df_principales['Escandallo'].astype(str) + " | " + df_principales['Código'].astype(str) + " | " + df_principales['Nombre']
    mapa_etiquetas = dict(zip(df_principales['Escandallo'], df_principales['Texto_Escandallo']))

    if 'Escandallo' in df_global_base.columns: df_global_base['Filtro_Display'] = df_global_base['Escandallo'].map(mapa_etiquetas)
    if 'Escandallo' in df_simulador.columns: df_simulador['Filtro_Display'] = df_simulador['Escandallo'].map(mapa_etiquetas)

# --- FUNCIONES DE ESTILO DE TABLA ---
def zebra_base(row):
    base_style = 'font-size: 16px;'
    if row.name % 2 == 0: return [base_style + 'background-color: #F8F9FA; color: #1E293B'] * len(row)
    else: return [base_style + 'background-color: #DBEAFE; color: #0F172A'] * len(row)

def style_rows_t1(row):
    tipo_val = row.get('TIPO', '') 
    if tipo_val == 'TotalRow' or tipo_val == 'TOTALROW': return ['background-color: #064E3B; font-weight: bold; color: #FFFFFF; font-size: 16px;'] * len(row)
    if isinstance(tipo_val, str) and 'principal' in tipo_val.lower(): return ['background-color: #1E40AF; font-weight: bold; color: #FFFFFF; font-size: 16px;'] * len(row)
    return zebra_base(row)

# --- APP LAYOUT ---
c_title, c_btn = st.columns([4, 1])
c_title.title("📊 Panel de Escandallos y Rentabilidad")
if c_btn.button("🔄 Actualizar todos los datos", type="primary", use_container_width=True):
    st.cache_data.clear()
    for key in list(st.session_state.keys()):
        if key != "password_correct": 
            del st.session_state[key]
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📋 DETALLE TÉCNICO (TEÓRICO)", "🏆 RANKING & SIMULACIÓN", "📈 PANEL EJECUTIVO (VENTAS REALES)"])

# --- PESTAÑA 1: DETALLE TÉCNICO PURAMENTE TEÓRICO ---
with tab1:
    with st.expander("🎛️ Panel de Filtros Teóricos", expanded=True):
        col_t1_1, col_t1_2, col_t1_3 = st.columns(3)
        familias_t1 = sorted(df_global_base['Familia'].unique()) if not df_global_base.empty and 'Familia' in df_global_base.columns else []
        sel_familia_t1 = col_t1_1.multiselect("📂 Familia", options=familias_t1, key="f_fam_t1")
        formatos_t1 = sorted(df_global_base['Formato'].unique()) if not df_global_base.empty and 'Formato' in df_global_base.columns else []
        sel_formato_t1 = col_t1_2.multiselect("📦 Formato", options=formatos_t1, key="f_for_t1")
        mask_t1 = pd.Series(True, index=df_global_base.index)
        if sel_familia_t1: mask_t1 &= df_global_base['Familia'].isin(sel_familia_t1)
        if sel_formato_t1: mask_t1 &= df_global_base['Formato'].isin(sel_formato_t1)
        opciones_escandallo_t1 = sorted(df_global_base[mask_t1]['Filtro_Display'].dropna().unique()) if not df_global_base.empty and 'Filtro_Display' in df_global_base.columns else []
        sel_escandallo_t1 = col_t1_3.multiselect("🏷️ Escandallo", options=opciones_escandallo_t1, key="f_esc_t1")
        if sel_escandallo_t1 and 'Filtro_Display' in df_global_base.columns: mask_t1 &= df_global_base['Filtro_Display'].isin(sel_escandallo_t1)
        df_t1_filtrado = df_global_base[mask_t1].copy() if not df_global_base.empty else pd.DataFrame()

    st.divider()
    if df_t1_filtrado.empty:
        st.info("ℹ️ No hay datos teóricos disponibles para los filtros seleccionados.")
    else:
        kpi_data = df_t1_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum()
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(render_kpi("Escandallos Mostrados", f"{kpi_data.count()}"), unsafe_allow_html=True)
        k2.markdown(render_kpi("Media a CP Teórico", formato_europeo(kpi_data.mean(), 2, ' €')), unsafe_allow_html=True)
        k3.markdown(render_kpi("Max a CP Teórico", formato_europeo(kpi_data.max(), 2, ' €')), unsafe_allow_html=True)
        k4.markdown(render_kpi("Min a CP Teórico", formato_europeo(kpi_data.min(), 2, ' €')), unsafe_allow_html=True)
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
        c_pag2.markdown(f"<div style='text-align:center; color:#6B7280; margin-top:10px; font-size:16px;'>Mostrando {st.session_state.page * ITEMS_PER_PAGE + 1} - {min((st.session_state.page + 1) * ITEMS_PER_PAGE, total_esc)} de {total_esc}</div>", unsafe_allow_html=True)

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
            df_fin.columns = [str(c).upper() for c in df_fin.columns]

            styled_df = df_fin.style.apply(style_rows_t1, axis=1).format({
                '%_CALCULADO': lambda x: formato_europeo(x, 2, " %"),
                'PRECIO EXW': lambda x: formato_europeo(x, 3, " €"),
                'PRECIO A CP TEÓRICO': lambda x: formato_europeo(x, 4, " €")
            })
            st.dataframe(styled_df, column_config={"TIPO": None}, use_container_width=True, hide_index=True)
            st.divider()

# --- PESTAÑA 2: RANKING Y SIMULACIÓN (CON GEMELO DIGITAL) ---
with tab2:
    st.subheader("🏆 Simulador Híbrido de Precios (Base Mercado Real)")
    st.info("💡 Este simulador arranca usando los **Precios Reales Medios** de tus ventas. Haz doble clic en los números azules de la columna **PRECIO EXW ✏️** para sobrescribirlos. Marca la casilla **🔍 VER** para desplegar el escandallo.")

    with st.expander("🎛️ Panel de Filtros del Simulador", expanded=True):
        col_t2_1, col_t2_2, col_t2_3, col_t2_4 = st.columns(4)
        
        familias_t2_sim = sorted(df_simulador['Familia'].unique()) if not df_simulador.empty and 'Familia' in df_simulador.columns else []
        sel_familia_t2_sim = col_t2_1.multiselect("📂 Familia", options=familias_t2_sim, key="f_fam_t2_sim")
        
        formatos_t2_sim = sorted(df_simulador['Formato'].unique()) if not df_simulador.empty and 'Formato' in df_simulador.columns else []
        sel_formato_t2_sim = col_t2_2.multiselect("📦 Formato", options=formatos_t2_sim, key="f_for_t2_sim")
        
        mask_t2_sim = pd.Series(True, index=df_simulador.index) if not df_simulador.empty else pd.Series(dtype=bool)
        if sel_familia_t2_sim: mask_t2_sim &= df_simulador['Familia'].isin(sel_familia_t2_sim)
        if sel_formato_t2_sim: mask_t2_sim &= df_simulador['Formato'].isin(sel_formato_t2_sim)
        
        opciones_escandallo_t2_sim = sorted(df_simulador[mask_t2_sim]['Filtro_Display'].dropna().unique()) if not df_simulador.empty and 'Filtro_Display' in df_simulador.columns else []
        sel_escandallo_t2_sim = col_t2_3.multiselect("🏷️ Escandallo", options=opciones_escandallo_t2_sim, key="f_esc_t2_sim")
        if sel_escandallo_t2_sim and 'Filtro_Display' in df_simulador.columns: mask_t2_sim &= df_simulador['Filtro_Display'].isin(sel_escandallo_t2_sim)
        
        if not df_simulador.empty and 'ORIGEN_PRECIO' in df_simulador.columns:
            try:
                origenes_t2_sim = sorted(df_simulador[df_simulador['Tipo'].str.contains('Principal', case=False, na=False)]['ORIGEN_PRECIO'].dropna().unique())
            except:
                origenes_t2_sim = sorted(df_simulador['ORIGEN_PRECIO'].dropna().unique())
        else:
            origenes_t2_sim = []
            
        sel_origen_t2_sim = col_t2_4.multiselect("💰 Origen", options=origenes_t2_sim, key="f_ori_t2_sim")
        
        df_sim_filtrado = df_simulador[mask_t2_sim].copy() if not df_simulador.empty else pd.DataFrame()

    if df_sim_filtrado.empty:
        st.warning("No hay datos para los filtros seleccionados.")
    else:
        df_rank = df_sim_filtrado.groupby('Escandallo')['Precio_escandallo_Calculado'].sum().reset_index()
        cols_info = ['Escandallo', 'Código', 'Nombre', '%_Calculado', 'Precio EXW', 'ORIGEN_PRECIO']
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
        
        if sel_origen_t2_sim and 'ORIGEN_PRECIO' in df_final.columns:
            df_final = df_final[df_final['ORIGEN_PRECIO'].isin(sel_origen_t2_sim)].reset_index(drop=True)
            
        if df_final.empty:
            st.warning("Ningún artículo cumple con el Origen seleccionado dentro de los filtros actuales.")
        else:
            df_final.insert(0, '🔍 VER', False)
            df_final['Pos'] = range(1, len(df_final)+1)
            df_final['%/CP'] = df_final['%_Calculado'] * 100

            cols_vis = ['🔍 VER', 'Pos', 'ORIGEN_PRECIO', 'Código', 'Nombre', '%/CP', 'Precio EXW', 'Precio_escandallo_Calculado']
            cols_final = [c for c in cols_vis if c in df_final.columns] + ['Escandallo']
            df_ed = df_final[cols_final].copy()
            
            df_ed_display = df_ed.copy()
            df_ed_display['%/CP'] = df_ed['%/CP'].apply(lambda x: formato_europeo(x, 2, " %"))
            df_ed_display['Precio_escandallo_Calculado'] = df_ed['Precio_escandallo_Calculado'].apply(lambda x: formato_europeo(x, 4, " €"))
            df_ed_display.rename(columns={'Precio_escandallo_Calculado': 'Precio a CP Simulado', 'ORIGEN_PRECIO': 'Origen'}, inplace=True)
            df_ed_display.columns = [str(c).upper() for c in df_ed_display.columns]

            styled_ed_display = df_ed_display.style.apply(zebra_base, axis=1)
            
            edited_df = st.data_editor(
                styled_ed_display,
                column_config={
                    "🔍 VER": st.column_config.CheckboxColumn("🔍 VER", default=False),
                    "POS": st.column_config.NumberColumn("POS", disabled=True),
                    "ORIGEN": st.column_config.TextColumn("ORIGEN", disabled=True),
                    "PRECIO EXW": st.column_config.NumberColumn("PRECIO EXW ✏️", required=True, format="%.3f €"),
                    "%/CP": st.column_config.TextColumn("%/CP", disabled=True),
                    "PRECIO A CP SIMULADO": st.column_config.TextColumn("PRECIO A CP SIMULADO", disabled=True),
                    "ESCANDALLO": None
                },
                disabled=["POS", "ORIGEN", "CÓDIGO", "NOMBRE", "%/CP", "PRECIO A CP SIMULADO", "ESCANDALLO"],
                hide_index=True, use_container_width=True, key=f"editor_nativo_{st.session_state.grid_key}"
            )

            col_edit = 'PRECIO EXW' if 'PRECIO EXW' in edited_df.columns else None
            col_orig = 'Precio EXW' if 'Precio EXW' in df_ed.columns else None
            
            if col_edit and col_orig:
                val_edit = pd.to_numeric(edited_df[col_edit], errors='coerce').fillna(0)
                val_orig = pd.to_numeric(df_ed[col_orig], errors='coerce').fillna(0).values
                diferencias = val_edit - val_orig
                
                if diferencias.abs().sum() > 0.0001:
                     st.toast("⚡ Guardando simulación...", icon="📊")
                     cambios = edited_df[diferencias.abs() > 0.0001]
                     for i, r in cambios.iterrows():
                        esc_val = r.get('ESCANDALLO')
                        cod_val = r.get('CÓDIGO')
                        precio_val = r.get('PRECIO EXW')
                        
                        mask = (st.session_state.df_simulador['Escandallo'] == esc_val) & (st.session_state.df_simulador['Código'].astype(str) == str(cod_val))
                        st.session_state.df_simulador.loc[mask, 'Precio EXW'] = float(precio_val)
                        if 'ORIGEN_PRECIO' in st.session_state.df_simulador.columns:
                            st.session_state.df_simulador.loc[mask, 'ORIGEN_PRECIO'] = 'Simulado Manual'
                            
                     st.session_state.df_simulador = recalcular_dataframe(st.session_state.df_simulador)
                     st.session_state.grid_key += 1 
                     st.rerun()
            
            filas_marcadas = edited_df[edited_df['🔍 VER'] == True]
            if not filas_marcadas.empty:
                for _, f_row in filas_marcadas.iterrows():
                    sel_esc = f_row['ESCANDALLO']
                    sel_cod = f_row['CÓDIGO']
                    sel_nombre = f_row['NOMBRE']
                    
                    st.markdown(f"###### 🔎 Trazabilidad del Escandallo: {sel_cod} - {sel_nombre}")
                    
                    df_bloque_esc = st.session_state.df_simulador[st.session_state.df_simulador['Escandallo'] == sel_esc]
                    breakdown_data = []
                    for _, item in df_bloque_esc.iterrows():
                        cod_item = str(item.get('Código', '')).strip()
                        pct_item = float(item.get('%_Calculado', 0.0))
                        coste_cong = float(item.get('Coste_congelación', 0.0))
                        coste_desp = float(item.get('Coste_despiece', 0.0))
                        precio_aplicado = float(item.get('Precio EXW', 0.0))
                        origen = str(item.get('ORIGEN_PRECIO', 'Teórico'))
                        
                        linea_cp = (precio_aplicado - coste_cong - coste_desp) * pct_item
                        breakdown_data.append({
                            'Código': cod_item, 'Artículo': item.get('Nombre', ''), '% Rendimiento': pct_item * 100, 
                            'Origen Precio': origen, 'Precio Aplicado': precio_aplicado,
                            'Coste Despiece': coste_desp, 'Coste Cong.': coste_cong, 'Aportación a CP': linea_cp
                        })
                        
                    df_breakdown = pd.DataFrame(breakdown_data).reset_index(drop=True)
                    df_breakdown.columns = [str(c).upper() for c in df_breakdown.columns]

                    def style_breakdown(row):
                        if row['CÓDIGO'] == str(sel_cod): return ['background-color: #1E3A8A; font-weight: bold; color: #FFFFFF; font-size: 16px;'] * len(row)
                        return zebra_base(row)
                        
                    st.dataframe(
                        df_breakdown.style.apply(style_breakdown, axis=1).format({
                            '% RENDIMIENTO': lambda x: formato_europeo(x, 2, " %"), 'PRECIO APLICADO': lambda x: formato_europeo(x, 3, " €"),
                            'COSTE DESPIECE': lambda x: formato_europeo(x, 3, " €"), 'COSTE CONG.': lambda x: formato_europeo(x, 3, " €"),
                            'APORTACIÓN A CP': lambda x: formato_europeo(x, 4, " €/kg")
                        }), use_container_width=True, hide_index=True
                    )

    # --- LISTA MAESTRA DE VENTAS REALES ---
    st.divider()
    st.subheader("📋 Escandallos Reales por Cliente (Lista Maestra)")
    st.info("💡 Haz clic en una o **varias filas a la vez** para auditar y comparar sus recetas abajo.")
    
    if not df_proc_global.empty:
        with st.expander("🎛️ Panel de Filtros de Ventas", expanded=True):
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
            df_master_disp.columns = [str(c).upper() for c in df_master_disp.columns]

            styled_master = df_master_disp.style.apply(zebra_base, axis=1).format({
                'KILOS': lambda x: formato_europeo(x, 0, " kg"),
                'PRECIO EXW': lambda x: formato_europeo(x, 3, " €"),
                'PRECIO A CP': lambda x: formato_europeo(x, 4, " €/kg")
            })

            event_master = st.dataframe(
                styled_master, use_container_width=True, hide_index=True,
                selection_mode="multi-row", on_select="rerun", key="table_master_t2_fixed"
            )
            
            if len(event_master.selection.rows) > 0:
                for row_idx in event_master.selection.rows:
                    sel_cli = str(df_master_disp.iloc[row_idx]['CLIENTE'])
                    sel_cod = str(df_master_disp.iloc[row_idx]['CÓDIGO'])
                    sel_exw = float(df_master_disp.iloc[row_idx]['PRECIO EXW'])
                    sel_art = str(df_master_disp.iloc[row_idx]['ARTÍCULO'])
                    
                    st.markdown(f"###### 🔎 Trazabilidad del Escandallo: {sel_cod} - {sel_art} (Cliente: {sel_cli})")
                    
                    esc_id = None; cod_principal_teorico = None; es_equivalencia = False
                    if sel_cod in mapa_escandallos:
                        esc_id = mapa_escandallos[sel_cod]; cod_principal_teorico = sel_cod
                    elif sel_cod in mapa_equivalencias:
                        esc_id = mapa_equivalencias[sel_cod][0]; cod_principal_teorico = mapa_equivalencias[sel_cod][1]; es_equivalencia = True
                    
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
                        df_breakdown.columns = [str(c).upper() for c in df_breakdown.columns]

                        def style_breakdown(row):
                            if row['CÓDIGO'] == sel_cod: return ['background-color: #1E3A8A; font-weight: bold; color: #FFFFFF; font-size: 16px;'] * len(row)
                            return zebra_base(row)
                            
                        st.dataframe(
                            df_breakdown.style.apply(style_breakdown, axis=1).format({
                                '% RENDIMIENTO': lambda x: formato_europeo(x, 2, " %"), 'PRECIO APLICADO': lambda x: formato_europeo(x, 3, " €"),
                                'COSTE DESPIECE': lambda x: formato_europeo(x, 3, " €"), 'COSTE CONG.': lambda x: formato_europeo(x, 3, " €"),
                                'APORTACIÓN A CP': lambda x: formato_europeo(x, 4, " €/kg")
                            }), use_container_width=True, hide_index=True
                        )
                    else: st.info("Este artículo no está registrado como 'Principal' ni como 'Equivalencia'.")
        else: st.info("ℹ️ Este cliente solo ha comprado artículos que no están mapeados.")

# --- PESTAÑA 3: PANEL EJECUTIVO CON FRAGMENTO DE ALTO RENDIMIENTO ---
with tab3:
    @st.fragment
    def renderizar_panel_ejecutivo():
        cliente_sel_final = None 
        
        if err_v: st.error(err_v)
        elif not df_proc_global.empty:
            with st.expander("🎛️ Panel de Filtros de Análisis y KPIs (Cascada Activa)", expanded=True):
                col_f1, col_f2, col_f3 = st.columns([1.5, 1, 1])
                
                all_clients = sorted(df_proc_global['Cliente'].unique()) if not df_proc_global.empty else []
                buscador = col_f1.text_input("🔍 Auto-seleccionar cadena (Ej: Escribe 'COVI' o 'DIA')")
                clientes_preseleccionados = [c for c in all_clients if buscador.lower() in c.lower()] if buscador else []
                sel_clients = col_f1.multiselect("🏢 Clientes (Selecciona uno o varios)", all_clients, default=clientes_preseleccionados)
                agrupar_cadena = col_f1.checkbox("🔗 Agrupar clientes seleccionados como una 'Cadena'", value=bool(buscador))
                
                df_proc_temp_fams = df_proc_global[df_proc_global['Familia'] != 'Sin clasificar'].copy()
                if sel_clients:
                    df_proc_temp_fams = df_proc_temp_fams[df_proc_temp_fams['Cliente'].isin(sel_clients)]
                fams_disp = sorted(df_proc_temp_fams['Familia'].unique()) if not df_proc_temp_fams.empty else []
                sel_fams = col_f2.multiselect("📂 Familias", fams_disp)
                
                df_proc_temp_arts = df_proc_temp_fams.copy()
                if sel_fams:
                    df_proc_temp_arts = df_proc_temp_arts[df_proc_temp_arts['Familia'].isin(sel_fams)]
                arts_disp = sorted(df_proc_temp_arts['Artículo'].unique()) if not df_proc_temp_arts.empty else []
                sel_arts = col_f3.multiselect("🏷️ Artículos", arts_disp)
                
                st.markdown("---")
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    vol_op = st.selectbox("📊 Filtro por Volumen Físico (kg)", ["-- Desactivado --", "Mayor o igual a (>=)", "Menor o igual a (<=)", "Entre"])
                    if vol_op == "Mayor o igual a (>=)": min_kilos = st.number_input("Mínimo (kg)", value=1000, step=100)
                    elif vol_op == "Menor o igual a (<=)": max_kilos = st.number_input("Máximo (kg)", value=5000, step=100)
                    elif vol_op == "Entre":
                        c1, c2 = st.columns(2)
                        min_kilos = c1.number_input("Mínimo (kg)", value=1000, step=100)
                        max_kilos = c2.number_input("Máximo (kg)", value=5000, step=100)
                with col_n2:
                    ben_op = st.selectbox("💶 Filtro por Beneficio (€/kg CP)", ["-- Desactivado --", "Mayor o igual a (>=)", "Menor o igual a (<=)", "Entre"])
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
                df_cli = df_proc_kpi.groupby('Cliente').agg(
                    Kilos_Vendidos=('Kilos', 'sum'), Kilos_CP_Totales=('Kilos_CP', 'sum'), Precio_CP_Total=('Precio_CP_Total', 'sum')
                ).reset_index()
                
                df_cli['Precio_Medio_CP'] = np.where(df_cli['Kilos_CP_Totales'] > 0, df_cli['Precio_CP_Total'] / df_cli['Kilos_CP_Totales'], 0.0)
                
                def calc_vs_market(cliente):
                    df_c = df_proc_kpi[df_proc_kpi['Cliente'] == cliente]
                    extra = 0.0
                    for _, r in df_c.iterrows():
                        if r['Kilos_CP'] > 0: 
                            extra += (r['Precio_CP_Unitario'] - bench_familia.get(r['Familia'], 0.0)) * r['Kilos_CP']
                    return extra
                    
                df_cli['Vs_Mercado_Euros'] = df_cli['Cliente'].apply(calc_vs_market)
                df_cli['Beneficio_kg'] = np.where(df_cli['Kilos_CP_Totales']>0, df_cli['Vs_Mercado_Euros'] / df_cli['Kilos_CP_Totales'], 0.0)
                
                if vol_op == "Mayor o igual a (>=)": df_cli = df_cli[df_cli['Kilos_Vendidos'] >= min_kilos]
                elif vol_op == "Menor o igual a (<=)": df_cli = df_cli[df_cli['Kilos_Vendidos'] <= max_kilos]
                elif vol_op == "Entre": df_cli = df_cli[(df_cli['Kilos_Vendidos'] >= min_kilos) & (df_cli['Kilos_Vendidos'] <= max_kilos)]

                if ben_op == "Mayor o igual a (>=)": df_cli = df_cli[df_cli['Beneficio_kg'] >= min_ben]
                elif ben_op == "Menor o igual a (<=)": df_cli = df_cli[df_cli['Beneficio_kg'] <= max_ben]
                elif ben_op == "Entre": df_cli = df_cli[(df_cli['Beneficio_kg'] >= min_ben) & (df_cli['Beneficio_kg'] <= max_ben)]

                if df_cli.empty:
                    st.warning("No hay clientes que cumplan con los filtros numéricos establecidos.")
                else:
                    st.divider()
                    st.markdown("### 📊 Indicadores de Rendimiento")
                    
                    clientes_filtrados = df_cli['Cliente'].tolist()
                    df_proc_kpi_filtered = df_proc_kpi[df_proc_kpi['Cliente'].isin(clientes_filtrados)]
                    
                    kpi_kilos_cp_tot = df_cli['Kilos_CP_Totales'].sum()
                    kpi_kilos_fisicos_tot = df_cli['Kilos_Vendidos'].sum()
                    kpi_beneficio_abs = df_cli['Vs_Mercado_Euros'].sum()
                    kpi_beneficio_kg = kpi_beneficio_abs / kpi_kilos_cp_tot if kpi_kilos_cp_tot > 0 else 0.0
                    kpi_cp_medio = df_cli['Precio_CP_Total'].sum() / kpi_kilos_cp_tot if kpi_kilos_cp_tot > 0 else 0.0
                    
                    ingreso_exw_tot = (df_proc_kpi_filtered['Kilos'] * df_proc_kpi_filtered['Precio EXW']).sum()
                    kpi_exw_medio = ingreso_exw_tot / kpi_kilos_fisicos_tot if kpi_kilos_fisicos_tot > 0 else 0.0
                    
                    if abs(kpi_beneficio_kg) < 0.0001: kpi_beneficio_kg = 0.0
                    if abs(kpi_beneficio_abs) < 0.001: kpi_beneficio_abs = 0.0
                    
                    k1, k2, k3, k4 = st.columns(4)
                    k1.markdown(render_kpi("Precio Medio EXW", formato_europeo(kpi_exw_medio, 3, ' €')), unsafe_allow_html=True)
                    k2.markdown(render_kpi("Precio Medio a CP", formato_europeo(kpi_cp_medio, 4, ' €')), unsafe_allow_html=True)
                    color_ben_kg = "#4ADE80" if kpi_beneficio_kg > 0 else ("#F87171" if kpi_beneficio_kg < 0 else "#94A3B8")
                    k3.markdown(render_kpi("Beneficio €/kg CP", f"{('+' if kpi_beneficio_kg>0 else '')}{formato_europeo(kpi_beneficio_kg, 4, ' €/kg')}", color_ben_kg), unsafe_allow_html=True)
                    color_ben_abs = "#4ADE80" if kpi_beneficio_abs > 0 else ("#F87171" if kpi_beneficio_abs < 0 else "#94A3B8")
                    k4.markdown(render_kpi("Beneficio Absoluto (€)", f"{('+' if kpi_beneficio_abs>0 else '')}{formato_europeo(kpi_beneficio_abs, 2, ' €')}", color_ben_abs), unsafe_allow_html=True)

                    df_cli['Kilos_Disp'] = df_cli['Kilos_Vendidos'].apply(lambda x: formato_europeo(x, 0, " kg"))
                    df_cli['Precio_Medio_CP_Disp'] = df_cli['Precio_Medio_CP'].apply(lambda x: formato_europeo(x, 4, " €/kg"))
                    df_cli['Beneficio_Abs_Disp'] = df_cli['Vs_Mercado_Euros'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €"))
                    df_cli['Beneficio_kg_Disp'] = df_cli['Beneficio_kg'].apply(lambda x: ("+" if x>0 else "") + formato_europeo(x, 4, " €/kg"))

                    st.divider()
                    st.subheader("🎯 Gráfico de rentabilidad de cliente")
                    
                    avg_k = df_cli['Kilos_Vendidos'].mean()
                    avg_b = df_cli['Beneficio_kg'].mean()
                    
                    punto_cliente = alt.selection_point(fields=['Cliente'], name='sel_cliente')
                    
                    base = alt.Chart(df_cli).mark_circle().encode(
                        x=alt.X('Kilos_Vendidos:Q', title='Volumen Físico Vendido (kg)', axis=alt.Axis(format=',.0f', labelExpr="replace(datum.label, ',', '.')")),
                        y=alt.Y('Beneficio_kg:Q', title='Beneficio €/kg CP', scale=alt.Scale(zero=False), axis=alt.Axis(format='.2f', labelExpr="replace(datum.label, '.', ',')")),
                        size=alt.Size('Precio_CP_Total:Q', legend=None),
                        color=alt.condition(
                            punto_cliente,
                            alt.Color('Beneficio_kg:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Beneficio €/kg', legend=alt.Legend(format=',.2f', labelExpr="replace(datum.label, '.', ',')")),
                            alt.value('lightgray')
                        ),
                        tooltip=[alt.Tooltip('Cliente:N', title='Cliente'), alt.Tooltip('Kilos_Disp:N', title='Volumen Físico'), alt.Tooltip('Precio_Medio_CP_Disp:N', title='Precio Medio a CP'), alt.Tooltip('Beneficio_kg_Disp:N', title='Beneficio €/kg CP'), alt.Tooltip('Beneficio_Abs_Disp:N', title='Beneficio Absoluto (€)')]
                    ).add_params(punto_cliente)
                    
                    rule_x = alt.Chart(pd.DataFrame({'x': [avg_k]})).mark_rule(color='gray', strokeDash=[5,5]).encode(x='x:Q')
                    rule_y = alt.Chart(pd.DataFrame({'y': [avg_b]})).mark_rule(color='gray', strokeDash=[5,5]).encode(y='y:Q')
                    
                    event_chart = st.altair_chart(base + rule_x + rule_y, use_container_width=True, on_select="rerun")
                    
                    st.subheader("🏆 Ranking Ejecutivo")
                    
                    def color_vs_market(val):
                        if val > 0: return 'background-color: #DCFCE7; color: #166534; font-weight: bold; font-size: 16px;'
                        if val < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold; font-size: 16px;'
                        return 'font-size: 16px;'
                    
                    df_rank_display = df_cli[['Cliente', 'Kilos_Vendidos', 'Precio_Medio_CP', 'Beneficio_kg', 'Vs_Mercado_Euros']].copy().reset_index(drop=True)
                    df_rank_display.rename(columns={'Kilos_Vendidos': 'Kilos Físicos', 'Precio_Medio_CP': 'Precio Medio a CP', 'Beneficio_kg': 'Beneficio €/kg CP', 'Vs_Mercado_Euros': 'Beneficio Absoluto (€)'}, inplace=True)
                    df_rank_display.columns = [str(c).upper() for c in df_rank_display.columns]

                    styled_rank = df_rank_display.style.apply(zebra_base, axis=1)
                    try: styled_rank = styled_rank.map(color_vs_market, subset=['BENEFICIO ABSOLUTO (€)'])
                    except AttributeError: styled_rank = styled_rank.applymap(color_vs_market, subset=['BENEFICIO ABSOLUTO (€)'])
                    
                    event_table = st.dataframe(
                        styled_rank.format({
                            'KILOS FÍSICOS': lambda x: formato_europeo(x, 0, " kg"), 'PRECIO MEDIO A CP': lambda x: formato_europeo(x, 4, " €/kg"),
                            'BENEFICIO €/KG CP': lambda x: ("+" if x>0 else "") + formato_europeo(x, 4, " €/kg"), 'BENEFICIO ABSOLUTO (€)': lambda x: ("+" if x>0 else "") + formato_europeo(x, 2, " €")
                        }), use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun"
                    )
                    
                    st.divider()
                    
                    if len(event_table.selection.rows) > 0:
                        cliente_sel_final = df_cli.iloc[event_table.selection.rows[0]]['Cliente']
                    elif hasattr(event_chart, 'selection') and 'sel_cliente' in event_chart.selection:
                        lista_sel = event_chart.selection['sel_cliente']
                        if len(lista_sel) > 0:
                            cliente_sel_final = lista_sel[0].get('Cliente')

                    if cliente_sel_final:
                        st.subheader(f"🔍 Análisis de Cesta: {cliente_sel_final}")
                        st.info("💡 Haz clic en una o **varias filas a la vez** para auditar y comparar sus recetas abajo.")
                        
                        df_zoom = df_proc_kpi[df_proc_kpi['Cliente'] == cliente_sel_final].groupby('Familia').agg(Kilos_Vendidos=('Kilos', 'sum'), Kilos_CP=('Kilos_CP', 'sum'), Precio_CP_Total=('Precio_CP_Total', 'sum')).reset_index()
                        df_zoom['Precio_CP_Cliente'] = np.where(df_zoom['Kilos_CP'] > 0, df_zoom['Precio_CP_Total'] / df_zoom['Kilos_CP'], 0.0)
                        df_zoom['Precio_CP_Mercado'] = df_zoom['Familia'].map(bench_familia)
                        df_zoom['Dif_Unitaria'] = df_zoom['Precio_CP_Cliente'] - df_zoom['Precio_CP_Mercado']
                        df_zoom['Extra_Generado'] = df_zoom['Dif_Unitaria'] * df_zoom['Kilos_CP'] 
                        
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
                            kilos_fis_fmt = formato_europeo(r['Kilos_Vendidos'], 0, " kg")
                            kilos_cp_fmt = formato_europeo(r['Kilos_CP'], 0, " kg")
                            extra_fmt = ("+" if r['Extra_Generado']>0 else "") + formato_europeo(r['Extra_Generado'], 2, " €")
                            
                            with st.expander(f"{icon} {r['Familia']} | Físico: {kilos_fis_fmt} (Equiv. {kilos_cp_fmt} CP) | Beneficio Absoluto: {extra_fmt}"):
                                col_m1, col_m2, col_m3 = st.columns(3)
                                col_m1.markdown(render_kpi("Precio a CP Cliente", formato_europeo(r['Precio_CP_Cliente'], 4, ' €/kg')), unsafe_allow_html=True)
                                col_m2.markdown(render_kpi("Precio a CP Mercado", formato_europeo(r['Precio_CP_Mercado'], 4, ' €/kg')), unsafe_allow_html=True)
                                dif_sign = "+" if r['Dif_Unitaria']>0 else ""
                                color_dif = "#4ADE80" if r['Dif_Unitaria'] > 0 else "#F87171"
                                col_m3.markdown(render_kpi("Beneficio €/kg CP", f"{dif_sign}{formato_europeo(r['Dif_Unitaria'], 4, ' €/kg')}", color_dif), unsafe_allow_html=True)
                                
                                df_arts = df_proc_kpi[(df_proc_kpi['Cliente'] == cliente_sel_final) & (df_proc_kpi['Familia'] == r['Familia'])].copy()
                                df_arts['Ingreso_EXW'] = df_arts['Kilos'] * df_arts['Precio EXW']
                                df_arts_grouped = df_arts.groupby(['Código', 'Artículo']).agg(
                                    Kilos=('Kilos', 'sum'), Kilos_CP=('Kilos_CP', 'sum'), Ingreso_EXW=('Ingreso_EXW', 'sum'), Precio_CP_Unitario=('Precio_CP_Unitario', 'first')
                                ).reset_index()
                                df_arts_grouped['Precio EXW Medio'] = np.where(df_arts_grouped['Kilos'] > 0, df_arts_grouped['Ingreso_EXW'] / df_arts_grouped['Kilos'], 0)
                                df_arts_grouped.drop(columns=['Ingreso_EXW'], inplace=True)
                                df_arts_grouped.rename(columns={'Precio_CP_Unitario': 'Precio a CP'}, inplace=True)
                                df_arts_grouped.columns = [str(c).upper() for c in df_arts_grouped.columns]
                                
                                styled_arts = df_arts_grouped.style.apply(zebra_base, axis=1).format({
                                    'KILOS': lambda x: formato_europeo(x, 0, " kg"), 'KILOS_CP': lambda x: formato_europeo(x, 0, " kg"),
                                    'PRECIO EXW MEDIO': lambda x: formato_europeo(x, 3, " €"), 'PRECIO A CP': lambda x: formato_europeo(x, 4, " €/kg")
                                })

                                event_arts = st.dataframe(styled_arts, use_container_width=True, hide_index=True, selection_mode="multi-row", on_select="rerun", key=f"arts_{cliente_sel_final}_{r['Familia']}")
                                
                                if len(event_arts.selection.rows) > 0:
                                    for row_idx in event_arts.selection.rows:
                                        selected_code = str(df_arts_grouped.iloc[row_idx]['CÓDIGO'])
                                        selected_exw = float(df_arts_grouped.iloc[row_idx]['PRECIO EXW MEDIO'])
                                        selected_name = str(df_arts_grouped.iloc[row_idx]['ARTÍCULO'])
                                        
                                        st.markdown(f"###### 🔎 Trazabilidad del Escandallo: {selected_code} - {selected_name}")
                                        
                                        esc_id = None; cod_principal_teorico = None; es_equivalencia = False
                                        if selected_code in mapa_escandallos:
                                            esc_id = mapa_escandallos[selected_code]; cod_principal_teorico = selected_code
                                        elif selected_code in mapa_equivalencias:
                                            esc_id = mapa_equivalencias[selected_code][0]; cod_principal_teorico = mapa_equivalencias[selected_code][1]; es_equivalencia = True
                                        
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
                                                    if cod_item in client_avg_active.get(cliente_sel_final, {}):
                                                        precio_aplicado = client_avg_active[cliente_sel_final][cod_item]; origen = "🥇 Venta a este cliente (P1)"
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
                                            df_breakdown.columns = [str(c).upper() for c in df_breakdown.columns]

                                            def style_breakdown(row):
                                                if row['CÓDIGO'] == selected_code: return ['background-color: #1E3A8A; font-weight: bold; color: #FFFFFF; font-size: 16px;'] * len(row)
                                                return zebra_base(row)
                                                
                                            st.dataframe(
                                                df_breakdown.style.apply(style_breakdown, axis=1).format({
                                                    '% RENDIMIENTO': lambda x: formato_europeo(x, 2, " %"), 'PRECIO APLICADO': lambda x: formato_europeo(x, 3, " €"),
                                                    'COSTE DESPIECE': lambda x: formato_europeo(x, 3, " €"), 'COSTE CONG.': lambda x: formato_europeo(x, 3, " €"),
                                                    'APORTACIÓN A CP': lambda x: formato_europeo(x, 4, " €/kg")
                                                }), use_container_width=True, hide_index=True
                                            )
                                        else: st.info("Este artículo no está registrado como 'Principal' ni como 'Equivalencia'.")
            
            st.divider()
            
            df_sobrantes = pd.DataFrame()
            if cliente_sel_final: 
                df_sobrantes = df_proc[(df_proc['Cliente'] == cliente_sel_final) & (df_proc['Familia'] == 'Sin clasificar')]
            elif sel_clients and agrupar_cadena: 
                df_sobrantes = df_proc[(df_proc['Cliente'] == nombre_grupo) & (df_proc['Familia'] == 'Sin clasificar')]
            else: 
                df_sobrantes = df_proc[(df_proc['Cliente'].isin(sel_clients if sel_clients else all_clients)) & (df_proc['Familia'] == 'Sin clasificar')]
            
            if not df_sobrantes.empty:
                with st.expander(f"⚠️ Artículos 'Sin clasificar' ({len(df_sobrantes)}) - Excedente real post-consumo CP"):
                    st.warning("Estos son los artículos (o restos de kilos) que el cliente compró pero que NO han sido consumidos por la receta de ningún artículo principal.")
                    df_sob_disp = df_sobrantes[['Código', 'Artículo', 'Cliente', 'Kilos', 'Precio EXW']].reset_index(drop=True)
                    df_sob_disp.columns = [str(c).upper() for c in df_sob_disp.columns]
                    
                    st.dataframe(
                        df_sob_disp.style.apply(zebra_base, axis=1).format({
                            'KILOS': lambda x: formato_europeo(x, 2, " kg"), 'PRECIO EXW': lambda x: formato_europeo(x, 3, " €")
                        }), use_container_width=True, hide_index=True
                    )

    renderizar_panel_ejecutivo()
