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

# Bloque de prueba (puedes borrarlo después)
if spreadsheet:
    nombres_hojas = [w.title for w in spreadsheet.worksheets()]
    st.sidebar.write("Hojas encontradas:", nombres_hojas)

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
                    st.error("❌ La hoja 'Usuarios' está vacía. Agrega al menos un usuario en la fila 2.")
                else:
                    usuarios_df = pd.DataFrame(data)
                    # Verificamos si las columnas existen
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
                            st.success(f"Bienvenido {u_input}")
                            st.rerun()
                        else:
                            st.error("🚫 Usuario o clave incorrectos.")
                    else:
                        st.error(f"⚠️ Faltan columnas en el Excel. Revisa que existan: {columnas_necesarias}")
            except Exception as e:
                st.error(f"❌ Error al leer la pestaña 'Usuarios': {e}")

    # SOPORTE DINÁMICO EN EL SIDEBAR
    st.divider()
    st.subheader("🆘 ¿Necesitas ayuda?")
    mi_whatsapp = "584127522988" 
    
    if st.session_state["logueado"]:
        u_name = st.session_state["user_name"]
        m_wa = f"Hola Píllalo, soy {u_name}. Necesito soporte técnico."
        link_wa = f"https://wa.me/{mi_whatsapp}?text={urllib.parse.quote(m_wa)}"
        st.markdown(f"""<a href="{link_wa}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:10px;text-align:center;border-radius:8px;font-weight:bold;">💬 Hablar con Soporte</div></a>""", unsafe_allow_html=True)
    else:
        st.info("Inicia sesión para recibir soporte personalizado.")

# --- 7. LÓGICA DE PANTALLAS ---

# --- PERFIL: INVITADO (VITRINA PÚBLICA) ---
if st.session_state["perfil"] == "Invitado":
    st.title("🔍 Encuentra los mejores precios en Maracaibo")
    if "visitado" not in st.session_state:
        registrar_estadistica("VISITA", "Entrada a vitrina")
        st.session_state["visitado"] = True

    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            zonas = sorted(df['Zona'].unique()) if 'Zona' in df.columns else []
            zona_sel = st.multiselect("📍 Filtrar por Zona:", zonas)
            if zona_sel: df = df[df['Zona'].isin(zona_sel)]
                
            for _, row in df.iterrows():
                with st.container():
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        foto = row.get('Foto', '')
                        st.image(foto if str(foto).startswith('http') else "https://via.placeholder.com/150", width=180)
                    with c2:
                        st.markdown(f"### {row['Producto']}")
                        try: p_usd = float(str(row.get('Precio', '0.00')).replace(',', '.'))
                        except: p_usd = 0.00
                        st.markdown(f"## 💰 ${p_usd:.2f} | <span style='color:#00D1FF'>{p_usd * tasa_bcv:.2f} Bs.</span>", unsafe_allow_html=True)
                        st.write(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")
                    st.divider()

# --- PERFIL: ADMIN (CONTROL TOTAL) ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Business Intelligence - Píllalo CEO")
    t_met, t_pag, t_usr, t_cfg = st.tabs(["📊 Estadísticas", "💰 Pagos", "👥 Usuarios", "⚙️ Sistema"])

    with t_met:
        if sheet:
            df_all = pd.DataFrame(sheet.get_all_records())
            if not df_all.empty:
                col1, col2 = st.columns(2)
                with col1:
                    top_df = df_all['Producto'].value_counts().head(5).reset_index()
                    top_df.columns = ['Producto', 'Cantidad']
                    st.plotly_chart(px.bar(top_df, x='Cantidad', y='Producto', orientation='h', title="Top 5 Productos"), use_container_width=True)
                with col2:
                    zona_df = df_all['Zona'].value_counts().reset_index()
                    zona_df.columns = ['Zona', 'Cantidad']
                    st.plotly_chart(px.pie(zona_df, names='Zona', values='Cantidad', hole=0.4, title="Distribución por Zonas"), use_container_width=True)

    with t_usr:
        try:
            u_sheet = spreadsheet.worksheet("Usuarios")
            df_u = pd.DataFrame(u_sheet.get_all_records())
            edited = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Guardar Cambios en Usuarios"):
                u_sheet.clear()
                u_sheet.append_row(df_u.columns.tolist())
                u_sheet.append_rows(edited.values.tolist())
                st.success("¡Usuarios actualizados!")
        except: st.error("No se encontró la pestaña 'Usuarios'")

    with t_cfg:
        if st.button("🔄 Forzar Recarga de Datos"):
            st.cache_data.clear()
            st.rerun()

# --- PERFIL: EMPRESA (PANEL DE SOCIO) ---
elif st.session_state["perfil"] == "Empresa":
    tienda_user = st.session_state.get("tienda_asociada", "Sin Tienda")
    st.title(f"🏢 Panel de Control: {tienda_user}")
    t1, t2 = st.tabs(["📦 Mi Inventario", "📤 Subir Productos"])

    with t1:
        if sheet:
            df_full = pd.DataFrame(sheet.get_all_records())
            df_full['fila'] = df_full.index + 2
            mis_productos = df_full[df_full['Tienda'] == tienda_user]
            
            if not mis_productos.empty:
                st.dataframe(mis_productos.drop(columns=['fila']), use_container_width=True)
                st.divider()
                st.subheader("✏️ Editar Precio Rápido")
                p_sel = st.selectbox("Selecciona producto:", mis_productos['Producto'].unique())
                row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
                st.subheader("✏️ Editar Precio Rápido")
                p_sel = st.selectbox("Selecciona producto:", mis_productos['Producto'].unique())
                row_p = mis_productos[mis_productos['Producto'] == p_sel].iloc[0]
                
                # --- LIMPIEZA DE PRECIO SEGURA ---
                precio_raw = str(row_p.get('Precio', '0.00')).replace(',', '.')
                # Quitamos cualquier cosa que no sea número o punto (como $)
                import re
                precio_limpio = re.sub(r'[^\d.]', '', precio_raw)
                
                try:
                    valor_inicial = float(precio_limpio) if precio_limpio else 0.00
                except ValueError:
                    valor_inicial = 0.00
                
                nuevo_p = st.number_input("Nuevo Precio ($):", value=valor_inicial, step=0.01)
                # ---------------------------------

                if st.button("Actualizar"):
                    sheet.update_cell(int(row_p['fila']), 4, nuevo_p) 
                    st.success(f"¡Precio de {p_sel} actualizado a ${nuevo_p:.2f}!")
                    st.rerun()
                
                if st.button("Actualizar"):
                    sheet.update_cell(int(row_p['fila']), 4, nuevo_p) # Col 4 es Precio
                    st.success("¡Precio actualizado!")
                    st.rerun()
            else:
                st.info("Aún no tienes productos cargados.")

    with t2:
        st.subheader("Carga Masiva vía Excel")
        file = st.file_uploader("Sube tu archivo .xlsx", type=['xlsx'])
        if file and st.button("🚀 Publicar Inventario"):
            df_new = pd.read_excel(file)
            df_new['Tienda'] = tienda_user # Seguridad: Forzamos su nombre
            sheet.append_rows(df_new.values.tolist(), value_input_option='USER_ENTERED')
            st.success(f"¡{len(df_new)} productos publicados!")
            st.balloons()

# --- PIE DE PÁGINA ---
st.divider()
st.caption(f"Píllalo 2026 | Business Intelligence | Tasa: {tasa_bcv:.2f} Bs.")