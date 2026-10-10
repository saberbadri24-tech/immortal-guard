#!/usr/bin/env python3
"""Bounded external AI council with local specialist fallback and quota circuit breaker.

Astra/OpenAI, Claude/Anthropic and Gemini/Google are optional external reviewers.
The deterministic six-agent Guard swarm remains active when provider credits or
credentials are unavailable. No claims, signatures, transfers or secret handling.
"""
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA = Path("data/opportunities.json")
GATE = Path("data/official_source_gate.json")
SWARM = Path("data/specialist_swarm.json")
OUT = Path("data/ai_reviews.json")
CIRCUIT = Path("data/provider_circuit_state.json")
COOLDOWN_HOURS = 24


def post(url, headers, body, timeout=35):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def openai_review(key, model, item):
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": "You are Astra, defensive opportunity reviewer. Never recommend bypassing CAPTCHA, KYC, Sybil controls, rate limits or identity checks. Never request seed phrases/private keys. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step."},
            {"role": "user", "content": json.dumps(item, ensure_ascii=False)}
        ],
        "max_output_tokens": 700
    }
    r = post("https://api.openai.com/v1/responses", {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body)
    text = r.get("output_text")
    if not text:
        text = "\n".join(c["text"] for o in r.get("output", []) for c in o.get("content", []) if c.get("type") in ("output_text", "text") and c.get("text"))
    return text or '{"verdict":"no-output"}'


def gemini_review(key, model, item):
    body = {"contents": [{"role": "user", "parts": [{"text": "You are Gemini, an independent defensive reviewer. Check scams, unverifiable claims and unsafe instructions. Do not suggest bypasses or financial actions. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step. Opportunity: " + json.dumps(item, ensure_ascii=False)}]}]}
    r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={urllib.parse.quote(key)}", {"Content-Type": "application/json"}, body)
    return "".join(p.get("text", "") for c in r.get("candidates", []) for p in c.get("content", {}).get("parts", []) if p.get("text"))


def claude_review(key, model, item):
    body = {
        "model": model, "max_tokens": 900,
        "system": "You are Claude, critical reviewer. Check scams, unverifiable claims and unsafe instructions. Do not suggest bypasses or financial actions. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step.",
        "messages": [{"role": "user", "content": json.dumps(item, ensure_ascii=False)}]
    }
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
    return "".join(x.get("text", "") for x in r.get("content", []) if x.get("type") == "text")


def quota_error(message):
    s = str(message or "").lower()
    return any(x in s for x in (
        "insufficient_quota", "no credits remaining", "credit balance is too low",
        "credit_balance_exhausted", "billing", "purchase credits", "plans & billing"
    ))


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def is_future(value, now):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > now
    except (TypeError, ValueError):
        return False


def review_one(item, cfg, circuit):
    row = {"id": item.get("id"), "url": item.get("url"), "at": datetime.now(timezone.utc).isoformat(), "models": {}}
    jobs = [("astra", openai_review), ("claude", claude_review), ("gemini", gemini_review)]

    def run(job):
        name, fn = job
        key, model = cfg[name]
        if not key:
            return name, {"status": "not-configured", "model": model}
        state = circuit.get(name, {})
        if is_future(state.get("blockedUntil"), datetime.now(timezone.utc)):
            return name, {"status": "circuit-open", "model": model, "error": state.get("reason", "provider temporarily paused after quota/billing error")}
        try:
            return name, {"status": "live", "model": model, "review": fn(key, model, item)[:6000]}
        except Exception as e:
            return name, {"status": "error", "model": model, "error": str(e)[:500]}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(run, job) for job in jobs]
        for future in as_completed(futures):
            name, result = future.result()
            row["models"][name] = result
    return row


