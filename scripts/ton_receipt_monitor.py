#!/usr/bin/env python3
"""Immortal Guard TON receipt monitor.

Monitors the configured temporary TON receiving address using TON Center API.
This does not sign, claim, transfer, or custody anything. It only detects
incoming on-chain activity and records receipts for the Guard dashboard.

TEMP_TON_ADDRESS is intentionally an environment variable so no wallet secret
or private key ever enters the repository.
"""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/ton_receipts.json")
STATE = Path("data/ton_receipt_state.json")
API = os.getenv("TONCENTER_API_URL", "https://toncenter.com/api/v2")
API_KEY = os.getenv("TONCENTER_API_KEY", "")
ADDRESS = os.getenv("TEMP_TON_ADDRESS", "").strip()

def get(path, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API.rstrip('/')}/{path}?{q}",
                                 headers={"User-Agent":"ImmortalGuard/1.0",
                                          **({"X-API-Key":API_KEY} if API_KEY else {})})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def load(p, default):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default

def main():
    now = datetime.now(timezone.utc).isoformat()
    if not ADDRESS:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "version":1,"updatedAt":now,"configured":False,"address":None,
            "count":0,"receipts":[],
            "status":"WAITING_FOR_TEMP_TON_ADDRESS",
            "safety":{"signing":False,"transfer":False,"secretStorage":False}
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("TON receipt monitor: TEMP_TON_ADDRESS not configured")
        return
    data = get("getTransactions", {"address":ADDRESS,"limit":100})
    txs = data.get("result", []) if data.get("ok", True) else []
    old = load(STATE, {"seen":[]})
    seen = set(old.get("seen", []))
    receipts = load(OUT, {"receipts":[]}).get("receipts", [])
    for tx in txs:
        txid = tx.get("transaction_id", {})
        key = f"{txid.get('lt','')}:{txid.get('hash','')}"
        if not key.strip(":") or key in seen:
            continue
        in_msg = tx.get("in_msg", {}) or {}
        value = in_msg.get("value")
        if value and str(value) != "0":
            receipts.append({
                "tx":key,
                "address":ADDRESS,
                "valueNanoTON":str(value),
                "source":in_msg.get("source"),
                "destination":in_msg.get("destination"),
                "timestamp":tx.get("utime"),
                "detectedAt":now
            })
        seen.add(key)
    receipts = receipts[-1000:]
    STATE.write_text(json.dumps({"version":1,"seen":list(seen)[-5000:]},indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({
        "version":1,"updatedAt":now,"configured":True,"address":ADDRESS,
        "count":len(receipts),"receipts":receipts,
        "status":"MONITORING",
        "note":"Incoming activity only. No automatic claim, signing or transfer.",
        "safety":{"signing":False,"transfer":False,"secretStorage":False}
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"TON receipt monitor: address configured; receipts={len(receipts)}")

if __name__ == "__main__": main()
