import time
import requests
import json
from .config import CHAPA_API_URL, CHAPA_SECRET_KEY

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
}

def create_tx_ref(tg_id: int) -> str:
    return f"sub-{tg_id}-{int(time.time())}"

def initialize_checkout(amount_etb: int, email: str, first_name: str, last_name: str, tx_ref: str, callback_url: str, return_url: str, meta: dict):
    payload = {
        "amount": str(amount_etb),
        "currency": "ETB",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": callback_url,
        "return_url": return_url,
        "customization": {
            "title": "Premium Subscription",
            "description": f"{amount_etb} ETB / 30 days"
        },
        "meta": meta or {}
    }
    url = f"{CHAPA_API_URL}/transaction/initialize"
    resp = requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    checkout_url = (data.get("data") or {}).get("checkout_url") or (data.get("data") or {}).get("authorization_url")
    if not checkout_url:
        raise RuntimeError(f"Unexpected response from Chapa: {data}")
    return checkout_url

def verify_payment(tx_ref: str):
    url = f"{CHAPA_API_URL}/transaction/verify/{tx_ref}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()
