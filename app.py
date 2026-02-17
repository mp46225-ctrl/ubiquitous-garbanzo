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

# --- 6. BARRA LATERAL (LOGIN Y SOPORTE) ---
with st.sidebar:
    st.title("⚡ Píllalo")
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

# --- PERFIL: INVITADO (INTERFAZ PREMIUM) ---
if st.session_state["perfil"] == "Invitado":
    # CSS MEJORADO: Fuerza la fila horizontal y oculta barras de scroll molestas
    st.markdown("""
        <style>
        .scroll-container {
            display: flex;
            flex-direction: row; /* Fuerza los items uno al lado del otro */
            overflow-x: auto;    /* Habilita el movimiento lateral */
            white-space: nowrap;
            padding: 15px 5px;
            gap: 15px;
            scrollbar-width: none; /* Firefox */
        }
        .scroll-container::-webkit-scrollbar {
            display: none; /* Chrome/Safari */
        }
        .scroll-item {
            flex: 0 0 auto;      /* IMPORTANTE: Evita que el item se encoja */
            width: 130px; 
            background: #1e1e1e;
            border-radius: 12px;
            padding: 10px;
            text-align: center;
            border: 1px solid #333;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
        }
        .product-card {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 15px;
            border: 1px solid #333;
            margin-bottom: 10px;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🔍 Vitrina Maracaibo")
    
    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            # 1. BUSCADOR
            query = st.text_input("🔎 ¿Qué buscas hoy?", placeholder="Ej: Harina, Refresco...", key="main_search")
            
            # Aplicar Filtros
            df_filtered = df.copy()
            if query:
                df_filtered = df_filtered[df_filtered['Producto'].astype(str).str.contains(query, case=False, na=False)]

            # 2. CINTA TRANSPORTADORA (PRODUCTOS TOP)
            if 'Prioridad' in df_filtered.columns and not query:
                df_filtered['Prioridad'] = pd.to_numeric(df_filtered['Prioridad'], errors='coerce').fillna(0)
                top_items = df_filtered[df_filtered['Prioridad'] > 0].sort_values(by='Prioridad', ascending=False)
                
                if not top_items.empty:
                    st.markdown("### 🔥 Destacados Píllalo")
                    
                    # Generamos el HTML para la cinta transportadora
                    scroll_html = '<div class="scroll-container">'
                    for _, row in top_items.iterrows():
                        try:
                            p_raw = str(row.get('Precio', '0.00')).replace(',', '.')
                            p_float = float(re.sub(r'[^\d.]', '', p_raw)) if p_raw else 0.00
                        except: p_float = 0.00
                        
                        img_url = row.get('Foto', "https://via.placeholder.com/150")
                        scroll_html += f'''
                            <div class="scroll-item">
                                <img src="{img_url}" style="width:100px; height:100px; object-fit:cover; border-radius:8px;">
                                <div style="font-size:12px; font-weight:bold; margin-top:5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{row['Producto']}</div>
                                <div style="color:#00D1FF; font-weight:bold;">${p_float:.2f}</div>
                            </div>
                        '''
                    scroll_html += '</div>'
                    st.markdown(scroll_html, unsafe_allow_html=True)
                    st.divider()

            # 3. MATRIZ DE PRODUCTOS (3 POR FILA)
            st.subheader("Todos los productos")
            
            cols = st.columns(3)
            for idx, (_, row) in enumerate(df_filtered.iterrows()):
                with cols[idx % 3]:
                    # --- LIMPIEZA DE PRECIO ---
                    try:
                        p_raw = str(row.get('Precio', '0.00')).replace(',', '.')
                        p_usd = float(re.sub(r'[^\d.]', '', p_raw)) if p_raw else 0.00
                    except: p_usd = 0.00
                    
                    # Tarjeta de producto
                    st.markdown(f"""
                        <div class="product-card">
                            <img src="{row.get('Foto', 'https://via.placeholder.com/150')}" style="width:100%; height:150px; object-fit:cover; border-radius:10px; margin-bottom:10px;">
                            <h4 style="margin:0; font-size:16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row['Producto']}</h4>
                            <p style="color:gray; font-size:12px; margin:5px 0;">🏪 {row['Tienda']}</p>
                            <h3 style="margin:5px 0; color:#00D1FF;">${p_usd:.2f}</h3>
                            <p style="font-size:13px; color:#aaa; margin-bottom:0;">{p_usd * tasa_bcv:.2f} Bs.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón de WhatsApp
                    tel_tienda = str(row.get('Telefono', '584127522988')).replace('+', '').strip()
                    if not tel_tienda or tel_tienda == 'nan': tel_tienda = "584127522988"
                    msg = f"Hola {row['Tienda']}, quiero el producto *{row['Producto']}* de Píllalo."
                    link_pedido = f"https://wa.me/{tel_tienda}?text={urllib.parse.quote(msg)}"
                    
                    st.link_button("🛒 Pedir", link_pedido, use_container_width=True, key=f"btn_{idx}")
                    st.write("")

# --- PERFIL: ADMIN ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Admin Panel")
    t_met, t_usr = st.tabs(["📊 Estadísticas", "👥 Usuarios"])
    with t_met:
        if sheet:
            df_all = pd.DataFrame(sheet.get_all_records())
            st.metric("Total Productos", len(df_all))
            st.plotly_chart(px.pie(df_all, names='Zona', title="Productos por Zona"), use_container_width=True)
    with t_usr:
        try:
            u_sheet = spreadsheet.worksheet("Usuarios")
            df_u = pd.DataFrame(u_sheet.get_all_records())
            edited = st.data_editor(df_u, num_rows="dynamic", use_container_width=True, key="editor_usuarios")
            if st.button("💾 Guardar Usuarios"):
                u_sheet.clear()
                u_sheet.append_row(df_u.columns.tolist())
                u_sheet.append_rows(edited.values.tolist())
                st.success("Sincronizado")
        except: st.error("Error en pestaña Usuarios")

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Portal: {tienda_user}")
    t1, t2 = st.tabs(["📦 Inventario", "📤 Subir Excel"])

    with t1:
        if sheet:
            df_full = pd.DataFrame(sheet.get_all_records())
            df_full['fila'] = df_full.index + 2
            mis_productos = df_full[df_full['Tienda'] == tienda_user]
            
            if not mis_productos.empty:
                st.dataframe(mis_productos.drop(columns=['fila']), use_container_width=True)
                st.divider()
                st.subheader("✏️ Editar Precio")
                
                # KEY ÚNICA para evitar el error DuplicateElementId
                p_sel = st.selectbox("Selecciona producto:", mis_productos['Producto'].unique(), key="sel_prod_empresa")
                row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
                
                # Limpieza de precio
                p_raw = str(row_p.get('Precio', '0.00')).replace(',', '.')
                p_limpio = re.sub(r'[^\d.]', '', p_raw)
                try: v_ini = float(p_limpio) if p_limpio else 0.00
                except: v_ini = 0.00
                
                nuevo_p = st.number_input("Nuevo Precio ($):", value=v_ini, step=0.01, key="num_prec_empresa")
                
                if st.button("Actualizar Precio Ahora", key="btn_upd_empresa"):
                    sheet.update_cell(int(row_p['fila']), 4, nuevo_p)
                    st.success(f"¡Actualizado a ${nuevo_p:.2f}!")
                    st.rerun()
            else:
                st.info("No tienes productos cargados.")

    with t2:
        file = st.file_uploader("Sube Excel", type=['xlsx'], key="uploader_excel")
        if file and st.button("🚀 Publicar", key="btn_pub_excel"):
            df_new = pd.read_excel(file)
            df_new['Tienda'] = tienda_user
            sheet.append_rows(df_new.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Cargado!")
            st.rerun()

# --- PIE ---
st.divider()
st.caption(f"Píllalo 2026 | Tasa: {tasa_bcv:.2f} Bs.")