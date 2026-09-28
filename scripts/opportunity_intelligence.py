#!/usr/bin/env python3
"""Immortal Guard Opportunity Intelligence Engine.

Broad, uncapped opportunity intelligence with value bands from Micro to Ultra.
The score is a decision-support proxy, not a claim of profit probability.
No signing, claiming, transferring, secret handling or control bypass.
"""
import json, math, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ENGINE=Path("data/engine_reviews.json")
VALUE=Path("data/value_hunt.json")
VERIFY=Path("data/verification_gate.json")
OUT=Path("data/opportunity_intelligence.json")

CATEGORIES={
 "airdrop":r"\b(airdrop|retroactive|token distribution|token reward)\b",
 "quests":r"\b(quest|campaign|activation|galxe|layer3|zealy|crew)\b",
 "points":r"\b(points|point program|loyalty|season)\b",
 "testnet":r"\b(testnet|devnet|test network|incentivized test|mainnet reward)\b",
 "faucet":r"\b(faucet|free test tokens)\b",
 "bounty":r"\b(bug bounty|bounty|whitehat|vulnerability|security reward)\b",
 "grant":r"\b(grant|funding|fellowship|builder fund|ecosystem fund)\b",
 "hackathon":r"\b(hackathon|contest|competition|challenge|prize pool)\b",
 "developer":r"\b(developer program|builder program|ecosystem program|developer)\b",
 "learn":r"\b(learn[- ]to[- ]earn|course|quiz|education|learn and earn)\b",
 "referral":r"\b(referral|affiliate|invite friends|commission)\b",
}
BLOCK=re.compile(r"(seed phrase|private key|recovery phrase|secret key|captcha bypass|kyc bypass|sybil bypass|fake account|multiple accounts|farm wallets|drain wallet|pay to claim|unlimited approval)",re.I)

def load(p,d):
 try:return json.loads(p.read_text(encoding="utf-8"))
 except Exception:return d

def host(url): return urlparse(url or "").netloc.lower().removeprefix("www.")

def cats(text):
 return [k for k,rx in CATEGORIES.items() if re.search(rx,text,re.I)] or ["general"]

def reward_band(v):
 if v>=5_000_000:return "ULTRA"
 if v>=1_000_000:return "MEGA"
 if v>=100_000:return "CRITICAL"
 if v>=10_000:return "HIGH"
 if v>=500:return "STANDARD"
 if v>0:return "MICRO"
 return "UNPRICED"

def deadline(text):
 if re.search(r"\b(ends today|ends tonight|last day|closing today|expires today)\b",text,re.I):return 100
 if re.search(r"\b(ends tomorrow|expires tomorrow|24 hours)\b",text,re.I):return 85
 if re.search(r"\b(this week|7 days|one week)\b",text,re.I):return 65
 if re.search(r"\b(deadline|expires?|closing|snapshot)\b",text,re.I):return 35
 return 10

def friction(text):
 n=len(re.findall(r"\b(connect wallet|sign|signature|transaction|gas|fee|deposit|stake|bridge)\b",text,re.I))*5
 n+=len(re.findall(r"\b(kyc|identity|passport|verification)\b",text,re.I))*8
 n+=len(re.findall(r"\b(captcha|discord|telegram|twitter|x\.com|github)\b",text,re.I))*2
 return min(100,n)

def competition(text):
 n=0
 n+=len(re.findall(r"\b(competitive|competition|contest|thousands|limited slots|selected|judged|leaderboard)\b",text,re.I))*8
 n+=len(re.findall(r"\b(first come|fcfs|limited|cap|allocation)\b",text,re.I))*6
 return min(100,n)

def reward_factor(v):
 if v<=0:return 0
 return min(40,round(10*math.log10(v+1)))

