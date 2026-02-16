import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import urllib3

# --- CONFIGURACIÓN E INTERFAZ ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Píllalo | Catálogo de Ahorros", page_icon="⚡", layout="wide")

# Estilo CSS para tarjetas y diseño móvil
st.markdown("""
    <style>
    .main { background-color: #f3f4f6; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .product-card {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
    .category-badge {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .price-usd { color: #059669; font-size: 24px; font-weight: 800; }
    .price-bs { color: #6b7280; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE DATOS ---
def obtener_tasa_bcv():
    try:
        url = "https://www.bcv.org.ve/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        tasa = soup.find("div", id="dolar").find("strong").text.strip()
        return float(tasa.replace(',', '.'))
    except: return 48.50 # Tasa de seguridad

@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        return gspread.authorize(creds)
    return None

# --- CARGA Y PROCESAMIENTO ---
TASA_BCV = obtener_tasa_bcv()
client = conectar_google()

try:
    # Cargamos datos
    df = pd.DataFrame(client.open("Pillalo_Data").sheet1.get_all_records())
    # Asegurar que las columnas existen
    for col in ['Producto', 'Tienda', 'Zona', 'Precio', 'WhatsApp', 'Categoria', 'Pago', 'Calificacion', 'Foto']:
        if col not in df.columns: df[col] = "N/A"
except:
    df = pd.DataFrame()

# --- BARRA LATERAL (Sidebar) ---
with st.sidebar:
    st.markdown("<h1 style='color: #1E40AF;'>⚡ Píllalo</h1>", unsafe_allow_html=True)
    st.metric("Tasa BCV", f"{TASA_BCV:.2f} Bs.")
    st.divider()
    
    st.subheader("🔍 Filtros Avanzados")
    buscar = st.text_input("Buscar producto...", placeholder="Ej: Café")
    
    zonas = ["Todas"] + sorted(df['Zona'].unique().tolist()) if not df.empty else ["Todas"]
    zona_sel = st.selectbox("📍 Sector", zonas)
    
    precio_max = st.slider("💰 Presupuesto máx ($)", 0.0, 500.0, 100.0)

# --- CUERPO PRINCIPAL ---
if not df.empty:
    # 1. Menú de Categorías (Pestañas)
    todas_cats = ["Todos"] + sorted(df['Categoria'].unique().tolist())
    cat_seleccionada = st.tabs(todas_cats)
    
    # Lógica de filtrado
    for i, tab in enumerate(cat_seleccionada):
        with tab:
            categoria_actual = todas_cats[i]
            
            # Filtrar el DataFrame
            df_final = df.copy()
            if categoria_actual != "Todos":
                df_final = df_final[df_final['Categoria'] == categoria_actual]
            if buscar:
                df_final = df_final[df_final['Producto'].str.contains(buscar, case=False, na=False)]
            if zona_sel != "Todas":
                df_final = df_final[df_final['Zona'] == zona_sel]
            
            df_final = df_final[df_final['Precio'].astype(float) <= precio_max]
            
            # Mostrar Resultados en Grid
            if df_final.empty:
                st.info("No pillamos nada con esos filtros. ¡Prueba otra combinación!")
            else:
                # Ordenar por los más nuevos
                df_final = df_final.iloc[::-1]
                
                # Crear columnas para las tarjetas
                cols = st.columns([1, 1], gap="medium") # 2 columnas para móvil y PC
                
                for idx, row in enumerate(df_final.iterrows()):
                    with cols[idx % 2]:
                        # Contenedor de la tarjeta
                        st.markdown(f"""
                        <div class="product-card">
                            <img src="{row[1]['Foto'] if row[1]['Foto'] != 'N/A' else 'https://via.placeholder.com/300?text=Sin+Foto'}" 
                                 style="width:100%; height:180px; object-fit: cover; border-radius: 10px; margin-bottom:10px;">
                            <span class="category-badge">{row[1]['Categoria']}</span>
                            <h3 style="margin: 10px 0 5px 0; font-size: 18px;">{row[1]['Producto']}</h3>
                            <p style="color: #6b7280; font-size: 13px; margin: 0;">🏪 {row[1]['Tienda']}</p>