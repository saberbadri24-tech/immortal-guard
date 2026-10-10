#!/usr/bin/env python3
"""Immortal Guard TON receipt monitor.

Monitors the configured temporary TON receiving address using TON Center API.
This does not sign, claim, transfer, or custody anything. It only detects
incoming on-chain activity and records receipts for the Guard dashboard.

TEMP_TON_ADDRESS is intentionally an environment variable so no wallet secret
or private key ever enters the repository.
"""
import json, os, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/ton_receipts.json")
STATE = Path("data/ton_receipt_state.json")
TRANSFER = Path("data/transfer_state.json")
API = os.getenv("TONCENTER_API_URL", "https://toncenter.com/api/v2")
API_KEY = os.getenv("TONCENTER_API_KEY", "")
ADDRESS = os.getenv("TEMP_TON_ADDRESS", "").strip()
# Optional TON Connect address fallback for deployments that already expose the
# connected wallet address as a public repository variable. Never use secrets.
MAIN_ADDRESS = os.getenv("MAIN_TON_ADDRESS", "").strip()

if not ADDRESS:
    ADDRESS = os.getenv("TON_CONNECT_ADDRESS", "").strip()

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

def valid_ton_address(value):
    return bool(re.fullmatch(r'(?:EQ|UQ)[A-Za-z0-9_-]{46}|-?[01]:[0-9a-fA-F]{64}', str(value or '').strip()))

def main():
    global ADDRESS
    now = datetime.now(timezone.utc).isoformat()
    # Support the owner's existing temporary-wallet app/config record as well as
    # Render/GitHub variables. Prefer the first valid address; never import secrets.
    candidates = [ADDRESS, os.getenv('TON_CONNECT_ADDRESS', '').strip()]
    temp = load(Path('data/temp_wallet.json'), {})
    if temp.get('configured') is True:
        candidates.append(str(temp.get('address') or '').strip())
    ADDRESS = next((x for x in candidates if valid_ton_address(x)), '')
    if not ADDRESS:
        print('TON receipt monitor: no valid temporary TON address; failing closed')
    if not ADDRESS:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "version":2,"updatedAt":now,"configured":False,"address":None,
            "count":0,"receipts":[],"balanceNanoTON":None,"balanceTON":None,
            "status":"WAITING_FOR_TEMP_TON_ADDRESS",
            "transferStatus":"WAITING_FOR_TEMP_TON_ADDRESS",
            "safety":{"signing":False,"transfer":False,"secretStorage":False}
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        TRANSFER.write_text(json.dumps({
            "version":2,"updatedAt":now,"status":"WAITING_FOR_TEMP_TON_ADDRESS",
            "temporaryAddress":None,"permanentAddress":MAIN_ADDRESS or None,
            "observed":[],
            "rule":"Only an outgoing on-chain transaction from the configured temporary address to the configured permanent address is a verified transfer."
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("TON receipt monitor: TEMP_TON_ADDRESS not configured")
        return
    data = get("getTransactions", {"address":ADDRESS,"limit":100})
    txs = data.get("result", []) if data.get("ok", True) else []
    balance_data = get("getAddressBalance", {"address":ADDRESS})
    balance_raw = balance_data.get("result") if balance_data.get("ok", True) else None
    balance_nano = int(balance_raw) if str(balance_raw or "").isdigit() else None
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
    transfers = load(TRANSFER, {"version":1,"status":"NOT_CONFIGURED","destination":MAIN_ADDRESS or None,"observed":[]})
    observed = transfers.get("observed", [])
    if MAIN_ADDRESS:
        for tx in txs:
            txid = tx.get("transaction_id", {}) or {}
            key = f"{txid.get('lt','')}:{txid.get('hash','')}"
            for msg in (tx.get("out_msgs") or []):
                dest = str(msg.get("destination") or "").strip()
                value = msg.get("value")
                if not key.strip(":") or not dest or dest != MAIN_ADDRESS or value in (None, "", "0"):
                    continue
                item = {
                    "tx":key,"from":ADDRESS,"to":dest,"valueNanoTON":str(value),
                    "timestamp":tx.get("utime"),"detectedAt":now
                }
                if not any(x.get("tx")==key and x.get("to")==dest for x in observed):
                    observed.append(item)
        observed = observed[-500:]
        transfer_status = "VERIFIED_ONCHAIN" if observed else "READY_FOR_OWNER_SIGNED_TRANSFER"
    else:
        transfer_status = "WAITING_FOR_MAIN_TON_ADDRESS"
    TRANSFER.write_text(json.dumps({
        "version":1,"updatedAt":now,"status":transfer_status,
        "temporaryAddress":ADDRESS,"permanentAddress":MAIN_ADDRESS or None,
        "observed":observed,
        "rule":"Only an outgoing on-chain transaction from the configured temporary address to the configured permanent address is a verified transfer."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    STATE.write_text(json.dumps({"version":1,"seen":list(seen)[-5000:]},indent=2)+"\n",encoding="utf-8")
    OUT.write_text(json.dumps({
        "version":2,"updatedAt":now,"configured":True,"address":ADDRESS,
        "count":len(receipts),"receipts":receipts,
        "balanceNanoTON":str(balance_nano) if balance_nano is not None else None,
        "balanceTON":(balance_nano/1e9) if balance_nano is not None else None,
        "balanceVerifiedAt":now if balance_nano is not None else None,
        "status":"MONITORING",
        "transferStatus":transfer_status,
        "note":"Incoming activity is monitored; outgoing transfer is never signed automatically and is verified on-chain after owner signature.",
        "safety":{"signing":False,"transfer":False,"secretStorage":False}
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"TON receipt monitor: address configured; receipts={len(receipts)}")

if __name__ == "__main__": main()
