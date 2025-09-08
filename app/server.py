from fastapi import FastAPI, Request, HTTPException
from .config import BASE_URL, PLAN_PRICE_ETB, SUBSCRIPTION_DAYS, REFERRAL_BONUS_ETB
from .payments import verify_payment
from . import db

app = FastAPI(title="Webhook Server")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/webhook/chapa")
async def chapa_webhook(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    tx_ref = body.get("tx_ref") or (body.get("data") or {}).get("tx_ref")
    if not tx_ref:
        tx_ref = req.query_params.get("tx_ref")
    if not tx_ref:
        raise HTTPException(status_code=400, detail="Missing tx_ref")
    try:
        verification = verify_payment(tx_ref)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"verify error: {e}")
    status = (verification.get("data") or {}).get("status")
    amount = (verification.get("data") or {}).get("amount")
    tx_ref_v = (verification.get("data") or {}).get("tx_ref")
    provider_txn_id = (verification.get("data") or {}).get("reference")
    meta = (verification.get("data") or {}).get("meta") or {}
    tg_id = int(meta.get("tg_id", "0"))
    if status == "success" and tx_ref == tx_ref_v and int(float(amount)) >= PLAN_PRICE_ETB and tg_id:
        db.mark_payment_success(tx_ref, provider_txn_id)
        db.grant_subscription_and_referral(tg_id, SUBSCRIPTION_DAYS, int(REFERRAL_BONUS_ETB*100))
        return {"ok": True}
    else:
        raise HTTPException(status_code=400, detail="Payment not successful or invalid amount")
