#!/usr/bin/env python3
"""Collect candidate reward/security opportunities from public publisher feeds.

Candidates are unverified until reviewed; this script never interacts with wallets.
"""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

FEEDS = {
    "HackerOne": "https://www.hackerone.com/blog/rss.xml",
    "Gitcoin": "https://gitcoin.co/blog/feed/",
    "TON Blog": "https://blog.ton.org/rss.xml",
    "Ethereum Foundation": "https://blog.ethereum.org/feed.xml",
}
KEYWORDS = re.compile(r"\b(airdrop|bounty|bug bounty|rewards?|grant|hackathon|contest|incentiv|testnet|ambassador)\b", re.I)
OUT = Path("data/opportunities.json")

def text(node, *names):
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""

def parse_feed(name, url):
    req = urllib.request.Request(url, headers={"User-Agent": "ImmortalGuardOpportunityRadar/1.0 (+public-feed-reader)"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(2_500_000)
    root = ET.fromstring(raw)
    entries = root.findall(".//item") or root.findall(".//{*}entry")
    results = []
    for item in entries[:100]:
        title = text(item, "title", "{*}title")
        link = text(item, "link", "{*}link")
        if not link:
            el = item.find("{*}link")
            if el is not None:
                link = el.attrib.get("href", "")
        summary = text(item, "description", "{*}summary", "{*}content")
        plain = re.sub(r"<[^>]+>", " ", summary)
        if not title or not link or not KEYWORDS.search(title + " " + plain):
            continue
        results.append({"title": title[:300], "url": link, "publisher": name,
                        "published": text(item, "pubDate", "{*}published", "{*}updated"),
                        "status": "candidate-unverified",
                        "note": "Feed match only. Verify official eligibility, dates, region, costs and wallet requests before acting."})
    return results

def main():
    collected, errors = [], []
    for name, url in FEEDS.items():
        try:
            collected.extend(parse_feed(name, url))
        except Exception as exc:
            errors.append({"publisher": name, "error": str(exc)[:300]})
    # Deduplicate by canonical URL, newest feed occurrence wins.
    unique = {item["url"].rstrip("/"): item for item in collected}
    items = sorted(unique.values(), key=lambda x: x.get("published", ""), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(items), "items": items, "sourceErrors": errors,
        "disclaimer": "Automated feed candidates, not verified active rewards. No guaranteed earnings."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Collected {len(items)} candidate items; {len(errors)} feed errors")
    # Don't fail the run when an individual publisher is temporarily unavailable.

if __name__ == "__main__":
    main()
