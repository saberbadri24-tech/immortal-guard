#!/usr/bin/env python3
"""Deterministic specialist swarm for Immortal Guard.

Runs independent local reviewers even when external AI credentials are absent.
This is a screening/triage layer, not a claim executor or profit predictor.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "specialist_swarm.json"
RISK_TERMS = (
    "seed phrase", "private key", "connect wallet to claim", "pay gas to receive",
    "guaranteed profit", "double your", "airdrop checker", "wallet validation"
)
SCAM_TERMS = ("drainer", "honeypot", "malicious", "fake token", "phishing", "impersonat")
UNSAFE_TERMS = ("bypass kyc", "bypass captcha", "ignore eligibility", "share seed", "private key")


def read_json(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def text_of(item):
    return " ".join(str(item.get(k) or "") for k in (
        "title", "name", "description", "summary", "url", "source", "instructions",
        "riskStatus", "decision", "status"
    )).lower()


def fingerprint(item):
    basis = "|".join(str(item.get(k) or "").strip().lower() for k in (
        "id", "opportunityId", "url", "source", "chain", "address", "name", "title"
    ))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def official_source_review(item, qualified):
    url = str(item.get("url") or item.get("officialUrl") or "").strip()
    parsed = urlparse(url)
    https = parsed.scheme == "https" and bool(parsed.hostname)
    return {
        "agent": "OfficialSourceSentinel",
        "pass": bool(qualified and https),
        "qualifiedByOfficialGate": bool(qualified),
        "httpsSource": https,
        "finding": "official gate + HTTPS source confirmed" if qualified and https
                   else "official-source qualification is missing or URL is not HTTPS"
    }


def scam_review(item):
    t = text_of(item)
    flags = sorted(set(x for x in SCAM_TERMS if x in t))
    hard = bool(item.get("security", {}).get("securityGate") == "BLOCK")
    return {
        "agent": "ThreatHunter",
        "pass": not hard and not flags,
        "flags": flags + (["security-gate-block"] if hard else []),
        "finding": "risk indicators detected" if hard or flags else "no listed text indicator; not a security audit"
    }


def eligibility_review(item, qualified):
    t = text_of(item)
    unsafe = sorted(x for x in UNSAFE_TERMS if x in t)
    explicit = bool(item.get("eligibilityVerified") or item.get("eligibility", {}).get("verified"))
    return {
        "agent": "EligibilityAuditor",
        "pass": bool(qualified and not unsafe),
        "eligibilityVerified": explicit,
        "unsafeInstructions": unsafe,
        "finding": "unsafe eligibility instruction detected" if unsafe else
                   "official gate qualifies source; individual eligibility still needs owner review"
    }


def freshness_review(item, now):
    raw = item.get("updatedAt") or item.get("publishedAt") or item.get("poolCreatedAt") or item.get("timestamp")
    age_hours = None
    if raw:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - dt).total_seconds() / 3600)
        except ValueError:
            pass
    stale = age_hours is not None and age_hours > 24 * 30
    return {
        "agent": "FreshnessKeeper",
        "pass": not stale,
        "ageHours": round(age_hours, 2) if age_hours is not None else None,
        "finding": "older than 30 days; refresh before action" if stale else
                   "freshness unknown" if age_hours is None else "within 30-day review window"
    }


def economics_review(item):
    # Only reports observed market signals. It deliberately does not infer earnings.
    liq = max(0.0, float(item.get("liquidityUsd") or item.get("liquidity_usd") or 0))
    vol = max(0.0, float(item.get("volume24hUsd") or item.get("volume_usd") or 0))
    reward = item.get("rewardUsd") or item.get("reward_usd")
    try:
        reward = float(reward) if reward is not None else None
    except (TypeError, ValueError):
        reward = None
    return {
        "agent": "ValueAnalyst",
        "pass": True,
        "observedLiquidityUsd": liq or None,
        "observedVolume24hUsd": vol or None,
        "publishedRewardUsd": reward,
        "estimatedIncomeUsd": None,
        "finding": "market signals only; no income estimate or profitability guarantee"
    }


def wallet_safety_review(item):
    t = text_of(item)
    flags = sorted(x for x in RISK_TERMS if x in t)
    return {
        "agent": "WalletSafetyOfficer",
        "pass": not any(x in t for x in UNSAFE_TERMS) and not any(
            x in t for x in ("seed phrase", "private key")
        ),
        "flags": flags,
        "signing": False,
        "claiming": False,
        "transfer": False,
        "finding": "manual wallet action only; never submit seed phrases or private keys"
    }


def review(item, qualified, now):
    checks = [
        official_source_review(item, qualified),
        scam_review(item),
        eligibility_review(item, qualified),
        freshness_review(item, now),
        economics_review(item),
        wallet_safety_review(item),
    ]
    blocked = any(
        c["agent"] == "ThreatHunter" and not c["pass"] or
        c["agent"] == "WalletSafetyOfficer" and not c["pass"]
        for c in checks
    )
    ready = bool(qualified and all(c["pass"] for c in checks))
    return {
        "id": item.get("id") or item.get("opportunityId") or fingerprint(item),
        "fingerprint": fingerprint(item),
        "title": str(item.get("title") or item.get("name") or "Untitled candidate")[:180],
        "url": item.get("url") or item.get("officialUrl"),
        "officialQualified": bool(qualified),
        "specialistsPassed": sum(1 for c in checks if c["pass"]),
        "specialistsTotal": len(checks),
        "status": "BLOCKED" if blocked else "READY_FOR_OWNER_REVIEW" if ready else "HOLD_FOR_EVIDENCE",
        "reviews": checks,
        "action": "OWNER_REVIEW_ONLY" if ready else "NO_ACTION",
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False}
    }


def build_payload(radar, opportunities, gate):
    now = datetime.now(timezone.utc)
    qualified_ids = {str(x) for x in (gate.get("qualifiedIds") or gate.get("qualified_ids") or [])}
    items = []
    seen = set()
    for source in (opportunities.get("items") or opportunities.get("opportunities") or [],
                   radar.get("items") or []):
        for item in source:
            if not isinstance(item, dict):
                continue
            fp = fingerprint(item)
            if fp in seen:
                continue
            seen.add(fp)
            key = str(item.get("id") or item.get("opportunityId") or "")
            qualified = bool(key and key in qualified_ids)
            items.append(review(item, qualified, now))
    items.sort(key=lambda x: (
        x["status"] == "READY_FOR_OWNER_REVIEW",
        x["specialistsPassed"],
        x["title"].lower()
    ), reverse=True)
    ready = sum(x["status"] == "READY_FOR_OWNER_REVIEW" for x in items)
    blocked = sum(x["status"] == "BLOCKED" for x in items)
    return {
        "version": 1,
        "updatedAt": now.isoformat(),
        "mode": "deterministic-specialist-swarm",
        "agents": ["OfficialSourceSentinel", "ThreatHunter", "EligibilityAuditor",
                   "FreshnessKeeper", "ValueAnalyst", "WalletSafetyOfficer"],
        "candidateCount": len(items),
        "readyForOwnerReview": ready,
        "blockedCount": blocked,
        "holdCount": len(items) - ready - blocked,
        "items": items[:5000],
        "summary": "No candidate is actionable without official-gate qualification and all local safety checks.",
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False}
    }


def main():
    payload = build_payload(
        read_json("radar_intel.json", {}),
        read_json("opportunities.json", {}),
        read_json("official_source_gate.json", {})
    )
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GUARD SPECIALIST SWARM: candidates={payload['candidateCount']} ready={payload['readyForOwnerReview']} blocked={payload['blockedCount']} hold={payload['holdCount']}")


if __name__ == "__main__":
    main()
