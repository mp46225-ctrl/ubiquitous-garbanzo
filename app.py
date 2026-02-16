import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import urllib3

# 1. CONFIGURACIÓN INICIAL (Siempre al principio)
st.set_page_config(page_title="Píllalo App", layout="wide")

# Inicializamos la sesión si no existe
if "logueado" not in st.session_state:
    st.session_state["logueado"] = False
    st.session_state["perfil"] = "Invitado"

# 2. FUNCIÓN DE LOGIN (En la barra lateral)
def login():
    with st.sidebar:
        st.title("🔑 Acceso")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar"):
            # Aquí puedes luego conectar con Google Sheets, por ahora usemos claves fijas:
            if user == "admin" and password == "pilla_ceo":
                st.session_state["logueado"] = True
                st.session_state["perfil"] = "Admin"
                st.rerun()
            elif user == "empresa" and password == "pilla_socio":
                st.session_state["logueado"] = True
                st.session_state["perfil"] = "Empresa"
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

# 3. LÓGICA DE NAVEGACIÓN
if not st.session_state["logueado"]:
    # --- VISTA PÚBLICA (Lo que ve el cliente) ---
    login() # Mostramos el formulario de login en el sidebar
    st.title("🔍 Píllalo - Ofertas del Día")
    
    # [PEGA AQUÍ TU CÓDIGO ACTUAL: El que carga el Excel y muestra las tarjetas de productos]
    st.info("Loguéate como empresa para subir inventario masivo.")

else:
    # --- VISTAS PRIVADAS ---
    perfil = st.session_state["perfil"]
    
    with st.sidebar:
        st.write(f"Conectado como: **{perfil}**")
        if st.button("Cerrar Sesión"):
            st.session_state["logueado"] = False
            st.session_state["perfil"] = "Invitado"
            st.rerun()

    if perfil == "Admin":
        st.title("👨‍✈️ Panel de Control CEO")
        # [PEGA AQUÍ EL CÓDIGO DE TUS GRÁFICAS Y ESTADÍSTICAS]
        st.write("Bienvenido al centro de mando.")

    elif perfil == "Empresa":
        st.title("🏢 Portal para Empresas")
        st.write("Desde aquí podrás subir tus archivos Excel pronto.")
        # [AQUÍ IRÁ EL FUTURO CARGADOR MASIVO]

# 4. FOOTER (Fuera de los if, se ve en todas las pantallas)
st.divider()
st.caption("Píllalo 2026 - El petróleo de la data en Maracaibo.")

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
    except: return 48.50 

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
    df = pd.DataFrame(client.open("Pillalo_Data").sheet1.get_all_records())
    for col in ['Producto', 'Tienda', 'Zona', 'Precio', 'WhatsApp', 'Categoria', 'Pago', 'Calificacion', 'Foto']:
        if col not in df.columns: df[col] = "N/A"
except:
    df = pd.DataFrame()

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h1 style='color: #1E40AF;'>⚡ Píllalo</h1>", unsafe_allow_html=True)
    st.metric("Tasa BCV", f"{TASA_BCV:.2f} Bs.")
    st.divider()
    st.subheader("🔍 Filtros")
    buscar = st.text_input("Buscar producto...", placeholder="Ej: Café")
    zonas = ["Todas"] + sorted(df['Zona'].unique().tolist()) if not df.empty else ["Todas"]
    zona_sel = st.selectbox("📍 Sector", zonas)
    precio_max = st.slider("💰 Presupuesto máx ($)", 0.0, 500.0, 100.0)

# --- CUERPO PRINCIPAL ---
if not df.empty:
    todas_cats = ["Todos"] + sorted(df['Categoria'].unique().tolist())
    tabs = st.tabs(todas_cats)
    
    for i, tab in enumerate(tabs):
        with tab:
            categoria_actual = todas_cats[i]
            df_final = df.copy()
            
            if categoria_actual != "Todos":
                df_final = df_final[df_final['Categoria'] == categoria_actual]
            if buscar:
                df_final = df_final[df_final['Producto'].str.contains(buscar, case=False, na=False)]
            if zona_sel != "Todas":
                df_final = df_final[df_final['Zona'] == zona_sel]
            
            df_final = df_final[df_final['Precio'].astype(float) <= precio_max]
            
            if df_final.empty:
                st.info("No pillamos nada con esos filtros.")
            else:
                df_final = df_final.iloc[::-1]
                cols = st.columns(2, gap="medium")
                
                for idx, (index_row, row) in enumerate(df_final.iterrows()):
                    with cols[idx % 2]:
                        foto_url = str(row['Foto']) if str(row['Foto']) != "N/A" and str(row['Foto']) != "" else "https://via.placeholder.com/300?text=Pillalo"
                        
                        # BLOQUE HTML CORREGIDO
                        st.markdown(f"""
                        <div class="product-card">
                            <img src="{foto_url}" style="width:100%; height:180px; object-fit: cover; border-radius: 10px; margin-bottom:10px;">
                            <span class="category-badge">{row['Categoria']}</span>
                            <h3 style="margin: 10px 0 5px 0; font-size: 18px;">{row['Producto']}</h3>
                            <p style="color: #6b7280; font-size: 13px; margin: 0;">🏪 {row['Tienda']} | 📍 {row['Zona']}</p>
                            <div style="margin: 15px 0;">
                                <span class="price-usd">${float(row['Precio']):.2f}</span>
                                <span class="price-bs">/ {float(row['Precio']) * TASA_BCV:.2f} Bs.</span>
                            </div>
                            <div style="font-size: 12px; color: #4b5563; margin-bottom: 10px;">
                                ⭐ {row['Calificacion']} | 💳 {row['Pago']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        msg = f"Hola! Vi el producto {row['Producto']} en Pillalo."
                        st.link_button(f"📲 Contactar", f"https://wa.me/{row['WhatsApp']}?text={msg}")
                        st.write("") 

else:
    st.warning("⚠️ No hay datos cargados aún.")