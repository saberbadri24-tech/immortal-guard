import json, pathlib, py_compile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))
intel=load("data/engine_reviews.json") if (ROOT/"data/engine_reviews.json").exists() else {}
ledger=load("data/revenue_ledger.json") if (ROOT/"data/revenue_ledger.json").exists() else {}
hunt=load("data/value_hunt.json") if (ROOT/"data/value_hunt.json").exists() else {}
assert ledger.get("accountingRule") == "PAID + VERIFIED + EVIDENCE = EARNED"
assert float(ledger.get("actualCollectedUsd",0)) >= 0
assert hunt.get("incomeRule") in (None,"Only owner-confirmed received funds count as income")
policy=hunt.get("safety",{}) or {}
for key in ("autoClaim","autoSigning","autoTransfer","secretStorage","bypassControls"):
    if key in policy: assert policy[key] is False, key
items=hunt.get("opportunities",hunt.get("items",[])) or []
assert isinstance(items,list)
if items:
    ids=[x.get("id") for x in items if isinstance(x,dict) and x.get("id")]
    assert len(ids)==len(set(ids))
print("GUARD FINAL CONTRACT: PASS")
print("opportunities:",len(items))
print("actualCollectedUsd:",ledger.get("actualCollectedUsd",0))
