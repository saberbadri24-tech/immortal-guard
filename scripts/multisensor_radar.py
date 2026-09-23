#!/usr/bin/env python3
"""Multisensor public-token discovery radar. Discovery only; never trades or signs."""
import json, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('data/radar_intel.json')
HEADERS = {'User-Agent': 'ImmortalGuard-MultisensorRadar/1.0', 'Accept': 'application/json'}
SOURCES = {
    'geckoterminal_new_pools': 'https://api.geckoterminal.com/api/v2/networks/new_pools',
    'dexscreener_profiles': 'https://api.dexscreener.com/token-profiles/latest/v1',
    'dexscreener_boosts': 'https://api.dexscreener.com/token-boosts/latest/v1',
}

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))

def rows(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        if isinstance(payload.get('data'), list): return payload['data']
        if isinstance(payload.get('pairs'), list): return payload['pairs']
    return []

def norm(item, source):
    attrs = item.get('attributes') or item
    rel = item.get('relationships') or {}
    base = attrs.get('base_token') or {}
    token = item.get('tokenAddress') or attrs.get('address') or attrs.get('token_address') or base.get('address')
    chain = item.get('chainId') or attrs.get('network') or attrs.get('chain_id')
    name = attrs.get('name') or attrs.get('name') or item.get('name')
    symbol = attrs.get('symbol') or item.get('symbol')
    url = item.get('url') or attrs.get('url') or ''
    liquidity = attrs.get('reserve_in_usd') or attrs.get('liquidity_usd') or 0
    volume = attrs.get('volume_usd') or 0
    try: liquidity = float(liquidity or 0)
    except (ValueError, TypeError): liquidity = 0
    try: volume = float(volume or 0)
    except (ValueError, TypeError): volume = 0
    return {'chain':chain,'address':token,'name':name,'symbol':symbol,'url':url,'liquidityUsd':liquidity,'volumeUsd':volume,'source':source}

def main():
    collected, errors = [], {}
    for source, url in SOURCES.items():
        try:
            payload = get_json(url)
            for item in rows(payload):
                r = norm(item, source)
                if r.get('address') or r.get('url'):
                    collected.append(r)
        except Exception as e:
            errors[source] = str(e)[:240]
        time.sleep(0.25)
    # Merge repeated token signals across public feeds.
    merged = {}
    for r in collected:
        key = (str(r.get('chain') or '').lower(), str(r.get('address') or r.get('url') or '').lower())
        if key == ('', ''): continue
        if key not in merged: merged[key] = dict(r, signals=[])
        m = merged[key]
        m['signals'].append(r['source'])
        for k in ('name','symbol','url'):
            if not m.get(k) and r.get(k): m[k] = r[k]
        m['liquidityUsd'] = max(m.get('liquidityUsd',0), r.get('liquidityUsd',0))
        m['volumeUsd'] = max(m.get('volumeUsd',0), r.get('volumeUsd',0))
    results=[]
    for m in merged.values():
        # Transparent discovery-priority score, not a profit probability or safety audit.
        score = min(25, 8 * max(0, len(set(m['signals']))-1))
        if m.get('liquidityUsd',0) >= 100000: score += 30
        elif m.get('liquidityUsd',0) >= 25000: score += 20
        elif m.get('liquidityUsd',0) >= 5000: score += 10
        if m.get('volumeUsd',0) >= 100000: score += 25
        elif m.get('volumeUsd',0) >= 10000: score += 15
        elif m.get('volumeUsd',0) >= 1000: score += 5
        m['discoveryScore'] = min(100, score)
        m['confidence'] = 'multi-source' if len(set(m['signals'])) > 1 else 'single-source'
        m['riskStatus'] = 'UNVERIFIED—manual contract/security review required'
        m['action'] = 'RESEARCH_ONLY'
        results.append(m)
    results.sort(key=lambda x:(x['discoveryScore'], x.get('volumeUsd',0), x.get('liquidityUsd',0)), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'version':1,'updatedAt':datetime.now(timezone.utc).isoformat(),'sources':SOURCES,'sourceErrors':errors,'sourceRows':len(collected),'uniqueCandidates':len(results),'items':results[:500],'disclaimer':'Discovery ranking only; not investment advice, not a rug-pull audit, and not a guarantee. No wallet connection, signing, trading, claiming, or transfers.'}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Multisensor radar: raw={len(collected)} unique={len(results)} source_errors={len(errors)}')

if __name__ == '__main__': main()
