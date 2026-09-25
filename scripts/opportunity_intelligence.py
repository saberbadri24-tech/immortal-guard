#!/usr/bin/env python3
"""Immortal Guard Opportunity Intelligence — competitor-class discovery layer.

Unifies airdrops, quests, points, testnets, bounties, grants, hackathons,
developer programs and other lawful reward paths into one research queue.
It ranks by evidence, freshness, explicit reward, estimated friction/cost,
eligibility signals and deadline urgency. It never signs, claims, transfers,
bypasses controls, stores secrets, or treats estimates as income.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ENGINE = Path("data/engine_reviews.json")
VALUE = Path("data/value_hunt.json")
RADAR = Path("data/radar_intel.json")
VERIFY = Path("data/verification_gate.json")
OUT = Path("data/opportunity_intelligence.json")

CATEGORIES = {
    "airdrop": r"\b(airdrop|retroactive|token distribution|token reward)\b",
    "quests": r"\b(quest|campaign|activation|galxe|layer3|zealy|crew)\b",
    "points": r"\b(points|point program|loyalty|season)\b",
    "testnet": r"\b(testnet|devnet|test network|incentivized test)\b",
    "bounty": r"\b(bug bounty|bounty|whitehat|vulnerability)\b",
    "grant": r"\b(grant|funding|fellowship|builder fund)\b",
    "hackathon": r"\b(hackathon|contest|competition|challenge|prize pool)\b",
    "developer": r"\b(developer program|builder program|ambassador|ecosystem program|developer)\b",
    "learn": r"\b(learn[- ]to[- ]earn|course|quiz|education|learn and earn)\b",
    "referral": r"\b(referral|affiliate|invite friends)\b",
}

BLOCK = re.compile(r"(seed phrase|private key|recovery phrase|secret key|captcha bypass|kyc bypass|sybil bypass|fake account|multiple accounts|farm wallets|drain wallet|pay to claim)", re.I)

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def host(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")

def categories(text):
    return [k for k,rx in CATEGORIES.items() if re.search(rx, text, re.I)] or ["general"]

def deadline_urgency(text):
    if re.search(r"\b(ends today|ends tonight|last day|closing today|expires today)\b", text, re.I):
        return 100
    if re.search(r"\b(ends tomorrow|expires tomorrow|24 hours)\b", text, re.I):
        return 85
    if re.search(r"\b(this week|7 days|one week)\b", text, re.I):
        return 65
    return 15

def friction(text):
    n = 0
    n += len(re.findall(r"\b(connect wallet|sign|signature|transaction|gas|fee|deposit|stake)\b", text, re.I)) * 5
    n += len(re.findall(r"\b(kyc|identity|passport|verification)\b", text, re.I)) * 8
    n += len(re.findall(r"\b(captcha|discord|telegram|twitter|x\.com|github)\b", text, re.I)) * 2
    return min(100, n)

def main():
    engine = load(ENGINE, {"items":[]})
    value = load(VALUE, {"items":[]})
    verify = load(VERIFY, {"items":[]})
    verification = {str(x.get("id")): x for x in verify.get("items", []) if x.get("id")}
    value_by_id = {str(x.get("id")): x for x in value.get("items", []) if x.get("id")}

    items = []
    for r in engine.get("items", []):
        rid = str(r.get("id") or "")
        text = " ".join(str(r.get(k) or "") for k in ("title","url","domain","earningType"))
        text += " " + json.dumps(r.get("freshnessSignals",{}), ensure_ascii=False)
        text += " " + json.dumps(r.get("eligibility",{}), ensure_ascii=False)
        cats = categories(text)
        blocked = r.get("verdict") == "blocked" or BLOCK.search(text)
        v = verification.get(rid, {})
        if v.get("verification") == "REJECT" or v.get("expiredSignal"):
            blocked = True
        if blocked:
            continue

        base = float(r.get("score") or 0)
        value_item = value_by_id.get(rid, {})
        value_score = float(value_item.get("valueScore") or 0)
        explicit = max(r.get("explicitUsdAmounts") or [0])
        evidence = float(r.get("evidenceLineage",{}).get("independentSources") or 0)
        urgency = deadline_urgency(text)
        friction_score = friction(text)
        verification_bonus = 15 if v.get("verification") == "REACHABLE_DOMAIN_ALIGNED" else (4 if v else 0)
        breadth_bonus = min(12, len(cats) * 3)

        intelligence_score = max(0, min(100, round(
            base * 0.32 + value_score * 0.30 + min(30, evidence * 7) +
            verification_bonus + urgency * 0.12 + breadth_bonus - friction_score * 0.10
        )))

        eligibility = r.get("eligibility", {})
        items.append({
            "id": rid,
            "title": r.get("title"),
            "url": r.get("url"),
            "domain": host(r.get("url")),
            "categories": cats,
            "intelligenceScore": intelligence_score,
            "baseScore": base,
            "valueScore": value_score,
            "explicitRewardUsd": explicit,
            "verification": v.get("verification", "UNVERIFIED"),
            "independentSources": int(evidence),
            "deadlineUrgency": urgency,
            "frictionScore": friction_score,
            "eligibility": eligibility,
            "priority": (
                "URGENT" if urgency >= 85 else
                "HIGH_VALUE" if explicit >= 2000 or value_score >= 75 else
                "VERIFIED" if v.get("verification") == "REACHABLE_DOMAIN_ALIGNED" else
                "RESEARCH"
            ),
            "nextAction": "OWNER_REVIEW",
            "safety": {
                "ownerApprovalRequired": True,
                "autoClaim": False,
                "autoSigning": False,
                "autoTransfer": False,
                "secretStorage": False,
                "bypassControls": False
            }
        })

    items.sort(key=lambda x:(x["intelligenceScore"], x["explicitRewardUsd"], x["independentSources"]), reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "version": 1,
        "updatedAt": now,
        "engine": "Immortal Guard Opportunity Intelligence",
        "coverage": list(CATEGORIES),
        "candidateCount": len(items),
        "urgentCount": sum(x["priority"]=="URGENT" for x in items),
        "highValueCount": sum(x["priority"]=="HIGH_VALUE" for x in items),
        "verifiedCount": sum(x["verification"]=="REACHABLE_DOMAIN_ALIGNED" for x in items),
        "items": items,
        "methodology": "Combines independent evidence, live verification, value signals, freshness/deadline urgency, category breadth and action friction. It is a research-priority score, not a probability of profit.",
        "competitor_coverage": [
            "quest/campaign discovery",
            "on-chain and market signal discovery",
            "bounty/grant/hackathon/developer opportunities",
            "eligibility and geography signal extraction",
            "reward and cost separation",
            "deadline urgency",
            "multi-source evidence convergence",
            "security and phishing screening",
            "historical novelty/change detection",
            "owner-gated action queue"
        ],
        "incomeRule": "Only owner-confirmed received funds count as income."
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Opportunity Intelligence: candidates={len(items)} urgent={payload['urgentCount']} high_value={payload['highValueCount']} verified={payload['verifiedCount']}")

if __name__ == "__main__":
    main()
