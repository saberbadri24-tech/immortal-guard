#!/usr/bin/env python3
"""Immortal Guard Revenue Magnet."""
import json,re
from datetime import datetime,timezone
from pathlib import Path
SRC=Path("data/engine_reviews.json"); OUT=Path("data/revenue_targets.json"); LEDGER=Path("data/revenue_ledger.json")
CASH=re.compile(r"bounty|bug bounty|grant|funding|cash prize|prize|award|paid|reward|commission|referral|hackathon|contest|bug report|security research|researcher",re.I)
SPEC=re.compile(r"airdrop|points|retroactive|token|testnet",re.I)
BLOCK=re.compile(r"seed phrase|private key|captcha bypass|kyc bypass|sybil|fake account|multiple accounts|pay to claim|deposit first|drain|exploit",re.I)
DIRECT=re.compile(r"submit|application|report|competition|grant|bounty|referral|commission|claim",re.I)
def num(x):
    try:return float(x)
    except:return 0.0
def host(url):
    m=re.search(r"https?://([^/]+)",str(url or ""))
    return (m.group(1) if m else "").lower().removeprefix("www.")
def main():
    now=datetime.now(timezone.utc).isoformat()
    data=json.loads(SRC.read_text(encoding="utf-8")) if SRC.exists() else {"items":[]}
    targets=[]
    for r in data.get('items',[]):
        text=" ".join(str(r.get(k,"")) for k in ("title","url","domain","earningType","nextAction"))
        if BLOCK.search(text) or str(r.get("verdict","")).lower()=="blocked": continue
        amount=max([num(x) for x in (r.get("explicitUsdAmounts") or []) if num(x)>0] or [0])
        trust=num(r.get("trustScore")); score=num(r.get("score"))
        evidence=num((r.get("evidenceLineage") or {}).get("independentSources"))
        cost=num((r.get("economics") or {}).get("costSignals"))
        eligibility=num((r.get("eligibility") or {}).get("signals"))
        cash=bool(CASH.search(text)) or r.get("earningType")=="direct_or_application_based"
        speculative=bool(SPEC.search(text)) or r.get("earningType")=="speculative_or_token_based"
        if not cash and not speculative: continue
        base=0.18 if cash else 0.03
        if evidence>=2: base+=0.10 if cash else 0.03
        if trust>=50: base+=0.10
        if DIRECT.search(text): base+=0.07
        if eligibility==0: base+=0.05
        if cost>0: base-=min(0.10,cost*0.02)
        p=max(0.01,min(0.75,base + (0.05 if amount >= 10000 else 0) + (0.05 if amount >= 100000 else 0))); expected=round(amount*p,2) if amount else 0.0
        friction=1.0+min(4.0,cost)+min(4.0,eligibility)
        magnet_score=round((expected+score*2+trust+evidence*8)/friction,2)
        targets.append({"id":r.get("id"),"title":r.get("title"),"url":r.get("url"),"domain":host(r.get("url") or r.get("domain")),"earningClass":"CASH_PATH" if cash else "SPECULATIVE_OPTION","headlineRewardUsd":amount,
        "revenueScale": ("unknown" if not amount else "micro" if amount < 100 else "small" if amount < 1000 else "mid" if amount < 10000 else "large" if amount < 100000 else "mega"),"estimatedPayoutProbability":round(p,3),"expectedRealizedUsd":expected,"frictionIndex":round(friction,2),"magnetScore":magnet_score,"why":"cash-first + evidence + executable path; high-value opportunities are retained rather than capped" if cash else "speculative only; never counted as income","nextAction":"OWNER_REVIEW_AND_SUBMIT" if cash else "MONITOR_ONLY","revenueState":"OPPORTUNITY_ONLY"})
    targets.sort(key=lambda x:(x["earningClass"]=="CASH_PATH",x["magnetScore"],x["expectedRealizedUsd"]),reverse=True)
    old={}
    if LEDGER.exists():
        try: old=json.loads(LEDGER.read_text(encoding='utf-8'))
        except: old={}
    verified=[x for x in old.get("settlements",[]) if str(x.get("status","VERIFIED")).upper()=="VERIFIED"]
    actual=round(sum(num(x.get("amountUsd")) for x in verified),2)
    OUT.write_text(json.dumps({"version":2,"updatedAt":now,"engine":"Revenue Magnet v2","principle":"maximize expected realized revenue per unit attention","targetCount":len(targets),"cashPathCount":sum(x["earningClass"]=="CASH_PATH" for x in targets),"speculativeCount":sum(x["earningClass"]=="SPECULATIVE_OPTION" for x in targets),"targets":targets,"actualCollectedUsd":actual,"accounting":"PAID + VERIFIED + EVIDENCE = EARNED","safety":{"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False,"kycBypass":False,"captchaBypass":False,"sybilBypass":False}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Revenue Magnet: {len(targets)} targets; actual=${actual:.2f}")
if __name__=="__main__":main()
