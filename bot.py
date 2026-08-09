import os
import telebot

# Получаем токен из переменных окружения Render
TOKEN = os.getenv('BOT_TOKEN')

# Проверка, что токен вообще подгрузился
if not TOKEN:
    raise ValueError("Не задан BOT_TOKEN в переменных окружения!")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот успешно запущен и работает! 🚀")

if __name__ == '__main__':
    print("Бот запущен и ожидает сообщения...")
    bot.infinity_polling()
