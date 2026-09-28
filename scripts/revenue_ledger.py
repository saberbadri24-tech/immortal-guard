#!/usr/bin/env python3
"""Durable, idempotent revenue accounting for Immortal Guard.
Only VERIFIED settlements with evidence count as realized revenue.
Discovery scores, estimates and token valuations never become income.
"""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

SRC=Path("data/verified_settlements.json")
OUT=Path("data/revenue_ledger.json")
TARGET=2000.0

def money(v):
    try:return round(float(v),2)
    except:return 0.0

def evidence(s):
    return bool(s.get("txHash") or s.get("receiptUrl") or s.get("providerReceipt") or s.get("evidenceUrl"))

def key(s):
    raw="|".join(str(s.get(k,"")).strip() for k in ("txHash","providerReceipt","source","amountUsd","paidAt"))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]

def main():
    now=datetime.now(timezone.utc).isoformat()
    raw=json.loads(SRC.read_text(encoding="utf-8")) if SRC.exists() else {"settlements":[]}
    accepted=[]; rejected=[]; seen=set()
    for s in raw.get("settlements",[]):
        status=str(s.get("status","")).upper()
        amount=money(s.get("amountUsd"))
        k=key(s)
        if k in seen: continue
        seen.add(k)
        if status!="VERIFIED" or amount<=0 or not evidence(s):
            rejected.append({"id":s.get("id"),"reason":"requires VERIFIED status, positive amount and evidence"})
            continue
        item=dict(s); item["idempotencyKey"]=k; item["amountUsd"]=amount
        accepted.append(item)
    actual=money(sum(x["amountUsd"] for x in accepted))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"version":1,"updatedAt":now,"accountingRule":"PAID + VERIFIED + EVIDENCE = EARNED","monthlyTargetUsd":TARGET,"actualCollectedUsd":actual,"targetGapUsd":money(max(0,TARGET-actual)),"verifiedSettlementCount":len(accepted),"settlements":accepted,"rejected":rejected,"idempotent":True,"safety":{"estimatedRewardsExcluded":True,"tokenValuationsExcluded":True,"unverifiedExcluded":True}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Revenue ledger: verified=%d actual=$%.2f" % (len(accepted),actual))

if __name__=="__main__": main()
