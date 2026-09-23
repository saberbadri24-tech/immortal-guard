#!/usr/bin/env python3
"""Independent Immortal Guard analysis engine.

Deterministic specialist council plus evidence-lineage/convergence analysis.
It never claims, signs, transfers, bypasses controls, or handles wallet secrets.
"""
import json, re, hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

IN = Path("data/opportunities.json")
OUT = Path("data/engine_reviews.json")
HISTORY = Path("data/history.json")
RADAR = Path("data/radar_intel.json")

SPECIALISTS = {
    "bounty": re.compile(r"\b(bug bounty|bounty|security research|vulnerability|hackerone)\b", re.I),
    "grant": re.compile(r"\b(grant|funding|fund|builders? program|developer program)\b", re.I),
    "hackathon": re.compile(r"\b(hackathon|hack|contest|competition|challenge)\b", re.I),
    "testnet": re.compile(r"\b(testnet|devnet|incentivized testnet|test network)\b", re.I),
    "rewards": re.compile(r"\b(airdrop|reward|rewards|points|retroactive|incentive|campaign)\b", re.I),
    "ambassador": re.compile(r"\b(ambassador|community program|creator program)\b", re.I),
    "developer": re.compile(r"\b(developer|developers|builders|open source|sdk|hackathon)\b", re.I),
    "ecosystem": re.compile(r"\b(ecosystem|foundation|protocol|network|mainnet|layer 2|l2)\b", re.I),
}
BLOCK = re.compile(
    r"(seed phrase|private key|recovery phrase|secret key|pay to claim|"
    r"captcha bypass|kyc bypass|sybil|fake account|multiple accounts|farm wallets|"
    r"disable security|connect.*unknown wallet|drain wallet)", re.I)
PRESSURE = re.compile(r"(urgent|limited time|guaranteed|risk.?free|100%|instant profit|double your|deposit first)", re.I)
ACTION = re.compile(r"(connect wallet|sign|claim|deposit|stake|bridge|mint|verify identity|kyc)", re.I)

TRUSTED_DOMAINS = {
    "hackerone.com": 30, "gitcoin.co": 28, "ethereum.org": 30, "blog.ethereum.org": 30,
    "ton.org": 30, "blog.ton.org": 30, "github.com": 26, "gitlab.com": 24,
    "chainlink.com": 26, "solana.com": 26, "polygon.technology": 26, "arbitrum.io": 26,
    "optimism.io": 26, "base.org": 26, "avax.network": 25,
    "starknet.io": 25, "zksync.io": 25, "scroll.io": 25, "linea.build": 25,
    "celestia.org": 25, "cosmos.network": 25, "near.org": 25, "sui.io": 25,
    "aptosfoundation.org": 25, "polkadot.com": 25, "uniswap.org": 25, "aave.com": 25,
    "coinbase.com": 24, "kraken.com": 24, "binance.com": 22, "okx.com": 22,
}
KNOWN_NEWS = {"news.google.com", "finance.yahoo.com", "coindesk.com", "theblock.co", "decrypt.co", "cointelegraph.com"}

def clean_url(url):
    try:
        p = urlparse(url.strip())
        host = p.netloc.lower().removeprefix("www.")
        path = re.sub(r"/+$", "", p.path or "/")
        return urlunparse(("https", host, path, "", "", ""))
    except Exception:
        return url.strip().lower()

def domain_score(host):
    host = host.removeprefix("www.")
    best = 0
    for d, score in TRUSTED_DOMAINS.items():
        if host == d or host.endswith("." + d):
            best = max(best, score)
    if host in KNOWN_NEWS:
        best = max(best, 10)
    return best

def classify(text):
    hits = [name for name, rx in SPECIALISTS.items() if rx.search(text)]
    return hits or ["general"]

def evidence_lineage(item, radar_index):
    url = clean_url(item.get("url", ""))
    host = urlparse(url).netloc.lower().removeprefix("www.")
    publisher = str(item.get("publisher", ""))
    evidence = list(dict.fromkeys(item.get("evidence", [])))
    token_key = str(item.get("address") or "").lower()
    radar = radar_index.get(token_key) if token_key else None
    sources = [{"type": "publisher", "id": publisher or host, "domain": host, "independent": host not in KNOWN_NEWS}]
    sources += [{"type": "feed_signal", "id": e, "domain": host, "independent": False} for e in evidence]
    if radar:
        for s in radar.get("signals", []):
            sources.append({"type": "onchain_sensor", "id": s, "domain": "public-market-data", "independent": True})
        if radar.get("security", {}).get("available"):
            sources.append({"type": "security_api", "id": "goplus", "domain": "gopluslabs.io", "independent": True})
    domains = sorted(set(s["domain"] for s in sources if s.get("domain")))
    independent = sorted(set(s["domain"] for s in sources if s.get("independent")))
    claim = re.sub(r"\s+", " ", item.get("title", "")).strip()[:180]
    claim_id = hashlib.sha256((claim.lower() + "|" + url).encode()).hexdigest()[:16]
    return {
        "claimId": claim_id,
        "claim": claim,
        "sourceCount": len(sources),
        "uniqueDomains": len(domains),
        "independentSources": len(independent),
        "domains": domains,
        "independentDomains": independent,
        "sourceTypes": sorted(set(s["type"] for s in sources)),
        "convergence": min(100, len(independent) * 20 + min(30, len(domains) * 5)),
        "lineage": sources,
    }

