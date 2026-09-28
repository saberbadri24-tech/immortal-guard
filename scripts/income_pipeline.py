#!/usr/bin/env python3
"""Immortal Guard income pipeline.

Ranks only plausible, evidence-backed earning opportunities. It never counts
estimated rewards as income and never performs claims, signatures, KYC/CAPTCHA
bypass, or financial transfers.
"""
import json,re
from datetime import datetime,timezone
from pathlib import Path

IN=Path("data/engine_reviews.json")
OUT=Path("data/income_pipeline.json")
LEDGER=Path("data/revenue_ledger.json")

DIRECT=re.compile(r"bug bounty|bounty|cash prize|prize|grant|funding|award|paid|payment",re.I)
SPEC=re.compile(r"airdrop|points|retroactive|token reward|testnet",re.I)
BLOCK=re.compile(r"seed phrase|private key|captcha bypass|kyc bypass|sybil|fake account|multiple accounts|pay to claim|deposit first",re.I)

def row(r):
    text=" ".join(str(r.get(k,"")) for k in ("title","url","domain","earningType","nextAction"))
    amount=max(r.get("explicitUsdAmounts") or [0])
    direct=bool(DIRECT.search(text)) or r.get("earningType")=="direct_or_application_based"
    speculative=bool(SPEC.search(text)) or r.get("earningType")=="speculative_or_token_based"
    blocked=bool(BLOCK.search(text)) or r.get("verdict")=="blocked"
    score=float(r.get("score") or 0)
    trust=float(r.get("trustScore") or 0)
    evidence=float((r.get("evidenceLineage") or {}).get("independentSources") or 0)
    cost=float((r.get("economics") or {}).get("costSignals") or 0)
    elig=float((r.get("eligibility") or {}).get("signals") or 0)
    fresh=(r.get("freshnessSignals") or {})
    payout = "EXPLICIT_REWARD" if amount>0 else "UNSPECIFIED"
    net=max(0,score + min(15,evidence*5) + min(10,trust/3) - min(15,cost*3) - min(15,elig*2))
    if blocked: stage="BLOCKED"
    elif direct and amount>0 and trust>=24 and not fresh.get("hasCostSignal") and not fresh.get("hasEligibility"): stage="HIGH_VALUE_REVIEW"
    elif direct: stage="EARN_REVIEW"
    elif speculative: stage="OPTIONAL_SPECULATIVE"
    else: stage="LOW_SIGNAL"
    return {
        "id":r.get("id"),"title":r.get("title"),"url":r.get("url"),"domain":r.get("domain"),
        "stage":stage,"earningType":r.get("earningType"),"explicitRewardUsd":amount,
        "payoutEvidence":payout,"netScore":round(net,2),"trustScore":trust,
        "independentSources":int(evidence),"costSignals":int(cost),"eligibilitySignals":int(elig),
        "freshness":fresh,
        "incomeRule":"Only funds actually observed on-chain or in a verified payment settlement count as income.",
        "nextAction":("OPEN_OFFICIAL_SOURCE_AND_COMPLETE_OWNER_ACTION" if stage in ("HIGH_VALUE_REVIEW","EARN_REVIEW") else "NO_FINANCIAL_ACTION")
    }

def main():
    data=json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items":[]}
    rows=[row(r) for r in data.get("items",[])]
    rows.sort(key=lambda x:(x["stage"]=="HIGH_VALUE_REVIEW",x["netScore"],x["explicitRewardUsd"],x["independentSources"]),reverse=True)
    now=datetime.now(timezone.utc).isoformat()
    counts={}
    for x in rows: counts[x["stage"]]=counts.get(x["stage"],0)+1
    payload={
      "version":1,"updatedAt":now,"engine":"Income Pipeline v1",
      "count":len(rows),"counts":counts,
      "priority":[x for x in rows if x["stage"] in ("HIGH_VALUE_REVIEW","EARN_REVIEW")][:100],
      "speculative":[x for x in rows if x["stage"]=="OPTIONAL_SPECULATIVE"][:100],
      "actualCollectedUsd":0,
      "verifiedSettlementCount":0,
      "actualIncomeRule":"No estimate, token price, TVL, reward ceiling or opportunity score is income. Income requires a verified receipt/settlement.",
      "safety":{"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False,"kycBypass":False,"captchaBypass":False,"sybilBypass":False}
    }
    if LEDGER.exists():
        try:
            ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
            payload["actualCollectedUsd"]=float(ledger.get("actualCollectedUsd") or 0)
            payload["verifiedSettlementCount"]=int(ledger.get("verifiedSettlementCount") or 0)
        except Exception:
            pass
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Income pipeline: {len(rows)} classified; high_value={counts.get('HIGH_VALUE_REVIEW',0)} earn_review={counts.get('EARN_REVIEW',0)}")
if __name__=="__main__": main()
