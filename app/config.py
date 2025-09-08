import os
from dotenv import load_dotenv
load_dotenv()

# Business rules
PLAN_PRICE_ETB = 200
REFERRAL_BONUS_ETB = 15
MIN_WITHDRAW_ETB = 150
SUBSCRIPTION_DAYS = 30

# Env
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))
BASE_URL = os.getenv("BASE_URL", "")  # public URL for webhook server

# Chapa
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY", "")
CHAPA_PUBLIC_KEY = os.getenv("CHAPA_PUBLIC_KEY", "")
CHAPA_API_URL = os.getenv("CHAPA_API_URL", "https://api.chapa.co/v1")

if not BOT_TOKEN:
    print("Warning: BOT_TOKEN not set in .env")
