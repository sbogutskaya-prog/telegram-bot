

import telebot
import os
import time
import base64
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8708904862:AAGC_rjx1aPVeCD4TuVWNKAf-7fNjbMst80")
CHAT_ID = int(os.environ.get("CHAT_ID", "-4886040653"))
FOLDER_ID = "1BR9-Ukm6nFbkAbx2OJzUFCq_N3--Vk-p"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

bot = telebot.TeleBot(BOT_TOKEN)

def get_drive_service():
    creds = None
    google_token = os.environ.get("GOOGLE_TOKEN")
    if google_token:
        creds = pickle.loads(base64.b64decode(google_token))
    elif os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds)

def get_folders():
    service = get_drive_service()
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name)"
    ).execute()
    return results.get("files", [])

def get_photos(folder_id):
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'image/'",
        fields="files(id, name)",
        pageSize=200
    ).execute()
    return results.get("files", [])

def get_first_photo_url(folder_id):
    photos = get_photos(folder_id)
    if photos:
        return f"https://drive.google.com/uc?export=download&id={photos[0]['id']}", len(photos)
    return None, 0

@bot.message_handler(commands=["menu", "start"])
def show_menu(message):
    folders = get_folders()
    if not folders:
        bot.send_message(message.chat.id, "Папки не найдены")
        return
    bot.send_message(message.chat.id, "📁 Выбери мероприятие:")
    for folder in folders:
        url, count = get_first_photo_url(folder['id'])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            f"📂 Открыть все {count} фото", callback_data=f"folder_{folder['id']}"
        ))
        caption = f"📁 *{folder['name']}*\n🖼 {count} фото"
        if url:
            try:
                bot.send_photo(message.chat.id, url, caption=caption, parse_mode="Markdown", reply_markup=markup)
            except:
                bot.send_message(message.chat.id, caption, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, parse_mode="Markdown", reply_markup=markup)
        time.sleep(0.5)

@bot.callback_query_handler(func=lambda call: call.data.startswith("folder_"))
def show_photos(call):
    folder_id = call.data.replace("folder_", "")
    photos = get_photos(folder_id)
    if not photos:
        bot.answer_callback_query(call.id, "Фото не найдены")
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"Загружаю {len(photos)} фото...")
    for i in range(0, len(photos), 10):
        batch = photos[i:i+10]
        media = []
        for photo in batch:
            url = f"https://drive.google.com/uc?export=download&id={photo['id']}"
            media.append(telebot.types.InputMediaPhoto(url))
        try:
            bot.send_media_group(call.message.chat.id, media)
            time.sleep(3)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

print("Бот запущен!")
bot.polling()