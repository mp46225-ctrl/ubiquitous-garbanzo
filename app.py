import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import plotly.express as px
import json
import requests
from bs4 import BeautifulSoup

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Píllalo - Business Suite", layout="wide", page_icon="⚡")

# --- 2. TASA BCV AUTOMÁTICA (SCRAPING) ---
@st.cache_data(ttl=3600)
def obtener_tasa_bcv_oficial():
    try:
        url = "https://www.bcv.org.ve/"
        # verify=False para evitar problemas con certificados del estado
        response = requests.get(url, verify=False, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        tasa_usd = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
        return float(tasa_usd.replace(',', '.'))
    except Exception:
        return 54.50  # Tasa de respaldo

tasa_bcv = obtener_tasa_bcv_oficial()

# --- 3. CONEXIÓN SEGURA A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        creds_info = st.secrets["gcp_service_account"]
        if isinstance(creds_info, str):
            creds_info = json.loads(creds_info)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open("Pillalo_Data")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

spreadsheet = conectar_google_sheets()
sheet = spreadsheet.sheet1 if spreadsheet else None

# --- 4. GESTIÓN DE SESIÓN ---
if "logueado" not in st.session_state:
    st.session_state["logueado"] = False
    st.session_state["perfil"] = "Invitado"
    st.session_state["user_name"] = ""

# --- 5. FUNCIONES DE APOYO ---
def registrar_estadistica(evento, detalle):
    try:
        est_sheet = spreadsheet.worksheet("Estadisticas")
        fecha = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        est_sheet.append_row([fecha, evento, detalle, "Web"], value_input_option='USER_ENTERED')
    except: pass

# --- 6. BARRA LATERAL (LOGIN Y TASA) ---
with st.sidebar:
    st.title("⚡ Píllalo")
    st.metric("Tasa BCV Hoy", f"{tasa_bcv} Bs.")
    st.divider()
    
    if not st.session_state["logueado"]:
        st.subheader("🔑 Acceso")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if u == "admin" and p == "pilla_ceo":
                st.session_state.update({"logueado": True, "perfil": "Admin", "user_name": "Admin"})
                st.rerun()
            elif u == "empresa" and p == "pilla_socio":
                st.session_state.update({"logueado": True, "perfil": "Empresa", "user_name": "Empresa"})
                st.rerun()
            else: st.error("Error de acceso")
    else:
        st.write(f"Sesión: **{st.session_state['user_name']}**")
        if st.button("Cerrar Sesión"):
            st.session_state.update({"logueado": False, "perfil": "Invitado"})
            st.rerun()

# --- 7. LÓGICA DE PANTALLAS ---

# --- PERFIL: INVITADO ---
if st.session_state["perfil"] == "Invitado":
    st.title("🔍 Encuentra los mejores precios")
    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        zonas = df['Zona'].unique() if 'Zona' in df.columns else []
        zona_sel = st.multiselect("📍 Zona de Maracaibo:", zonas)
        if zona_sel: df = df[df['Zona'].isin(zona_sel)]
            
        for _, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 3])
                with c1:
                    foto = row.get('Foto', '')
                    if str(foto).startswith('http'):
                        st.image(foto, width=180)
                    else: st.image("https://via.placeholder.com/150?text=Sin+Foto", width=180)
                with c2:
                    st.markdown(f"### {row['Producto']}")
                    
                    # --- FILTRO DE SEGURIDAD PARA PRECIOS ---
                    try:
                        # Limpiamos el valor de cualquier cosa que no sea número o punto
                        valor_limpio = str(row.get('Precio', '0.00')).replace(',', '.')
                        p_usd = float(valor_limpio)
                    except ValueError:
                        p_usd = 0.00  # Si hay error (ej: una celda vacía), ponemos 0.00
                    
                    p_bs = p_usd * tasa_bcv
                    
                    # Mostramos con tu formato de punto decimal
                    st.markdown(f"## 💰 ${p_usd:.2f} | <span style='color:#00D1FF'>{p_bs:.2f} Bs.</span>", unsafe_allow_html=True)
                    st.write(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")

# --- PERFIL: ADMIN ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Dashboard CEO")
    st.write("Control total de la plataforma.")
    # Aquí puedes añadir gráficas de Plotly como en versiones anteriores

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    st.title("🏢 Portal Business")
    t1, t2, t3 = st.tabs(["📦 Mis Productos", "📤 Carga & Tutorial", "🔥 Marketing"])

    with t1:
        st.subheader("Tu Inventario")
        if sheet:
            df_e = pd.DataFrame(sheet.get_all_records())
            # Filtra por el nombre de la empresa para que no vean lo de otros
            mis_datos = df_e[df_e['Tienda'].str.upper() == st.session_state["user_name"].upper()]
            st.dataframe(mis_datos, use_container_width=True)

    with t2:
        st.subheader("🚀 Guía de Carga Rápida")
        st.info("Para que tus productos luzcan bien, usa el generador de enlaces de abajo.")
        
        # --- GENERADOR DE LINKS ---
        with st.expander("🖼️ GENERADOR DE LINKS PARA FOTOS (Haz clic aquí)"):
            st.write("1. Sube tu foto. 2. Copia el link. 3. Pégalo en el Excel.")
            foto_file = st.file_uploader("Elige imagen", type=['jpg','png','jpeg'])
            if foto_file and st.button("Generar Link"):
                # Reemplaza con tu API KEY de ImgBB
                api_key = "1f2081c8821957a63c9a0c0df237fdba" 
                res = requests.post("https://api.imgbb.com/1/upload", {"key": api_key}, files={"image": foto_file.getvalue()})
                if res.json()["success"]:
                    link = res.json()["data"]["url"]
                    st.success("Copia este link:")
                    st.code(link)
                else: st.error("Error al subir")

        st.divider()
        
        # --- CARGA EXCEL ---
        st.subheader("Cargar Plantilla")
        # Botón para descargar plantilla
        cols = ["Producto", "Tienda", "Zona", "Precio", "WhatsApp", "Categoria", "Pago", "Calificacion", "Foto"]
        df_p = pd.DataFrame([["Ejemplo", st.session_state["user_name"], "Norte", 1.0, "58412...", "Víveres", "Efectivo", 5, "link-foto"]], columns=cols)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as wr: df_p.to_excel(wr, index=False)
        st.download_button("📥 Descargar Plantilla", data=buf.getvalue(), file_name="plantilla_pillalo.xlsx")
        
        up = st.file_uploader("Sube tu archivo relleno", type=['xlsx'])
        if up and st.button("🚀 Publicar"):
            df_up = pd.read_excel(up)
            df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
            df_up['Fecha'] = datetime.now().strftime("%d/%m %I:%M %p")
            sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Productos publicados con éxito!")

    with t3:
        st.subheader("🚀 Impulsa tu Negocio")
        c1, c2 = st.columns(2)
        with c1:
            st.write("🔥 **Oferta Flash**")
            st.caption("Destaca un producto por 24h.")
            if st.button("Solicitar Flash"):
                st.toast("Enviado al Admin")
        with c2:
            st.write("💎 **Plan Premium**")
            st.caption("Aparece primero en las búsquedas.")
            if st.button("Ver Planes"):
                st.info("Contacto: 0412-PILLALO")

st.divider()
st.caption(f"Píllalo 2026 - Maracaibo | Tasa BCV: {tasa_bcv} Bs.")