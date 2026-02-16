import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configuración de seguridad
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# REVISA ESTO: El nombre debe ser igual al de tu archivo JSON
creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
client = gspread.authorize(creds)

# 2. Abrir la hoja de Google
# IMPORTANTE: "Pillalo_Data" debe ser el nombre exacto de tu Google Sheet
try:
    # Abrimos el archivo por su nombre y seleccionamos la primera pestaña
    sheet = client.open("Pillalo_Data").sheet1
    print("✅ ¡Conectado con éxito a Google Sheets!")
except Exception as e:
    print(f"❌ Error: No encontré la hoja. Revisa el nombre o los permisos. \nDetalle: {e}")
    exit()

def subir_precio(producto, tienda, zona, precio, whatsapp, categoria):
    try:
        # Preparamos la fila
        nueva_fila = [producto, tienda, zona, precio, whatsapp, categoria]
        # La pegamos al final de la hoja
        sheet.append_row(nueva_fila)
        print(f"🚀 '{producto}' subido con éxito a Pillalo!")
    except Exception as e:
        print(f"❌ Error al subir los datos: {e}")

# --- PRUEBA DE FUEGO ---
# Esto es lo que se ejecutará cuando corras el archivo
print("Enviando datos de prueba...")
subir_precio("Harina PAN", "Supermercado Fiorella", "Curva de Molina", 1.05, "584120000000", "Comida")