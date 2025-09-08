# bot.py - Telegram bot ready for Render webhook

import telebot
from flask import Flask, request

# =============================
# CONFIG
# =============================
BOT_TOKEN = "8485995133:AAFIkJxi4bFftyA5hCgCZ4d45utPzBOfCYo"
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =============================
# COMMAND HANDLERS
# =============================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Hello! Bot is live on Render.\nUse /help to see commands.")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "📖 Available commands:\n/start - Start bot\n/help - Show this message")

# Fallback handler for any other message
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "⚠️ Please use /start or /help")

# =============================
# WEBHOOK
# =============================
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# =============================
# RUN FLASK APP
# =============================
if __name__ == "__main__":
    print("🤖 Bot is starting on Render...")
    app.run(host="0.0.0.0", port=5000)
