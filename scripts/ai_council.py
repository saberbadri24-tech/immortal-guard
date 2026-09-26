#!/usr/bin/env python3
"""Live AI council for Immortal Guard.

Astra = OpenAI coordinator; Claude = Anthropic reviewer; Gemini = Google reviewer.
Secrets are read only from environment. No claims, signing, transfers or key handling.
"""
import json, os, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
DATA=Path('data/opportunities.json'); OUT=Path('data/ai_reviews.json')
def post(url,headers,body,timeout=45):
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers,method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e: raise RuntimeError(f'HTTP {e.code}: {e.read().decode("utf-8","replace")[:500]}')
def openai_review(key,model,item):
    body={'model':model,'input':[{'role':'system','content':'You are Astra, defensive opportunity reviewer. Never recommend bypassing CAPTCHA, KYC, Sybil controls, rate limits or identity checks. Never request seed phrases/private keys. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step.'},{'role':'user','content':json.dumps(item,ensure_ascii=False)}],'max_output_tokens':700}
    r=post('https://api.openai.com/v1/responses',{'Authorization':f'Bearer {key}','Content-Type':'application/json'},body)
    text=r.get('output_text')
    if not text:
        text='\n'.join(c['text'] for o in r.get('output',[]) for c in o.get('content',[]) if c.get('type') in ('output_text','text') and c.get('text'))
    return text or '{"verdict":"no-output"}'
def gemini_review(key,model,item):
    body={'contents':[{'role':'user','parts':[{'text':'You are Gemini, an independent defensive reviewer. Check scams, unverifiable claims and unsafe instructions. Do not suggest bypasses or financial actions. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step. Opportunity: '+json.dumps(item,ensure_ascii=False)}]}]}
    r=post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={urllib.parse.quote(key)}',{'Content-Type':'application/json'},body)
    return ''.join(p.get('text','') for c in r.get('candidates',[]) for p in c.get('content',{}).get('parts',[]) if p.get('text'))

def claude_review(key,model,item):
    body={'model':model,'max_tokens':900,'system':'You are Claude, critical reviewer. Check scams, unverifiable claims and unsafe instructions. Do not suggest bypasses or financial actions. Return concise JSON: verdict, risks, evidence_to_check, next_safe_step.','messages':[{'role':'user','content':json.dumps(item,ensure_ascii=False)}]}
    r=post('https://api.anthropic.com/v1/messages',{'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'},body)
    return ''.join(x.get('text','') for x in r.get('content',[]) if x.get('type')=='text')
def main():
    data=json.loads(DATA.read_text(encoding='utf-8')); items=sorted([x for x in data.get('items',[]) if x.get('status')!='blocked'], key=lambda x: float(x.get('score',0) or 0), reverse=True)[:25]
    cfg={'astra':(os.getenv('OPENAI_API_KEY'),os.getenv('ASTRA_MODEL','gpt-5.6-luna')),'claude':(os.getenv('ANTHROPIC_API_KEY'),os.getenv('CLAUDE_MODEL','claude-sonnet-4-6')),'gemini':(os.getenv('GEMINI_API_KEY'),os.getenv('GEMINI_MODEL','gemini-3.8-flash'))}
    missing=[n for n,(k,_) in cfg.items() if not k]; reviews=[]; successes=0; provider={n:0 for n in cfg}
    for item in items:
        row={'id':item.get('id'),'url':item.get('url'),'at':datetime.now(timezone.utc).isoformat(),'models':{}}
        for name,fn in [('astra',openai_review),('claude',claude_review),('gemini',gemini_review)]:
            key,model=cfg[name]
            if not key: row['models'][name]={'status':'not-configured'}; continue
            try:
                result=fn(key,model,item)
                row['models'][name]={'status':'live','model':model,'review':result[:6000]}
                successes+=1; provider[name]+=1
            except Exception as e: row['models'][name]={'status':'error','model':model,'error':str(e)[:500]}
        reviews.append(row)
    OUT.write_text(json.dumps({'version':1,'updatedAt':datetime.now(timezone.utc).isoformat(),'live':successes>0,'configured':not missing,'missingProviders':missing,'successfulCalls':successes,'providerSuccess':provider,'count':len(reviews),'items':reviews,'safety':{'autoClaim':False,'autoSigning':False,'autoTransfer':False,'secretStorage':False}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'AI council: reviews={len(reviews)} successful_calls={successes}; missing={missing}')
if __name__=='__main__': main()
