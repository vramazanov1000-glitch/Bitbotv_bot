import os
import telebot

# Получаем токен из переменных окружения Render
TOKEN = os.getenv('BOT_TOKEN')

# Проверка, что токен подгрузился
if not TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет, Васиф! Бот успешно запущен и работает! 🚀")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

if __name__ == '__main__':
    print("Бот запущен и ожидает сообщения...")
    bot.infinity_polling()
