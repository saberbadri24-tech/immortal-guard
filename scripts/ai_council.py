#!/usr/bin/env python3
"""Live AI council for Immortal Guard.

Astra = OpenAI coordinator
Claude = Anthropic reviewer
Immortal Guard remains the final deterministic safety gate.

Secrets are read only from process environment. Nothing is written back to source,
and no model is allowed to claim, sign, transfer, bypass controls, or handle keys.
"""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

DATA = Path("data/opportunities.json")
OUT = Path("data/ai_reviews.json")

def post(url, headers, body, timeout=45):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code}: {detail}")

def openai_review(api_key, model, item):
    prompt = json.dumps(item, ensure_ascii=False)
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": (
                "You are Astra, the coordinator of Immortal Guard. Review the opportunity "
                "as a defensive intelligence task. Never recommend bypassing CAPTCHA, KYC, "
                "Sybil controls, rate limits, or identity checks. Never request or expose "
                "seed phrases/private keys. Return concise JSON with keys: verdict, risks, "
                "evidence_to_check, next_safe_step."
            )},
            {"role": "user", "content": prompt}
        ],
        "max_output_tokens": 700
    }
    r = post("https://api.openai.com/v1/responses",
             {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, body)
    text = r.get("output_text")
    if not text:
        parts = []
        for o in r.get("output", []):
            for c in o.get("content", []):
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    parts.append(c["text"])
        text = "\n".join(parts)
    return text or json.dumps({"verdict":"no-output"})

def claude_review(api_key, model, item):
    body = {
        "model": model, "max_tokens": 900,
        "system": (
            "You are Claude, the critical reviewer for Immortal Guard. Inspect the supplied "
            "opportunity for scam indicators, unverifiable claims and unsafe instructions. "
            "Do not suggest bypasses or financial actions. Return concise JSON: verdict, "
            "risks, evidence_to_check, next_safe_step."
        ),
        "messages": [{"role":"user","content":json.dumps(item, ensure_ascii=False)}]
    }
    r = post("https://api.anthropic.com/v1/messages",
             {"x-api-key": api_key, "anthropic-version": "2023-06-01",
              "content-type": "application/json"}, body)
    return "".join(x.get("text","") for x in r.get("content",[]) if x.get("type")=="text")

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = [x for x in data.get("items",[]) if x.get("status") != "blocked"][:20]
    cfg = {
        "astra": (os.getenv("OPENAI_API_KEY"), os.getenv("ASTRA_MODEL","gpt-5.6-luna")),
        "claude": (os.getenv("ANTHROPIC_API_KEY"), os.getenv("CLAUDE_MODEL","claude-sonnet-5")),
    }
    missing = [name for name,(key,_) in cfg.items() if not key]
    reviews=[]
    for item in items:
        row={"id":item.get("id"),"url":item.get("url"),"at":datetime.now(timezone.utc).isoformat(),"models":{}}
        for name, fn, pair in [
            ("astra",openai_review,cfg["astra"]),
            ("claude",claude_review,cfg["claude"]),
        ]:
            key,model=pair
            if not key:
                row["models"][name]={"status":"not-configured"}
                continue
            try:
                row["models"][name]={"status":"live","model":model,"review":fn(key,model,item)[:6000]}
            except Exception as e:
                row["models"][name]={"status":"error","model":model,"error":str(e)[:500]}
        reviews.append(row)
    OUT.write_text(json.dumps({
        "version":1,"updatedAt":datetime.now(timezone.utc).isoformat(),
        "live": not missing,"missingProviders":missing,"count":len(reviews),
        "items":reviews,
        "safety":{"autoClaim":False,"autoSigning":False,"autoTransfer":False,"secretStorage":False}
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if missing:
        print("AI council not fully configured; missing: "+", ".join(missing))
    else:
        print(f"AI council live: {len(reviews)} opportunities reviewed by Astra/Claude")

if __name__=="__main__":
    main()
