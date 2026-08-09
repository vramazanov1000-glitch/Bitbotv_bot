import os
from flask import Flask
import telebot

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# Простой сервер, чтобы Render не усыплял бота
app = Flask('')

@app.route('/')
def home():
    return "Bitbotv is alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет, Васиф! Бот успешно запущен на Render и готов к работе 🚀")

if __name__ == '__main__':
    import threading
    t = threading.Thread(target=run_web)
    t.start()
    bot.infinity_polling()