#!/usr/bin/env python3
"""Immortal Guard collection router.

Turns verified opportunities into a collection queue. It NEVER stores keys,
signs transactions, bypasses KYC/CAPTCHA/Sybil controls, or transfers funds.
Only explicitly declared, allowlisted no-signature payout APIs can be marked
auto-collectable; everything else is routed to owner review.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REVIEWS = Path("data/engine_reviews.json")
OPPS = Path("data/opportunities.json")
OUT = Path("data/collection_queue.json")
TEMP = Path("data/temp_wallet.json")

ALLOWED = {
    "hackerone.com", "gitcoin.co", "ton.org", "blog.ton.org",
    "ethereum.org", "blog.ethereum.org", "immunefi.com",
    "code4rena.com", "sherlock.xyz"
}
BLOCK = re.compile(r"(seed phrase|private key|recovery phrase|secret key|captcha bypass|kyc bypass|sybil|fake account|multiple accounts|farm wallets)", re.I)
OWNER_ACTION = re.compile(r"(connect wallet|sign|signature|login|captcha|kyc|verify identity|claim)", re.I)

def host(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")

def main():
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8")).get("items", []) if REVIEWS.exists() else []
    now = datetime.now(timezone.utc).isoformat()
    q = []
    for r in reviews:
        if r.get("verdict") == "blocked" or BLOCK.search(str(r)):
            continue
        url = r.get("url", "")
        h = host(url)
        # Every discovered/reviewed opportunity is owner-gated. A future
        # protocol adapter may classify a payout as no-signature, but it still
        # cannot start until the owner approves the opportunity.
        mode = "OWNER_REVIEW"
        q.append({
            "id": r.get("id"), "url": url, "domain": h,
            "mode": mode, "status": "pending",
            "destination": "TEMP_TON_WALLET",
            "createdAt": now,
            "ownerApprovalRequired": True,
            "note": "No seed/private key. Owner approval is required before any claim/collection. No automatic signing or transfer."
        })
    payload = {
        "version": 1, "updatedAt": now, "temporaryWallet": "USER_TON_ADDRESS",
        "permanentWalletTransfer": "OWNER_APPROVAL_ONLY",
        "count": len(q), "items": q,
        "safety": {"autoSigning": False, "autoTransfer": False, "secretStorage": False,
                   "kycBypass": False, "captchaBypass": False, "sybilBypass": False}
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    TEMP.write_text(json.dumps({
        "type": "temporary-receiving-destination", "addressSource": "OWNER_CONFIG",
        "storesSecrets": False, "note": "This is a destination record, not a private-key wallet."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Collection router: {len(q)} queued; owner-review={sum(x['ownerApprovalRequired'] for x in q)}")

if __name__ == "__main__":
    main()