def main():
 engine=load(ENGINE,{"items":[]})
 value=load(VALUE,{"items":[]})
 verify=load(VERIFY,{"items":[]})
 vmap={str(x.get("id")):x for x in verify.get("items",[]) if x.get("id")}
 valmap={str(x.get("id")):x for x in value.get("items",[]) if x.get("id")}
 items=[]
 for r in engine.get("items",[]):
  rid=str(r.get("id") or "")
  text=" ".join(str(r.get(k) or "") for k in ("title","url","domain","earningType","nextAction"))
  text+=" "+json.dumps(r.get("freshnessSignals",{}),ensure_ascii=False)+" "+json.dumps(r.get("eligibility",{}),ensure_ascii=False)
  if r.get("verdict")=="blocked" or BLOCK.search(text):continue
  v=vmap.get(rid,{})
  if v.get("verification")=="REJECT" or v.get("expiredSignal"):continue
  vi=valmap.get(rid,{})
  base=float(r.get("score") or 0)
  value_score=float(vi.get("valueScore") or 0)
  amounts=r.get("explicitUsdAmounts") or []
  reward=max([float(x) for x in amounts if isinstance(x,(int,float))]+[0])
  evidence=int(r.get("evidenceLineage",{}).get("independentSources") or 0)
  trust=float(r.get("trustScore") or 0)
  urg=deadline(text)
  fr=friction(text)
  comp=competition(text)
  verified=15 if v.get("verification")=="REACHABLE_DOMAIN_ALIGNED" else (4 if v else 0)
  elig=r.get("eligibility",{})
  elig_signals=int(elig.get("signals") or 0)
  eligibility_clarity=20 if elig_signals>0 else 6
  security=20 if v.get("verification")=="REACHABLE_DOMAIN_ALIGNED" and not v.get("blockedSignal") else 5
  freshness=20 if r.get("freshnessSignals",{}).get("published") else 8
  band=reward_band(reward)
  reward_component=reward_factor(reward)
  realization=max(0,min(100,round(
   reward_component*0.24 + value_score*0.20 + min(20,evidence*5)*0.16 +
   min(20,trust)*0.10 + verified*0.08 + eligibility_clarity*0.08 +
   security*0.06 + freshness*0.04 + urg*0.04 +
   max(0,10-fr*0.08) + max(0,8-comp*0.06)
  )))
  items.append({
   "id":rid,"title":r.get("title"),"url":r.get("url"),"domain":host(r.get("url")),
   "categories":cats(text),"rewardUsd":reward,"rewardBand":band,
   "realizationScore":realization,"intelligenceScore":realization,
   "baseScore":base,"valueScore":value_score,"verification":v.get("verification","UNVERIFIED"),
   "independentSources":evidence,"deadlineUrgency":urg,"frictionScore":round(fr,1),
   "competitionScore":round(comp,1),"eligibility":elig,
   "eligibilityClarity":eligibility_clarity,
   "securityGate":{"passed":security>=15,"urlChecked":bool(v),"contractAudit":"REQUIRED_WHEN_CONTRACT_EXISTS","drainerPhishingScreen":not bool(v.get("blockedSignal"))},
   "priorityBand":band,
   "priority":("URGENT" if urg>=85 else ("ULTRA" if band=="ULTRA" else ("MEGA" if band=="MEGA" else ("CRITICAL" if band=="CRITICAL" else ("HIGH_VALUE" if realization>=70 else ("VERIFIED" if v.get("verification")=="REACHABLE_DOMAIN_ALIGNED" else "RESEARCH")))))),
   "nextAction":"OWNER_REVIEW",
   "safety":{"ownerApprovalRequired":True,"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False,"bypassControls":False}
  })
 items.sort(key=lambda x:(x["realizationScore"],x["rewardUsd"],x["independentSources"]),reverse=True)
 now=datetime.now(timezone.utc).isoformat()
 counts={b:sum(x["rewardBand"]==b for x in items) for b in ["MICRO","STANDARD","HIGH","CRITICAL","MEGA","ULTRA","UNPRICED"]}
 payload={"version":2,"updatedAt":now,"engine":"Immortal Guard Opportunity Intelligence","candidateCount":len(items),
  "coverage":list(CATEGORIES),"bands":counts,
  "items":items,
  "methodology":{
   "principle":"maximize realistic opportunity value, not nominal reward ceiling",
   "uncappedCandidateSet":True,
   "realizationScore":"Reward magnitude is tempered by evidence, source trust, verification, eligibility clarity, freshness, competition and action friction.",
   "expectedValueProxy":"rewardUsd × evidence/verification/eligibility/freshness/friction signals; this is a prioritization proxy, not a statistical probability or profit guarantee.",
   "incomeRule":"Only owner-confirmed received funds count as income."
  },
  "safety":{"securityReviewBeforeAction":True,"ownerApprovalRequired":True,"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False,"bypassControls":False},
  "competitorCoverage":["airdrops","testnets","mainnet rewards","faucets","learn-to-earn","quests","points","exchange/protocol campaigns","bounties","grants","hackathons","developer programs","referrals","security research"],
 }
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Opportunity Intelligence v2: candidates={len(items)} bands={counts}")

if __name__=="__main__":main()
