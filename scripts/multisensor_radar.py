#!/usr/bin/env python3
"""Multisensor public-token discovery radar. Discovery only; never trades or signs."""
import json, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('data/radar_intel.json')
HISTORY_OUT = Path('data/radar_memory.json')
ALERTS_OUT = Path('data/radar_alerts.json')

def load_memory():
    try:
        if HISTORY_OUT.exists():
            data = json.loads(HISTORY_OUT.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def opportunity_fingerprint(item):
    basis = '|'.join(str(item.get(k) or '').lower() for k in (
        'chain','address','symbol','name','url'
    ))
    import hashlib
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()[:24]

def temporal_intelligence(item, memory, now_iso):
    fp = opportunity_fingerprint(item)
    previous = memory.get(fp) or {}
    first_seen = previous.get('firstSeen') or now_iso
    last_seen = previous.get('lastSeen')
    old_score = float(previous.get('opportunityScore') or 0)
    new_score = float(item.get('opportunityScore') or 0)
    delta = round(new_score - old_score, 2) if last_seen else 0
    source_gain = int(item.get('sourceCount') or 0) - int(previous.get('sourceCount') or 0)
    novelty = 0
    if not last_seen:
        novelty += 55
    if source_gain > 0:
        novelty += min(20, source_gain * 10)
    if delta >= 20:
        novelty += 20
    elif delta >= 10:
        novelty += 10
    if item.get('security', {}).get('securityGate') == 'BLOCK':
        novelty = min(novelty, 25)
    item['immortalFingerprint'] = fp
    item['temporal'] = {
        'firstSeen': first_seen,
        'lastSeen': last_seen,
        'scoreDelta': delta,
        'sourceCountDelta': source_gain,
        'noveltyScore': min(100, novelty),
        'changeType': (
            'NEW_DISCOVERY' if not last_seen else
            'SIGNAL_STRENGTHENED' if delta >= 10 or source_gain > 0 else
            'SIGNAL_WEAKENED' if delta <= -10 else 'STABLE'
        )
    }
    item['researchPriority'] = min(100, round(
        item.get('opportunityScore', 0) * 0.55 +
        item['temporal']['noveltyScore'] * 0.30 +
        min(20, item.get('sourceCount', 1) * 5) * 0.15
    ))
    return fp

def update_memory(results, memory, now_iso):
    next_memory = {}
    for item in results:
        fp = item['immortalFingerprint']
        next_memory[fp] = {
            'firstSeen': item['temporal']['firstSeen'],
            'lastSeen': now_iso,
            'opportunityScore': item.get('opportunityScore', 0),
            'sourceCount': item.get('sourceCount', 0),
            'securityGate': item.get('security', {}).get('securityGate', 'UNKNOWN'),
            'name': item.get('name'),
            'symbol': item.get('symbol'),
            'chain': item.get('chain'),
            'address': item.get('address')
        }
    # Keep bounded persistent memory; newest observations are retained first.
    items = sorted(next_memory.items(), key=lambda kv: kv[1].get('lastSeen',''), reverse=True)[:5000]
    return dict(items)

def build_alerts(results):
    alerts = []
    for item in results:
        t = item.get('temporal') or {}
        if t.get('changeType') == 'NEW_DISCOVERY' or t.get('scoreDelta', 0) >= 15 or t.get('sourceCountDelta', 0) > 0:
            alerts.append({
                'fingerprint': item.get('immortalFingerprint'),
                'priority': item.get('researchPriority', 0),
                'type': t.get('changeType'),
                'chain': item.get('chain'),
                'symbol': item.get('symbol'),
                'name': item.get('name'),
                'address': item.get('address'),
                'opportunityScore': item.get('opportunityScore', 0),
                'securityGate': (item.get('security') or {}).get('securityGate', 'UNKNOWN'),
                'action': 'RESEARCH_ONLY'
            })
    alerts.sort(key=lambda x: x['priority'], reverse=True)
    return alerts[:100]

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

def security_chain_id(chain):
    mapping = {
        'ethereum': '1', 'eth': '1',
        'bsc': '56', 'binance-smart-chain': '56',
        'polygon': '137', 'polygon_pos': '137', 'matic': '137',
        'arbitrum': '42161', 'arbitrum-one': '42161',
        'optimism': '10',
        'base': '8453',
        'avalanche': '43114', 'avax': '43114',
    }
    return mapping.get(str(chain or '').lower())


def goplus_security(chain, address):
    """Best-effort security intelligence. Empty/unknown is never treated as safe."""
    chain_id = security_chain_id(chain)
    if not chain_id or not address or not str(address).startswith('0x'):
        return None
    url = f'https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode('utf-8'))
        result = (payload.get('result') or {}).get(str(address).lower()) or {}
        if not result:
            result = (payload.get('result') or {}).get(address) or {}
        return result or None
    except Exception:
        return None


def security_summary(sec):
    if not sec:
        return {
            'available': False,
            'hardRiskFlags': [],
            'softRiskFlags': [],
            'securityPenalty': 0,
            'securityGate': 'UNKNOWN'
        }

    def yes(key):
        return str(sec.get(key, '')).lower() in ('1', 'true', 'yes')

    hard = []
    soft = []
    checks = {
        'honeypot': 'is_honeypot',
        'fake-token': 'fake_token',
        'airdrop-scam': 'is_airdrop_scam',
        'malicious-token': 'is_malicious',
        'blacklist': 'is_blacklisted',
        'trading-suspended': 'transfer_pausable',
        'mintable': 'is_mintable',
        'proxy': 'is_proxy',
        'modifiable-tax': 'slippage_modifiable',
        'owner-control': 'can_take_back_ownership',
    }
    for label, key in checks.items():
        if yes(key):
            hard.append(label)

    if str(sec.get('is_open_source', '')) == '0':
        soft.append('unverified-source')
    if yes('is_in_dex') is False and 'is_in_dex' in sec:
        soft.append('not-in-dex')
    if yes('is_honeypot') or yes('is_malicious') or yes('is_airdrop_scam'):
        gate = 'BLOCK'
    elif hard:
        gate = 'HIGH_RISK'
    elif soft:
        gate = 'REVIEW'
    else:
        gate = 'NO_FLAG_REPORTED'

    penalty = min(70, 35 * len(set(hard)) + 8 * len(set(soft)))
    return {
        'available': True,
        'hardRiskFlags': sorted(set(hard)),
        'softRiskFlags': sorted(set(soft)),
        'securityPenalty': penalty,
        'securityGate': gate,
        'rawSelected': {
            k: sec.get(k) for k in (
                'is_open_source', 'is_proxy', 'is_honeypot', 'is_mintable',
                'is_blacklisted', 'transfer_pausable', 'slippage_modifiable',
                'can_take_back_ownership', 'is_in_dex', 'holder_count',
                'is_airdrop_scam', 'is_malicious', 'trust_list'
            ) if k in sec
        }
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
        if key == ('', ''):
            continue
        if key not in merged:
            merged[key] = dict(r, signals=[], sourceCount=0)
        m = merged[key]
        m['signals'].append(r['source'])
        for k in ('name', 'symbol', 'url', 'poolCreatedAt'):
            if not m.get(k) and r.get(k):
                m[k] = r[k]
        for k in ('liquidityUsd', 'volume24hUsd', 'txns24h', 'boostAmount',
                  'communitySusReports', 'communityPositivePct', 'priceChange24hPct',
                  'fdvUsd', 'marketCapUsd'):
            m[k] = max(m.get(k, 0), r.get(k, 0))
        m['sourceCount'] = len(set(m['signals']))

    results = []
    # Security API is deliberately capped to avoid rate-limit pressure.
    # Unknown security data never receives a positive safety assumption.
    security_checked = 0
    for m in merged.values():
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
        if m['priceChange24hPct'] > 10:
            score += min(10, int(m['priceChange24hPct'] / 10))
        if m['boostAmount'] > 0:
            score += 4
        if m['communityPositivePct'] >= 70:
            score += 2

        flags = []
        if liq < 5000: flags.append('very-low-liquidity')
        if liq and vol / liq > 20: flags.append('extreme-volume-to-liquidity')
        if abs(m['priceChange24hPct']) > 200: flags.append('extreme-24h-move')
        if m['communitySusReports'] > 0: flags.append('community-suspicion-reports')

        # Pull security intelligence for a small, high-signal subset first.
        sec = None
        if security_checked < 20 and m.get('address'):
            sec = goplus_security(m.get('chain'), m.get('address'))
            security_checked += 1
            if sec is None:
                time.sleep(0.05)
        security = security_summary(sec)
        flags.extend(security['hardRiskFlags'])
        flags.extend(security['softRiskFlags'])

        raw_score = min(100, score)
        opportunity_score = max(0, min(100, raw_score - security['securityPenalty']))
        if security['securityGate'] == 'BLOCK':
            opportunity_score = min(opportunity_score, 10)

        m['marketSignalScore'] = raw_score
        m['securityPenalty'] = security['securityPenalty']
        m['opportunityScore'] = opportunity_score
        m['security'] = security
        m['riskFlags'] = sorted(set(flags))
        m['confidence'] = 'multi-source' if m['sourceCount'] > 1 else 'single-source'
        m['riskStatus'] = (
            'BLOCKED_BY_SECURITY_SIGNAL' if security['securityGate'] == 'BLOCK'
            else 'UNVERIFIED—manual contract/security/ownership/liquidity-lock review required'
        )
        m['action'] = 'RESEARCH_ONLY'
        m['decision'] = 'DO_NOT_INTERACT' if security['securityGate'] == 'BLOCK' else 'RESEARCH_ONLY'
        results.append(m)

    now_iso = datetime.now(timezone.utc).isoformat()
    memory = load_memory()
    for item in results:
        temporal_intelligence(item, memory, now_iso)
    alerts = build_alerts(results)
    memory = update_memory(results, memory, now_iso)
    results.sort(
        key=lambda x: (
            x.get('researchPriority', 0),
            x['opportunityScore'],
            x['marketSignalScore'],
            x.get('volume24hUsd', 0),
            x.get('liquidityUsd', 0)
        ),
        reverse=True
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_OUT.write_text(json.dumps({
        'version': 1,
        'updatedAt': now_iso,
        'items': memory
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    ALERTS_OUT.write_text(json.dumps({
        'version': 1,
        'updatedAt': now_iso,
        'count': len(alerts),
        'alerts': alerts,
        'safetyBoundary': 'Alerts are research signals only; no automated interaction or transaction is performed.'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    OUT.write_text(json.dumps({
        'version': 4,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'sources': SOURCES,
        'securitySources': ['GoPlus Token Security API (best effort; unknown != safe)'],
        'sourceErrors': errors,
        'sourceRows': len(collected),
        'uniqueCandidates': len(results),
        'securityChecksAttempted': security_checked,
        'memoryItems': len(memory),
        'alertCount': len(alerts),
        'noveltyLayer': 'temporal memory + change detection + convergence-aware research priority',
        'items': results[:500],
        'methodology': (
            'Multisensor discovery combines new/trending pools, public DEX profiles, boosts and '
            'community takeovers. It separates market-signal strength from security risk. '
            'GoPlus security intelligence is used as a risk gate where supported. '
            'OpportunityScore is a research-priority score, not a profit probability or safety rating.'
        ),
        'safetyBoundary': (
            'No wallet signing, private keys, seed phrases, claims, trades, approvals, transfers, '
            'or irreversible on-chain actions are performed by this radar.'
        ),
        'disclaimer': (
            'Discovery and risk-screening only; not investment advice, not a complete smart-contract '
            'audit, not a prediction and not a guarantee of profit. Security APIs can be incomplete or stale.'
        )
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(
        f'Multisensor radar v4: raw={len(collected)} unique={len(results)} '
        f'security_checks={security_checked} source_errors={len(errors)}'
    )


if __name__ == '__main__':
    main()