def extract_money(text):
    """Extract explicit monetary amounts; never treat token prices/TVL as earnings."""
    vals=[]
    for m in re.finditer(r"(?:\$|USD\s*)([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k|K|m|M)?", text):
        try:
            v=float(m.group(1).replace(",","")); mult=m.group(2)
            if mult and mult.lower()=="k": v*=1000
            if mult and mult.lower()=="m": v*=1000000
            vals.append(v)
        except ValueError: pass
    return sorted(set(v for v in vals if 50 <= v <= 10000000), reverse=True)[:5]

def earning_class(text, specialists):
    """Classify only explicit earning mechanisms; airdrops/points stay speculative."""
    t=text.lower()
    if re.search(r"bug bounty|bounty|cash prize|prize pool|grant|funding|award|paid|payment", t):
        return "direct_or_application_based"
    if re.search(r"airdrop|points|retroactive|incentive|rewards?", t):
        return "speculative_or_token_based"
    return "unknown"

def analyze(item, radar_index):
    title = item.get("title", "")
    note = item.get("note", "")
    text = f"{title} {note} {item.get('url','')}"
    explicitMoney = extract_money(text)
    earningType = earning_class(text, [])
    url = clean_url(item.get("url", ""))
    host = urlparse(url).netloc.lower().removeprefix("www.")
    blocked = bool(BLOCK.search(text)) or item.get("status") == "blocked"
    pressure = len(PRESSURE.findall(text))
    actions = len(ACTION.findall(text))
    specialists = classify(text)
    trust = domain_score(host)
    lineage = evidence_lineage(item, radar_index)
    score = int(item.get("score", 0) or 0)
    score += trust + min(15, len(set(item.get("evidence", []))) * 3)
    score += min(12, len(specialists) * 3)
    score += min(15, lineage["independentSources"] * 5)
    score -= min(24, pressure * 8) + min(15, actions * 3)
    if blocked:
        score = 0
    score = max(0, min(100, score))
    if blocked:
        verdict, risk, action = "blocked", "critical", "BLOCK"
    elif trust >= 24 and score >= 65:
        verdict, risk, action = "high-confidence-candidate", "lower", "OWNER_REVIEW"
    elif score >= 50:
        verdict, risk, action = "candidate", "review", "OWNER_REVIEW"
    else:
        verdict, risk, action = "weak-candidate", "review", "VERIFY"
    return {
        "id": item.get("id"), "url": url, "domain": host,
        "earningType": earningType, "explicitUsdAmounts": explicitMoney,
        "countsTowardMonthlyTarget": bool(explicitMoney) and earningType == "direct_or_application_based",
        "monthlyTargetUsd": 10000,
        "specialists": specialists, "trustScore": trust,
        "evidenceCount": len(set(item.get("evidence", []))),
        "actionComplexity": actions, "pressureSignals": pressure,
        "evidenceLineage": lineage, "score": score, "verdict": verdict,
        "risk": risk, "nextAction": action,
        "checks": [
            "confirm the opportunity on the project's official domain",
            "confirm dates, geography, eligibility and required actions",
            "treat repeated news copies as one source, not independent confirmation",
            "never provide seed/private keys or bypass CAPTCHA/KYC/Sybil controls",
            "owner approval required before any wallet signature or financial action"
        ],
    }

def main():
    if not IN.exists():
        raise SystemExit("Missing radar input: data/opportunities.json")
    data = json.loads(IN.read_text(encoding="utf-8"))
    raw = data.get("items", [])
    radar_index = {}
    if RADAR.exists():
        try:
            for x in json.loads(RADAR.read_text(encoding="utf-8")).get("items", []):
                if x.get("address"):
                    radar_index[str(x["address"]).lower()] = x
        except Exception:
            radar_index = {}
    reviews = [analyze(x, radar_index) for x in raw]
    reviews.sort(key=lambda x: (x["score"], x["evidenceLineage"]["convergence"], x["trustScore"], -x["actionComplexity"]), reverse=True)
    counts = Counter(r["verdict"] for r in reviews)
    specialist_counts = Counter(s for r in reviews for s in r["specialists"])
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "version": 3,
        "updatedAt": now,
        "engine": "Immortal Guard Independent Specialist Council + Evidence Lineage",
        "independent": True,
        "apiRequired": False,
        "specialists": sorted(SPECIALISTS),
        "sourceCoverage": len(set(r["domain"] for r in reviews)),
        "independentSourceCoverage": len(set(d for r in reviews for d in r["evidenceLineage"]["independentDomains"])),
        "count": len(reviews),
        "verdicts": dict(counts),
        "specialistCounts": dict(specialist_counts),
        "monthlyTargetUsd": 10000,
        "qualifiedEarningPotentialUsd": sum(max(r.get("explicitUsdAmounts",[]) or [0]) for r in reviews if r.get("countsTowardMonthlyTarget")),
        "actualCollectedUsd": 0,
        "actualCollectedRule": "Only owner-confirmed received funds count; opportunity estimates never count as income.",
        "convergenceModel": "independent source domains > repeated copies; on-chain/security signals are separate evidence types",
        "items": reviews[:300],
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    h = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"runs":[]}
    h["runs"] = (h.get("runs", []) + [{"at": now, "engineCount": len(reviews), "topScore": reviews[0]["score"] if reviews else 0, "independentSources": payload["independentSourceCoverage"]}])[-500:]
    HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Independent engine v3: {len(reviews)} analyzed; independent_sources={payload['independentSourceCoverage']}; top={payload['items'][0]['score'] if reviews else 0}")

if __name__ == "__main__":
    main()
