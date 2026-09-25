#!/usr/bin/env python3
"""Build a truthful, machine-readable Guard health snapshot.

Safe only: reads generated data and never signs, transfers, claims, or handles
wallet secrets.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

FILES = [
    "radar_intel.json","radar_memory.json","radar_alerts.json","opportunities.json",
    "history.json","engine_reviews.json","evidence_graph.json","airdrop_plus.json",
    "value_hunt.json","owner_actions.json","collection_queue.json","temp_wallet.json",
    "claim_adapters.json","ton_receipts.json","ton_receipt_state.json",
    "ai_reviews.json","daily_hunt.json","owner_approval_ledger.json"
]
def load(name):
    try:
        return json.loads(Path("data", name).read_text(encoding="utf-8"))
    except Exception:
        return {}

def main():
    now = datetime.now(timezone.utc).isoformat()
    q = load("collection_queue.json")
    receipts = load("ton_receipts.json")
    opps = load("opportunities.json")
    adapters = load("claim_adapters.json")
    temp = load("temp_wallet.json")
    health = {
        "version": 1,
        "updatedAt": now,
        "automation": {
            "discovery": True,
            "deduplication": True,
            "evidenceReview": True,
            "airdropPlus": True,
            "valueHunter": True,
            "ownerQueue": True,
            "receiptMonitoring": bool(receipts.get("configured")),
            "automaticSigning": False,
            "automaticTransfer": False,
            "privateKeyStorage": False,
            "kycBypass": False,
            "captchaBypass": False,
            "sybilBypass": False
        },
        "counts": {
            "opportunities": len(opps.get("items", [])),
            "queue": len(q.get("items", [])),
            "receipts": len(receipts.get("receipts", [])),
            "adapters": len(adapters.get("adapters", []))
        },
        "wallet": {
            "temporaryAddressConfigured": bool(receipts.get("configured")),
            "addressSource": temp.get("addressSource")
        },
        "blockers": []
    }
    if not receipts.get("configured"):
        health["blockers"].append("TEMP_TON_ADDRESS is not configured")
    health["blockers"].append("Claims requiring signature/KYC/CAPTCHA remain owner-approved actions")
    Path("data/guard_status.json").write_text(
        json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(health, ensure_ascii=False))

if __name__ == "__main__":
    main()
