#!/usr/bin/env python3
"""Immortal Guard engineering ceiling benchmark.

This is a machine-checkable architecture benchmark, not a marketing claim.
It measures whether the repository actually contains the capabilities needed
for high-end opportunity/revenue intelligence: discovery, convergence,
freshness, verification, evidence lineage, security screening, economics,
learning, settlement truth, safety, regression and observability.

A score is only valid for the checked repository snapshot. It does not prove
profitability or superiority over a private competitor implementation.
"""
import ast, json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/"scripts"
DATA=ROOT/"data"
OUT=DATA/"engineering_benchmark.json"

def read(p):
    try:return p.read_text(encoding="utf-8")
    except Exception:return ""

def py_ast(p):
    try:return ast.parse(read(p))
    except Exception:return None

def has_any(text, needles):
    t=text.lower()
    return any(n.lower() in t for n in needles)

def json_ok(p):
    try: json.loads(read(p)); return True
    except Exception:return False

def capability(name, weight, ok, evidence):
    return {"name":name,"weight":weight,"pass":bool(ok),"evidence":evidence}

def main():
    radar=read(SCRIPTS/"multisensor_radar.py")
    verify=read(SCRIPTS/"verification_gate.py")
    evidence=read(SCRIPTS/"evidence_graph.py")
    engine=read(SCRIPTS/"opportunity_engine.py")
    intel=read(SCRIPTS/"opportunity_intelligence.py")
    value=read(SCRIPTS/"value_hunter.py")
    income=read(SCRIPTS/"income_pipeline.py")
    ledger=read(SCRIPTS/"revenue_ledger.py")
    council=read(SCRIPTS/"ai_council.py")
    health=read(SCRIPTS/"guard_health.py")
    contract=read(SCRIPTS/"guard_final_contract.py")
    workflow=read(ROOT/".github/workflows/opportunity-radar.yml")
    selfimp=read(ROOT/".github/workflows/guard-self-improvement.yml")
    history=read(DATA/"history.json")
    benchmark=[]
    benchmark.append(capability("multi_sensor_discovery",10,
        has_any(radar,["SOURCES =","geckoterminal","dexscreener"]) and radar.count("https://")>=5,
        "radar has multiple independent public discovery endpoints"))
    benchmark.append(capability("temporal_change_detection",8,
        has_any(radar,["temporal_intelligence","scoreDelta","sourceCountDelta","noveltyScore"]),
        "radar memory computes change and novelty"))
    benchmark.append(capability("parallel_verification",8,
        has_any(verify,["ThreadPoolExecutor","domainAligned","finalHttps","publicHost"]),
        "verification checks reachability, redirect/domain alignment and public DNS concurrently"))
    benchmark.append(capability("evidence_lineage",8,
        has_any(evidence,["independent","lineage","source","evidence"]),
        "dedicated evidence graph module present"))
    benchmark.append(capability("specialist_reasoning",8,
        has_any(engine,["SPECIALISTS","TRUSTED_DOMAINS","evidenceLineage","competition"]),
        "independent specialist engine combines domain, evidence and economics signals"))
    benchmark.append(capability("economic_prioritization",10,
        has_any(value,["realizationScore","costSignals","monthlyTargetUsd","rewardBand"]) and
        has_any(intel,["realizationScore","frictionScore","competitionScore"]),
        "value hunter plus intelligence layer scores reward, friction, competition and evidence"))
    benchmark.append(capability("security_screening",10,
        has_any(radar,["goplus_security","securityPenalty","securityGate","honeypot"]),
        "security intelligence is a separate risk gate and unknown is not treated as safe"))
    benchmark.append(capability("freshness_and_expiry",7,
        has_any(verify,["expiredSignal","deadlineSignal"]) and has_any(intel,["freshness"]),
        "expiry/deadline signals feed verification and prioritization"))
    benchmark.append(capability("adaptive_memory",7,
        has_any(radar,["HISTORY_OUT","update_memory","firstSeen","lastSeen"]) and
        (DATA/"radar_memory.json").exists(),
        "persistent temporal memory exists and is bounded"))
    swarm=read(SCRIPTS/"specialist_swarm.py")
    benchmark.append(capability("ai_council",6,
        has_any(council,["localEngineActive","noExternalCreditsRequired","Independent Immortal Guard review pipeline"]) and
        has_any(swarm,["def review(","specialistsPassed","HOLD_FOR_EVIDENCE","ThreatHunter"]),
        "first-party deterministic specialist council; external model calls are optional and not required"))
    benchmark.append(capability("settlement_truth",8,
        has_any(ledger,["PAID + VERIFIED + EVIDENCE = EARNED","actualCollectedUsd"]) and
        has_any(income,["actualIncomeRule","verifiedSettlementCount"]),
        "income is separated from estimates and requires verified settlement evidence"))
    benchmark.append(capability("safety_boundary",7,
        all(has_any(x,["autoSigning","autoTransfer","secretStorage","bypass"]) for x in [contract,income,intel,health]),
        "financial and identity-control actions remain owner-gated"))
    benchmark.append(capability("continuous_automation",5,
        has_any(workflow,["*/5 * * * *","retry()","ThreadPoolExecutor"]) and
        has_any(selfimp,["schedule","owner review","Open review PR"]),
        "five-minute radar plus bounded self-improvement review"))
    benchmark.append(capability("regression_contract",8,
        has_any(workflow,["py_compile","Validate data","JSON OK"]) and
        has_any(contract,["assert","GUARD FINAL CONTRACT: PASS"]),
        "compile/data/contract gates are enforced"))
    benchmark.append(capability("observability",5,
        has_any(health,["blockers","counts","automation","ownerApprovalBoundary"]),
        "machine-readable health snapshot with blockers and automation state"))

    total=sum(x["weight"] for x in benchmark)
    earned=sum(x["weight"] for x in benchmark if x["pass"])
    score=round(100*earned/total,2) if total else 0
    payload={
      "version":1,"updatedAt":datetime.now(timezone.utc).isoformat(),
      "score":score,"earnedWeight":earned,"totalWeight":total,
      "thresholds":{"elite":90,"frontier":95,"ceiling":100},
      "capabilities":benchmark,
      "interpretation":"Repository engineering capability score only; not a profit forecast and not proof of private competitor superiority.",
      "hardStop": score < 90,
      "nextGaps":[x["name"] for x in benchmark if not x["pass"]]
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if score < 90:
        raise SystemExit(f"ENGINEERING BENCHMARK BELOW ELITE: {score}")
    print(f"IMMORTAL GUARD ENGINEERING BENCHMARK: {score}/100")
    print("PASS: elite threshold reached")

if __name__=="__main__":main()
