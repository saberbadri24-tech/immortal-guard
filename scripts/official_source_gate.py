#!/usr/bin/env python3
"""Official-source + live-verification qualification gate for Immortal Guard."""
import json,re
from pathlib import Path
from urllib.parse import urlparse

IN=Path("data/opportunities.json")
VERIFY=Path("data/verification_gate.json")
OUT=Path("data/official_source_gate.json")
OFFICIAL_DOMAINS={
"hackerone.com","immunefi.com","code4rena.com","sherlock.xyz","gitcoin.co",
"ton.org","blog.ton.org","ethereum.org","blog.ethereum.org","solana.com",
"polygon.technology","arbitrum.io","optimism.io","base.org","avax.network",
"starknet.io","zksync.io","scroll.io","linea.build","celestia.org","cosmos.network",
"near.org","sui.io","aptosfoundation.org","polkadot.com","chainlink.com","chain.link",
"uniswap.org","aave.com","coinbase.com","kraken.com","binance.com","okx.com",
"galxe.com","app.galxe.com","layer3.xyz","zealy.io","questn.com"
}
REWARD=re.compile(r"(airdrop|reward|rewards|bounty|grant|prize|points|incentive|hackathon|testnet|ambassador|retroactive)",re.I)

def host(url):
    return urlparse(url or "").netloc.lower().removeprefix("www.")
def is_official(h):
    return any(h==d or h.endswith("."+d) for d in OFFICIAL_DOMAINS)

def main():
    data=json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items":[]}
    vg=json.loads(VERIFY.read_text(encoding="utf-8")) if VERIFY.exists() else {"items":[]}
    checks={str(x.get("id")):x for x in vg.get("items",[])}
    rows=[]; qualified=[]; discovery=[]
    for x in data.get("items",[]):
        iid=str(x.get("id")); h=host(x.get("url")); direct=is_official(h); v=checks.get(iid,{})
        live=v.get("verification")=="REACHABLE_DOMAIN_ALIGNED"
        clean=not v.get("expiredSignal") and not v.get("blockedSignal")
        reward=bool(v.get("rewardSignal")) or bool(REWARD.search(str(x.get("title",""))+" "+str(x.get("note",""))))
        eligible=bool(v.get("eligibilitySignal"))
        ok=direct and live and clean and reward
        reason=[]
        if not direct: reason.append("not-direct-official-domain")
        if not live: reason.append("live-verification-not-aligned")
        if not clean: reason.append("expired-or-blocked-signal")
        if not reward: reason.append("no-reward-signal")
        if ok:
            qualified.append(x.get("id"))
        else:
            discovery.append(x.get("id"))
        rows.append({"id":x.get("id"),"title":x.get("title"),"url":x.get("url"),"domain":h,
          "officialDomain":direct,"liveVerified":live,"rewardSignal":reward,"eligibilitySignal":eligible,
          "qualification":"OFFICIAL_VERIFIED_ACTIONABLE" if ok else "DISCOVERY_ONLY",
          "reasons":reason})
    OUT.write_text(json.dumps({
      "version":2,"officialVerifiedActionableCount":len(qualified),
      "discoveryOnlyCount":len(discovery),"qualifiedIds":qualified,
      "discoveryOnlyIds":discovery,"items":rows,
      "rule":"A direct official domain alone is not enough; live HTTPS/domain verification and a reward/action signal are required."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Official source gate: actionable={len(qualified)} discovery_only={len(discovery)}")
if __name__=="__main__": main()
