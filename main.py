import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes
import requests

# Configuration du bot Telegram
TELEGRAM_BOT_TOKEN = "7708331542:AAEkSO_E9c6WRZnK0BxO49UXLWOonLD85pM"
GEMINI_API_KEY = "AIzaSyCvvmosqHfcb08skdw___PlnFhUid7-ErQ"  # Clé chiffrée enregistrée

# ID de l'administrateur (à remplacer par l'ID réel)
ADMIN_ID = [7148392834]
# Configuration de l'API Gemini
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

# Dictionnaire pour stocker l'historique des conversations par utilisateur
user_sessions = {}

# Fonction pour gérer les messages texte
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if user_id not in user_sessions:
        user_sessions[user_id] = model.start_chat(history=[
            {"role": "user", "parts": ["Hi"]},
            {"role": "model", "parts": ["Hi there! How can I help you today?"]},
        ])

    chat_session = user_sessions[user_id]
    response = chat_session.send_message(user_message)

    await update.message.reply_text(response.text)

# Fonction pour gérer les images
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()  # Obtenir la meilleure qualité
    photo_url = photo_file.file_path

    # Télécharger l'image localement
    image_path = f"downloads/image_{user_id}.jpg"
    response = requests.get(photo_url)
    with open(image_path, "wb") as file:
        file.write(response.content)

    # Envoyer l'image à Gemini pour analyse
    chat_session = model.start_chat()
    gemini_response = chat_session.send_message(["Analyze this image:", image_path])

    await update.message.reply_text(gemini_response.text)

# Fonction pour gérer les messages vocaux (audio)
async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio_file = await update.message.voice.get_file()
    audio_url = audio_file.file_path

    # Télécharger l'audio localement
    audio_path = f"downloads/audio_{update.message.from_user.id}.ogg"
    response = requests.get(audio_url)
    with open(audio_path, "wb") as file:
        file.write(response.content)

    # Simuler une réponse (l'API Gemini ne supporte pas encore l'audio)
    await update.message.reply_text("I received your audio! Currently, I can't process voice messages, but I'm working on it!")

# Fonction pour la commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a text, image, or audio, and I'll try to respond.")

# Commande admin pour lister tous les utilisateurs
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Accès non autorisé.")
        return

    if not user_sessions:
        await update.message.reply_text("Aucun utilisateur trouvé.")
        return

    message = "Liste des utilisateurs :\n"
    for user_id in user_sessions.keys():
        message += f"User ID: {user_id}\n"
    await update.message.reply_text(message)

# Commande admin pour envoyer un message à tous les utilisateurs
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Accès non autorisé.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(args)
    count = 0
    for user_id in user_sessions.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi au user {user_id}: {e}")
    await update.message.reply_text(f"Message broadcast envoyé à {count} utilisateurs.")

# Commande admin pour envoyer un message à un utilisateur précis
async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Accès non autorisé.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /message <user_id> <message>")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("L'ID utilisateur doit être un nombre.")
        return

    message = " ".join(args[1:])
    try:
        await context.bot.send_message(chat_id=target_user_id, text=message)
        await update.message.reply_text("Message envoyé.")
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi au user {target_user_id}: {e}")
        await update.message.reply_text("Erreur lors de l'envoi du message.")

# Configuration du bot Telegram
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

    # Ajout des commandes d'administration
    app.add_handler(CommandHandler("listusers", list_users))
    app.add_handler(CommandHandler("broadcast", broadcast_message))
    app.add_handler(CommandHandler("message", send_message_to_user))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
