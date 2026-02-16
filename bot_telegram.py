import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Conexión a Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credenciales.json', scope)
client = gspread.authorize(creds)
sheet = client.open("Pillalo_Data").sheet1

# 2. Configuración del Bot (PEGA TU TOKEN AQUÍ)
TOKEN = "8370053677:AAH2Ro5VRcl2nVgho1GIh2F7OnlqX-b_HFg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ ¡Epa, Pillalo! Mandame el producto así:\n\n"
        "Producto, Tienda, Zona, Precio, WhatsApp, Categoria\n\n"
        "Ejemplo: Harina, Candido, Delicias, 1.05, 584121234567, Comida"
    )

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    try:
        # Separamos los datos por la coma
        datos = [d.strip() for d in texto.split(",")]
        
        if len(datos) == 6:
            # Subimos a Google Sheets
            sheet.append_row(datos)
            await update.message.reply_text(f"✅ ¡Pillado! '{datos[0]}' ya está en la App.")
        else:
            await update.message.reply_text("❌ Primo, faltan datos. Son 6 campos separados por coma.")
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))
    
    print("🚀 Bot de Pillalo encendido...")
    app.run_polling()