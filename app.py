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

# --- PERFIL: INVITADO ---
if st.session_state["perfil"] == "Invitado":
    st.markdown("""
        <style>
        .product-card {
            background: white; padding: 12px; border-radius: 15px;
            border: 1px solid #eee; text-align: left;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.02); margin-bottom: 5px;
        }
        .img-contain {
            width: 100%; height: 160px; object-fit: contain;
            margin-bottom: 10px; background: #ffffff; border-radius: 10px;
        }
        .tit-prod { font-size: 14px; font-weight: bold; color: #222; height: 35px; overflow: hidden; line-height: 1.2; }
        .tienda-tag { font-size: 11px; color: #007bff; font-weight: bold; }
        .price-usd { color: #001F3F; font-size: 19px; font-weight: 900; margin-top: 5px; }
        .price-bs { color: #FF8C00; font-size: 12px; font-weight: bold; margin-bottom: 8px; }
        .fecha-upd { 
            font-size: 9px; color: #bbb; padding-top: 8px; 
            border-top: 1px solid #f9f9f9; display: flex; justify-content: space-between;
            margin-bottom: 10px;
        }
        div[data-testid="stNumericInput"] label { display: none; }
        div[data-testid="stNumericInput"] { margin-top: -15px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔎 Vitrina Maracaibo")

    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            for col, val in {'Telefono': '584127522988', 'Zona': 'Maracaibo', 'Rating': 5, 'Actualizado': 'Hoy', 'Prioridad': 0}.items():
                if col not in df.columns: df[col] = val
        except:
            st.error("Error cargando base de datos.")
            st.stop()

        # 1. BUSCADOR
        query = st.text_input("", placeholder="🔎 ¿Qué buscáis hoy, primo?", key="main_search")

        # 2. 🔥 RECOMENDADOS
        if not query:
            df['Prioridad'] = pd.to_numeric(df['Prioridad'], errors='coerce').fillna(0)
            top_items = df[df['Prioridad'] > 0].sort_values(by='Prioridad', ascending=False).head(5)
            if not top_items.empty:
                st.subheader("🔥 Recomendados")
                c_top = st.columns(len(top_items))
                for i, (idx, row) in enumerate(top_items.iterrows()):
                    with c_top[i]:
                        try: p_f_t = float(re.sub(r'[^\d.,]', '', str(row.get('Precio', '0'))).replace(',', '.'))
                        except: p_f_t = 0.0
                        st.markdown(f'''
                            <div style="text-align: center; background: white; border-radius: 12px; border: 1px solid #eee; padding: 8px;">
                                <img src="{row.get('Foto', '')}" style="width:100%; height:80px; object-fit:contain;">
                                <div style="color:#001F3F; font-size:12px; font-weight:bold;">${p_f_t:.2f}</div>
                            </div>
                        ''', unsafe_allow_html=True)
                        if st.button("➕", key=f"t_add_{idx}", use_container_width=True):
                            pn = row['Producto']
                            if pn in st.session_state["carrito"]: st.session_state["carrito"][pn]['cant'] += 1
                            else: st.session_state["carrito"][pn] = {'precio': p_f_t, 'tel': row['Telefono'], 'tienda': row['Tienda'], 'cant': 1}
                            st.rerun()
                st.divider()

        # 3. CATÁLOGO Y FAVORITOS
        tab_cat, tab_fav = st.tabs(["🛒 Catálogo General", "❤️ Mis Favoritos"])

        with tab_cat:
            df_display = df.copy()
            if query:
                df_display = df_display[df_display['Producto'].astype(str).str.contains(query, case=False, na=False)]
            
            df_display = df_display.reset_index(drop=True)
            cols = st.columns(4)
            for idx, row in df_display.iterrows():
                with cols[idx % 4]:
                    try: p_usd = float(re.sub(r'[^\d.,]', '', str(row.get('Precio', '0'))).replace(',', '.'))
                    except: p_usd = 0.0
                    
                    prod_name = row['Producto']
                    es_fav = prod_name in st.session_state["favoritos"]
                    
                    st.markdown(f"""
                        <div class="product-card">
                            <div style="text-align:right; font-size:16px;">{'❤️' if es_fav else '🤍'}</div>
                            <img src="{row.get('Foto', '')}" class="img-contain">
                            <div class="tienda-tag">🏪 {row['Tienda']}</div>
                            <div class="tit-prod">{prod_name}</div>
                            <div class="price-usd">${p_usd:.2f}</div>
                            <div class="price-bs">≈ {(p_usd * tasa_bcv):.2f} Bs.</div>
                            <div class="fecha-upd">
                                <span>📍 {row.get('Zona')}</span>
                                <span>🕒 {row.get('Actualizado')}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    cf, cq, ca = st.columns([0.8, 1.2, 1])
                    if cf.button("❤️" if not es_fav else "💔", key=f"fv_{idx}"):
                        if es_fav: st.session_state["favoritos"].remove(prod_name)
                        else: st.session_state["favoritos"].append(prod_name)
                        st.rerun()
                    with cq:
                        qty = st.number_input("", 1, 99, 1, key=f"q_{idx}")
                    if ca.button("🛒", key=f"a_{idx}"):
                        if prod_name in st.session_state["carrito"]: 
                            st.session_state["carrito"][prod_name]['cant'] += qty
                        else: 
                            st.session_state["carrito"][prod_name] = {
                                'precio': p_usd, 
                                'tel': row['Telefono'], 
                                'tienda': row['Tienda'],
                                'cant': qty
                            }
                        st.toast(f"¡{qty}x {prod_name}!")

        with tab_fav:
            if not st.session_state["favoritos"]:
                st.info("No tenéis favoritos guardados.")
            else:
                fav_items = df[df['Producto'].isin(st.session_state["favoritos"])]
                f_cols = st.columns(4)
                for f_idx, f_row in fav_items.reset_index().iterrows():
                    with f_cols[f_idx % 4]:
                        st.image(f_row.get('Foto', ''), use_container_width=True)
                        st.write(f"**{f_row['Producto']}**")
                        if st.button("Quitar ❤️", key=f"rm_{f_idx}"):
                            st.session_state["favoritos"].remove(f_row['Producto'])
                            st.rerun()

        # --- 4. SIDEBAR CARRITO MULTI-TIENDA (CORREGIDO) ---
        if st.session_state["carrito"]:
            with st.sidebar:
                st.header("🛒 Mi Pedido")
                
                # Agrupar productos por tienda
                tiendas_en_carrito = {}
                for p_nombre, info in st.session_state["carrito"].items():
                    t_nombre = info.get('tienda', 'Tienda Desconocida')
                    if t_nombre not in tiendas_en_carrito:
                        tiendas_en_carrito[t_nombre] = []
                    tiendas_en_carrito[t_nombre].append({'nombre': p_nombre, 'info': info})

                total_general = 0
                
                for tienda, productos in tiendas_en_carrito.items():
                    with st.expander(f"🏪 {tienda}", expanded=True):
                        subtotal_tienda = 0
                        # Formato de Ticket para el mensaje
                        fecha_ticket = datetime.now().strftime("%d/%m/%Y")
                        msg_whatsapp = f" *📦 NUEVO PEDIDO - PÍLLALO* ⚡\n"
                        msg_whatsapp += f"----------------------------------\n"
                        msg_whatsapp += f"🏠 *Tienda:* {tienda.upper()}\n"
                        msg_whatsapp += f"📅 *Fecha:* {fecha_ticket}\n"
                        msg_whatsapp += f"----------------------------------\n"
                        
                        for item in productos:
                            p_name = item['nombre']
                            info = item['info']
                            sub_item = info['precio'] * info['cant']
                            subtotal_tienda += sub_item
                            total_general += sub_item
                            
                            st.write(f"**{p_name}**")
                            st.caption(f"{info['cant']} x ${info['precio']:.2f} = ${sub_item:.2f}")
                            # Agregando al ticket de texto
                            msg_whatsapp += f"✅ {info['cant']}x {p_name}\n"
                            msg_whatsapp += f"      Subt: ${sub_item:.2f}\n"
                        
                        msg_whatsapp += f"----------------------------------\n"
                        msg_whatsapp += f"💰 *TOTAL A PAGAR:* ${subtotal_tienda:.2f}\n"
                        msg_whatsapp += f"----------------------------------\n"
                        msg_whatsapp += f"⚡ _Enviado desde Vitrina Maracaibo_"
                        
                        whatsapp_tienda = productos[0]['info']['tel']
                        
                        # CREACIÓN DEL ENLACE SEGURO
                        link_final = f"https://wa.me/{whatsapp_tienda}?text={urllib.parse.quote(msg_whatsapp)}"
                        
                        # Botón con link directo
                        st.markdown(f"""
                            <a href="{link_final}" target="_blank" style="text-decoration: none;">
                                <div style="
                                    background-color: #25D366;
                                    color: white;
                                    padding: 10px 20px;
                                    text-align: center;
                                    border-radius: 8px;
                                    font-weight: bold;
                                    margin-top: 10px;
                                    cursor: pointer;
                                    border: none;">
                                    🚀 Enviar Pedido a {tienda}
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
                
                st.divider()
                st.metric("TOTAL GENERAL", f"${total_general:.2f}")
                st.caption(f"Ref: {(total_general * tasa_bcv):.2f} Bs.")
                
                if st.button("Vaciar Todo 🗑️", use_container_width=True):
                    st.session_state["carrito"] = {}
                    st.rerun()

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Portal: {tienda_user}")
    
    t1, t2, t3, t4 = st.tabs(["📦 Inventario", "📈 Marketing", "💎 Mi Plan", "📤 Carga Masiva"])

    with t1:
        df_full = pd.DataFrame(sheet.get_all_records())
        df_full['fila'] = df_full.index + 2
        mis_productos = df_full[df_full['Tienda'] == tienda_user]

        with st.expander("➕ Cargar UN producto rápido"):
            with st.form("form_rapido"):
                nuevo_nombre = st.text_input("Nombre del Producto")
                nuevo_precio = st.number_input("Precio ($)", min_value=0.0, step=0.01)
                nueva_foto = st.text_input("Link de la Foto")
                nueva_prioridad = st.selectbox("¿Es destacado?", [0, 1, 2, 3])
                if st.form_submit_button("🚀 Publicar"):
                    if nuevo_nombre and nueva_foto:
                        tel_tienda = mis_productos['Telefono'].iloc[0] if not mis_productos.empty else "58412"
                        nueva_fila = [nuevo_nombre, tienda_user, nueva_prioridad, str(nuevo_precio).replace(',', '.'), nueva_foto, tel_tienda]
                        sheet.append_row(nueva_fila, value_input_option='USER_ENTERED')
                        st.success("¡Publicado!")
                        st.rerun()
        
        st.divider()
        if not mis_productos.empty:
            st.dataframe(mis_productos.drop(columns=['fila']), use_container_width=True)
            p_sel = st.selectbox("Editar precio de:", mis_productos['Producto'].unique())
            row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
            p_limpio = str(row_p.get('Precio', '0.00')).replace(',', '.')
            try: v_ini = float(p_limpio)
            except: v_ini = 0.0
            nuevo_p = st.number_input("Nuevo Precio ($):", value=v_ini, step=0.01)
            if st.button("Actualizar Precio"):
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
        st.info("Plan: PRO COMERCIO")

    with t4:
        st.subheader("📤 Carga Masiva")
        IMGBB_API_KEY = "1f2081c8821957a63c9a0c0df237fdba" 
        with st.expander("📸 Subir fotos"):
            img_file = st.file_uploader("Elegí imagen", type=['png', 'jpg', 'jpeg'])
            if img_file and st.button("Generar Enlace"):
                res = requests.post("https://api.imgbb.com/1/upload", {"key": IMGBB_API_KEY}, files={"image": img_file.getvalue()})
                if res.json()["status"] == 200:
                    st.code(res.json()["data"]["url"])
        
        file = st.file_uploader("Excel .xlsx", type=['xlsx'])
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