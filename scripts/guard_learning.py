#!/usr/bin/env python3
"""Evidence-gated learning layer for Immortal Guard.

Only owner-confirmed outcomes and verified settlements may change calibration.
No estimated rewards, token prices, clicks or unverified claims are treated
as positive outcomes. With insufficient observations, the layer stays neutral.
"""
import json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
HISTORY=DATA/"history.json"
ACTIONS=DATA/"owner_actions.json"
LEDGER=DATA/"revenue_ledger.json"
OUT=DATA/"learning_state.json"

def load(p, default):
    try:
        x=json.loads(p.read_text(encoding="utf-8"))
        return x if isinstance(x,(dict,list)) else default
    except Exception:return default

def rows(x):
    if isinstance(x,dict):
        for k in ("items","opportunities","actions","history"):
            if isinstance(x.get(k),list): return x[k]
    return x if isinstance(x,list) else []

def key(x):
    return str(x.get("id") or x.get("opportunityId") or x.get("fingerprint") or "")

def main():
    history=rows(load(HISTORY,{}))
    actions=rows(load(ACTIONS,{}))
    ledger=load(LEDGER,{})
    observations={}
    for r in history+actions:
        k=key(r)
        if not k: continue
        text=json.dumps(r,ensure_ascii=False).lower()
        outcome=None
        if any(s in text for s in ("paid","settled","verified_settlement","earned")):
            if r.get("verified") is True or r.get("settled") is True or r.get("status") in ("PAID","SETTLED","VERIFIED"):
                outcome=1
        if any(s in text for s in ("rejected","expired","scam","blocked")) and outcome is None:
            if r.get("verified") is True or r.get("ownerConfirmed") is True:
                outcome=0
        if outcome is not None:
            o=observations.setdefault(k,{"positive":0,"negative":0})
            o["positive" if outcome else "negative"]+=1

    verified_settlements=int(ledger.get("verifiedSettlementCount") or 0)
    if verified_settlements:
        for k in list(observations)[:verified_settlements]:
            observations[k]["positive"]+=1

    adjustments={}
    for k,o in observations.items():
        n=o["positive"]+o["negative"]
        if n<3: continue
        # Conservative empirical adjustment: +/- 10 max, shrinking toward zero.
        adj=10*((o["positive"]-o["negative"])/n)*min(1.0,n/20)
        adjustments[k]=round(adj,2)

    payload={
      "version":1,"updatedAt":datetime.now(timezone.utc).isoformat(),
      "observationCount":len(observations),"calibratedCount":len(adjustments),
      "neutralUntilMinimumObservations":3,
      "adjustments":adjustments,
      "method":"empirical owner-confirmed outcome calibration only; maximum adjustment +/-10",
      "incomeRule":"verified settlement evidence only",
      "safety":{"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False,"bypassControls":False}
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Guard learning: observations={len(observations)} calibrated={len(adjustments)}")

if __name__=="__main__":main()
