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

# --- 5. FUNCIONES DE APOYO ---
def registrar_estadistica(evento, detalle):
    try:
        est_sheet = spreadsheet.worksheet("Estadisticas")
        fecha = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        est_sheet.append_row([fecha, evento, detalle, "Web"], value_input_option='USER_ENTERED')
    except: pass

# --- 6. BARRA LATERAL (LOGO, TASA Y LOGIN) ---
with st.sidebar:
    logo_url = "https://i.ibb.co/4wrgcH2N/Gemini-Generated-Image-gtozd3gtozd3gtoz.png" 
    st.image(logo_url, use_container_width=True)
    
    st.divider()
    st.metric("Tasa BCV Hoy", f"{tasa_bcv:.2f} Bs.")
    st.caption("Píllalo, pedilo y listo! ⚡")
    st.divider()
    
    if not st.session_state["logueado"]:
        st.subheader("🔑 Acceso")
        u_input = st.text_input("Usuario")
        p_input = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar"):
            try:
                user_sheet = spreadsheet.worksheet("Usuarios")
                data = user_sheet.get_all_records()
                
                if not data:
                    st.error("❌ Hoja 'Usuarios' vacía.")
                else:
                    usuarios_df = pd.DataFrame(data)
                    columnas_necesarias = ['Usuario', 'Clave', 'Perfil']
                    if all(col in usuarios_df.columns for col in columnas_necesarias):
                        match = usuarios_df[(usuarios_df['Usuario'] == u_input) & (usuarios_df['Clave'].astype(str) == p_input)]
                        if not match.empty:
                            user_data = match.iloc[0]
                            st.session_state.update({
                                "logueado": True, 
                                "perfil": user_data['Perfil'], 
                                "user_name": u_input,
                                "tienda_asociada": user_data.get('Tienda_Asociada', 'Todas')
                            })
                            st.rerun()
                        else:
                            st.error("🚫 Credenciales incorrectas.")
                    else:
                        st.error(f"⚠️ Faltan columnas: {columnas_necesarias}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    else:
        st.write(f"Usuario: **{st.session_state['user_name']}**")
        st.write(f"Perfil: **{st.session_state['perfil']}**")
        if st.button("Cerrar Sesión"):
            st.session_state.update({"logueado": False, "perfil": "Invitado", "user_name": ""})
            st.rerun()

    st.divider()
    st.subheader("🆘 Soporte")
    mi_whatsapp = "584127522988"
    link_wa = f"https://wa.me/{mi_whatsapp}?text=Hola Píllalo, necesito soporte técnico."
    st.markdown(f"""<a href="{link_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:8px;font-weight:bold;">💬 WhatsApp Soporte</div></a>""", unsafe_allow_html=True)

# --- 7. LÓGICA DE PANTALLAS ---

# --- PERFIL: INVITADO (FAVORITOS, RATINGS Y 4 COLUMNAS) ---
if st.session_state["perfil"] == "Invitado":
    # Inicializar Carrito y Favoritos
    if "carrito" not in st.session_state: st.session_state["carrito"] = {}
    if "favoritos" not in st.session_state: st.session_state["favoritos"] = []

    st.markdown("""
        <style>
        .product-card {
            background: white; padding: 12px; border-radius: 12px;
            border: 1px solid #e0e0e0; text-align: left;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.05); height: 460px;
            margin-bottom: 15px; position: relative;
        }
        .img-contain {
            width: 100%; height: 110px; object-fit: contain;
            margin-bottom: 8px; background: #f9f9f9; border-radius: 8px;
        }
        .tit-prod { font-size: 14px; font-weight: bold; color: #222; height: 35px; overflow: hidden; line-height: 1.2; }
        .tienda-tag { font-size: 12px; color: #007bff; font-weight: bold; }
        .rating-star { color: #FFD700; font-size: 12px; margin: 5px 0; }
        .price-usd { color: #001F3F; font-size: 18px; font-weight: 900; margin-top: 5px; }
        .price-bs { color: #FF8C00; font-size: 12px; font-weight: bold; }
        .fecha-upd { font-size: 9px; color: #aaa; margin-top: 8px; border-top: 1px solid #eee; padding-top: 4px; }
        .fav-icon { position: absolute; top: 10px; right: 10px; color: #ff4b4b; cursor: pointer; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Vitrina Maracaibo")
    
    if sheet:
        try:
            raw_data = sheet.get_all_records()
            if not raw_data: st.stop()
            df = pd.DataFrame(raw_data)
            
            # Escudo de columnas (Rating y Zona)
            if 'Telefono' not in df.columns: df['Telefono'] = "584127522988"
            if 'Zona' not in df.columns: df['Zona'] = "Maracaibo"
            if 'Rating' not in df.columns: df['Rating'] = 5 # 5 estrellas por defecto
            if 'Actualizado' not in df.columns: df['Actualizado'] = datetime.now().strftime("%d/%m/%y")
        except: st.stop()

        # --- BUSCADOR Y PESTAÑAS DE NAVEGACIÓN ---
        query = st.text_input("", placeholder="🔎 ¿Qué buscáis hoy, primo?", key="main_search")
        tab_cat, tab_fav = st.tabs(["🛒 Catálogo General", "❤️ Mis Favoritos"])

        # Lógica del Carrito (Resumen expandible)
        if st.session_state["carrito"]:
            with st.sidebar.expander(f"🛒 Carrito ({len(st.session_state['carrito'])})", expanded=True):
                t_usd = 0
                for p, info in list(st.session_state["carrito"].items()):
                    t_usd += info['precio'] * info['cant']
                    st.write(f"**{p}** x{info['cant']}")
                st.write(f"**Total: ${t_usd:.2f}**")
                if st.button("🚀 Pedir por WA"):
                    # (Aquí va la lógica de envío que ya tenemos)
                    pass

        with tab_cat:
            df_filtered = df.copy()
            if query:
                df_filtered = df_filtered[df_filtered['Producto'].astype(str).str.contains(query, case=False, na=False)]
            
            # Matriz de 4 Columnas
            df_display = df_filtered.reset_index(drop=True)
            cols = st.columns(4)
            
            for idx, row in df_display.iterrows():
                with cols[idx % 4]:
                    p_usd = float(str(row.get('Precio', 0)).replace(',', '.'))
                    rating = int(row.get('Rating', 5))
                    stars = "⭐" * rating
                    es_fav = row['Producto'] in st.session_state["favoritos"]
                    
                    # HTML de la tarjeta
                    st.markdown(f"""
                        <div class="product-card">
                            <div style="text-align:right; font-size:18px;">{'❤️' if es_fav else '🤍'}</div>
                            <img src="{row.get('Foto', '')}" class="img-contain">
                            <div class="tit-prod">{row['Producto']}</div>
                            <div class="tienda-tag">🏪 {row['Tienda']}</div>
                            <div class="rating-star">{stars}</div>
                            <div class="price-usd">${p_usd:.2f}</div>
                            <div class="price-bs">≈ {(p_usd * tasa_bcv):.2f} Bs.</div>
                            <div class="fecha-upd">📍 {row.get('Zona')} | 🕒 {row.get('Actualizado')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Botonera de interacción
                    c1, c2 = st.columns(2)
                    if c1.button("❤️" if not es_fav else "💔", key=f"fav_{idx}"):
                        if row['Producto'] in st.session_state["favoritos"]:
                            st.session_state["favoritos"].remove(row['Producto'])
                        else:
                            st.session_state["favoritos"].append(row['Producto'])
                        st.rerun()
                        
                    if c2.button("➕", key=f"add_{idx}"):
                        p_nom = row['Producto']
                        if p_nom in st.session_state["carrito"]: st.session_state["carrito"][p_nom]['cant'] += 1
                        else: st.session_state["carrito"][p_nom] = {'precio': p_usd, 'tel': row['Telefono'], 'cant': 1}
                        st.toast(f"¡{p_nom} añadido!")

        with tab_fav:
            if not st.session_state["favoritos"]:
                st.info("No tenéis favoritos todavía. ¡Empezá a darle amor a los productos! ❤️")
            else:
                df_favs = df[df['Producto'].isin(st.session_state["favoritos"])]
                st.dataframe(df_favs[['Producto', 'Tienda', 'Precio']], use_container_width=True)

# --- PERFIL: EMPRESA  ---
elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Portal: {tienda_user}")
    
    t1, t2, t3, t4 = st.tabs(["📦 Inventario", "📈 Marketing", "💎 Mi Plan", "📤 Carga Masiva"])

    with t1:
        # Obtenemos datos para la tabla de inventario
        df_full = pd.DataFrame(sheet.get_all_records())
        df_full['fila'] = df_full.index + 2
        mis_productos = df_full[df_full['Tienda'] == tienda_user]

        with st.expander("➕ Cargar UN producto rápido (Sin Excel)"):
            with st.form("form_rapido"):
                nuevo_nombre = st.text_input("Nombre del Producto")
                nuevo_precio = st.number_input("Precio ($)", min_value=0.0, step=0.01)
                nueva_foto = st.text_input("Link de la Foto (Pestaña 4)")
                nueva_prioridad = st.selectbox("¿Es destacado?", [0, 1, 2, 3])
                
                if st.form_submit_button("🚀 Publicar en Vitrina"):
                    if nuevo_nombre and nueva_foto:
                        tel_tienda = mis_productos['Telefono'].iloc[0] if not mis_productos.empty else "58412"
                        nueva_fila = [nuevo_nombre, tienda_user, nueva_prioridad, str(nuevo_precio).replace(',', '.'), nueva_foto, tel_tienda]
                        sheet.append_row(nueva_fila, value_input_option='USER_ENTERED')
                        st.success(f"¡{nuevo_nombre} publicado!")
                        st.rerun()
        
        st.divider()
        if not mis_productos.empty:
            st.dataframe(mis_productos.drop(columns=['fila']), use_container_width=True)
            st.subheader("✏️ Editar Precio Rápido")
            p_sel = st.selectbox("Selecciona producto:", mis_productos['Producto'].unique())
            row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
            
            p_limpio = str(row_p.get('Precio', '0.00')).replace(',', '.')
            try: v_ini = float(p_limpio)
            except: v_ini = 0.0
            
            nuevo_p = st.number_input("Nuevo Precio ($):", value=v_ini, step=0.01)
            if st.button("Actualizar Precio Ahora"):
                sheet.update_cell(int(row_p['fila']), 4, str(nuevo_p).replace(',', '.'))
                st.success("¡Actualizado!")
                st.rerun()

    with t2:
        st.subheader("📊 Rendimiento")
        c1, c2 = st.columns(2)
        c1.metric("Vistas", "1,240", "+12%")
        c2.metric("WhatsApp", "85", "+5%")

    with t3:
        st.subheader("💎 Suscripción")
        st.info("🛡️ Plan: **PRO COMERCIO**")
        st.error("Próximo Pago: 15 de Marzo")

    with t4:
        st.subheader("🖼️ Gestor de Imágenes y Excel")
        IMGBB_API_KEY = "1f2081c8821957a63c9a0c0df237fdba" 

        with st.expander("📸 PASO 1: Subir fotos"):
            img_file = st.file_uploader("Elegí imagen", type=['png', 'jpg', 'jpeg'], key="up_img")
            if img_file and st.button("Generar Enlace"):
                res = requests.post("https://api.imgbb.com/1/upload", {"key": IMGBB_API_KEY}, files={"image": img_file.getvalue()})
                if res.json()["status"] == 200:
                    link = res.json()["data"]["url"]
                    st.code(link)
                    st.success("Copiá este link al Excel")

        st.divider()
        st.write("### 📥 PASO 2: Subir Excel")
        file = st.file_uploader("Archivo .xlsx", type=['xlsx'])
        if file and st.button("🚀 Publicar Todo"):
            df_new = pd.read_excel(file)
            df_new['Tienda'] = tienda_user
            if 'Precio' in df_new.columns:
                df_new['Precio'] = df_new['Precio'].astype(str).str.replace(',', '.')
            sheet.append_rows(df_new.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Cargado!")
            st.rerun()

st.divider()
st.caption(f"Píllalo 2026 | Tasa: {tasa_bcv:.2f} Bs.")