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

# --- 6. BARRA LATERAL (LOGIN DINÁMICO) ---
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
                usuarios_df = pd.DataFrame(user_sheet.get_all_records())
                
                # Buscamos coincidencia
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
                    st.error("Credenciales incorrectas")
            except:
                st.error("Error al validar usuarios. ¿Existe la pestaña 'Usuarios'?")
    else:
        st.write(f"Usuario: **{st.session_state['user_name']}**")
        st.write(f"Perfil: **{st.session_state['perfil']}**")
        if st.button("Cerrar Sesión"):
            st.session_state.update({"logueado": False, "perfil": "Invitado", "user_name": ""})
            st.rerun()

# --- 7. LÓGICA DE PANTALLAS ---

# --- PERFIL: INVITADO ---
if st.session_state["perfil"] == "Invitado":
    st.title("🔍 Encuentra los mejores precios")
    # Registramos la visita
    if "visitado" not in st.session_state:
        registrar_estadistica("VISITA", "Usuario anónimo entró a la vitrina")
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
    st.title("👨‍✈️ Business Intelligence - Píllalo CEO")
    t_metrica, t_pagos, t_usuarios, t_sistema = st.tabs(["📊 Estadísticas", "💰 Pagos", "👥 Usuarios", "⚙️ Config"])

    with t_metrica:
        if sheet:
            df_total = pd.DataFrame(sheet.get_all_records())
            try:
                est_sheet = spreadsheet.worksheet("Estadisticas")
                df_est = pd.DataFrame(est_sheet.get_all_records())
            except: 
                df_est = pd.DataFrame(columns=['Fecha', 'Evento', 'Detalle'])

            # --- MÉTRICAS KPI ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📦 Productos", len(df_total))
            c2.metric("🏪 Comercios", df_total['Tienda'].nunique() if 'Tienda' in df_total.columns else 0)
            
            visitas = len(df_est[df_est['Evento'] == 'VISITA']) if 'Evento' in df_est.columns else 0
            planes = len(df_est[df_est['Evento'] == 'PAGO_PREMIUM']) if 'Evento' in df_est.columns else 0
            c3.metric("👤 Visitas Totales", visitas)
            c4.metric("💎 Planes Vendidos", planes)

            st.divider()

            # --- GRÁFICOS (REPARADOS) ---
            if not df_total.empty:
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    st.subheader("🔥 Top 5 Productos")
                    # Contamos y reseteamos nombres manualmente para evitar el error 'index'
                    top_df = df_total['Producto'].value_counts().head(5).reset_index()
                    top_df.columns = ['Producto', 'Cantidad'] # Forzamos nombres claros
                    
                    fig_top = px.bar(
                        top_df, 
                        x='Cantidad', 
                        y='Producto', 
                        orientation='h',
                        color_discrete_sequence=['#FF4B4B'],
                        text_auto=True
                    )
                    fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_top, use_container_width=True)

                with col_g2:
                    st.subheader("📍 Oferta por Zona")
                    # Contamos y reseteamos nombres manualmente
                    zona_chart_df = df_total['Zona'].value_counts().reset_index()
                    zona_chart_df.columns = ['Zona', 'Cantidad'] # Forzamos nombres claros
                    
                    fig_pie = px.pie(
                        zona_chart_df, 
                        names='Zona', 
                        values='Cantidad', 
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Aún no hay datos para mostrar gráficos.")

    with t_usuarios:
        st.subheader("🔐 Gestión de Usuarios (Google Sheets)")
        try:
            u_sheet = spreadsheet.worksheet("Usuarios")
            df_u = pd.DataFrame(u_sheet.get_all_records())
            edited = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Actualizar Credenciales"):
                u_sheet.clear()
                u_sheet.append_row(df_u.columns.tolist())
                u_sheet.append_rows(edited.values.tolist())
                st.success("Usuarios actualizados")
        except: st.error("Crea la pestaña 'Usuarios' en el Excel")

    with t_pagos:
        try:
            df_p = df_est[df_est['Evento'] == 'PAGO_PREMIUM']
            st.dataframe(df_p, use_container_width=True)
        except: st.info("Sin registros de pago")

    with t_sistema:
        if st.button("🔄 Recargar Todo"):
            st.cache_data.clear()
            st.rerun()

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    st.title(f"🏢 Panel: {st.session_state['user_name']}")
    t1, t2, t3 = st.tabs(["📦 Inventario", "📤 Carga", "🚀 Marketing"])
    
    # Aquí el filtro de tienda es automático según el usuario
    tienda_user = st.session_state["tienda_asociada"]

    with t1:
        if sheet:
            df_e = pd.DataFrame(sheet.get_all_records())
            df_e['fila'] = df_e.index + 2
            # Si es una empresa específica, solo ve lo suyo
            mis_datos = df_e[df_e['Tienda'] == tienda_user] if tienda_user != "Todas" else df_e
            
            if not mis_datos.empty:
                st.dataframe(mis_datos.drop(columns=['fila']), use_container_width=True)
                # Lógica de Modificar/Eliminar igual a la anterior...
            else: st.warning("No tienes productos cargados aún.")

    # ... (Resto de pestañas t2 y t3 igual al código anterior)

# --- 8. SECCIÓN DE SOPORTE DINÁMICO (SIDEBAR) ---
with st.sidebar:
    st.divider()
    st.subheader("🆘 ¿Necesitas ayuda?")
    
    # CONFIGURA TU NÚMERO AQUÍ
    mi_whatsapp = "584127522988" 
    
    if st.session_state["logueado"]:
        user = st.session_state["user_name"]
        perfil = st.session_state["perfil"]
        
        # Personalizamos el mensaje según quién escribe
        if perfil == "Admin":
            mensaje_wa = "Hola, soy el Admin de Píllalo. Necesito asistencia técnica con la base de datos."
        else:
            mensaje_wa = f"Hola Píllalo, soy {user}. Necesito soporte con mi cuenta de socio y la carga de productos."
        
        # Codificamos el mensaje para URL
        import urllib.parse
        mensaje_encoded = urllib.parse.quote(mensaje_wa)
        link_wa = f"https://wa.me/{mi_whatsapp}?text={mensaje_encoded}"
        
        # Botón estilizado con HTML/CSS para que sea verde WhatsApp
        st.markdown(f"""
            <a href="{link_wa}" target="_blank" style="text-decoration: none;">
                <div style="
                    background-color: #25D366;
                    color: white;
                    padding: 12px;
                    text-align: center;
                    border-radius: 8px;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 10px;
                    border: none;
                    cursor: pointer;
                    transition: 0.3s;
                ">
                    💬 Hablar con Soporte
                </div>
            </a>
        """, unsafe_allow_html=True)
        
        st.caption("Horario de atención: 8:00 AM - 8:00 PM")
    else:
        st.info("👋 ¡Hola! Si eres socio y tienes problemas para entrar, contacta al administrador del sistema.")

# --- PIE DE PÁGINA ---
st.divider()
st.caption(f"Píllalo 2026 | Business Intelligence Suite | Tasa BCV: {tasa_bcv:.2f} Bs.")