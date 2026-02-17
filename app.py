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

# --- PERFIL: INVITADO (DISEÑO COMPACTO INTEGRADO) ---
if st.session_state["perfil"] == "Invitado":
    if "carrito" not in st.session_state: st.session_state["carrito"] = {}
    if "favoritos" not in st.session_state: st.session_state["favoritos"] = []

    st.markdown("""
        <style>
        /* Tarjeta principal sin alto fijo */
        .product-card {
            background: white; padding: 12px; border-radius: 12px;
            border: 1px solid #eee; text-align: left;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.05); 
            margin-bottom: 5px; position: relative;
        }
        .img-contain {
            width: 100%; height: 100px; object-fit: contain;
            margin-bottom: 5px; background: #fdfdfd; border-radius: 8px;
        }
        .tit-prod { font-size: 13px; font-weight: bold; color: #222; height: 32px; overflow: hidden; line-height: 1.1; margin-bottom: 2px; }
        .tienda-tag { font-size: 11px; color: #007bff; font-weight: bold; margin-bottom: 0px; }
        .rating-star { color: #FFD700; font-size: 10px; margin: 2px 0; }
        .price-usd { color: #001F3F; font-size: 18px; font-weight: 900; margin-top: 2px; }
        .price-bs { color: #FF8C00; font-size: 11px; font-weight: bold; margin-bottom: 8px; }
        
        /* Fecha y Zona más pegadas */
        .fecha-upd { 
            font-size: 9px; color: #bbb; 
            padding-top: 5px; border-top: 1px solid #f9f9f9;
            display: flex; justify-content: space-between;
            margin-bottom: 10px;
        }

        /* Quitamos etiquetas de los inputs para ganar espacio */
        div[data-testid="stNumericInput"] label { display: none; }
        div[data-testid="stNumericInput"] { margin-top: -15px; }
        
        /* Ajuste de botones para que parezcan integrados */
        .stButton button { margin-top: -5px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Vitrina Maracaibo")
    
    if sheet:
        try:
            raw_data = sheet.get_all_records()
            df = pd.DataFrame(raw_data)
            # Escudo de columnas
            for col, val in {'Telefono': '584127522988', 'Zona': 'Maracaibo', 'Rating': 5, 'Actualizado': 'Hoy'}.items():
                if col not in df.columns: df[col] = val
        except:
            st.error("Error de datos")
            st.stop()

        # 1. BUSCADOR
        query = st.text_input("", placeholder="🔎 ¿Qué buscáis hoy, primo?", key="main_search")
        
        # 2. SECCIÓN 🔥 RECOMENDADOS
        df_filtered = df.copy()
        if query:
            df_filtered = df_filtered[df_filtered['Producto'].astype(str).str.contains(query, case=False, na=False)]

        if 'Prioridad' in df_filtered.columns and not query:
            df_filtered['Prioridad'] = pd.to_numeric(df_filtered['Prioridad'], errors='coerce').fillna(0)
            top_items = df_filtered[df_filtered['Prioridad'] > 0].sort_values(by='Prioridad', ascending=False)
            if not top_items.empty:
                st.markdown("### 🔥 Recomendados")
                cols_top = st.columns([1]*len(top_items) + [4])
                for i, (idx, row) in enumerate(top_items.iterrows()):
                    with cols_top[i]:
                        try:
                            p_f_t = float(re.sub(r'[^\d.,]', '', str(row.get('Precio', '0'))).replace(',', '.'))
                        except: p_f_t = 0.0
                        st.markdown(f'<div style="text-align:center;"><img src="{row.get("Foto","")}" style="height:50px; object-fit:contain;"><br><b style="font-size:10px;">${p_f_t:.2f}</b></div>', unsafe_allow_html=True)
                        if st.button("➕", key=f"top_{idx}", use_container_width=True):
                            pn = row['Producto']
                            if pn in st.session_state["carrito"]: st.session_state["carrito"][pn]['cant'] += 1
                            else: st.session_state["carrito"][pn] = {'precio': p_f_t, 'tel': row['Telefono'], 'cant': 1}
                            st.rerun()

        # 3. MATRIZ GENERAL (INTEGRADA)
        tab_cat, tab_fav = st.tabs(["🛒 Catálogo", "❤️ Favoritos"])
        
        with tab_cat:
            df_display = df_filtered.reset_index(drop=True)
            cols = st.columns(4)
            for idx, row in df_display.iterrows():
                with cols[idx % 4]:
                    # Limpieza de precio
                    try: p_usd = float(re.sub(r'[^\d.,]', '', str(row.get('Precio', '0'))).replace(',', '.'))
                    except: p_usd = 0.0
                    
                    stars = "⭐" * int(row.get('Rating', 5))
                    es_fav = row['Producto'] in st.session_state["favoritos"]
                    
                    # TODO EL CONTENIDO DENTRO DE LA TARJETA (incluyendo botones)
                    with st.container():
                        st.markdown(f"""
                            <div class="product-card">
                                <div style="text-align:right; font-size:14px;">{'❤️' if es_fav else '🤍'}</div>
                                <img src="{row.get('Foto', '')}" class="img-contain">
                                <div class="tienda-tag">🏪 {row['Tienda']}</div>
                                <div class="tit-prod">{row['Producto']}</div>
                                <div class="rating-star">{stars}</div>
                                <div class="price-usd">${p_usd:.2f}</div>
                                <div class="price-bs">≈ {(p_usd * tasa_bcv):.2f} Bs.</div>
                                <div class="fecha-upd">
                                    <span>📍 {row.get('Zona')}</span>
                                    <span>🕒 {row.get('Actualizado')}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Los botones ahora están justo debajo de la tarjeta en la misma columna
                        c_fav, c_qty, c_add = st.columns([0.7, 1.3, 1])
                        with c_fav:
                            if st.button("❤️" if not es_fav else "💔", key=f"f_{idx}"):
                                if es_fav: st.session_state["favoritos"].remove(row['Producto'])
                                else: st.session_state["favoritos"].append(row['Producto'])
                                st.rerun()
                        with c_qty:
                            qty = st.number_input("", 1, 50, 1, key=f"q_{idx}")
                        with c_add:
                            if st.button("🛒", key=f"a_{idx}"):
                                pn = row['Producto']
                                if pn in st.session_state["carrito"]: st.session_state["carrito"][pn]['cant'] += qty
                                else: st.session_state["carrito"][pn] = {'precio': p_usd, 'tel': row['Telefono'], 'cant': qty}
                                st.toast(f"¡{qty}x {pn}!")

        # 4. CARRITO EN SIDEBAR (Resumen)
        if st.session_state["carrito"]:
            with st.sidebar:
                st.subheader("🛒 Tu Carrito")
                total_c = sum(item['precio'] * item['cant'] for item in st.session_state["carrito"].values())
                for p, info in st.session_state["carrito"].items():
                    st.write(f"**{p}** x{info['cant']}")
                st.divider()
                st.write(f"**Total: ${total_c:.2f}**")

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