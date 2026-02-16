import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import urllib3

# Desactivar advertencias de certificados (el BCV a veces tiene problemas con eso)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Píllalo | El Rayo del Ahorro", page_icon="⚡")

# --- FUNCIÓN PARA EL BCV (ESTO ES LO QUE FALTABA) ---
def obtener_tasa_bcv():
    try:
        url = "https://www.bcv.org.ve/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Intentamos conectar con el BCV
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscamos el valor del dólar en su tabla
        tasa_dolar = soup.find("div", id="dolar").find("strong").text.strip()
        tasa_limpia = float(tasa_dolar.replace(',', '.'))
        return tasa_limpia
    except Exception as e:
        # Si el BCV no responde, devolvemos una tasa fija para que la app no explote
        return 45.50

# --- FUNCIÓN PARA CONECTAR GOOGLE (NUBE O LOCAL) ---
@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        info_llaves = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llaves, scope)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
    return gspread.authorize(creds)

# --- CARGA DE DATOS ---
try:
    client = conectar_google()
    sheet = client.open("Pillalo_Data").sheet1
    
    @st.cache_data(ttl=60)
    def cargar_datos():
        data = sheet.get_all_records()
        return pd.DataFrame(data)

    df = cargar_datos()
except Exception as e:
    st.error(f"Error de conexión: {e}")
    df = pd.DataFrame()

# --- INTERFAZ ---
st.markdown("<h1 style='text-align: center; color: #1E40AF;'>⚡ Píllalo</h1>", unsafe_allow_html=True)
st.write("---")

# --- TASA DINÁMICA ---
@st.cache_data(ttl=3600)
def get_tasa_actualizada():
    return obtener_tasa_bcv()

TASA_BS = get_tasa_actualizada()

# Sidebar con la tasa
st.sidebar.metric(label="Tasa BCV hoy", value=f"{TASA_BS:.2f} Bs/USD") 

busqueda = st.text_input("🔍 ¿Qué buscáis hoy en Maracaibo?", placeholder="Ej: Harina, Batería, Aceite...")

if not df.empty:
    if busqueda:
        resultados = df[df['Producto'].str.contains(busqueda, case=False, na=False)]
    else:
        resultados = df.tail(10)

    if not resultados.empty:
        for _, row in resultados.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(row['Producto'])
                    st.caption(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")
                with col2:
                    st.markdown(f"### ${row['Precio']}")
                    # Aquí hacemos el cálculo con la tasa del BCV
                    st.caption(f"{float(row['Precio']) * TASA_BS:.2f} Bs.")
                
                link_ws = f"https://wa.me/{row['WhatsApp']}?text=Hola, lo vi en Píllalo"
                st.link_button("Contactar", link_ws)
                st.divider()
    else:
        st.warning("No pillamos nada con ese nombre.")
else:
    st.info("Esperando datos... Cargá algo desde el Bot de Telegram!")