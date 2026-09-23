#!/usr/bin/env python3
"""Multisensor public-token discovery radar. Discovery only; never trades or signs."""
import json, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('data/radar_intel.json')
HEADERS = {'User-Agent': 'ImmortalGuard-MultisensorRadar/2.0', 'Accept': 'application/json'}
SOURCES = {
    'geckoterminal_new_pools': 'https://api.geckoterminal.com/api/v2/networks/new_pools?include_gt_community_data=true',
    'geckoterminal_trending_pools': 'https://api.geckoterminal.com/api/v2/networks/trending_pools?duration=24h&include_gt_community_data=true',
    'dexscreener_profiles': 'https://api.dexscreener.com/token-profiles/latest/v1',
    'dexscreener_boosts': 'https://api.dexscreener.com/token-boosts/latest/v1',
    'dexscreener_takeovers': 'https://api.dexscreener.com/community-takeovers/latest/v1',
}

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))

def rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get('data'), list): return payload['data']
        if isinstance(payload.get('pairs'), list): return payload['pairs']
    return []

def num(v):
    try: return float(v or 0)
    except (ValueError, TypeError): return 0.0

def norm(item, source):
    attrs = item.get('attributes') or item
    token_rel = (item.get('relationships') or {}).get('base_token', {}).get('data') or {}
    token = item.get('tokenAddress') or attrs.get('address') or attrs.get('token_address')
    chain = item.get('chainId') or attrs.get('network') or attrs.get('chain_id')
    if token_rel.get('id'):
        token = token or str(token_rel['id']).split('_', 1)[-1]
        chain = chain or str(token_rel['id']).split('_', 1)[0]
    name = attrs.get('name') or item.get('name')
    symbol = attrs.get('symbol') or item.get('symbol')
    url = item.get('url') or attrs.get('url') or ''
    liquidity = num(attrs.get('reserve_in_usd') or attrs.get('liquidity_usd'))
    volume_obj = attrs.get('volume_usd') or {}
    tx_obj = attrs.get('transactions') or {}
    volume = num(volume_obj.get('h24') if isinstance(volume_obj, dict) else volume_obj)
    txns = num((tx_obj.get('h24') or {}).get('buys', 0) + (tx_obj.get('h24') or {}).get('sells', 0)) if isinstance(tx_obj, dict) else 0
    change = num((attrs.get('price_change_percentage') or {}).get('h24')) if isinstance(attrs.get('price_change_percentage'), dict) else 0
    fdv = num(attrs.get('fdv_usd'))
    market_cap = num(attrs.get('market_cap_usd'))
    created = attrs.get('pool_created_at')
    community_bad = num(attrs.get('community_sus_report'))
    community_pos = num(attrs.get('sentiment_vote_positive_percentage'))
    boosted = num(item.get('amount') or attrs.get('amount'))
    return {
        'chain': chain, 'address': token, 'name': name, 'symbol': symbol, 'url': url,
        'liquidityUsd': liquidity, 'volume24hUsd': volume, 'txns24h': txns,
        'priceChange24hPct': change, 'fdvUsd': fdv, 'marketCapUsd': market_cap,
        'poolCreatedAt': created, 'communitySusReports': community_bad,
        'communityPositivePct': community_pos, 'boostAmount': boosted, 'source': source
    }

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
        time.sleep(0.2)

    merged = {}
    for r in collected:
        key = (str(r.get('chain') or '').lower(), str(r.get('address') or r.get('url') or '').lower())
        if key == ('', ''): continue
        if key not in merged:
            merged[key] = dict(r, signals=[], sourceCount=0)
        m = merged[key]
        m['signals'].append(r['source'])
        for k in ('name','symbol','url','poolCreatedAt'):
            if not m.get(k) and r.get(k): m[k] = r[k]
        for k in ('liquidityUsd','volume24hUsd','txns24h','boostAmount','communitySusReports','communityPositivePct','priceChange24hPct','fdvUsd','marketCapUsd'):
            m[k] = max(m.get(k, 0), r.get(k, 0))
        m['sourceCount'] = len(set(m['signals']))

    results = []
    for m in merged.values():
        # Discovery score = market activity + cross-source confirmation + momentum.
        # It is NOT a probability of profit and NOT a safety audit.
        score = min(25, 8 * max(0, m['sourceCount'] - 1))
        liq, vol, tx = m['liquidityUsd'], m['volume24hUsd'], m['txns24h']
        if liq >= 250000: score += 25
        elif liq >= 100000: score += 20
        elif liq >= 25000: score += 14
        elif liq >= 5000: score += 7
        if vol >= 1000000: score += 20
        elif vol >= 100000: score += 16
        elif vol >= 10000: score += 10
        elif vol >= 1000: score += 4
        if tx >= 500: score += 12
        elif tx >= 100: score += 8
        elif tx >= 25: score += 4
        if m['priceChange24hPct'] > 10: score += min(10, int(m['priceChange24hPct'] / 10))
        if m['boostAmount'] > 0: score += 4
        if m['communityPositivePct'] >= 70: score += 2
        m['discoveryScore'] = min(100, score)

        flags = []
        if liq < 5000: flags.append('very-low-liquidity')
        if liq and vol / liq > 20: flags.append('extreme-volume-to-liquidity')
        if abs(m['priceChange24hPct']) > 200: flags.append('extreme-24h-move')
        if m['communitySusReports'] > 0: flags.append('community-suspicion-reports')
        if m['sourceCount'] > 1:
            confidence = 'multi-source'
        else:
            confidence = 'single-source'
        m['confidence'] = confidence
        m['riskFlags'] = flags
        m['riskStatus'] = 'UNVERIFIED—manual contract/security/ownership/liquidity-lock review required'
        m['action'] = 'RESEARCH_ONLY'
        results.append(m)

    results.sort(key=lambda x: (x['discoveryScore'], x.get('volume24hUsd',0), x.get('liquidityUsd',0)), reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'version': 2,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'sources': SOURCES,
        'sourceErrors': errors,
        'sourceRows': len(collected),
        'uniqueCandidates': len(results),
        'items': results[:500],
        'methodology': 'Cross-source discovery using new/trending pools, public DEX profiles, boosts and community takeovers. Ranking favors liquidity, volume, transaction activity and independent source confirmation.',
        'disclaimer': 'Discovery ranking only; not investment advice, not a rug-pull audit, not a prediction and not a guarantee of profit. No wallet connection, signing, trading, claiming, or transfers.'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Multisensor radar v2: raw={len(collected)} unique={len(results)} source_errors={len(errors)}')

if __name__ == '__main__': main()
