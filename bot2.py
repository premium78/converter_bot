import telebot

import os

import sqlite3

import subprocess

from telebot import types

from PIL import Image

from datetime import datetime





# --- Configuration ---

API_TOKEN = '8290180916:AAHTmjUny7BLGr9MqMyANV7IMmU6lChIotM'

bot = telebot.TeleBot(API_TOKEN)





# টেম্পোরারি ডাটা স্টোর

user_mode = {} 

user_photos = {} 





# --- Keyboards ---

def main_menu():

    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)

    markup.add("🔄 Converter")

    return markup





def converter_menu():

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(

        types.InlineKeyboardButton("🖼️ Photos → PDF", callback_data="p_to_pdf"),

        types.InlineKeyboardButton("🎥 Video → Audio", callback_data="v_to_a"),

        types.InlineKeyboardButton("✍️ Text → TXT File", callback_data="t_to_txt")

    )

    return markup





# --- Handlers ---

@bot.message_handler(commands=['start'])

def start(message):

    # পাসওয়ার্ড সিস্টেম রিমুভ করা হয়েছে, সরাসরি মেনু আসবে

    bot.send_message(

        message.chat.id, 

        "👋 Welcome! নিচে থাকা বাটনে ক্লিক করে কাজ শুরু করুন।", 

        reply_markup=main_menu()

    )





@bot.message_handler(func=lambda m: m.text == "🔄 Converter")

def open_converter(message):

    bot.send_message(message.chat.id, "⚡ **Select Converter Option**", reply_markup=converter_menu(), parse_mode="Markdown")





@bot.callback_query_handler(func=lambda call: True)

def callback_query(call):

    uid = call.from_user.id

    

    if call.data == "p_to_pdf":

        user_mode[uid] = "PDF_MODE"

        user_photos[uid] = []

        bot.edit_message_text("📸 **আপনার ফটো পাঠান...**", 

                              call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    

    elif call.data == "t_to_txt":

        user_mode[uid] = "TXT_MODE"

        bot.edit_message_text("✍️ আপনি যে লেখাটি টেক্সট ফাইল বানাতে চান সেটি লিখে পাঠান:", 

                              call.message.chat.id, call.message.message_id)





    elif call.data == "v_to_a":

        user_mode[uid] = "AUDIO_MODE"

        bot.edit_message_text("🎥 অডিও করার জন্য ভিডিওটি পাঠান:", call.message.chat.id, call.message.message_id)





    elif call.data == "make_pdf_now":

        if uid in user_photos and user_photos[uid]:

            create_pdf(call.message, uid)

        else:

            bot.answer_callback_query(call.id, "⚠️ কোনো ফটো পাননি!", show_alert=True)





@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])

def handle_incoming_files(message):

    uid = message.from_user.id

    mode = user_mode.get(uid)





    if not mode:

        return





    # Photo to PDF Logic

    if mode == "PDF_MODE" and message.content_type == 'photo':

        file_info = bot.get_file(message.photo[-1].file_id)

        downloaded = bot.download_file(file_info.file_path)

        path = f"img_{message.message_id}_{uid}.jpg"

        

        with open(path, 'wb') as f:

            f.write(downloaded)

        

        if uid not in user_photos:

            user_photos[uid] = []

        user_photos[uid].append(path)

        

        markup = types.InlineKeyboardMarkup()

        markup.add(types.InlineKeyboardButton(f"✅ পিডিএফ করতে এখানে ক্লিক করুন ({len(user_photos[uid])})", callback_data="make_pdf_now"))

        bot.reply_to(message, "📥 ফটো পাওয়া গেছে! আরও ফটো দিন অথবা কনফার্ম করতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

        return





    # Text to TXT Logic

    if mode == "TXT_MODE" and message.text:

        status = bot.reply_to(message, "📄 ফাইল তৈরি হচ্ছে...")

        file_path = f"Note_{uid}.txt"

        with open(file_path, "w", encoding="utf-8") as f:

            f.write(message.text)

        

        with open(file_path, "rb") as f:

            bot.send_document(message.chat.id, f, caption="✅ আপনার টেক্সট ফাইল!")

        

        os.remove(file_path)

        bot.delete_message(message.chat.id, status.message_id)

        user_mode[uid] = None

        return





    # Video to Audio Logic

    if mode == "AUDIO_MODE" and message.content_type == 'video':

        status = bot.reply_to(message, "⏳ ভিডিও থেকে অডিও করা হচ্ছে...")

        file_info = bot.get_file(message.video.file_id)

        downloaded = bot.download_file(file_info.file_path)

        v_path, a_path = f"v_{uid}.mp4", f"a_{uid}.mp3"

        

        with open(v_path, "wb") as f:

            f.write(downloaded)

        

        subprocess.run(f"ffmpeg -i {v_path} -vn -acodec libmp3lame -q:a 2 {a_path} -y", shell=True)

        

        with open(a_path, "rb") as a:

            bot.send_audio(message.chat.id, a, caption="✅ অডিও তৈরি সফল!")

            

        os.remove(v_path)

        os.remove(a_path)

        bot.delete_message(message.chat.id, status.message_id)

        user_mode[uid] = None

        return





def create_pdf(message, uid):

    status = bot.send_message(message.chat.id, "📑 পিডিএফ তৈরি হচ্ছে...")

    pdf_path = f"Storage_{uid}.pdf"

    try:

        images = [Image.open(p).convert('RGB') for p in user_photos[uid]]

        images[0].save(pdf_path, save_all=True, append_images=images[1:])

        

        with open(pdf_path, "rb") as f:

            bot.send_document(message.chat.id, f, caption=f"✅ সফলভাবে পিডিএফ তৈরি হয়েছে!")

        

        # ফাইল ক্লিনআপ

        for p in user_photos[uid]:

            if os.path.exists(p): os.remove(p)

        if os.path.exists(pdf_path): os.remove(pdf_path)

        

        user_photos[uid] = []

        user_mode[uid] = None

    except Exception as e:

        bot.send_message(message.chat.id, f"❌ ভুল হয়েছে: {str(e)}")

    

    bot.delete_message(message.chat.id, status.message_id)





print("🚀 বট সফলভাবে চালু হয়েছে (পাসওয়ার্ড ছাড়া)...")

bot.polling(none_stop=True)
