import os
from fastapi import FastAPI, Request, HTTPException
import telebot
import anyio

TOKEN = os.getenv("BOT_TOKEN")
SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://telegram-bot-XXXX.onrender.com

if not TOKEN or not SECRET or not WEBHOOK_URL:
    raise RuntimeError("Set BOT_TOKEN, WEBHOOK_SECRET and WEBHOOK_URL in environment")

bot = telebot.TeleBot(TOKEN)
app = FastAPI()

@app.on_event("startup")
def startup():
    # remove any old webhook and set the new one
    bot.remove_webhook()
    bot.set_webhook(f"{WEBHOOK_URL}/webhook/{SECRET}")

@app.get("/")
def root():
    return {"ok": True}

@app.post("/webhook/{secret}")
async def receive_update(secret: str, request: Request):
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    update = telebot.types.Update.de_json(data)
    # run processing in thread so we don't block the event loop
    await anyio.to_thread.run_sync(lambda: bot.process_new_updates([update]))
    return {"ok": True}
