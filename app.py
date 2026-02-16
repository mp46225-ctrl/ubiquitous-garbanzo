import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import urllib3

# Configuración inicial
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Píllalo | El Rayo del Ahorro", page_icon="⚡", layout="wide")

# --- ESTILOS CSS MEJORADOS ---
st.markdown("""
    <style>
    .product-card {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
    }
    .badge-pago {
        background-color: #f1f5f9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        margin-right: 5px;
    }
    .rating-star { color: #f59e0b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO (BCV Y GOOGLE) ---
def obtener_tasa_bcv():
    try:
        url = "https://www.bcv.org.ve/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        tasa = soup.find("div", id="dolar").find("strong").text.strip()
        return float(tasa.replace(',', '.'))
    except: return 48.50

@st.cache_resource
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        return gspread.authorize(creds)
    return None

# --- CARGA DE DATOS ---
TASA_BS = obtener_tasa_bcv()
try:
    client = conectar_google()
    df = pd.DataFrame(client.open("Pillalo_Data").sheet1.get_all_records())
except:
    df = pd.DataFrame()

# --- INTERFAZ PRINCIPAL ---
st.title("⚡ Píllalo Maracaibo")

if not df.empty:
    # --- BARRA LATERAL (FILTROS) ---
    with st.sidebar:
        st.header("🔍 Filtros")
        
        # Filtro de Búsqueda
        buscar = st.text_input("¿Qué buscáis?", placeholder="Ej: Harina...")
        
        # Filtro por Zona
        zonas_disponibles = ["Todas"] + sorted(df['Zona'].unique().tolist())
        zona_sel = st.selectbox("📍 Por Zona", zonas_disponibles)
        
        # Filtro por Precio (Slider)
        precio_max = float(df['Precio'].max())
        rango_precio = st.slider("💰 Rango de Precio ($)", 0.0, precio_max, (0.0, precio_max))
        
        # Filtro por Calificación
        min_rating = st.slider("⭐ Calificación mínima", 1, 5, 1)

    # --- LÓGICA DE FILTRADO ---
    mask = (df['Precio'] >= rango_precio[0]) & (df['Precio'] <= rango_precio[1])
    
    if buscar:
        mask &= df['Producto'].str.contains(buscar, case=False, na=False)
    if zona_sel != "Todas":
        mask &= (df['Zona'] == zona_sel)
    if 'Calificacion' in df.columns:
        mask &= (df['Calificacion'] >= min_rating)
        
    df_filtrado = df[mask].iloc[::-1] # Mostrar más nuevos primero

    # --- MOSTRAR RESULTADOS ---
    st.write(f"Se pillaron **{len(df_filtrado)}** productos")
    
    # Grid de 2 columnas para que quepa más en pantalla
    cols = st.columns(2)
    for i, (_, row) in enumerate(df_filtrado.iterrows()):
        with cols[i % 2]:
            # Formatear calificación
            estrellas = "⭐" * int(row.get('Calificacion', 5))
            
            st.markdown(f"""
            <div class="product-card">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 14px; color: #1e40af; font-weight: bold;">{row['Tienda']}</span>
                    <span class="rating-star">{estrellas}</span>
                </div>
                <h3 style="margin: 5px 0;">{row['Producto']}</h3>
                <p style="color: #64748b; font-size: 13px; margin-bottom: 10px;">📍 {row['Zona']}</p>
                <div style="margin-bottom: 10px;">
                    <span class="badge-pago">💳 {row.get('Pago', 'Efectivo/Pago Móvil')}</span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 10px;">
                    <span style="font-size: 22px; font-weight: bold; color: #16a34a;">${row['Precio']}</span>
                    <span style="font-size: 14px; color: #94a3b8;">({row['Precio']*TASA_BS:.2f} Bs.)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link_ws = f"https://wa.me/{row['WhatsApp']}?text=Hola, vi *{row['Producto']}* en Píllalo."
            st.link_button(f"Preguntar en {row['Tienda']}", link_ws, use_container_width=True)
            st.write("")

else:
    st.info("Carga datos en el Excel para empezar.")