#!/usr/bin/env python3
"""Build a compact, versioned evidence graph for Immortal Guard.

The graph separates repeated reporting from independent evidence and links
opportunity claims to market/security signals already collected by the Guard.
No wallet action is performed.
"""
import json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

OPPS = Path("data/opportunities.json")
REVIEWS = Path("data/engine_reviews.json")
RADAR = Path("data/radar_intel.json")
OUT = Path("data/evidence_graph.json")

def canon(s):
    return str(s or "").strip().lower()

def main():
    opps = json.loads(OPPS.read_text(encoding="utf-8")) if OPPS.exists() else {"items":[]}
    reviews = json.loads(REVIEWS.read_text(encoding="utf-8")) if REVIEWS.exists() else {"items":[]}
    radar = json.loads(RADAR.read_text(encoding="utf-8")) if RADAR.exists() else {"items":[]}
    review_by_id = {canon(x.get("id")): x for x in reviews.get("items", [])}
    radar_by_addr = {canon(x.get("address")): x for x in radar.get("items", []) if x.get("address")}
    nodes, edges = [], []
    seen_nodes = set()
    for item in opps.get("items", []):
        oid = canon(item.get("id"))
        if not oid:
            continue
        claim_id = "claim:" + hashlib.sha256((canon(item.get("title"))+"|"+canon(item.get("url"))).encode()).hexdigest()[:16]
        if claim_id not in seen_nodes:
            nodes.append({"id":claim_id,"type":"claim","label":item.get("title","")[:180]}); seen_nodes.add(claim_id)
        url = item.get("url","")
        host = urlparse(url).netloc.lower().removeprefix("www.")
        sid = "source:" + host
        if sid not in seen_nodes:
            nodes.append({"id":sid,"type":"source","label":host}); seen_nodes.add(sid)
        edges.append({"from":sid,"to":claim_id,"relation":"reports"})
        r = review_by_id.get(oid, {})
        lineage = r.get("evidenceLineage", {})
        for d in lineage.get("independentDomains", []):
            iid = "source:" + d
            if iid not in seen_nodes:
                nodes.append({"id":iid,"type":"source","label":d}); seen_nodes.add(iid)
            edges.append({"from":iid,"to":claim_id,"relation":"independent_support"})
        address = canon(item.get("address"))
        if address and address in radar_by_addr:
            rid = "onchain:" + hashlib.sha256(address.encode()).hexdigest()[:16]
            if rid not in seen_nodes:
                nodes.append({"id":rid,"type":"onchain_signal","label":address}); seen_nodes.add(rid)
            edges.append({"from":rid,"to":claim_id,"relation":"onchain_context"})
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "version": 1,
        "updatedAt": now,
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodes": nodes[:5000],
        "edges": edges[:10000],
        "method": "claim -> source/evidence -> on-chain context; repeated news domains are not counted as independent confirmation",
        "safetyBoundary": "Evidence graph is research metadata only; it performs no wallet, signing, claim, transfer, or trade action."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Evidence graph: nodes={len(nodes)} edges={len(edges)}")

if __name__ == "__main__":
    main()
