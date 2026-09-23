#!/usr/bin/env python3
"""Immortal Guard Airdrop Plus — high-coverage opportunity hunter.

This is the Guard's airdrop specialist. It watches the normalized radar,
extracts reward/airdrop candidates, scores quality and urgency, detects the
claim phase, and creates a deterministic action plan.

It does NOT create accounts, bypass eligibility, solve CAPTCHA/KYC, sign
transactions, custody keys, or move funds. Protocol-specific collection is
only possible through an explicitly verified official adapter.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

IN = Path("data/opportunities.json")
REVIEWS = Path("data/engine_reviews.json")
OUT = Path("data/airdrop_plus.json")
ACTIONS = Path("data/owner_actions.json")
LEDGER = Path("data/owner_approval_ledger.json")

REWARD = re.compile(
    r"\b(airdrop|token distribution|token claim|claim|rewards?|points|"
    r"retroactive|incentive|allocation|community reward|quest|campaign|"
    r"testnet reward|mainnet reward)\b", re.I)
LIVE = re.compile(r"\b(claim now|claim is live|claims? open|live now|"
                  r"distribution is live|token claim|claim window)\b", re.I)
UPCOMING = re.compile(r"\b(upcoming|launch|snapshot|eligib|points|"
                      r"testnet|season|campaign|registration)\b", re.I)
DANGER = re.compile(r"(seed phrase|private key|recovery phrase|"
                    r"captcha bypass|kyc bypass|sybil|fake account|"
                    r"multiple accounts|pay to claim|deposit first|"
                    r"guaranteed profit|100% profit)", re.I)
WALLET = re.compile(r"(connect wallet|wallet|sign|signature|claim|"
                    r"verify identity|kyc|login)", re.I)

OFFICIAL = {
    "ton.org","blog.ton.org","ethereum.org","blog.ethereum.org","solana.com",
    "polygon.technology","arbitrum.io","optimism.io","base.org","avax.network",
    "starknet.io","zksync.io","scroll.io","linea.build","celestia.org",
    "cosmos.network","near.org","sui.io","aptosfoundation.org","polkadot.com",
    "chainlink.com","uniswap.org","aave.com","gitcoin.co","hackerone.com",
    "immunefi.com","code4rena.com","sherlock.xyz","coinbase.com","kraken.com",
    "binance.com","okx.com"
}

def domain(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")

def official_score(host):
    return 30 if any(host == d or host.endswith("." + d) for d in OFFICIAL) else 0

def phase(title, url, publisher):
    text = f"{title} {url} {publisher}"
    if LIVE.search(text):
        return "CLAIM_LIVE"
    if UPCOMING.search(text):
        return "EARLY_OR_UPCOMING"
    return "DISCOVERY"

def main():
    data = json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items":[]}
    reviews = {x.get("id"): x for x in json.loads(REVIEWS.read_text(encoding="utf-8")).get("items", [])} if REVIEWS.exists() else {}
    rows = []
    seen = set()
    for x in data.get("items", []):
        title = x.get("title","")
        url = x.get("url","")
        text = f"{title} {url} {x.get('publisher','')} {x.get('note','')}"
        if not REWARD.search(text) or DANGER.search(text):
            continue
        key = re.sub(r"[^a-z0-9]+"," ",title.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        host = domain(url)
        review = reviews.get(x.get("id"), {})
        score = int(x.get("score",0) or 0)
        score += official_score(host)
        score += 15 if LIVE.search(text) else 0
        score += 8 if "airdrop" in text.lower() else 0
        score += 5 if "reward" in text.lower() or "points" in text.lower() else 0
        score -= 20 if not official_score(host) else 0
        score = max(0, min(100, score))
        p = phase(title,url,x.get("publisher",""))
        needs_owner = bool(WALLET.search(text)) or p == "CLAIM_LIVE"
        rows.append({
            "id": x.get("id"),
            "title": title[:300],
            "url": url,
            "domain": host,
            "phase": p,
            "score": score,
            "officialDomain": bool(official_score(host)),
            "specialists": ["airdrop","rewards","eligibility","risk","claim-phase"],
            "sourceEvidence": x.get("evidence",[]),
            "qualification": "official-domain" if official_score(host) else "discovery-only",
            "engineScore": review.get("score",0),
            "action": "OWNER_REVIEW",
            "destination": "TEMP_TON_WALLET",
            "collectionMode": "PROTOCOL_ADAPTER_ONLY",
            "ownerApprovalRequired": True,
            "checks": [
                "verify the current opportunity on its official domain",
                "check eligibility, geography, snapshot/claim dates and terms",
                "never submit seed/private key or bypass CAPTCHA/KYC/Sybil controls",
                "if a signature is required, stop and wait for owner approval"
            ]
        })
    rows.sort(key=lambda z:(z["score"], z["phase"]=="CLAIM_LIVE"), reverse=True)
    now = datetime.now(timezone.utc).isoformat()
    ledger = {"version": 1, "updatedAt": now, "items": []}
    if LEDGER.exists():
        try:
            ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            ledger = {"version": 1, "updatedAt": now, "items": []}
    existing = {x.get("id"): x for x in ledger.get("items", []) if x.get("id")}
    for x in rows:
        old = existing.get(x["id"], {})
        existing[x["id"]] = {
            **old,
            "id": x["id"], "title": x["title"], "url": x["url"],
            "domain": x["domain"],
            "firstSeenAt": old.get("firstSeenAt", now),
            "lastSeenAt": now,
            "phase": x["phase"], "score": x["score"],
            "status": old.get("status", "WAITING_OWNER_APPROVAL"),
            "ownerApprovalRequired": True,
            "lastReason": "Discovered and retained until owner decision."
        }
    ledger["items"] = sorted(existing.values(), key=lambda z: z.get("lastSeenAt",""), reverse=True)
    ledger["updatedAt"] = now
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    payload = {
        "version": 1,
        "name": "Immortal Guard Airdrop Plus",
        "updatedAt": now,
        "count": len(rows),
        "liveClaimCandidates": sum(x["phase"]=="CLAIM_LIVE" for x in rows),
        "highConfidence": sum(x["score"]>=75 and x["officialDomain"] for x in rows),
        "verifiedOfficialCandidates": sum(x["officialDomain"] and x["score"]>=60 for x in rows),
        "items": rows,
        "architecture": {
            "discovery":"multi-source radar",
            "specialists":"airdrop/reward/eligibility/risk/claim-phase",
            "destination":"temporary TON receiving destination",
            "collection":"official protocol adapter only",
            "permanentTransfer":"owner approval only"
        },
        "safety": {
            "autoClaim": False,
            "autoSigning": False,
            "autoTransfer": False,
            "secretStorage": False,
            "kycBypass": False,
            "captchaBypass": False,
            "sybilBypass": False
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    actions = [{
        "id": x["id"], "title": x["title"], "url": x["url"],
        "status": "WAITING_OWNER_APPROVAL",
        "reason": "Discovered and retained. No claim, connection, signature, or transfer occurs until owner approval.",
        "destination": "TEMP_TON_WALLET"
    } for x in rows]
    ACTIONS.write_text(json.dumps({"version":1,"updatedAt":now,"count":len(actions),"items":actions},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Airdrop Plus: {len(rows)} candidates; live={payload['liveClaimCandidates']}; high={payload['highConfidence']}")

if __name__ == "__main__":
    main()
