import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import urllib3

# Desactivar advertencias de certificados del BCV
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Píllalo | El Rayo del Ahorro", page_icon="⚡", layout="centered")

# --- ESTILO PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stTextInput { border-radius: 20px; }
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border-left: 5px solid #1E40AF;
    }
    .price-tag {
        color: #16a34a;
        font-weight: bold;
        font-size: 24px;
    }
    .bs-price {
        color: #64748b;
        font-size: 16px;
    }
    .store-info {
        color: #1e40af;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN TASA BCV ---
def obtener_tasa_bcv():
    try:
        url = "https://www.bcv.org.ve/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        tasa_dolar = soup.find("div", id="dolar").find("strong").text.strip()
        return float(tasa_dolar.replace(',', '.'))
    except:
        return 48.50 # Tasa de respaldo

@st.cache_data(ttl=3600)
def get_tasa_actualizada():
    return obtener_tasa_bcv()

TASA_BS = get_tasa_actualizada()

# --- CONEXIÓN GOOGLE SHEETS ---
@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        info_llaves = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info_llaves, scope)
        return gspread.authorize(creds)
    return None

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
    st.error(f"Error: {e}")
    df = pd.DataFrame()

# --- INTERFAZ DE USUARIO ---
st.markdown("<h1 style='text-align: center; color: #1E40AF;'>⚡ Píllalo</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b;'>¡El rayo del ahorro en Maracaibo! ⛈️</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067451.png", width=100)
    st.metric(label="Tasa BCV", value=f"{TASA_BS:.2f} Bs.")
    st.info("💡 Los precios se actualizan cada minuto.")

# Buscador
busqueda = st.text_input("", placeholder="🔍 ¿Qué buscáis hoy? (Harina, Café, Batería...)")

if not df.empty:
    # Filtrar resultados
    if busqueda:
        resultados = df[df['Producto'].str.contains(busqueda, case=False, na=False)]
    else:
        # Si no hay búsqueda, mostrar los más recientes arriba
        resultados = df.iloc[::-1].head(10)

    if not resultados.empty:
        for _, row in resultados.iterrows():
            # Crear la tarjeta visual
            with st.container():
                st.markdown(f"""
                <div class="product-card">
                    <span style='color: #64748b; font-size: 12px; text-transform: uppercase;'>{row.get('Categoria', 'General')}</span>
                    <h3 style='margin: 0; color: #0f172a;'>{row['Producto']}</h3>
                    <p class="store-info">🏪 {row['Tienda']} | 📍 {row['Zona']}</p>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <span class="price-tag">${row['Precio']}</span><br>
                            <span class="bs-price">≈ {float(row['Precio']) * TASA_BS:.2f} Bs.</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de WhatsApp
                link_ws = f"https://wa.me/{row['WhatsApp']}?text=Hola, vi el producto *{row['Producto']}* en Píllalo. ¿Sigue disponible?"
                st.link_button(f"📲 Contactar al vendedor", link_ws, use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning("No pillamos nada con ese nombre. ¡Intenta con otra palabra!")
else:
    st.warning("Aún no hay productos registrados. ¡Usa el bot para cargar el primero!")