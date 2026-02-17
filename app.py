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

# --- 5. FUNCIONES DE APOYO ---
def registrar_estadistica(evento, detalle):
    try:
        est_sheet = spreadsheet.worksheet("Estadisticas")
        fecha = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        est_sheet.append_row([fecha, evento, detalle, "Web"], value_input_option='USER_ENTERED')
    except: pass

# --- 6. BARRA LATERAL (LOGO, TASA Y LOGIN) ---
with st.sidebar:
    # --- EL LOGO ENCIMA DE LA TASA ---
    logo_url = "https://i.ibb.co/4wrgcH2N/Gemini-Generated-Image-gtozd3gtozd3gtoz.png" 
    st.image(logo_url, use_container_width=True)
    
    # --- TASA BCV ---
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

# --- PERFIL: INVITADO (CONTENIDO PRINCIPAL) ---
if st.session_state["perfil"] == "Invitado":
    # Mantenemos tus estilos pero mejoramos la visual de la tarjeta
    st.markdown("""
        <style>
        .product-card {
            background: white; padding: 12px; border-radius: 15px;
            border: 1px solid #f0f0f0; text-align: center;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.03); height: 280px;
            margin-bottom: 10px;
        }
        .img-contain {
            width: 100%; height: 130px; object-fit: contain;
            margin-bottom: 10px; background: white;
        }
        .price-style { color: #001F3F; font-size: 20px; font-weight: bold; margin-bottom: 0px; }
        .bcv-style { color: #FF8C00; font-size: 12px; font-weight: bold; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Vitrina Maracaibo")
    
    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            # 1. BUSCADOR
            query = st.text_input("", placeholder="🔎 ¿Qué buscáis hoy, primo?", key="main_search")
            
            df_filtered = df.copy()
            if query:
                df_filtered = df_filtered[df_filtered['Producto'].astype(str).str.contains(query, case=False, na=False)]

            # 2. PRODUCTOS TOP (CINTA HORIZONTAL)
            if 'Prioridad' in df_filtered.columns and not query:
                df_filtered['Prioridad'] = pd.to_numeric(df_filtered['Prioridad'], errors='coerce').fillna(0)
                top_items = df_filtered[df_filtered['Prioridad'] > 0].sort_values(by='Prioridad', ascending=False)
                
                if not top_items.empty:
                    st.markdown("### 🔥 Destacados")
                    cols_top = st.columns([1]*len(top_items) + [4])
                    for i, (idx, row) in enumerate(top_items.iterrows()):
                        with cols_top[i]:
                            p_raw = str(row.get('Precio', '0')).replace(',', '.')
                            p_f = float(re.sub(r'[^\d.]', '', p_raw)) if p_raw else 0.0
                            
                            st.markdown(f'''
                                <div style="text-align: center; background: white; border-radius: 10px; border: 1px solid #eee; padding: 5px;">
                                    <img src="{row.get('Foto', '')}" style="width:100%; height:60px; object-fit:contain;">
                                    <div style="font-size:10px; font-weight:bold; color:#333; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{row['Producto']}</div>
                                    <div style="color:#001F3F; font-size:11px; font-weight:bold;">${p_f:.2f}</div>
                                </div>
                            ''', unsafe_allow_html=True)
                            
                            if st.button("🔍", key=f"top_{idx}", use_container_width=True):
                                @st.dialog(f"{row['Producto']}")
                                def detalle_top(item, precio):
                                    st.image(item.get('Foto', ""), use_container_width=True)
                                    c1, c2 = st.columns(2)
                                    c1.metric("Precio USD", f"${precio:.2f}")
                                    c2.metric("Precio BCV", f"{(precio * tasa_bcv):.2f} Bs.")
                                    st.write(f"🏠 **Tienda:** {item['Tienda']}")
                                    tel = str(item.get('Telefono', '584127522988')).replace('+', '').replace(' ', '').strip()
                                    msg = urllib.parse.quote(f"Hola {item['Tienda']}, quiero el destacado *{item['Producto']}*.")
                                    st.link_button("🛒 Pedir Ahora", f"https://wa.me/{tel}?text={msg}", use_container_width=True)
                                detalle_top(row, p_f)
                    st.divider()

            # 3. MATRIZ GENERAL (3 Columnas)
            st.subheader("Catálogo de Productos")
            df_display = df_filtered.reset_index(drop=True)
            cols = st.columns(3)
            
            for idx, row in df_display.iterrows():
                with cols[idx % 3]:
                    try:
                        p_raw_m = str(row.get('Precio', '0')).replace(',', '.')
                        p_usd = float(re.sub(r'[^\d.]', '', p_raw_m)) if p_raw_m else 0.0
                    except: p_usd = 0.0
                    
                    st.markdown(f"""
                        <div class="product-card">
                            <img src="{row.get('Foto', '')}" class="img-contain">
                            <div style="font-size:14px; font-weight:bold; color:#222; height:35px; overflow:hidden;">{row['Producto']}</div>
                            <div class="price-style">${p_usd:.2f}</div>
                            <div class="bcv-style">{(p_usd * tasa_bcv):.2f} Bs.</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    tel = str(row.get('Telefono', '584127522988')).replace('+', '').replace(' ', '').strip()
                    msg = urllib.parse.quote(f"Hola {row['Tienda']}, quiero el producto *{row['Producto']}* de Píllalo.")
                    st.markdown(f"""
                        <a href="https://wa.me/{tel}?text={msg}" target="_blank" style="text-decoration:none;">
                            <div style="background-color:#25D366; color:white; padding:10px; text-align:center; border-radius:10px; font-weight:bold; font-size:13px; margin-top:-5px; margin-bottom:25px;">
                                🛒 Pedir
                            </div>
                        </a>
                    """, unsafe_allow_html=True)

# --- PERFIL: EMPRESA (CON MARKETING Y PLANES RESTAURADOS) ---
elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Portal: {tienda_user}")
    
    # Restauramos las 4 pestañas clave
    t1, t2, t3, t4 = st.tabs(["📦 Inventario", "📈 Marketing", "💎 Mi Plan", "📤 Subir Excel"])

    with t1:
        if sheet:
            df_full = pd.DataFrame(sheet.get_all_records())
            df_full['fila'] = df_full.index + 2
            mis_productos = df_full[df_full['Tienda'] == tienda_user]
            
            if not mis_productos.empty:
                st.dataframe(mis_productos.drop(columns=['fila']), use_container_width=True)
                st.divider()
                st.subheader("✏️ Editar Precio Rápido")
                
                p_sel = st.selectbox("Selecciona producto:", mis_productos['Producto'].unique(), key="sel_prod_empresa")
                row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
                
                # Respetando punto para decimales
                p_raw = str(row_p.get('Precio', '0.00')).replace(',', '.')
                p_limpio = re.sub(r'[^\d.]', '', p_raw)
                try: v_ini = float(p_limpio) if p_limpio else 0.00
                except: v_ini = 0.00
                
                nuevo_p = st.number_input("Nuevo Precio ($):", value=v_ini, step=0.01, key="num_prec_empresa")
                
                if st.button("Actualizar Precio Ahora", key="btn_upd_empresa"):
                    sheet.update_cell(int(row_p['fila']), 4, str(nuevo_p).replace(',', '.'))
                    st.success(f"¡Actualizado a ${nuevo_p:.2f}!")
                    st.rerun()
            else:
                st.info("Aún no tienes productos en vitrina.")

    with t2:
        st.subheader("📊 Rendimiento de Ventas")
        c1, c2 = st.columns(2)
        # Datos simulados basados en la tienda
        c1.metric("Vistas de Perfil", "1,240", "+12%")
        c2.metric("Clicks a WhatsApp", "85", "+5%")
        
        st.markdown("---")
        st.subheader("📢 Ofertas Relámpago")
        st.write("Configura un banner de oferta que aparecerá en la parte superior de la vitrina.")
        promo_txt = st.text_input("Texto de la oferta", placeholder="Ej: ¡20% de descuento en toda la tienda!")
        if st.button("Activar Promoción"):
            st.success("¡Promoción enviada a revisión!")

    with t3:
        st.subheader("💎 Estado de la Suscripción")
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            st.info("🛡️ Tu plan actual es: **PRO COMERCIO**")
            st.write("**Beneficios activos:**")
            st.write("- ✅ Productos ilimitados")
            st.write("- ✅ Botón de WhatsApp directo")
            st.write("- ✅ Estadísticas en tiempo real")
            st.write("- ✅ Soporte prioritario")
        
        with col_p2:
            st.markdown("### Próximo Pago")
            st.error("15 de Marzo")
            st.button("Pagar Suscripción")

   with t4:
        st.subheader("🖼️ Gestor de Imágenes y Carga Masiva")
        
        # --- CONFIGURACIÓN API IMGBB ---
        # Pegá aquí tu API Key de ImgBB
        IMGBB_API_KEY = "1f2081c8821957a63c9a0c0df237fdba" 

        # --- SUBIDOR DE FOTOS REAL ---
        with st.expander("📸 PASO 1: Subir fotos y obtener enlaces directos"):
            st.write("Subí la foto para obtener el link que pondrás en el Excel.")
            img_file = st.file_uploader("Selecciona una imagen", type=['png', 'jpg', 'jpeg'], key="img_uploader")
            
            if img_file:
                if st.button("Generar Enlace"):
                    with st.spinner("Subiendo a la nube de Píllalo..."):
                        try:
                            # Preparar la imagen para la API
                            url = "https://api.imgbb.com/1/upload"
                            payload = {
                                "key": IMGBB_API_KEY,
                            }
                            files = {
                                "image": img_file.getvalue(),
                            }
                            response = requests.post(url, payload, files=files)
                            data = response.json()
                            
                            if data["status"] == 200:
                                # Este es el link directo al archivo
                                direct_link = data["data"]["url"]
                                
                                st.image(img_file, width=150)
                                st.success("✅ ¡Imagen lista para el inventario!")
                                st.code(direct_link, language="text")
                                st.caption("Copiá este enlace y pegalo en la columna 'Foto' de tu Excel.")
                            else:
                                st.error("Error de ImgBB. Revisá tu API Key.")
                        except Exception as e:
                            st.error(f"Error de conexión: {e}")

        st.divider()

        # --- CARGA DE EXCEL ---
        st.write("### 📥 PASO 2: Subir archivo de Inventario")
        st.info("Asegurate de que tu Excel use puntos para los decimales (Ej: 2.15).")
        
        file = st.file_uploader("Archivo .xlsx", type=['xlsx'], key="uploader_excel")
        
        if file and st.button("🚀 Publicar en Vitrina", key="btn_pub_excel"):
            try:
                df_new = pd.read_excel(file)
                df_new['Tienda'] = tienda_user
                
                # REGLA DE ORO: Limpieza de precios automática (Comas por Puntos)
                if 'Precio' in df_new.columns:
                    df_new['Precio'] = df_new['Precio'].astype(str).str.replace(',', '.')
                
                # Subida a Sheets
                sheet.append_rows(df_new.values.tolist(), value_input_option='USER_ENTERED')
                st.success(f"¡Molleja! {len(df_new)} productos nuevos publicados.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al subir el Excel: {e}")

# --- PIE ---
st.divider()
st.caption(f"Píllalo 2026 | Tasa: {tasa_bcv:.2f} Bs.")