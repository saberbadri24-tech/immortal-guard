#!/usr/bin/env python3
"""Immortal Guard protocol adapter registry.

Only explicit, reviewed adapters may ever become executable. Generic web
scraping or arbitrary claim transactions are deliberately unsupported.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path("data/claim_adapters.json")
ADAPTERS=[
 {"id":"ton-official-receipt","network":"TON","mode":"RECEIPT_MONITOR","signing":False,
  "status":"enabled","description":"Detect incoming TON payments to the temporary receiving address."},
 {"id":"owner-web-flow","network":"MULTI","mode":"OWNER_WEB_FLOW","signing":True,
  "status":"enabled","description":"Prepare an official claim URL/action for the owner; never signs automatically."},
 {"id":"owner-signature","network":"MULTI","mode":"OWNER_SIGNATURE","signing":True,
  "status":"enabled","description":"Prepare transaction context and stop for explicit owner signature."},
]
payload={"version":1,"updatedAt":datetime.now(timezone.utc).isoformat(),
         "adapters":ADAPTERS,
         "rules":{"genericClaimExecution":False,"automaticSigning":False,
                  "privateKeyStorage":False,"bypassControls":False}}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Claim adapter registry: ready")
