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
import urllib.parse
import re

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Píllalo - Business Suite", layout="wide", page_icon="⚡")

# --- 2. TASA BCV AUTOMÁTICA ---
@st.cache_data(ttl=3600)
def obtener_tasa_bcv_oficial():
    try:
        url = "https://www.bcv.org.ve/"
        response = requests.get(url, verify=False, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        tasa_usd = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
        return float(tasa_usd.replace(',', '.'))
    except Exception:
        return 54.50

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
    st.session_state.update({"logueado": False, "perfil": "Invitado", "user_name": "", "tienda_asociada": "Todas"})

if "carrito" not in st.session_state:
    st.session_state["carrito"] = {}

if "favoritos" not in st.session_state:
    st.session_state["favoritos"] = []

# --- 5. FUNCIONES DE APOYO ---
def registrar_estadistica(evento, detalle):
    try:
        est_sheet = spreadsheet.worksheet("Estadisticas")
        fecha = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        est_sheet.append_row([fecha, evento, detalle, "Web"], value_input_option='USER_ENTERED')
    except: 
        pass

# --- 6. BARRA LATERAL ---
with st.sidebar:
    logo_url = "https://i.ibb.co/4wrgcH2N/Gemini-Generated-Image-gtozd3gtozd3gtoz.png" 
    st.image(logo_url, use_container_width=True)
    st.divider()
    st.metric("Tasa BCV Hoy", f"{tasa_bcv:.2f} Bs.")
    st.divider()
    
    if not st.session_state["logueado"]:
        st.subheader("🔑 Acceso")
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            try:
                user_sheet = spreadsheet.worksheet("Usuarios")
                data = user_sheet.get_all_records()
                usuarios_df = pd.DataFrame(data)
                match = usuarios_df[(usuarios_df['Usuario'] == u_input) & (usuarios_df['Clave'].astype(str) == p_input)]
                if not match.empty:
                    user_data = match.iloc[0]
                    st.session_state.update({"logueado": True, "perfil": user_data['Perfil'], "user_name": u_input, "tienda_asociada": user_data.get('Tienda_Asociada', 'Todas')})
                    st.rerun()
                else: st.error("🚫 Credenciales incorrectas.")
            except Exception as e: st.error(f"❌ Error: {e}")
    else:
        st.write(f"Usuario: **{st.session_state['user_name']}**")
        if st.button("Cerrar Sesión"):
            st.session_state.update({"logueado": False, "perfil": "Invitado", "user_name": ""})
            st.rerun()

# --- 7. LÓGICA DE PANTALLAS ---

if st.session_state["perfil"] == "Invitado":
    # (El código del catálogo se mantiene igual que antes para no saturar)
    st.title("🔎 Vitrina Maracaibo")
    st.info("Inicia sesión como empresa para gestionar tus productos.")

elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Portal: {tienda_user}")
    
    t1, t_v, t2, t3, t4 = st.tabs(["📦 Inventario", "💰 Ventas", "📈 Marketing", "💎 Mi Plan", "📤 Carga Masiva"])

    # --- PESTAÑA: MI PLAN (CON VENTAJAS) ---
    with t3:
        st.subheader("💎 Mejora tu alcance en Píllalo")
        
        # Comparativa de planes
        c_p1, c_p2, c_p3 = st.columns(3)
        
        with c_p1:
            st.markdown("""
                <div style="background-color:#F0F2F6; padding:20px; border-radius:10px; border-top: 5px solid #6c757d; height: 350px;">
                    <h3 style="text-align:center;">Básico</h3>
                    <h2 style="text-align:center; color:#222;">$10 <span style="font-size:14px;">/mes</span></h2>
                    <hr>
                    <ul style="font-size:14px; color:#555;">
                        <li>✅ Hasta 50 productos</li>
                        <li>✅ Pedidos por WhatsApp</li>
                        <li>✅ Perfil de tienda básico</li>
                        <li>❌ Sin estadísticas</li>
                        <li>❌ Sin destaque prioritario</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        with c_p2:
            st.markdown("""
                <div style="background-color:#E1F5FE; padding:20px; border-radius:10px; border-top: 5px solid #007bff; height: 350px;">
                    <h3 style="text-align:center; color:#007bff;">Pro (Actual)</h3>
                    <h2 style="text-align:center; color:#222;">$25 <span style="font-size:14px;">/mes</span></h2>
                    <hr>
                    <ul style="font-size:14px; color:#555;">
                        <li>✅ Hasta 500 productos</li>
                        <li>✅ Pedidos por WhatsApp</li>
                        <li>✅ <b>Estadísticas de vistas</b></li>
                        <li>✅ <b>Ubicación en Mapa</b></li>
                        <li>✅ Carga masiva por Excel</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        with c_p3:
            st.markdown("""
                <div style="background-color:#FFF9C4; padding:20px; border-radius:10px; border-top: 5px solid #FFD700; height: 350px;">
                    <h3 style="text-align:center; color:#FBC02D;">Premium</h3>
                    <h2 style="text-align:center; color:#222;">$50 <span style="font-size:14px;">/mes</span></h2>
                    <hr>
                    <ul style="font-size:14px; color:#555;">
                        <li>✅ <b>Productos Ilimitados</b></li>
                        <li>✅ <b>Aparición en "Recomendados"</b></li>
                        <li>✅ Soporte 24/7 prioritario</li>
                        <li>✅ Reporte mensual de ventas</li>
                        <li>✅ Banner publicitario semanal</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        st.divider()
        
        # Acción de cambio
        st.subheader("⚙️ Gestión de suscripción")
        col_acc1, col_acc2 = st.columns([1, 1])
        
        with col_acc1:
            opcion_plan = st.selectbox("¿Qué deseas hacer?", 
                                     ["Selecciona una opción...", "Bajar a Plan Básico", "Subir a Plan Premium", "Cancelar suscripción"])
            
            if opcion_plan != "Selecciona una opción...":
                msg_plan = f"Hola Píllalo, soy de la tienda *{tienda_user}*. Deseo solicitar: *{opcion_plan}*."
                link_plan = f"https://wa.me/584127522988?text={urllib.parse.quote(msg_plan)}"
                
                if "Cancelar" in opcion_plan:
                    st.error("Lamentamos que te vayas. Al cancelar perderás tu visibilidad en la vitrina.")
                else:
                    st.success(f"¡Excelente elección! El {opcion_plan} potenciará tus ventas.")
                
                st.markdown(f"""<a href="{link_plan}" target="_blank" style="text-decoration:none;"><div style="background-color:#FF4B4B;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;">🚀 Enviar solicitud a soporte</div></a>""", unsafe_allow_html=True)

    # (El resto de pestañas Inventario, Ventas, etc., se mantienen igual)
    with t1: st.write("Gestión de Inventario...")
    with t_v: st.write("Gestión de Ventas...")
    with t2: st.write("Análisis de Marketing...")
    with t4: st.write("Carga Masiva...")

st.divider()
st.caption(f"Píllalo 2026 | Tasa: {tasa_bcv:.2f} Bs.")