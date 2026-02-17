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
        # verify=False para evitar problemas con certificados del estado
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
    st.session_state["logueado"] = False
    st.session_state["perfil"] = "Invitado"
    st.session_state["user_name"] = ""

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
                    if str(foto).startswith('http'):
                        st.image(foto, width=180)
                    else: st.image("https://via.placeholder.com/150?text=Sin+Foto", width=180)
                with c2:
                    st.markdown(f"### {row['Producto']}")
                    
                    # --- FILTRO DE SEGURIDAD PARA PRECIOS ---
                    try:
                        # Limpiamos el valor de cualquier cosa que no sea número o punto
                        valor_limpio = str(row.get('Precio', '0.00')).replace(',', '.')
                        p_usd = float(valor_limpio)
                    except ValueError:
                        p_usd = 0.00  # Si hay error (ej: una celda vacía), ponemos 0.00
                    
                    p_bs = p_usd * tasa_bcv
                    
                    # Mostramos con tu formato de punto decimal
                    st.markdown(f"## 💰 ${p_usd:.2f} | <span style='color:#00D1FF'>{p_bs:.2f} Bs.</span>", unsafe_allow_html=True)
                    st.write(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")

# --- PERFIL: ADMIN ---
elif st.session_state["perfil"] == "Admin":
    st.title("👨‍✈️ Dashboard CEO")
    st.write("Control total de la plataforma.")
    # Aquí puedes añadir gráficas de Plotly como en versiones anteriores

# --- PERFIL: EMPRESA ---
elif st.session_state["perfil"] == "Empresa":
    st.title("🏢 Portal Business - Píllalo")
    
    # Definimos las pestañas
    t1, t2, t3 = st.tabs(["📦 Mis Productos", "📤 Carga & Tutorial", "🚀 Marketing"])

   with t1:
        st.subheader("📦 Gestión de Inventario por Sucursal")
        if sheet:
            df_e = pd.DataFrame(sheet.get_all_records())
            
            if not df_e.empty:
                todas_las_sucursales = sorted(df_e['Tienda'].unique())
                sucursal_sel = st.selectbox("📍 Selecciona Sucursal para gestionar:", todas_las_sucursales)
                
                # Obtenemos los índices reales de la hoja para poder editar/borrar
                # Agregamos una columna de ID temporal basada en el índice del Excel (+2 por encabezado y base 0)
                df_e['fila_excel'] = df_e.index + 2
                mis_datos = df_e[df_e['Tienda'] == sucursal_sel]
                
                if not mis_datos.empty:
                    st.write(f"Inventario de **{sucursal_sel}**")
                    st.dataframe(mis_datos.drop(columns=['fila_excel']), use_container_width=True)
                    
                    # --- SUB-MENÚ DE ACCIONES ---
                    st.divider()
                    col_mod, col_del = st.columns(2)
                    
                    with col_mod:
                        st.markdown("### ✏️ Modificar Producto")
                        prod_a_editar = st.selectbox("Producto a editar:", mis_datos['Producto'].unique())
                        # Obtenemos la fila actual del producto
                        datos_prod = mis_datos[mis_datos['Producto'] == prod_a_editar].iloc[0]
                        
                        nuevo_nombre = st.text_input("Nombre:", value=datos_prod['Producto'])
                        nuevo_precio = st.number_input("Precio ($):", value=float(str(datos_prod['Precio']).replace(',','.')), step=0.01)
                        
                        if st.button("💾 Guardar Cambios"):
                            fila = int(datos_prod['fila_excel'])
                            # Actualizamos columnas A (Producto) y D (Precio) - Ajusta según tu orden de Excel
                            sheet.update_cell(fila, 1, nuevo_nombre)
                            sheet.update_cell(fila, 4, nuevo_precio)
                            st.success(f"¡{prod_a_editar} actualizado!")
                            st.rerun()

                    with col_del:
                        st.markdown("### 🗑️ Eliminar")
                        opcion_borrar = st.radio("Tipo de borrado:", ["Un solo producto", "TODO el inventario de esta sucursal"])
                        
                        if opcion_borrar == "Un solo producto":
                            prod_a_borrar = st.selectbox("Producto a eliminar:", mis_datos['Producto'].unique(), key="del_uno")
                            if st.button("❌ Eliminar Producto"):
                                fila_b = int(mis_datos[mis_datos['Producto'] == prod_a_borrar].iloc[0]['fila_excel'])
                                sheet.delete_rows(fila_b)
                                st.warning(f"Producto {prod_a_borrar} eliminado.")
                                st.rerun()
                        
                        else:
                            st.error("⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER")
                            if st.button("💣 BORRAR TODO EL INVENTARIO"):
                                # Borramos de abajo hacia arriba para no dañar los índices
                                filas_a_borrar = sorted(mis_datos['fila_excel'].tolist(), reverse=True)
                                for f in filas_a_borrar:
                                    sheet.delete_rows(f)
                                st.success(f"Inventario de {sucursal_sel} limpiado por completo.")
                                st.rerun()
                else:
                    st.warning("No hay productos para esta sucursal.")

    with t2:
        st.subheader("🚀 Guía de Carga Rápida")
        # --- GENERADOR DE LINKS ---
        with st.expander("🖼️ GENERADOR DE LINKS PARA FOTOS"):
            foto_file = st.file_uploader("Elige imagen", type=['jpg','png','jpeg'])
            if foto_file and st.button("Generar Link"):
                api_key = "TU_API_KEY_AQUI" 
                res = requests.post("https://api.imgbb.com/1/upload", {"key": api_key}, files={"image": foto_file.getvalue()})
                if res.json()["success"]:
                    link = res.json()["data"]["url"]
                    st.success("Copia este link:")
                    st.code(link)
                else: st.error("Error al subir")

        st.divider()
        # --- CARGA EXCEL ---
        up = st.file_uploader("Sube tu archivo Excel", type=['xlsx'])
        if up and st.button("🚀 Publicar Inventario"):
            df_up = pd.read_excel(up)
            # Normalizamos precios a punto decimal antes de subir
            df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
            df_up['Fecha'] = datetime.now().strftime("%d/%m %I:%M %p")
            sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Productos publicados!")

    with t3:
        st.subheader("🚀 Planes Premium")
        # Aquí va el código de los planes Bronce, Plata y Oro que ya tenemos
        st.write("Selecciona un plan para destacar tus productos.")
        st.divider()
        
        # --- CARGA EXCEL ---
        st.subheader("Cargar Plantilla")
        # Botón para descargar plantilla
        cols = ["Producto", "Tienda", "Zona", "Precio", "WhatsApp", "Categoria", "Pago", "Calificacion", "Foto"]
        df_p = pd.DataFrame([["Ejemplo", st.session_state["user_name"], "Norte", 1.0, "58412...", "Víveres", "Efectivo", 5, "link-foto"]], columns=cols)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as wr: df_p.to_excel(wr, index=False)
        st.download_button("📥 Descargar Plantilla", data=buf.getvalue(), file_name="plantilla_pillalo.xlsx")
        
        up = st.file_uploader("Sube tu archivo relleno", type=['xlsx'])
        if up and st.button("🚀 Publicar"):
            df_up = pd.read_excel(up)
            df_up['Precio'] = df_up['Precio'].astype(str).str.replace(',', '.').astype(float)
            df_up['Fecha'] = datetime.now().strftime("%d/%m %I:%M %p")
            sheet.append_rows(df_up.values.tolist(), value_input_option='USER_ENTERED')
            st.success("¡Productos publicados con éxito!")

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
            * Sello de 'Tienda Verificada'.
            * Apareces arriba de los 'Invitados'.
            * Soporte vía WhatsApp.
            """)
            if st.button("Elegir Bronce", key="plan_b"):
                st.session_state["plan_elegido"] = "BRONCE"
                st.toast("Has seleccionado el Plan Bronce")

        with col_silver:
            st.success("### 🥈 PLATA")
            st.markdown("""
            **Costo: $15 / mes**
            * Todo lo del plan Bronce.
            * **3 Ofertas Flash** al mes.
            * Logo de tu tienda en la vitrina.
            """)
            if st.button("Elegir Plata", key="plan_s"):
                st.session_state["plan_elegido"] = "PLATA"
                st.toast("Has seleccionado el Plan Plata")

        with col_gold:
            st.warning("### 🥇 ORO")
            st.markdown("""
            **Costo: $40 / mes**
            * Todo lo del plan Plata.
            * **Ofertas Flash Ilimitadas**.
            * Banner publicitario en el inicio.
            * Analítica de clics semanal.
            """)
            if st.button("Elegir Oro", key="plan_g"):
                st.session_state["plan_elegido"] = "ORO"
                st.toast("Has seleccionado el Plan Oro")

        st.divider()

        # --- SECCIÓN DE OFERTAS FLASH ---
        col_flash, col_pago = st.columns(2)
        
        with col_flash:
            st.markdown("### 🔥 Activar Oferta Flash")
            st.caption("Destaca un producto con un cronómetro y precio especial por 24h.")
            # Solo dejamos elegir si tiene productos
            if not mis_datos.empty:
                prod_f = st.selectbox("Selecciona Producto:", mis_datos['Producto'].unique())
                desc = st.slider("Descuento a aplicar (%)", 5, 50, 20)
                if st.button("🚀 Lanzar Oferta Flash"):
                    st.success(f"Solicitud enviada para poner {prod_f} en Oferta Flash.")
                    registrar_estadistica("MARKETING_FLASH", f"{st.session_state['user_name']} solicita flash para {prod_f}")
            else:
                st.warning("Carga productos primero para activar ofertas.")

        with col_pago:
            st.markdown("### 💳 Confirmar suscripción")
            plan_sel = st.session_state.get("plan_elegido", "Ninguno")
            st.write(f"Plan seleccionado: **{plan_sel}**")
            
            if plan_sel != "Ninguno":
                metodo = st.selectbox("Método de Pago:", ["Pago Móvil", "Zelle", "Efectivo (Oficina)", "Binance P2P"])
                ref = st.text_input("Número de Referencia / Comprobante:")
                
                if st.button("Confirmar Pago y Activar 🚀"):
                    if ref:
                        st.balloons()
                        st.success("¡Recibido! El equipo de Píllalo verificará el pago y activará tus beneficios en breve.")
                        registrar_estadistica("PAGO_PREMIUM", f"{st.session_state['user_name']} pagó {plan_sel} - Ref: {ref}")
                    else:
                        st.error("Por favor ingresa el número de referencia.")


st.divider()
st.caption(f"Píllalo 2026 - Maracaibo | Tasa BCV: {tasa_bcv} Bs.")