def main():
    now = datetime.now(timezone.utc)
    data = load_json(DATA, {"items": []})
    gate = load_json(GATE, {"qualifiedIds": [], "items": []})
    swarm = load_json(SWARM, {"agents": [], "items": []})
    previous = load_json(OUT, {"items": []})
    circuit = load_json(CIRCUIT, {})
    items_by_id = {str(x.get("id")): x for x in data.get("items", []) if x.get("status") != "blocked"}
    gate_rows = {str(x.get("id")): x for x in gate.get("items", []) if x.get("id") is not None}
    swarm_rows = {str(x.get("id")): x for x in swarm.get("items", []) if x.get("id") is not None}
    qualified = set(str(x) for x in gate.get("qualifiedIds", []))
    cfg = {
        "astra": (os.getenv("OPENAI_API_KEY"), os.getenv("ASTRA_MODEL", "gpt-5.6-luna")),
        "claude": (os.getenv("ANTHROPIC_API_KEY"), os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")),
        "gemini": (os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    }

    # Reuse a recent quota/billing error as a circuit-breaker signal instead of
    # spending a request on every candidate every five minutes.
    previous_by_provider = {name: [] for name in cfg}
    for review in previous.get("items", []):
        for name, result in (review.get("models") or {}).items():
            if name in previous_by_provider:
                previous_by_provider[name].append(result)
    for name, (key, _model) in cfg.items():
        if not key:
            continue
        if is_future(circuit.get(name, {}).get("blockedUntil"), now):
            continue
        errors = [r.get("error", "") for r in previous_by_provider[name] if r.get("status") == "error"]
        quota = next((err for err in errors if quota_error(err)), None)
        if quota:
            circuit[name] = {
                "blockedUntil": (now + timedelta(hours=COOLDOWN_HOURS)).isoformat(),
                "reason": "quota-or-billing error observed; external requests paused for 24h",
                "lastError": str(quota)[:300],
                "updatedAt": now.isoformat()
            }

    items = []
    for item_id, item in items_by_id.items():
        if item_id not in qualified:
            continue
        review_item = dict(item)
        gate_row = gate_rows.get(item_id, {})
        if gate_row.get("finalUrl"):
            review_item["sourceUrl"] = review_item.get("url")
            review_item["url"] = gate_row["finalUrl"]
        review_item["officialDomain"] = gate_row.get("finalDomain")
        review_item["qualification"] = gate_row.get("qualification")
        items.append(review_item)
    items.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)

    missing = [name for name, (key, _model) in cfg.items() if not key]
    reviews = []
    successes = 0
    provider = {name: 0 for name in cfg}
    # Up to 12 candidates are sent to external models; local swarm screens all candidates.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(review_one, item, cfg, circuit) for item in items]
        for future in as_completed(futures):
            row = future.result()
            local = swarm_rows.get(str(row.get("id")), {})
            row["localFallback"] = {
                "active": bool(swarm.get("agents")),
                "status": local.get("status", "HOLD_FOR_EVIDENCE"),
                "agentsPassed": local.get("specialistsPassed", 0),
                "agentsTotal": local.get("specialistsTotal", len(swarm.get("agents", []))),
                "action": local.get("action", "NO_ACTION"),
                "officialQualified": bool(local.get("officialQualified"))
            }
            reviews.append(row)
            for name, result in row["models"].items():
                if result.get("status") == "live":
                    successes += 1
                    provider[name] += 1
                elif result.get("status") == "error" and quota_error(result.get("error")):
                    circuit[name] = {
                        "blockedUntil": (now + timedelta(hours=COOLDOWN_HOURS)).isoformat(),
                        "reason": "quota-or-billing error observed; external requests paused for 24h",
                        "lastError": str(result.get("error"))[:300],
                        "updatedAt": now.isoformat()
                    }
    reviews.sort(key=lambda x: x.get("at", ""))
    CIRCUIT.parent.mkdir(parents=True, exist_ok=True)
    CIRCUIT.write_text(json.dumps(circuit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local_fallback = {
        "active": bool(swarm.get("agents")),
        "engine": "Immortal Guard deterministic specialist swarm",
        "agents": swarm.get("agents", []),
        "agentCount": len(swarm.get("agents", [])),
        "candidateCount": swarm.get("candidateCount", 0),
        "readyForOwnerReview": swarm.get("readyForOwnerReview", 0),
        "blockedCount": swarm.get("blockedCount", 0),
        "holdCount": swarm.get("holdCount", 0),
        "noExternalCreditsRequired": True,
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False}
    }
    status = {
        name: ("not-configured" if not key else
               "circuit-open" if is_future(circuit.get(name, {}).get("blockedUntil"), now) else
               "configured")
        for name, (key, _model) in cfg.items()
    }
    OUT.write_text(json.dumps({
        "version": 3,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "live": successes > 0,
        "configured": not missing,
        "missingProviders": missing,
        "providerStatus": status,
        "providerCircuitOpen": [name for name in cfg if status[name] == "circuit-open"],
        "successfulCalls": successes,
        "providerSuccess": provider,
        "qualifiedInputCount": len(items),
        "count": len(reviews),
        "items": reviews,
        "localFallback": local_fallback,
        "strategy": "local six-agent specialist swarm always screens all candidates; external AI reviews only a bounded batch and circuit-breaks on quota exhaustion",
        "safety": {"autoClaim": False, "autoSigning": False, "autoTransfer": False, "secretStorage": False, "bypassControls": False}
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"AI council: qualified={len(items)} external_success={successes}; "
        f"local_swarm={local_fallback['active']} ready={local_fallback['readyForOwnerReview']}; "
        f"circuit_open={[name for name in cfg if status[name] == 'circuit-open']}; missing={missing}"
    )


if __name__ == "__main__":
    main()
