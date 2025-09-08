import sqlite3
import time
import os
import sys
from pathlib import Path

DB_PATH = os.path.join(Path(__file__).resolve().parent.parent, "data.sqlite")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  tg_id INTEGER PRIMARY KEY,
  phone TEXT,
  ref_code TEXT UNIQUE,
  referred_by TEXT,
  balance_cents INTEGER DEFAULT 0,
  subscription_until INTEGER DEFAULT 0,
  created_at INTEGER
);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tx_ref TEXT UNIQUE,
  tg_id INTEGER,
  amount_cents INTEGER,
  status TEXT,
  provider_txn_id TEXT,
  created_at INTEGER
);

CREATE TABLE IF NOT EXISTS referrals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  referrer_tg_id INTEGER,
  referee_tg_id INTEGER,
  amount_cents INTEGER,
  status TEXT,
  created_at INTEGER
);

CREATE TABLE IF NOT EXISTS payouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_id INTEGER,
  amount_cents INTEGER,
  phone TEXT,
  status TEXT,
  created_at INTEGER,
  paid_at INTEGER
);
"""

def connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = connect()
    cur = con.cursor()
    cur.executescript(SCHEMA)
    con.commit()
    con.close()

def ensure_user(tg_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT tg_id, ref_code FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    if row:
        con.close()
        return row[1]
    import random, string
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    ref_code = f"{str(tg_id)[-3:]}{rand}"
    cur.execute("INSERT INTO users (tg_id, ref_code, created_at) VALUES (?, ?, ?)", (tg_id, ref_code, int(time.time())))
    con.commit()
    con.close()
    return ref_code

def set_referred_by(tg_id, ref_code):
    if not ref_code:
        return
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT tg_id FROM users WHERE ref_code = ?", (ref_code,))
    owner = cur.fetchone()
    if not owner:
        con.close()
        return
    owner_id = owner[0]
    if owner_id == tg_id:
        con.close()
        return
    cur.execute("SELECT referred_by FROM users WHERE tg_id = ?", (tg_id,))
    rb = cur.fetchone()
    if rb and (rb[0] is None or rb[0] == ""):
        cur.execute("UPDATE users SET referred_by = ? WHERE tg_id = ?", (ref_code, tg_id))
    con.commit()
    con.close()

def save_payment(tx_ref, tg_id, amount_cents, status, provider_txn_id=None):
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO payments (tx_ref, tg_id, amount_cents, status, provider_txn_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (tx_ref, tg_id, amount_cents, status, provider_txn_id, int(time.time())))
    con.commit()
    con.close()

def mark_payment_success(tx_ref, provider_txn_id):
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE payments SET status='success', provider_txn_id=? WHERE tx_ref=?", (provider_txn_id, tx_ref))
    con.commit()
    con.close()

def grant_subscription_and_referral(tg_id, plan_days, bonus_cents):
    now = int(time.time())
    add_until = now + plan_days * 86400
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT subscription_until, referred_by FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    referred_by = None
    if row:
        current_until, referred_by = row
        if current_until and current_until > now:
            new_until = current_until + plan_days * 86400
        else:
            new_until = add_until
        cur.execute("UPDATE users SET subscription_until = ? WHERE tg_id = ?", (new_until, tg_id))
    if referred_by:
        cur.execute("SELECT tg_id FROM users WHERE ref_code = ?", (referred_by,))
        r = cur.fetchone()
        if r:
            referrer_id = r[0]
            cur.execute("UPDATE users SET balance_cents = COALESCE(balance_cents,0) + ? WHERE tg_id = ?", (bonus_cents, referrer_id))
            cur.execute("INSERT INTO referrals (referrer_tg_id, referee_tg_id, amount_cents, status, created_at) VALUES (?, ?, ?, 'earned', ?)",
                        (referrer_id, tg_id, bonus_cents, now))
    con.commit()
    con.close()

def get_user(tg_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT tg_id, phone, ref_code, referred_by, balance_cents, subscription_until, created_at FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    con.close()
    return row

def create_payout_request(tg_id, amount_cents, phone):
    now = int(time.time())
    con = connect()
    cur = con.cursor()
    cur.execute("INSERT INTO payouts (tg_id, amount_cents, phone, status, created_at) VALUES (?, ?, ?, 'pending', ?)", (tg_id, amount_cents, phone, now))
    cur.execute("UPDATE users SET balance_cents = balance_cents - ? WHERE tg_id = ?", (amount_cents, tg_id))
    con.commit()
    cur.execute("SELECT last_insert_rowid()")
    pid = cur.fetchone()[0]
    con.close()
    return pid

def list_pending_payouts(limit=20):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT id, tg_id, amount_cents, phone, status, created_at FROM payouts WHERE status='pending' ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return rows

def mark_payout_paid(payout_id):
    now = int(time.time())
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE payouts SET status='paid', paid_at=? WHERE id=?", (now, payout_id))
    con.commit()
    con.close()

if __name__ == "__main__":
    if "--init" in sys.argv:
        init_db()
        print("Database initialized at", DB_PATH)
