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
        response = requests.get(url, verify=False, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        tasa_usd = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
        return float(tasa_usd.replace(',', '.'))
    except Exception:
        return 54.50  # Tasa de respaldo por si falla el BCV

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
    st.session_state.update({"logueado": False, "perfil": "Invitado", "user_name": ""})

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
    st.metric("Tasa BCV Hoy", f"{tasa_bcv:.2f} Bs.")
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
                    st.image(foto if str(foto).startswith('http') else "https://via.placeholder.com/150?text=Sin+Foto", width=180)
                with c2:
                    st.markdown(f"### {row['Producto']}")
                    try:
                        p_usd = float(str(row.get('Precio', '0.00')).replace(',', '.'))
                    except: p_usd = 0.00
                    p_bs = p_usd * tasa_bcv
                    st.markdown(f"## 💰 ${p_usd:.2f} | <span style='color:#00D1FF'>{p_bs:.2f} Bs.</span>", unsafe_allow_html=True)
                    st.write(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")
                st.divider()

# --- PERFIL: ADMIN ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Dashboard CEO")
    t_adm1, t_adm2, t_adm3 = st.tabs(["💰 Aprobar Pagos", "📊 Inteligencia", "⚙️ Sistema"])

    with t_adm1:
        st.subheader("Pagos Pendientes")
        try:
            est_sheet = spreadsheet.worksheet("Estadisticas")
            df_est = pd.DataFrame(est_sheet.get_all_records())
            pagos = df_est[df_est['Evento'].str.contains("PAGO", na=False)]
            st.dataframe(pagos, use_container_width=True)
        except: st.error("No se encontró la pestaña 'Estadisticas'")

    with t_adm2:
        st.subheader("🔎 Análisis de Mercado")
        if sheet:
            df_mkt = pd.DataFrame(sheet.get_all_records())
            if not df_mkt.empty:
                col_m1, col_m2 = st.columns(2)
                
                # Identificamos columnas existentes para evitar errores de nombres
                c_cat = 'Categoria' if 'Categoria' in df_mkt.columns else df_mkt.columns[0]
                c_zona = 'Zona' if 'Zona' in df_mkt.columns else df_mkt.columns[0]

                with col_m1:
                    fig_cat = px.pie(df_mkt, names=c_cat, hole=0.4, title="Distribución por Categorías")
                    st.plotly_chart(fig_cat, use_container_width=True)
                
                with col_m2:
                    # Corrección del error de Plotly: Usamos nombres genéricos tras el conteo
                    df_z = df_mkt[c_zona].value_counts().reset_index()
                    df_z.columns = ['Ubicacion', 'Cantidad'] # Renombramos manualmente para ir a la segura
                    
                    fig_z = px.bar(
                        df_z, 
                        x='Ubicacion', 
                        y='Cantidad', 
                        title="Zonas con más Productos", 
                        color_discrete_sequence=['#00D1FF']
                    )
                    st.plotly_chart(fig_z, use_container_width=True)
            else:
                st.info("Esperando datos para generar gráficas...")

    with t_adm3:
        if st.button("Limpiar Caché"):
            st.cache_data.clear()
            st.success("Caché limpia")

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    st.title("🏢 Portal Business")
    t1, t2, t3 = st.tabs(["📦 Mis Productos", "📤 Carga Masiva", "🚀 Marketing"])

    with t1:
        st.subheader("Gestión de Inventario")
        if sheet:
            df_e = pd.DataFrame(sheet.get_all_records())
            if not df_e.empty:
                sucursales = sorted(df_e['Tienda'].unique())
                sucursal_sel = st.selectbox("📍 Sucursal:", sucursales)
                df_e['fila_excel'] = df_e.index + 2
                mis_datos = df_e[df_e['Tienda'] == sucursal_sel]
                
                if not mis_datos.empty:
                    st.dataframe(mis_datos.drop(columns=['fila_excel']), use_container_width=True)
                    st.divider()
                    col_mod, col_del = st.columns(2)
                    with col_mod:
                        st.markdown("### ✏️ Modificar")
                        prod_ed = st.selectbox("Elegir:", mis_datos['Producto'].unique())
                        datos_p = mis_datos[mis_datos['Producto'] == prod_ed].iloc[0]
                        n_nom = st.text_input("Nombre:", value=datos_p['Producto'])
                        n_pre = st.number_input("Precio ($):", value=float(str(datos_p['Precio']).replace(',','.')), step=0.01)
                        if st.button("💾 Guardar"):
                            sheet.update_cell(int(datos_p['fila_excel']), 1, n_nom)
                            sheet.update_cell(int(datos_p['fila_excel']), 4, n_pre)
                            st.success("¡Listo!"); st.rerun()
                    with col_del:
                        st.markdown("### 🗑️ Eliminar")
                        if st.button("❌ Eliminar Producto"):
                            sheet.delete_rows(int(datos_p['fila_excel']))
                            st.rerun()
                else: st.warning("Sin productos")

    with t2:
        st.subheader("📤 Cargar Inventario")
        # Generador de fotos
        with st.expander("🖼️ GENERADOR DE LINKS FOTOS"):
            f_img = st.file_uploader("Subir", type=['jpg','png','jpeg'])
            if f_img and st.button("Generar"):
                res = requests.post("https://api.imgbb.com/1/upload", {"key": "1f2081c8821957a63c9a0c0df237fdba"}, files={"image": f_img.getvalue()})
                if res.json()["success"]: st.code(res.json()["data"]["url"])
        st.divider()
        up_ex = st.file_uploader("Excel", type=['xlsx'])
        if up_ex and st.button("🚀 Publicar"):
            df_up = pd.read_excel(up_ex)
            df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
            sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Publicado!")

    with t3:
        st.subheader("🚀 Impulsa tus ventas")
        col_b, col_s, col_g = st.columns(3)
        with col_b:
            st.info("### 🥉 BRONCE ($5)\n* Sello Verificado\n* Ranking mejorado")
            if st.button("Elegir Bronce"): st.session_state["plan"] = "BRONCE"
        with col_s:
            st.success("### 🥈 PLATA ($15)\n* 3 Ofertas Flash\n* Logo en vitrina")
            if st.button("Elegir Plata"): st.session_state["plan"] = "PLATA"
        with col_g:
            st.warning("### 🥇 ORO ($40)\n* Flash Ilimitado\n* Banner Principal")
            if st.button("Elegir Oro"): st.session_state["plan"] = "ORO"
        
        st.divider()
        st.markdown("### 💳 Confirmar suscripción")
        p_sel = st.session_state.get("plan", "Ninguno")
        st.write(f"Plan: **{p_sel}**")
        ref = st.text_input("Referencia de Pago:")
        if st.button("Confirmar Pago 🚀") and ref:
            registrar_estadistica("PAGO_PREMIUM", f"{st.session_state['user_name']} - {p_sel} - Ref: {ref}")
            st.balloons()

st.divider()
st.caption(f"Píllalo 2026 | Tasa BCV: {tasa_bcv:.2f} Bs.")