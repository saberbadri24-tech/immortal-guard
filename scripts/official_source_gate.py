#!/usr/bin/env python3
"""Official-source gate with separate owner-review and fully-qualified tiers."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

IN = Path("data/opportunities.json")
VERIFY = Path("data/verification_gate.json")
OUT = Path("data/official_source_gate.json")
AI_REVIEW_LIMIT = 12
OFFICIAL_DOMAINS = {
    "hackerone.com", "immunefi.com", "code4rena.com", "sherlock.xyz", "gitcoin.co",
    "ton.org", "blog.ton.org", "ethereum.org", "blog.ethereum.org", "solana.com",
    "polygon.technology", "arbitrum.io", "optimism.io", "base.org", "avax.network",
    "starknet.io", "zksync.io", "scroll.io", "linea.build", "celestia.org", "cosmos.network",
    "near.org", "sui.io", "aptosfoundation.org", "polkadot.com", "chainlink.com", "chain.link",
    "uniswap.org", "aave.com", "coinbase.com", "kraken.com", "binance.com", "okx.com",
    "galxe.com", "app.galxe.com", "layer3.xyz", "zealy.io", "questn.com"
}
REWARD = re.compile(r"(airdrop|reward|rewards|bounty|grant|prize|points|incentive|retroactive|funding|stipend|scholarship|paid|earnings|token distribution|reimbursement)", re.I)


def host(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")


def is_official(value):
    h = host(value) if "://" in str(value or "") else str(value or "").lower().removeprefix("www.")
    return any(h == d or h.endswith("." + d) for d in OFFICIAL_DOMAINS)


def evaluate_item(item, verification):
    original_url = str(item.get("url") or "").strip()
    final_url = str(verification.get("finalUrl") or original_url).strip()
    final_domain = host(final_url)
    direct_official = is_official(final_domain)
    try:
        status_code = int(verification.get("statusCode") or 0)
    except (TypeError, ValueError):
        status_code = 0
    live = bool(
        verification.get("reachable") is True
        and verification.get("finalHttps") is True
        and verification.get("publicHost") is True
        and 200 <= status_code < 400
    )
    clean = not verification.get("expiredSignal") and not verification.get("blockedSignal")
    reward = bool(verification.get("rewardSignal")) or bool(
        REWARD.search(str(item.get("title") or "") + " " + str(item.get("note") or ""))
    )
    eligibility_evidence = bool(verification.get("eligibilitySignal"))
    reviewable = direct_official and live and clean and reward
    actionable = reviewable and eligibility_evidence
    reasons = []
    if not direct_official:
        reasons.append("final-destination-not-allowlisted-official-domain")
    if not live:
        reasons.append("final-page-not-reachable-HTTPS-public")
    if not clean:
        reasons.append("expired-or-blocked-signal")
    if not reward:
        reasons.append("no-reward-signal")
    if reviewable and not eligibility_evidence:
        reasons.append("eligibility-not-evidenced-owner-review-required")
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": original_url,
        "finalUrl": final_url,
        "sourceDomain": host(original_url),
        "finalDomain": final_domain,
        "officialDomain": direct_official,
        "liveVerified": live,
        "rewardSignal": reward,
        "eligibilitySignal": eligibility_evidence,
        "expiredSignal": bool(verification.get("expiredSignal")),
        "blockedSignal": bool(verification.get("blockedSignal")),
        "qualification": (
            "OFFICIAL_VERIFIED_ACTIONABLE" if actionable else
            "OFFICIAL_VERIFIED_REVIEW" if reviewable else "DISCOVERY_ONLY"
        ),
        "reviewable": reviewable,
        "actionable": actionable,
        "reasons": reasons
    }


def build_payload(data, verification_data):
    checks = {
        str(x.get("id")): x
        for x in verification_data.get("items", [])
        if x.get("id") is not None
    }
    rows = [evaluate_item(item, checks.get(str(item.get("id")), {})) for item in data.get("items", [])]
    reviewable = [r for r in rows if r["reviewable"]]
    actionable = [r for r in rows if r["actionable"]]
    discovery = [r for r in rows if not r["reviewable"]]
    by_id = {
        str(x.get("id")): x for x in data.get("items", []) if x.get("id") is not None
    }
    reviewable.sort(
        key=lambda r: (
            float(by_id.get(str(r.get("id")), {}).get("score") or 0),
            bool(r.get("eligibilitySignal")),
            str(by_id.get(str(r.get("id")), {}).get("published") or "")
        ),
        reverse=True
    )
    return {
        "version": 3,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "officialVerifiedActionableCount": len(actionable),
        "officialVerifiedReviewCount": len(reviewable),
        "aiReviewBatchSize": min(AI_REVIEW_LIMIT, len(reviewable)),
        "discoveryOnlyCount": len(discovery),
        "qualifiedIds": [r.get("id") for r in reviewable[:AI_REVIEW_LIMIT]],
        "reviewCandidateIds": [r.get("id") for r in reviewable],
        "actionableIds": [r.get("id") for r in actionable],
        "discoveryOnlyIds": [r.get("id") for r in discovery],
        "items": rows,
        "rule": "Official source + live HTTPS final destination + clean reward signal enters owner-review triage. Eligibility evidence is required for the stricter actionable tier; missing eligibility never triggers a claim."
    }


def main():
    data = json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items": []}
    verification_data = json.loads(VERIFY.read_text(encoding="utf-8")) if VERIFY.exists() else {"items": []}
    payload = build_payload(data, verification_data)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Official source gate: actionable={payload['officialVerifiedActionableCount']} "
        f"reviewable={payload['officialVerifiedReviewCount']} "
        f"AI_batch={payload['aiReviewBatchSize']} discovery_only={payload['discoveryOnlyCount']}"
    )


if __name__ == "__main__":
    main()
