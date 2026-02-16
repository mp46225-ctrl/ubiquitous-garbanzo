import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import plotly.express as px
import json

# --- 1. CONFIGURACIÓN DE PÁGINA Y CONEXIÓN SEGURA ---
st.set_page_config(page_title="Píllalo - Admin & Business", layout="wide")

def conectar_google_sheets():
    try:
        # Cargamos credenciales desde Streamlit Secrets de forma robusta
        creds_info = st.secrets["gcp_service_account"]
        
        # Si llega como string lo convertimos, si es AttrDict se usa directo
        if isinstance(creds_info, str):
            creds_info = json.loads(creds_info)
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Pillalo_Data") 
        return spreadsheet
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

spreadsheet = conectar_google_sheets()
sheet = spreadsheet.sheet1 if spreadsheet else None

# --- 2. GESTIÓN DE SESIÓN ---
if "logueado" not in st.session_state:
    st.session_state["logueado"] = False
    st.session_state["perfil"] = "Invitado"

# --- 3. FUNCIONES DE APOYO ---
def registrar_estadistica(evento, detalle):
    try:
        est_sheet = spreadsheet.worksheet("Estadisticas")
        fecha = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        est_sheet.append_row([fecha, evento, detalle, "Sistema Web"], value_input_option='USER_ENTERED')
    except:
        pass

# --- 4. LOGIN EN BARRA LATERAL ---
with st.sidebar:
    st.title("⚡ Píllalo")
    if not st.session_state["logueado"]:
        st.subheader("🔑 Acceso")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if user == "admin" and password == "pilla_ceo":
                st.session_state["logueado"] = True
                st.session_state["perfil"] = "Admin"
                st.rerun()
            elif user == "empresa" and password == "pilla_socio":
                st.session_state["logueado"] = True
                st.session_state["perfil"] = "Empresa"
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    else:
        st.write(f"Conectado como: **{st.session_state['perfil']}**")
        if st.button("Cerrar Sesión"):
            st.session_state["logueado"] = False
            st.session_state["perfil"] = "Invitado"
            st.rerun()

# --- 5. LÓGICA DE PANTALLAS ---

# --- PERFIL: INVITADO (VISTA PÚBLICA) ---
if st.session_state["perfil"] == "Invitado":
    st.title("🔍 Píllalo - Ofertas en Maracaibo")
    st.subheader("¡Los mejores precios en un solo lugar!")
    
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Filtro de Zona
        zonas_disponibles = df['Zona'].unique() if 'Zona' in df.columns else []
        zona_sel = st.multiselect("📍 Filtrar por Zona:", zonas_disponibles)
        
        if zona_sel:
            df = df[df['Zona'].isin(zona_sel)]
            
        # Galería de productos con paracaídas para errores de imagen
        for index, row in df.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 3])
                with c1:
                    foto_url = row.get('Foto', '')
                    # Validación de seguridad para la imagen
                    if foto_url and str(foto_url).startswith('http'):
                        try:
                            st.image(foto_url, width=180)
                        except:
                            st.image("https://via.placeholder.com/150?text=Error+Imagen", width=180)
                    else:
                        st.image("https://via.placeholder.com/150?text=Sin+Foto", width=180)
                
                with c2:
                    st.markdown(f"### {row.get('Producto', 'Sin Nombre')}")
                    # Limpieza de precio: siempre con punto (.)
                    precio_val = str(row.get('Precio', '0.00')).replace(',', '.')
                    st.markdown(f"💰 **Precio: ${precio_val}**")
                    st.write(f"🏪 {row.get('Tienda', 'N/A')} | 📍 {row.get('Zona', 'N/A')}")
                    st.write(f"📞 WhatsApp: {row.get('WhatsApp', 'N/A')}")
                st.divider()

# --- PERFIL: ADMIN (EL CEO) ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Panel de Control CEO")
    tab1, tab2 = st.tabs(["📈 Análisis de Mercado", "⚙️ Gestión Total"])
    
    with tab1:
        try:
            est_data = spreadsheet.worksheet("Estadisticas").get_all_records()
            df_est = pd.DataFrame(est_data)
            col_a, col_b = st.columns(2)
            with col_a:
                fig = px.pie(df_est, names='Evento', title='Actividad del Sistema')
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.metric("Total Operaciones", len(df_est))
                st.write("Top Acciones:")
                st.bar_chart(df_est['Evento'].value_counts())
        except:
            st.warning("No hay datos de estadísticas suficientes.")

# --- PERFIL: EMPRESA (SOCIOS COMERCIALES) ---
elif st.session_state["perfil"] == "Empresa":
    st.title("🏢 Portal de Socios - Carga Masiva")
    
    # 1. Descarga de Plantilla
    st.subheader("1. Obtener Plantilla")
    columnas = ["Producto", "Tienda", "Zona", "Precio", "WhatsApp", "Categoria", "Pago", "Calificacion", "Foto"]
    df_plantilla = pd.DataFrame([["Salsa Roja", "Tienda X", "Norte", 4.25, "584120000000", "Víveres", "Efectivo", 5, "https://link.com/foto.jpg"]], columns=columnas)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_plantilla.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Descargar Plantilla Excel",
        data=buffer.getvalue(),
        file_name="plantilla_pillalo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    
    # 2. Subida de Archivo
    st.subheader("2. Cargar Inventario")
    archivo = st.file_uploader("Sube tu Excel relleno", type=['xlsx'])
    
    if archivo:
        df_up = pd.read_excel(archivo)
        st.write("Vista previa de la carga:")
        st.dataframe(df_up.head())
        
        if st.button("🚀 Publicar Inventario"):
            with st.spinner("Procesando datos..."):
                # Limpieza: Comas por Puntos en el precio para cumplir tu requerimiento
                if 'Precio' in df_up.columns:
                    df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
                
                # Sello de tiempo para el historial
                df_up['Fecha'] = datetime.now().strftime("%d/%m %I:%M %p")
                
                # Envío masivo a Google Sheets
                sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
                
                registrar_estadistica("CARGA_MASIVA", f"Empresa cargó {len(df_up)} productos")
                st.success(f"¡Éxito! {len(df_up)} productos publicados.")

# --- FOOTER ---
st.divider()
st.caption("Píllalo 2026 - Maracaibo, Zulia.")