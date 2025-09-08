import logging
import time
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.builtin import CommandStart

from .config import (
    BOT_TOKEN, ADMIN_TG_ID, BASE_URL,
    PLAN_PRICE_ETB, MIN_WITHDRAW_ETB, REFERRAL_BONUS_ETB, SUBSCRIPTION_DAYS
)
from . import db
from .payments import create_tx_ref, initialize_checkout

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

CURRENCY = "ETB"

def fmt_money(cents: int) -> str:
    return f"{(cents or 0)/100:.2f} {CURRENCY}"

@dp.message_handler(CommandStart())
async def start(message: types.Message):
    tg_id = message.from_user.id
    my_ref = db.ensure_user(tg_id)
    args = message.get_args()
    if args:
        db.set_referred_by(tg_id, args.strip())
    text = (
        "👋 <b>Welcome!</b>\\n\\n"
        f"• Subscription: <b>{PLAN_PRICE_ETB} {CURRENCY}/30 days</b>\\n"
        f"• Referral bonus: <b>{REFERRAL_BONUS_ETB} {CURRENCY}</b> per friend who subscribes\\n"
        f"• Withdraw when balance ≥ <b>{MIN_WITHDRAW_ETB} {CURRENCY}</b>\\n\\n"
        "Use /subscribe to pay, /referral to invite friends, /balance to check earnings."
    )
    await message.answer(text)

@dp.message_handler(commands=["terms"])
async def terms(message: types.Message):
    text = (
        "<b>Terms</b>\\n"
        "- Referral is single-level only. You earn a one-time bonus when your friend pays.\\n"
        "- No guaranteed returns or investments.\\n"
        f"- Minimum withdrawal: {MIN_WITHDRAW_ETB} {CURRENCY}.\\n"
        "- Payouts via telebirr (processed periodically).\\n"
        "- Abuse/fraud leads to account closure."
    )
    await message.answer(text)

