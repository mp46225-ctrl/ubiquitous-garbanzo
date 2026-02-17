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

# --- PERFIL: INVITADO (DISEÑO PROFESIONAL Y ORDENADO) ---
if st.session_state["perfil"] == "Invitado":
    # 1. CSS PARA ORDENAR TODO (Colores Píllalo)
    st.markdown("""
        <style>
        /* Contenedor principal para que no se pegue a los bordes */
        .main-container { padding: 10px; }
        
        /* Logo centrado */
        .logo-container {
            display: flex; justify-content: center; margin-bottom: 20px;
        }
        
        /* Tarjetas de productos ordenadas */
        .product-card {
            background: white;
            border-radius: 15px;
            padding: 15px;
            border: 1px solid #f0f0f0;
            border-top: 5px solid #FF8C00; /* Naranja Píllalo */
            text-align: center;
            margin-bottom: 20px;
            height: 320px; /* Altura fija para que todas se vean iguales */
            box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
        }
        
        .img-fix {
            width: 100%; height: 130px; object-fit: contain; margin-bottom: 10px;
        }
        
        .price-style {
            color: #001F3F; font-size: 20px; font-weight: bold; margin: 5px 0;
        }
        
        .bcv-style {
            color: #666; font-size: 12px; margin-bottom: 10px;
        }
        
        /* Botón de Pedir estilo Píllalo */
        .btn-pedir {
            background-color: #FF8C00; color: white !important;
            padding: 10px; border-radius: 10px; text-decoration: none;
            font-weight: bold; display: block; transition: 0.3s;
        }
        .btn-pedir:hover { background-color: #e67e00; }
        </style>
    """, unsafe_allow_html=True)

   # 1. LOGO Y ENCABEZADO (CORREGIDO)
    # He extraído el link directo para que la imagen cargue de una vez
    logo_pillalo = "https://i.ibb.co/cKnXPjwT/pillalo-logo.png" 
    
    st.markdown(f"""
        <div style="display: flex; justify-content: center; margin-bottom: 10px;">
            <img src="https://i.ibb.co/4Z9YF8YF/pillalo.png" width="200">
        </div>
        <p style="text-align: center; color: #001F3F; font-weight: bold; font-style: italic; margin-top: -10px;">
            ¡Píllalo, pedilo y listo!
        </p>
    """, unsafe_allow_html=True)

            # 4. MATRIZ DE PRODUCTOS (ORDENADA)
            # Usamos 2 columnas para móviles o 3 para PC de forma automática
            cols = st.columns(2 if query else 3)
            
            for idx, row in df_filtered.reset_index(drop=True).iterrows():
                with cols[idx % len(cols)]:
                    try:
                        p_raw = str(row.get('Precio', '0')).replace(',', '.')
                        p_usd = float(re.sub(r'[^\d.]', '', p_raw))
                    except: p_usd = 0.0
                    
                    # HTML de la Tarjeta
                    st.markdown(f"""
                        <div class="product-card">
                            <img src="{row.get('Foto', '')}" class="img-fix">
                            <div style="font-weight: bold; color: #333; height: 40px; overflow: hidden;">{row['Producto']}</div>
                            <div class="price-style">${p_usd:.2f}</div>
                            <div class="bcv-style">{(p_usd * tasa_bcv):.2f} Bs.</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Botón WhatsApp debajo de la tarjeta para que no rompa el diseño
                    tel = str(row.get('Telefono', '584127522988')).replace('+', '').replace(' ', '').strip()
                    msg = urllib.parse.quote(f"¡Epa! Pillé el producto *{row['Producto']}* en la app. ¿Está disponible?")
                    
                    st.markdown(f"""
                        <a href="https://wa.me/{tel}?text={msg}" target="_blank" class="btn-pedir">
                            🛒 Pedir
                        </a>
                        <br>
                    """, unsafe_allow_html=True)
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