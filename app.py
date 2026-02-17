import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
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
        return 54.50  # Tasa de respaldo

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
    st.write("Control total de la plataforma.")

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    st.title("🏢 Portal Business - Píllalo")
    t1, t2, t3 = st.tabs(["📦 Mis Productos", "📤 Carga & Plantilla", "🚀 Marketing"])

    with t1:
        st.subheader("📦 Gestión de Inventario")
        if sheet:
            df_e = pd.DataFrame(sheet.get_all_records())
            if not df_e.empty:
                sucursales = sorted(df_e['Tienda'].unique())
                sucursal_sel = st.selectbox("📍 Selecciona Sucursal:", sucursales)
                df_e['fila_excel'] = df_e.index + 2
                mis_datos = df_e[df_e['Tienda'] == sucursal_sel]
                
                if not mis_datos.empty:
                    st.dataframe(mis_datos.drop(columns=['fila_excel']), use_container_width=True)
                    st.divider()
                    col_mod, col_del = st.columns(2)
                    
                    with col_mod:
                        st.markdown("### ✏️ Modificar")
                        prod_ed = st.selectbox("Producto:", mis_datos['Producto'].unique())
                        datos_p = mis_datos[mis_datos['Producto'] == prod_ed].iloc[0]
                        n_nom = st.text_input("Nombre:", value=datos_p['Producto'])
                        n_pre = st.number_input("Precio ($):", value=float(str(datos_p['Precio']).replace(',','.')), step=0.01)
                        if st.button("💾 Guardar"):
                            sheet.update_cell(int(datos_p['fila_excel']), 1, n_nom)
                            sheet.update_cell(int(datos_p['fila_excel']), 4, n_pre)
                            st.success("¡Actualizado!"); st.rerun()

                    with col_del:
                        st.markdown("### 🗑️ Eliminar")
                        tipo_b = st.radio("Acción:", ["Uno", "Todo"])
                        if tipo_b == "Uno":
                            p_b = st.selectbox("Eliminar:", mis_datos['Producto'].unique())
                            if st.button("❌ Borrar"):
                                sheet.delete_rows(int(mis_datos[mis_datos['Producto'] == p_b].iloc[0]['fila_excel']))
                                st.rerun()
                        elif st.button("💣 VACIAR TODO"):
                            for f in sorted(mis_datos['fila_excel'].tolist(), reverse=True): sheet.delete_rows(f)
                            st.rerun()
                else: st.warning("No hay productos.")

    with t2:
        st.subheader("📤 Carga Masiva")
        with st.expander("🖼️ GENERADOR DE LINKS PARA FOTOS"):
            f_img = st.file_uploader("Imagen", type=['jpg','png','jpeg'])
            if f_img and st.button("Generar Link"):
                res = requests.post("https://api.imgbb.com/1/upload", {"key": "TU_API_KEY_AQUI"}, files={"image": f_img.getvalue()})
                if res.json()["success"]: st.code(res.json()["data"]["url"])
        
        st.divider()
        # Plantilla
        cols = ["Producto", "Tienda", "Zona", "Precio", "WhatsApp", "Categoria", "Pago", "Calificacion", "Foto"]
        df_pl = pd.DataFrame([["Ejemplo", "Tienda X", "Norte", 1.0, "58412...", "Varios", "Efectivo", 5, "link"]], columns=cols)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as wr: df_pl.to_excel(wr, index=False)
        st.download_button("📥 Descargar Plantilla", data=buf.getvalue(), file_name="plantilla.xlsx")
        
        up_ex = st.file_uploader("Subir Excel", type=['xlsx'])
        if up_ex and st.button("🚀 Publicar Inventario"):
            df_up = pd.read_excel(up_ex)
            df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
            df_up['Fecha'] = datetime.now().strftime("%d/%m %I:%M %p")
            sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Publicado!")

    with t3:
        st.subheader("🚀 Píllalo Boost - Impulsa tus Ventas")
        st.write("Elige cómo quieres destacar en la plataforma para vender más rápido.")
        
        # --- SECCIÓN DE PLANES PREMIUM ---
        st.markdown("### 💎 Planes Premium")
        col_bronze, col_silver, col_gold = st.columns(3)
        
        with col_bronze:
            st.info("### 🥉 BRONCE")
            st.markdown("""
            **Costo: $5 / mes**
            * ✅ Sello de 'Tienda Verificada'.
            * ✅ Apareces arriba de los 'Invitados'.
            * ✅ Soporte técnico vía WhatsApp.
            """)
            if st.button("Elegir Bronce", key="plan_b"):
                st.session_state["plan"] = "BRONCE"
                st.toast("Has seleccionado el Plan Bronce")

        with col_silver:
            st.success("### 🥈 PLATA")
            st.markdown("""
            **Costo: $15 / mes**
            * ✅ Todo lo del plan Bronce.
            * ✅ **3 Ofertas Flash** al mes.
            * ✅ Logo de tu tienda en la vitrina.
            """)
            if st.button("Elegir Plata", key="plan_s"):
                st.session_state["plan"] = "PLATA"
                st.toast("Has seleccionado el Plan Plata")

        with col_gold:
            st.warning("### 🥇 ORO")
            st.markdown("""
            **Costo: $40 / mes**
            * ✅ Todo lo del plan Plata.
            * ✅ **Ofertas Flash Ilimitadas**.
            * ✅ Banner publicitario en el inicio.
            * ✅ Analítica de clics semanal.
            """)
            if st.button("Elegir Oro", key="plan_g"):
                st.session_state["plan"] = "ORO"
                st.toast("Has seleccionado el Plan Oro")

        st.divider()

        # --- SECCIÓN DE OFERTAS FLASH Y PAGO ---
        col_flash, col_pago = st.columns(2)
        
        with col_flash:
            st.markdown("### 🔥 Activar Oferta Flash")
            st.caption("Destaca un producto con un cronómetro y precio especial por 24h.")
            if not mis_datos.empty:
                prod_f = st.selectbox("Selecciona Producto:", mis_datos['Producto'].unique(), key="sel_flash")
                desc = st.slider("Descuento a aplicar (%)", 5, 50, 20)
                if st.button("🚀 Lanzar Oferta Flash"):
                    st.success(f"Solicitud enviada para {prod_f}.")
                    registrar_estadistica("MARKETING_FLASH", f"{sucursal_sel} solicita flash para {prod_f} (-{desc}%)")
            else:
                st.warning("Carga productos primero para activar ofertas.")

        with col_pago:
            st.markdown("### 💳 Confirmar suscripción")
            p_sel = st.session_state.get("plan", "Ninguno")
            st.write(f"Plan seleccionado: **{p_sel}**")
            
            if p_sel != "Ninguno":
                metodo = st.selectbox("Método de Pago:", ["Pago Móvil", "Zelle", "Efectivo (Oficina)", "Binance P2P"])
                ref = st.text_input("Número de Referencia / Comprobante:", placeholder="Ej: 12345678")
                
                if st.button("Confirmar Pago y Activar 🚀"):
                    if ref:
                        st.balloons()
                        st.success("¡Recibido! Verificaremos el pago y activaremos tus beneficios.")
                        registrar_estadistica("PAGO_PREMIUM", f"{st.session_state['user_name']} pagó {p_sel} via {metodo} - Ref: {ref}")
                    else:
                        st.error("Por favor ingresa el número de referencia.")

st.divider()
st.caption(f"Píllalo 2026 - Maracaibo | Tasa BCV: {tasa_bcv:.2f} Bs.")