@dp.message_handler(commands=["referral"])
async def referral(message: types.Message):
    tg_id = message.from_user.id
    ref_code = db.ensure_user(tg_id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={ref_code}"
    await message.answer(
        "🔗 <b>Your referral link</b>\\n"
        f"{link}\\n\\n"
        f"Earn {REFERRAL_BONUS_ETB} {CURRENCY} when each friend subscribes."
    )

@dp.message_handler(commands=["subscribe"])
async def subscribe(message: types.Message):
    tg_id = message.from_user.id
    db.ensure_user(tg_id)
    tx_ref = create_tx_ref(tg_id)
    callback_url = f"{BASE_URL}/webhook/chapa" if BASE_URL else ""
    return_url = f"https://t.me/{(await bot.get_me()).username}"
    meta = {"tg_id": tg_id}
    email = f"user{tg_id}@example.com"
    first_name = message.from_user.first_name or "TG"
    last_name = str(tg_id)
    try:
        checkout = initialize_checkout(PLAN_PRICE_ETB, email, first_name, last_name, tx_ref, callback_url, return_url, meta)
    except Exception as e:
        await message.answer(f"❌ Payment init failed: {e}")
        return
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Pay {PLAN_PRICE_ETB} ETB (telebirr)", url=checkout))
    await message.answer(
        f"💳 Pay <b>{PLAN_PRICE_ETB} {CURRENCY}</b> to activate 30 days. After paying, you'll be redirected back here.\\n"
        "If payment succeeds, you'll receive a confirmation in minutes.",
        reply_markup=kb
    )

@dp.message_handler(commands=["balance"])
async def balance(message: types.Message):
    tg_id = message.from_user.id
    data = db.get_user(tg_id)
    if not data:
        db.ensure_user(tg_id)
        data = db.get_user(tg_id)
    _, phone, ref_code, referred_by, balance_cents, subscription_until, _ = data
    sub_text = "Inactive"
    if subscription_until and subscription_until > int(time.time()):
        days_left = int((subscription_until - int(time.time()))/86400)
        sub_text = f"Active ({days_left} days left)"
    await message.answer(
        f"🧾 <b>Subscription:</b> {sub_text}\\n"
        f"💰 <b>Referral balance:</b> {fmt_money(balance_cents)}\\n"
        f"📞 <b>Phone for payout:</b> {phone or 'not set'}\\n\\n"
        f"Use /withdraw to cash out when balance ≥ {MIN_WITHDRAW_ETB} {CURRENCY}."
    )

@dp.message_handler(commands=["withdraw"])
async def withdraw(message: types.Message):
    tg_id = message.from_user.id
    user = db.get_user(tg_id)
    if not user:
        db.ensure_user(tg_id)
        user = db.get_user(tg_id)
    _, phone, _, _, balance_cents, _, _ = user
    if (balance_cents or 0) < MIN_WITHDRAW_ETB*100:
        await message.answer(f"Your balance is below {MIN_WITHDRAW_ETB} {CURRENCY}. Keep inviting friends!")
        return
    await message.answer(
        "Send your <b>telebirr phone number</b> in the format: \\n"
        "<code>/phone 09XXXXXXXX</code>"
    )

@dp.message_handler(commands=["phone"])
async def set_phone(message: types.Message):
    tg_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("Usage: /phone 09XXXXXXXX")
        return
    phone = parts[1]
    import sqlite3, os
    from pathlib import Path
    DB_PATH = os.path.join(Path(__file__).resolve().parent.parent, "data.sqlite")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("UPDATE users SET phone=? WHERE tg_id=?", (phone, tg_id))
    con.commit()
    con.close()
    await message.answer(f"✅ Phone set to {phone}. Now send /requestwithdraw <amount>")

@dp.message_handler(commands=["requestwithdraw"])
async def request_withdraw(message: types.Message):
    tg_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("Usage: /requestwithdraw <amount_etb> (>=150)")
        return
    try:
        amount_etb = int(parts[1])
    except ValueError:
        await message.answer("Amount must be a number.")
        return
    if amount_etb < MIN_WITHDRAW_ETB:
        await message.answer(f"Minimum is {MIN_WITHDRAW_ETB} {CURRENCY}.")
        return
    user = db.get_user(tg_id)
    _, phone, _, _, balance_cents, _, _ = user
    if not phone:
        await message.answer("Set your payout phone first: /phone 09XXXXXXXX")
        return
    cents = amount_etb*100
    if (balance_cents or 0) < cents:
        await message.answer("Insufficient balance.")
        return
    pid = db.create_payout_request(tg_id, cents, phone)
    await message.answer(f"✅ Payout request created (ID: {pid}) — you'll be paid to {phone}.")

@dp.message_handler(commands=["admin"])
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_TG_ID:
        return
    args = message.text.split(maxsplit=2)
    if len(args) == 1:
        await message.answer("Admin cmds: /admin pending | /admin payout <id> paid")
        return
    if args[1] == "pending":
        rows = db.list_pending_payouts()
        if not rows:
            await message.answer("No pending payouts.")
            return
        text = "Pending payouts:\\n"
        for r in rows:
            pid, tg_id, amount_cents, phone, status, created_at = r
            text += f"#{pid} user:{tg_id} amount:{amount_cents/100:.2f} {CURRENCY} phone:{phone} since:{time.strftime('%Y-%m-%d %H:%M', time.localtime(created_at))}\\n"
        await message.answer(text)
    elif args[1] == "payout" and len(args) == 3:
        parts = args[2].split()
        if len(parts) != 2 or parts[1] != "paid":
            await message.answer("Usage: /admin payout <id> paid")
            return
        try:
            pid = int(parts[0])
        except ValueError:
            await message.answer("Invalid payout id.")
            return
        db.mark_payout_paid(pid)
        await message.answer(f"Payout #{pid} marked as PAID.")
    else:
        await message.answer("Unknown admin command.")

if __name__ == "__main__":
    db.ensure_user(0)
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
