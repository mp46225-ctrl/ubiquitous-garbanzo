import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Píllalo | El Rayo del Ahorro", page_icon="⚡")

# --- FUNCIÓN PARA CONECTAR (NUBE O LOCAL) ---
@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Si estamos en la nube (Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        info_llaves = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llaves, scope)
    # Si estamos probando en la PC
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
        
    client = gspread.authorize(creds)
    return client

# --- CARGA DE DATOS ---
try:
    client = conectar_google()
    # Asegúrate de que este nombre sea EXACTO al de tu Google Sheet
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

# Tasa de cambio (puedes hacer que esto también se lea del Excel luego)
TASA_BS = 45.50 

busqueda = st.text_input("🔍 ¿Qué buscáis hoy en Maracaibo?", placeholder="Ej: Harina, Batería, Aceite...")

if not df.empty:
    # Filtrado
    if busqueda:
        resultados = df[df['Producto'].str.contains(busqueda, case=False, na=False)]
    else:
        resultados = df.head(10) # Mostrar los últimos 10 por defecto

    if not resultados.empty:
        for _, row in resultados.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(row['Producto'])
                    st.caption(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")
                with col2:
                    st.markdown(f"### ${row['Precio']}")
                    st.caption(f"{row['Precio'] * TASA_BS:.2f} Bs.")
                
                link_ws = f"https://wa.me/{row['WhatsApp']}?text=Hola, lo vi en Píllalo"
                st.link_button("Contactar", link_ws)
                st.divider()
    else:
        st.warning("No pillamos nada con ese nombre.")
else:
    st.info("Esperando datos... Cargá algo desde el Bot de Telegram para ver la magia.")