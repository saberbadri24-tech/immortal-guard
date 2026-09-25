#!/usr/bin/env python3
"""Immortal Guard verification gate.

Turns raw discovery into evidence-aware candidates before scoring. It checks
the discovered URL over HTTPS, follows redirects, records the final host,
rejects unsafe URL patterns, detects stale/expired language, and measures
whether the publisher and destination domains agree. It never logs in,
connects a wallet, signs, claims, transfers, or bypasses controls.
"""
import json
import re
import socket
import ipaddress
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

IN = Path("data/opportunities.json")
OUT = Path("data/verification_gate.json")
BLOCK = re.compile(
    r"(seed phrase|private key|recovery phrase|secret key|captcha bypass|kyc bypass|"
    r"sybil|fake account|multiple accounts|farm wallets|drain wallet|pay to claim)",
    re.I,
)
EXPIRY = re.compile(
    r"(expired|ended|closed|deadline passed|no longer available|campaign has ended|"
    r"registration is closed|applications are closed)",
    re.I,
)
DEADLINE = re.compile(
    r"(deadline|ends? on|ends? in|until|expires?|closing date|snapshot)",
    re.I,
)
HEADERS = {
    "User-Agent": "ImmortalGuard-VerificationGate/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def host(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")

def root_domain(h):
    parts = [x for x in h.split(".") if x]
    return ".".join(parts[-2:]) if len(parts) >= 2 else h

def safe_url(url):
    p = urllib.parse.urlparse(url)
    return p.scheme.lower() == "https" and bool(p.netloc) and not p.username and not p.password

def resolve_public(hostname):
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        ips = sorted({info[4][0] for info in infos})
        for raw in ips:
            ip = ipaddress.ip_address(raw)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False, ips
        return bool(ips), ips
    except Exception:
        return False, []

def fetch(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS, method="GET")
            with urllib.request.urlopen(req, timeout=12) as r:
                body = r.read(180000)
                final_url = r.geturl()
                return r.status, final_url, r.headers.get("content-type", ""), body
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1 + attempt)
    raise last

def verify(item):
    url = str(item.get("url") or "").strip()
    blob = f"{item.get('title','')} {item.get('note','')} {url}"
    result = {
        "id": item.get("id"),
        "url": url,
        "sourceDomain": host(url),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "reachable": False,
        "https": False,
        "redirected": False,
        "finalUrl": None,
        "finalDomain": None,
        "domainAligned": False,
        "contentType": None,
        "publicHost": False,
        "resolvedIps": [],
        "rewardSignal": False,
        "eligibilitySignal": False,
        "expiredSignal": bool(EXPIRY.search(blob)),
        "deadlineSignal": bool(DEADLINE.search(blob)),
        "blockedSignal": bool(BLOCK.search(blob)),
        "verification": "UNVERIFIED",
        "reasons": [],
    }
    if not safe_url(url):
        result["reasons"].append("non-HTTPS-or-invalid-url")
        result["verification"] = "REJECT"
        return result
    result["https"] = True
    try:
        initial_host = host(url)
        public, ips = resolve_public(initial_host)
        result["publicHost"] = public
        result["resolvedIps"] = ips[:10]
        if not public:
            result["reasons"].append("host-did-not-resolve-to-public-address")
            result["verification"] = "REJECT"
            return result
        status, final_url, ctype, body = fetch(url)
        final_host = host(final_url)
        text = re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace"))
        text = re.sub(r"\s+", " ", text)[:12000]
        result["reachable"] = 200 <= status < 400
        result["statusCode"] = status
        result["finalUrl"] = final_url
        result["finalDomain"] = final_host
        result["contentType"] = ctype
        result["redirected"] = final_url.rstrip("/") != url.rstrip("/")
        result["domainAligned"] = root_domain(host(url)) == root_domain(final_host)
        result["finalHttps"] = urllib.parse.urlparse(final_url).scheme.lower() == "https"
        result["expiredSignal"] = result["expiredSignal"] or bool(EXPIRY.search(text))
        result["deadlineSignal"] = result["deadlineSignal"] or bool(DEADLINE.search(text))
        result["rewardSignal"] = bool(re.search(r"(\$\s?[0-9][0-9,.]*|USD|reward|rewards|bounty|grant|prize|airdrop|points)", text, re.I))
        result["eligibilitySignal"] = bool(re.search(r"(eligible|eligibility|requirements?|qualify|qualification|region|country|resident|KYC|identity)", text, re.I))
        result["blockedSignal"] = result["blockedSignal"] or bool(BLOCK.search(text))
        if not result["reachable"]:
            result["reasons"].append(f"http-status-{status}")
        if not result["finalHttps"]:
            result["reasons"].append("final-url-not-HTTPS")
        if not result["domainAligned"]:
            result["reasons"].append("cross-domain-redirect")
        if result["blockedSignal"]:
            result["reasons"].append("unsafe-instructions-detected")
        if result["expiredSignal"]:
            result["reasons"].append("expired-or-closed-signal")
        if result["reachable"] and result["finalHttps"] and result["domainAligned"] and not result["blockedSignal"] and not result["expiredSignal"]:
            result["verification"] = "REACHABLE_DOMAIN_ALIGNED"
        elif result["reachable"] and not result["blockedSignal"]:
            result["verification"] = "REVIEW"
    except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError) as exc:
        result["reasons"].append(f"fetch-error:{str(exc)[:160]}")
        result["verification"] = "UNVERIFIED"
    except Exception as exc:
        result["reasons"].append(f"unexpected:{str(exc)[:160]}")
    return result

def main():
    data = json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items": []}
    rows = data.get("items", [])
    checks = []
    by_id = {}
    for item in rows:
        r = verify(item)
        checks.append(r)
        if r.get("id"):
            by_id[str(r["id"])] = r
    verified = sum(x["verification"] == "REACHABLE_DOMAIN_ALIGNED" for x in checks)
    rejected = sum(x["verification"] == "REJECT" for x in checks)
    payload = {
        "version": 1,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(checks),
        "verifiedReachable": verified,
        "rejected": rejected,
        "items": checks,
        "summary": {
            "reachableDomainAlignedIsNotProofOfLegitimacy": True,
            "contractOwnershipAudit": "manual-or-protocol-specific-evidence-required",
            "walletAction": False,
            "signing": False,
            "claim": False,
            "transfer": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verification gate: checked={len(checks)} reachable_aligned={verified} rejected={rejected}")

if __name__ == "__main__":
    main()
