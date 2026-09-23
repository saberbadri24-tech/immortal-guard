#!/usr/bin/env python3
"""Safe Immortal Guard public opportunity radar. Never claims, signs, transfers, or handles secrets."""
import json,re,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse,quote
FEEDS={
    "HackerOne":"https://www.hackerone.com/blog/rss.xml",
    "Gitcoin":"https://gitcoin.co/blog/feed/",
    "TON Blog":"https://blog.ton.org/rss.xml",
    "Ethereum Foundation":"https://blog.ethereum.org/feed.xml",
    "Google News — security bounties":"https://news.google.com/rss/search?q="+quote("(bug bounty OR security bounty OR vulnerability rewards)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — grants":"https://news.google.com/rss/search?q="+quote("(web3 OR crypto OR blockchain) (grant OR funding OR builders program)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — hackathons":"https://news.google.com/rss/search?q="+quote("(web3 OR crypto OR blockchain) (hackathon OR coding contest OR developer challenge)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — testnets":"https://news.google.com/rss/search?q="+quote("(blockchain OR web3) (testnet OR devnet OR incentivized testnet)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — rewards":"https://news.google.com/rss/search?q="+quote("(web3 OR crypto) (rewards OR points OR incentive campaign OR retroactive)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — airdrop":"https://news.google.com/rss/search?q="+quote("(crypto OR web3) (airdrop OR token distribution) -seed -private-key -recovery")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — ambassador":"https://news.google.com/rss/search?q="+quote("(web3 OR blockchain) (ambassador OR community program OR creator program)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — developer":"https://news.google.com/rss/search?q="+quote("(blockchain OR web3) (developer OR builders OR SDK) (grant OR bounty OR program)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — TON programs":"https://news.google.com/rss/search?q="+quote("(TON OR Toncoin) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Ethereum programs":"https://news.google.com/rss/search?q="+quote("(Ethereum OR ETH) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Solana programs":"https://news.google.com/rss/search?q="+quote("(Solana) (grant OR hackathon OR bounty OR developer OR rewards)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Polygon programs":"https://news.google.com/rss/search?q="+quote("(Polygon OR POL) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Arbitrum programs":"https://news.google.com/rss/search?q="+quote("(Arbitrum) (grant OR hackathon OR bounty OR incentives OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Optimism programs":"https://news.google.com/rss/search?q="+quote("(Optimism OR OP) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Base programs":"https://news.google.com/rss/search?q="+quote("(Base) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Avalanche programs":"https://news.google.com/rss/search?q="+quote("(Avalanche OR AVAX) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Starknet programs":"https://news.google.com/rss/search?q="+quote("(Starknet) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — zkSync programs":"https://news.google.com/rss/search?q="+quote("(zkSync) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Scroll programs":"https://news.google.com/rss/search?q="+quote("(Scroll) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Linea programs":"https://news.google.com/rss/search?q="+quote("(Linea) (grant OR hackathon OR bounty OR testnet OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Celestia programs":"https://news.google.com/rss/search?q="+quote("(Celestia) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Cosmos programs":"https://news.google.com/rss/search?q="+quote("(Cosmos OR Cosmos SDK) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — NEAR programs":"https://news.google.com/rss/search?q="+quote("(NEAR) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Sui programs":"https://news.google.com/rss/search?q="+quote("(Sui) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Aptos programs":"https://news.google.com/rss/search?q="+quote("(Aptos) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Polkadot programs":"https://news.google.com/rss/search?q="+quote("(Polkadot) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Chainlink programs":"https://news.google.com/rss/search?q="+quote("(Chainlink) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — Uniswap programs":"https://news.google.com/rss/search?q="+quote("(Uniswap) (grant OR hackathon OR bounty OR developer)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — DeFi opportunities":"https://news.google.com/rss/search?q="+quote("(DeFi OR protocol) (grant OR bounty OR hackathon OR rewards)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — open source rewards":"https://news.google.com/rss/search?q="+quote("(open source) (bounty OR grant OR reward OR contest)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — bug bounty platforms":"https://news.google.com/rss/search?q="+quote("(HackerOne OR Immunefi OR Code4rena OR Sherlock) (bounty OR contest)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — crypto research":"https://news.google.com/rss/search?q="+quote("(crypto OR blockchain) (research grant OR research bounty OR fellowship)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — startup programs":"https://news.google.com/rss/search?q="+quote("(crypto OR web3) (accelerator OR incubator OR builder program)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — ecosystem funding":"https://news.google.com/rss/search?q="+quote("(blockchain ecosystem) (funding OR grant OR builder)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — retroactive programs":"https://news.google.com/rss/search?q="+quote("(web3 OR crypto) (retroactive rewards OR points program OR contributor rewards)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — global opportunities":"https://news.google.com/rss/search?q="+quote("(web3 OR crypto OR blockchain) (opportunity OR program OR rewards OR grant)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — official announcements":"https://news.google.com/rss/search?q="+quote("(crypto OR blockchain) (official announcement) (grant OR bounty OR hackathon OR testnet)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — developer contests":"https://news.google.com/rss/search?q="+quote("(developer) (contest OR challenge OR bounty) (web3 OR blockchain OR crypto)")+"&hl=en-US&gl=US&ceid=US:en",
    "Google News — community rewards":"https://news.google.com/rss/search?q="+quote("(web3 OR blockchain) (community rewards OR contributor rewards OR ambassador)")+"&hl=en-US&gl=US&ceid=US:en"
}
KEYWORDS=re.compile(r"\b(airdrop|bounty|bug bounty|rewards?|grant|hackathon|contest|incentiv|testnet|ambassador|retroactive|points)\b",re.I)
BLOCKED=re.compile(r"(seed phrase|private key|recovery phrase|pay to claim|captcha bypass|kyc bypass|sybil|fake account|multiple accounts|farm wallets)",re.I)
OUT=Path("data/opportunities.json"); HISTORY=Path("data/history.json")
def txt(n,*names):
    for x in names:
        e=n.find(x)
        if e is not None and e.text:return e.text.strip()
    return ""
def feed(name,url):
    q=urllib.request.Request(url,headers={"User-Agent":"ImmortalGuardOpportunityRadar/2.0"})
    with urllib.request.urlopen(q,timeout=20) as r: raw=r.read(2500000)
    root=ET.fromstring(raw); entries=root.findall(".//item") or root.findall(".//{*}entry"); out=[]
    for it in entries[:100]:
        title=txt(it,"title","{*}title"); link=txt(it,"link","{*}link")
        if not link:
            e=it.find("{*}link"); link=e.attrib.get("href","") if e is not None else ""
        summary=txt(it,"description","{*}summary","{*}content"); blob=re.sub(r"<[^>]+>"," ",summary)
        blob=f"{title} {blob}"; host=urlparse(link).netloc.lower()
        if not title or not link or not KEYWORDS.search(blob): continue
        official=any(d in host for d in ("hackerone.com","gitcoin.co","ton.org","ethereum.org")); google_news=("news.google.com" in host); blocked=bool(BLOCKED.search(blob))
        score=20+(30 if official else 0)+(15 if google_news else 0)+(20 if re.search(r"airdrop|reward|bounty|grant",blob,re.I) else 0)+(10 if re.search(r"official|announce|program|foundation",blob,re.I) else 0)-(70 if blocked else 0)
        score=max(0,min(100,score))
        out.append({"id":re.sub(r"[^a-z0-9]+","-",link.lower()).strip("-")[-120:],"title":title[:300],"url":link,"publisher":name,"domain":host,"published":txt(it,"pubDate","{*}published","{*}updated"),"status":"blocked" if blocked else ("candidate" if official else "needs-review"),"score":score,"risk":"blocked" if blocked else ("lower" if official and score>=60 else "review"),"evidence":["public-feed","keyword-match"]+["official-domain"]*int(official)+["google-news-discovery"]*int(google_news),"action":"BLOCK" if blocked else "REVIEW","note":"Verify eligibility, dates, region, contract and official instructions. No automatic claim, signature or transfer."})
    return out
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def main():
    items=[]; errors=[]
    for n,u in FEEDS.items():
        try:items+=feed(n,u)
        except Exception as e:errors.append({"publisher":n,"error":str(e)[:300]})
    items=list({x["url"].rstrip("/"):x for x in items}.values()); items=sorted(items,key=lambda x:(x["score"],x.get("published","")),reverse=True)[:300]
    now=datetime.now(timezone.utc).isoformat(); old=load(OUT,{"items":[]}); om={x.get("url"):x for x in old.get("items",[])}
    for x in items:
        if x["url"] in om and om[x["url"]].get("score")!=x["score"]: x["scoreChanged"]={"from":om[x["url"]].get("score"),"to":x["score"]}
    h=load(HISTORY,{"runs":[]}); h["runs"]=(h.get("runs",[])+[{"at":now,"count":len(items),"blocked":sum(x["status"]=="blocked" for x in items),"feedErrors":errors}])[-500:]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"version":2,"updatedAt":now,"count":len(items),"items":items,"sourceErrors":errors,"engine":{"coordinator":"Astra","reviewer":"Claude","discovery":"Google News + official feeds","finalGuard":"Immortal Guard","scanIntervalMinutes":5,"learning":"score/history deltas","autoClaim":False,"autoTransfer":False,"autoSigning":False,"secretStorage":False}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    HISTORY.write_text(json.dumps({"version":1,"runs":h["runs"]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Radar: {len(items)} items; blocked={sum(x['status']=='blocked' for x in items)}; errors={len(errors)}")
if __name__=="__main__":main()
