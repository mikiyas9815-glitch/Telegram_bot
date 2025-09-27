import os
from flask import Flask, request, abort
import telebot

# --- Required environment variables ---
TOKEN = os.environ.get("BOT_TOKEN")            # set this in Render
SECRET = os.environ.get("WEBHOOK_SECRET")      # set this in Render (random string)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")    # set this to your render app URL (see dashboard)

if not TOKEN or not SECRET or not WEBHOOK_URL:
    raise RuntimeError("BOT_TOKEN, WEBHOOK_SECRET and WEBHOOK_URL must be set in environment")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route(f"/webhook/{SECRET}", methods=["POST"])
def webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

# Example handler - change this to your real handlers
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Hello — webhook is working 🚀")

# Set webhook on module import (works with gunicorn)
bot.remove_webhook()
bot.set_webhook(f"{WEBHOOK_URL}/webhook/{SECRET}")
