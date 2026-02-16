import streamlit as st
import pandas as pd

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Píllalo | El Rayo del Ahorro", page_icon="⚡")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Sustituye este link por el tuyo (asegúrate de que termine en /export?format=csv)
SHEET_ID = "1hoSlaN_VtGCmPOsLFhHCNpxsK-gFqABepTLaAKTaYWI" # El código largo que sale en el link de tu Google Sheet
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60) # Actualiza los datos cada 60 segundos
def cargar_datos():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except:
        st.error("⚠️ No pude conectar con la base de datos. Revisa el link.")
        return pd.DataFrame()

df = cargar_datos()

# --- INTERFAZ ---
st.markdown("<h1 style='text-align: center; color: #1E40AF;'>⚡ Píllalo</h1>", unsafe_allow_html=True)
st.write("---")

# Buscador
busqueda = st.text_input("🔍 ¿Qué buscáis hoy?", placeholder="Ej: Batería, Harina, Repuestos...")

if not df.empty:
    if busqueda:
        # Filtrar datos de la hoja de Google
        resultados = df[df['Producto'].str.contains(busqueda, case=False, na=False)]
        
        if not resultados.empty:
            resultados = resultados.sort_values(by="Precio")
            
            for index, row in resultados.iterrows():
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(f"{row['Producto']}")
                        st.caption(f"🏪 {row['Tienda']} | 📍 {row['Zona']}")
                    with col2:
                        st.markdown(f"### `${row['Precio']}`")
                        # Botón de WhatsApp
                        link_ws = f"https://wa.me/{row['WhatsApp']}?text=Hola, vi {row['Producto']} en Píllalo"
                        st.link_button("Pedir", link_ws)
                    st.divider()
        else:
            st.warning("No pillamos nada con ese nombre. ¡Probá con otra palabra!")
    else:
        st.info("Escribí arriba para buscar los mejores precios de Maracaibo.")
else:
    st.warning("La base de datos está vacía o desconectada.")

# --- BOTÓN PARA CARGAR (Solo tú o autorizados) ---
st.sidebar.title("Configuración")
if st.sidebar.button("🔄 Actualizar Precios"):
    st.cache_data.clear()
    st.rerun()