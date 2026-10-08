#!/usr/bin/env python3
"""Immortal Guard Value Hunter — uncapped value-first prioritizer."""
import json,re,math
from datetime import datetime,timezone
from pathlib import Path

IN=Path("data/engine_reviews.json"); OUT=Path("data/value_hunt.json")
HUNT=Path("data/daily_hunt.json"); LEDGER=Path("data/revenue_ledger.json")
TARGET=2000.0; STALE_DAYS=60

def parse_dt(v):
 if not v:return None
 try:
  d=datetime.fromisoformat(str(v).strip().replace("Z","+00:00"))
  return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
 except:return None

def age_days(v,now):
 d=parse_dt(v); return (now-d).total_seconds()/86400 if d else None

def amounts(r):
 return sorted({float(v) for v in (r.get("explicitUsdAmounts") or []) if isinstance(v,(int,float)) and 0<float(v)<=100_000_000},reverse=True)

def band(v):
 if v>=5_000_000:return "ULTRA"
 if v>=1_000_000:return "MEGA"
 if v>=100_000:return "CRITICAL"
 if v>=10_000:return "HIGH"
 if v>=500:return "STANDARD"
 if v>0:return "MICRO"
 return "UNPRICED"

def earning_class(r):
 b=" ".join(str(r.get(k) or "") for k in ("title","url","domain","earningType","nextAction"))
 if re.search(r"bug bounty|bounty|vulnerability reward|security reward",b,re.I):return "CASH_BOUNTY"
 if re.search(r"grant|funding|builder fund|fellowship",b,re.I):return "CASH_GRANT"
 if re.search(r"hackathon|contest|competition|challenge|prize",b,re.I):return "CASH_CONTEST"
 if re.search(r"affiliate|referral|commission|ambassador",b,re.I):return "COMMISSION"
 if re.search(r"airdrop|points|retroactive|token reward|testnet|faucet|quest",b,re.I):return "TOKEN_OR_CAMPAIGN"
 return "OTHER"

def main():
 if not IN.exists():raise SystemExit("missing engine_reviews.json")
 payload=json.loads(IN.read_text(encoding="utf-8")); now=datetime.now(timezone.utc)
 candidates=[]; rejected=[]; seen_ids=set()
 for r in payload.get("items",[]):
  if r.get("verdict")=="blocked" or r.get("risk")=="critical":continue
  if not r.get("domain"):continue
  rid=str(r.get("id") or "")
  if rid and rid in seen_ids: continue
  if rid: seen_ids.add(rid)
  age=age_days(r.get("freshnessSignals",{}).get("published"),now)
  if age is not None and age>STALE_DAYS and not r.get("freshnessSignals",{}).get("hasDeadline"):
   rejected.append({"id":r.get("id"),"reason":"stale-publication","ageDays":round(age,1)});continue
  a=amounts(r); reward=a[0] if a else 0; b=band(reward)
  evidence=min(20,int(r.get("evidenceLineage",{}).get("independentSources",0))*5)
  trust=min(20,int(r.get("trustScore",0)))
  agefresh=20 if age is None else max(0,20-min(20,int(age/4)))
  reward_component=min(35,round(8*math.log10(reward+1))) if reward else 0
  action=max(0,8-min(8,int(r.get("actionComplexity",0))))
  cost=max(0,min(10,int(r.get("economics",{}).get("costSignals",0))*2))
  score=max(0,min(100,round(reward_component+evidence+trust+agefresh+action-cost)))
  earning=earning_class(r)
  direct=earning in {"CASH_BOUNTY","CASH_GRANT","CASH_CONTEST","COMMISSION"}
  blob=" ".join(str(r.get(k) or "") for k in ("title","url","domain","nextAction","eligibility"))
  kyc=bool(re.search(r"\bkyc\b|identity verification|passport",blob,re.I))
  eligibility_signals=int(r.get("eligibility",{}).get("signals") or 0)
  candidates.append({**r,"valueScore":score,"realizationScore":score,
   "maxExplicitRewardUsd":reward,"rewardBand":b,
   "freshnessDays":round(age,1) if age is not None else None,
   "incomeMode":"direct_or_application_based" if direct else "speculative_or_campaign",
   "earningClass":earning,"cashPath":direct,"kycSignal":kyc,
   "eligibilityClarity":"EXPLICIT_SIGNALS" if eligibility_signals else "MANUAL_CHECK_REQUIRED",
   "priorityBand":b if b in {"ULTRA","MEGA","CRITICAL","HIGH"} else ("STANDARD" if score>=55 else ("MICRO" if reward else "UNPRICED")),
   "monthlyTargetUsd":TARGET,"targetContributionMode":"evidence_only_until_paid",
   "requiredNextStep":"OWNER_REVIEW_AND_SUBMISSION" if direct else "OWNER_REVIEW",
   "doNotCountAsIncome":True})
 candidates.sort(key=lambda x:(x["realizationScore"],x["maxExplicitRewardUsd"],x.get("trustScore",0)),reverse=True)
 direct=[x for x in candidates if x["incomeMode"]=="direct_or_application_based"]
 counts={b:sum(x["rewardBand"]==b for x in candidates) for b in ["MICRO","STANDARD","HIGH","CRITICAL","MEGA","ULTRA","UNPRICED"]}
 out={"version":2,"updatedAt":now.isoformat(),"monthlyTargetUsd":TARGET,"staleDays":STALE_DAYS,
  "uncapped":True,"candidateCount":len(candidates),"freshRejectedCount":len(rejected),
  "directEarningCount":len(direct),"bands":counts,"items":candidates,
  "strategy":{"primary":"maximize realistic opportunity value rather than nominal reward ceiling",
   "priority":"realizationScore combines reward magnitude with evidence, trust, freshness, action friction and cost signals",
   "uncapped":"never truncate the candidate set to a fixed top-N",
   "cashPath":"cash bounties/grants/contests/commissions are distinguished from speculative token or campaign rewards",
   "incomeRule":"only owner-confirmed received funds count toward the monthly target"}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 h={"version":3,"updatedAt":now.isoformat(),"huntDateUtc":now.date().isoformat(),
  "dailyLimit":None,"count":len(candidates),"allQualifiedCount":len(candidates),
  "directEarningCount":len(direct),"bands":counts,"monthlyTargetUsd":TARGET,
  "actualCollectedUsd":0,"verifiedSettlementCount":0,"targetGapUsd":TARGET,
  "opportunityIds":[x["id"] for x in candidates],"opportunities":candidates,
  "rule":"UNCAPPED: report every qualified opportunity; prioritize by realization score, not reward ceiling.",
  "incomeRule":"Only owner-confirmed received funds count as collected income.",
  "safetyRule":"Owner approval is required before any wallet signature, claim, transfer or financial action."}
 if LEDGER.exists():
  try:
   l=json.loads(LEDGER.read_text(encoding="utf-8"));h["actualCollectedUsd"]=float(l.get("actualCollectedUsd") or 0)
   h["verifiedSettlementCount"]=int(l.get("verifiedSettlementCount") or 0)
   h["targetGapUsd"]=round(max(0,TARGET-h["actualCollectedUsd"]),2)
  except:pass
 HUNT.write_text(json.dumps(h,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Value Hunter v2: candidates={len(candidates)} bands={counts} direct={len(direct)}")

if __name__=="__main__":main()
