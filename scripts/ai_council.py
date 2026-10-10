#!/usr/bin/env python3
"""Independent Immortal Guard review pipeline. No external LLM/provider calls."""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data/opportunities.json")
GATE = Path("data/official_source_gate.json")
SWARM = Path("data/specialist_swarm.json")
OUT = Path("data/ai_reviews.json")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def main():
    now = datetime.now(timezone.utc).isoformat()
    data = load_json(DATA, {"items": []})
    gate = load_json(GATE, {"qualifiedIds": [], "items": []})
    swarm = load_json(SWARM, {"agents": [], "items": []})
    items_by_id = {
        str(x.get("id")): x for x in data.get("items", [])
        if x.get("status") != "blocked" and x.get("id") is not None
    }
    gate_rows = {
        str(x.get("id")): x for x in gate.get("items", [])
        if x.get("id") is not None
    }
    swarm_rows = {
        str(x.get("id")): x for x in swarm.get("items", [])
        if x.get("id") is not None
    }
    qualified = set(str(x) for x in gate.get("qualifiedIds", []))
    candidates = []
    for item_id, item in items_by_id.items():
        if item_id not in qualified:
            continue
        gate_row = gate_rows.get(item_id, {})
        candidates.append((item, gate_row))
    candidates.sort(key=lambda pair: float(pair[0].get("score", 0) or 0), reverse=True)

    rows = []
    for item, gate_row in candidates:
        item_id = str(item.get("id"))
        local = swarm_rows.get(item_id, {})
        rows.append({
            "id": item_id,
            "url": gate_row.get("finalUrl") or item.get("url"),
            "at": now,
            "models": {},
            "localFallback": {
                "active": bool(swarm.get("agents")),
                "status": local.get("status", "HOLD_FOR_EVIDENCE"),
                "agentsPassed": local.get("specialistsPassed", 0),
                "agentsTotal": local.get("specialistsTotal", len(swarm.get("agents", []))),
                "action": local.get("action", "NO_ACTION"),
                "officialQualified": bool(local.get("officialQualified") or gate_row.get("qualified"))
            },
            "independentEngine": {
                "status": "local_review_only",
                "officialDomain": gate_row.get("finalDomain"),
                "qualification": gate_row.get("qualification"),
                "ownerReviewRequired": True,
                "automaticClaim": False,
                "automaticSigning": False,
                "automaticTransfer": False
            }
        })

    local_fallback = {
        "active": bool(swarm.get("agents")),
        "engine": "Immortal Guard deterministic specialist swarm",
        "agents": swarm.get("agents", []),
        "agentCount": len(swarm.get("agents", [])),
        "candidateCount": swarm.get("candidateCount", len(candidates)),
        "readyForOwnerReview": swarm.get("readyForOwnerReview", 0),
        "blockedCount": swarm.get("blockedCount", 0),
        "holdCount": swarm.get("holdCount", 0),
        "noExternalCreditsRequired": True,
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False}
    }
    OUT.write_text(json.dumps({
        "version": 4,
        "updatedAt": now,
        "live": False,
        "configured": True,
        "externalModelsEnabled": False,
        "localEngineActive": local_fallback["active"],
        "providerStatus": {"independent_engine": "active" if local_fallback["active"] else "waiting_for_swarm_data"},
        "providerCircuitOpen": [],
        "successfulCalls": 0,
        "qualifiedInputCount": len(candidates),
        "count": len(rows),
        "items": rows,
        "localFallback": local_fallback,
        "strategy": "first-party specialist swarm reviews evidence; no external provider calls or credit dependencies",
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False, "bypassControls": False}
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "independent_engine_review_complete",
        "qualified": len(candidates),
        "rows": len(rows),
        "localSwarm": local_fallback["active"],
        "externalModelCalls": 0
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
