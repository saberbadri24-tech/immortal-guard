#!/usr/bin/env python3
"""Official-source qualification gate for Immortal Guard."""
import json
from pathlib import Path
from urllib.parse import urlparse

IN=Path("data/opportunities.json")
OUT=Path("data/official_source_gate.json")
OFFICIAL_DOMAINS={
"hackerone.com","immunefi.com","code4rena.com","sherlock.xyz","gitcoin.co",
"ton.org","ethereum.org","blog.ethereum.org","solana.com","polygon.technology",
"arbitrum.io","optimism.io","base.org","avax.network","starknet.io","zksync.io",
"scroll.io","linea.build","celestia.org","cosmos.network","near.org","sui.io",
"aptosfoundation.org","polkadot.com","chainlink.com","chain.link","uniswap.org",
"aave.com","coinbase.com","kraken.com","binance.com","okx.com","galxe.com",
"app.galxe.com","layer3.xyz","zealy.io","questn.com"
}
AGGREGATORS={"news.google.com","coindesk.com","cointelegraph.com","decrypt.co",
"theblock.co","finance.yahoo.com","yahoo.com","medium.com"}

def host(url): return urlparse(url or "").netloc.lower().removeprefix("www.")
def is_official(h): return any(h==d or h.endswith("."+d) for d in OFFICIAL_DOMAINS)

def main():
    data=json.loads(IN.read_text(encoding="utf-8")) if IN.exists() else {"items":[]}
    rows=[]; qualified=[]; discovery=[]
    for x in data.get("items",[]):
        h=host(x.get("url")); direct=is_official(h); agg=h in AGGREGATORS or "news.google.com" in h
        rows.append({"id":x.get("id"),"title":x.get("title"),"url":x.get("url"),
                     "domain":h,"officialDomain":direct,"aggregator":agg,
                     "qualification":"OFFICIAL_DIRECT" if direct else "DISCOVERY_ONLY"})
        (qualified if direct else discovery).append(x.get("id"))
    OUT.write_text(json.dumps({
      "version":1,"officialDomainCount":len(qualified),
      "discoveryOnlyCount":len(discovery),"qualifiedIds":qualified,
      "discoveryOnlyIds":discovery,"items":rows,
      "rule":"Search/news/press aggregators can discover leads but cannot qualify earning opportunities."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Official source gate: official={len(qualified)} discovery_only={len(discovery)}")
if __name__=="__main__": main()
