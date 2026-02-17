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

if st.session_state["perfil"] == "Invitado":
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
        # --- ESCUDO DE SEGURIDAD AL CARGAR DATOS ---
        try:
            raw_data = sheet.get_all_records()
            if not raw_data:
                st.warning("⚠️ La vitrina está vacía por ahora.")
                st.stop()
            df = pd.DataFrame(raw_data)
            
            # Validación de columnas básicas
            for col in ['Producto', 'Tienda', 'Precio', 'Foto', 'Telefono']:
                if col not in df.columns:
                    st.error(f"Falta la columna '{col}' en la base de datos.")
                    st.stop()
        except Exception:
            st.error("Error al conectar con la base de datos.")
            st.stop()

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
                                
                                # TICKET PARA DESTACADOS
                                tel = str(item.get('Telefono', '584127522988')).replace('+', '').replace(' ', '').strip()
                                fecha_t = datetime.now().strftime("%d/%m/%Y")
                                msg_t = (f"*📦 NUEVO PEDIDO - PÍLLALO* ⚡\n---\n📅 *Fecha:* {fecha_t}\n🛍️ *Producto:* {item['Producto']}\n"
                                         f"💰 *Precio:* ${precio:.2f}\n📉 *Tasa BCV:* {tasa_bcv:.2f} Bs.\n💸 *Total:* {(precio * tasa_bcv):.2f} Bs.\n---\n¿Está disponible?")
                                st.link_button("🛒 Pedir Ahora", f"https://wa.me/{tel}?text={urllib.parse.quote(msg_t)}", use_container_width=True)
                            detalle_top(row, p_f)
                st.divider()

        # 3. MATRIZ GENERAL (3 Columnas)
        st.subheader("🛒 Tu Pedido")
        # Mostrar resumen del carrito si tiene algo
        if st.session_state["carrito"]:
            with st.expander(f"📋 Ver mi pedido ({len(st.session_state['carrito'])} ítems)"):
                total_usd_carrito = 0
                for prod_name, info in list(st.session_state["carrito"].items()):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    subtotal = info['precio'] * info['cant']
                    total_usd_carrito += subtotal
                    c1.write(f"**{prod_name}**")
                    c2.write(f"{info['cant']}x")
                    if c3.button("❌", key=f"del_{prod_name}"):
                        del st.session_state["carrito"][prod_name]
                        st.rerun()
                
                st.divider()
                st.write(f"**Total Pedido: ${total_usd_carrito:.2f} ({total_usd_carrito * tasa_bcv:.2f} Bs.)**")
                
                # Botón Final para enviar todo el carrito
                if st.button("🚀 Enviar Pedido Completo por WhatsApp", use_container_width=True):
                    fecha_h = datetime.now().strftime("%d/%m/%Y")
                    detalle_items = ""
                    for p, info in st.session_state["carrito"].items():
                        detalle_items += f"- {info['cant']}x {p} (${info['precio']:.2f})\n"
                    
                    ticket_final = (
                        f"*📦 NUEVO PEDIDO MULTIPLE - PÍLLALO* ⚡\n"
                        f"------------------------------\n"
                        f"📅 *Fecha:* {fecha_h}\n"
                        f"{detalle_items}"
                        f"------------------------------\n"
                        f"💰 *TOTAL USD:* ${total_usd_carrito:.2f}\n"
                        f"📉 *TASA BCV:* {tasa_bcv:.2f} Bs.\n"
                        f"💸 *TOTAL BS:* {(total_usd_carrito * tasa_bcv):.2f} Bs.\n"
                        f"------------------------------\n"
                        f"¿Tienen disponibilidad de todo? 🌩️"
                    )
                    # Usamos el teléfono del primer producto para el ejemplo o uno fijo
                    tel_destino = list(st.session_state["carrito"].values())[0]['tel']
                    webbrowser.open(f"https://wa.me/{tel_destino}?text={urllib.parse.quote(ticket_final)}")

        st.divider()
        st.subheader("Catálogo de Productos")
        cols = st.columns(3)
        
        for idx, row in df_display.iterrows():
            with cols[idx % 3]:
                # ... (tu código de estilo de tarjeta aquí) ...
                
                # BOTÓN DE AÑADIR (Reemplaza al de Pedir Directo)
                if st.button(f"➕ Añadir", key=f"add_{idx}", use_container_width=True):
                    p_id = row['Producto']
                    if p_id in st.session_state["carrito"]:
                        st.session_state["carrito"][p_id]['cant'] += 1
                    else:
                        st.session_state["carrito"][p_id] = {
                            'precio': p_usd,
                            'tel': tel,
                            'cant': 1
                        }
                    st.toast(f"¡{p_id} añadido! 🛒")
                    st.rerun()

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