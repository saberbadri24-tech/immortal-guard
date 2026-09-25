#!/usr/bin/env python3
"""Immortal Guard Value Hunter — income-focused opportunity prioritizer.

Turns the broad radar into a value-first hunt: fresh opportunities, explicit
reward evidence, high-value bounty/grant/contest programs, cost/eligibility
checks, novelty and source quality. Estimates are never counted as income.
"""
import json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse

IN=Path("data/engine_reviews.json")
OUT=Path("data/value_hunt.json")
HUNT=Path("data/daily_hunt.json")
TARGET=2000.0
STALE_DAYS=60
VALUE_CUTOFF=2000.0

def parse_dt(v):
    if not v: return None
    s=str(v).strip().replace("Z","+00:00")
    try:
        d=datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def age_days(v, now):
    d=parse_dt(v)
    return (now-d).total_seconds()/86400 if d else None

def explicit_amounts(r):
    vals=r.get("explicitUsdAmounts") or []
    return sorted({float(v) for v in vals if isinstance(v,(int,float)) and 0 < float(v) <= 10_000_000}, reverse=True)

def category_bonus(spec):
    s=set(spec or [])
    if "bounty" in s: return 30
    if "hackathon" in s: return 24
    if "grant" in s: return 22
    if "developer" in s: return 18
    if "rewards" in s: return 16
    if "testnet" in s: return 12
    if "ambassador" in s: return 8
    return 4

def value_score(r,now):
    amounts=explicit_amounts(r)
    max_reward=amounts[0] if amounts else 0
    age=age_days(r.get("freshnessSignals",{}).get("published"),now)
    fresh=25 if age is None else max(0,25-min(25,int(age/4)))
    trust=min(20,int(r.get("trustScore",0)))
    evidence=min(15,int(r.get("evidenceLineage",{}).get("independentSources",0))*5)
    cat=category_bonus(r.get("specialists"))
    reward=0
    if max_reward>=100000: reward=40
    elif max_reward>=50000: reward=35
    elif max_reward>=10000: reward=30
    elif max_reward>=5000: reward=24
    elif max_reward>=VALUE_CUTOFF: reward=20
    elif max_reward: reward=8
    action=max(0,10-min(10,int(r.get("actionComplexity",0))*2))
    costs=max(0,int(r.get("economics",{}).get("costSignals",0))*2)
    score=min(100, reward+fresh+trust+evidence+cat+action-costs)
    return score,max_reward,age

def main():
    if not IN.exists(): raise SystemExit("missing engine_reviews.json")
    payload=json.loads(IN.read_text(encoding="utf-8"))
    now=datetime.now(timezone.utc)
    candidates=[]
    rejected=[]
    for r in payload.get("items",[]):
        if r.get("verdict")=="blocked" or r.get("risk")=="critical": continue
        domain=r.get("domain","")
        if not domain: continue
        age=age_days(r.get("freshnessSignals",{}).get("published"),now)
        amounts=explicit_amounts(r)
        # Old announcements are retained for history but never promoted as a fresh hunt.
        if age is not None and age > STALE_DAYS and not r.get("freshnessSignals",{}).get("hasDeadline"):
            rejected.append({"id":r.get("id"),"reason":"stale-publication","ageDays":round(age,1)})
            continue
        score,reward,age=value_score(r,now)
        specialists=r.get("specialists",[])
        high_value=reward>=VALUE_CUTOFF
        direct=r.get("earningType")=="direct_or_application_based"
        speculative=r.get("earningType")=="speculative_or_token_based"
        candidates.append({
            **r,
            "valueScore":score,
            "maxExplicitRewardUsd":reward,
            "freshnessDays":round(age,1) if age is not None else None,
            "highValueSignal":high_value,
            "incomeMode":"direct_or_application_based" if direct else ("speculative_or_token_based" if speculative else "unknown"),
            "priorityBand":"HIGH_VALUE" if score>=75 or reward>=VALUE_CUTOFF else ("STRONG" if score>=60 else "WATCH"),
            "monthlyTargetUsd":TARGET,
            "targetContributionMode":"evidence_only_until_paid",
            "requiredNextStep":"OWNER_REVIEW",
            "doNotCountAsIncome":not direct,
        })
    candidates.sort(key=lambda x:(x["valueScore"],x["maxExplicitRewardUsd"],x.get("trustScore",0),x.get("freshnessDays") is None),reverse=True)
    top=candidates[:25]
    direct=[x for x in top if x["incomeMode"]=="direct_or_application_based"]
    high=[x for x in top if x["maxExplicitRewardUsd"]>=VALUE_CUTOFF]
    hunt=top[:10]
    out={
        "version":1,"updatedAt":now.isoformat(),"monthlyTargetUsd":TARGET,
        "valueCutoffUsd":VALUE_CUTOFF,"staleDays":STALE_DAYS,
        "candidateCount":len(candidates),"freshRejectedCount":len(rejected),
        "highValueCount":len(high),"directEarningCount":len(direct),
        "highValueCandidates":[x["id"] for x in high],
        "items":top,
        "strategy":{
            "primary":"prioritize fresh, evidence-backed opportunities with explicit high-value rewards or direct earning mechanisms",
            "secondary":"bounties/grants/contests/developer programs outrank low-value points-only campaigns",
            "antiNoise":"stale announcements and repeated low-value campaigns are not promoted into the daily hunt",
            "incomeRule":"only owner-confirmed received funds count toward the $10,000 monthly target"
        }
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    h={
        "version":2,"updatedAt":now.isoformat(),"huntDateUtc":now.date().isoformat(),
        "dailyLimit":10,"count":len(hunt),"allQualifiedCount":len(candidates),
        "highValueCount":len(high),"directEarningCount":len(direct),
        "monthlyTargetUsd":TARGET,"actualCollectedUsd":0,
        "targetGapUsd":TARGET,"opportunityIds":[x["id"] for x in hunt],
        "opportunities":hunt,
        "rule":"Fresh value-first hunt. High-value/direct opportunities are prioritized; stale announcements are excluded.",
        "incomeRule":"Only owner-confirmed received funds count as collected income."
    }
    HUNT.write_text(json.dumps(h,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Value Hunter: candidates={len(candidates)} high_value={len(high)} direct={len(direct)} top={(hunt[0]['valueScore'] if hunt else 0)}")
if __name__=="__main__": main()
