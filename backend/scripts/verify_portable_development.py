"""Authenticated clean-install check; writes require explicit disposable consent."""
from pathlib import Path
import argparse,getpass,json,uuid,urllib.request,urllib.error,hashlib,gzip
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[2]

def verify(frontend,backend,password,writes):
    token=None;wearer=None;events=[]
    def call(path,body=None,method=None,raw=False,expected=(200,201)):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if wearer:headers['X-Wardrobe-Profile-Id']=wearer
        if body is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(frontend+'/api/v1'+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=330) as r:status=r.status;wire=r.read()
        except urllib.error.HTTPError as e:status=e.code;wire=e.read()
        if status not in expected:raise AssertionError('Unexpected HTTP '+str(status)+' on '+path+'; inspect owned server logs (credentials omitted).')
        return wire if raw else json.loads(wire)
    with urllib.request.urlopen(backend+'/health',timeout=15) as r:assert r.status==200
    manifest=json.loads((ROOT/'assets/development/manifest.json').read_text(encoding='utf-8'))
    snapshot=json.loads(gzip.decompress((ROOT/'assets/development/snapshot.json.gz').read_bytes()))['tables']
    email=snapshot['users'][0]['email'];token=call('/account/login',{'email':email,'password':password})['access_token']
    cap=call('/recommendations/capabilities');mixed=cap['mixed_wardrobe'];assert mixed['enabled'] and mixed['compatibility']['enabled'] and mixed['personalization']['enabled']
    wearer=mixed['wearers'][0];profiles=call('/account/wardrobe-profiles');assert any(p['id']==wearer for p in profiles)
    garments=call('/wardrobe/garments?include_wearer_eligibility=true');assert len(garments)==51
    assert sum('development_evidence' in g for g in garments)==30
    media={m['id']:m for m in snapshot['media_assets']}
    for g in garments:
        wire=call('/media/'+g['preferred_media_id'],raw=True)
        assert hashlib.sha256(wire).hexdigest()==manifest['media'][media[g['preferred_media_id']]['storage_key']]
    events.append({'check':'authenticated wardrobe/media','available':51,'synthetic':30,'images':51})
    if not writes:return {'result':'PASS','writes':False,'checks':events}
    def recommend(raw,key=None,refinement=None):
        body={'request_text':raw,'wearer_profile_id':wearer,'submission_key':key or 'handover-'+uuid.uuid4().hex}
        if refinement:body['refinement']=refinement
        result=call('/recommendations?pipeline=integrated',body)
        assert result['outcome']=='Selected' and result['score_metadata']['profile_name']=='fashion_compatibility_v2'
        score=result['score_metadata'];ratio=lambda v:F(v['numerator'],v['denominator']) if v is not None else F()
        assert ratio(score['total'])==sum((w*ratio(score[c]['summary']['value']) for w,c in zip((F(3,5),F(1,5),F(1,5)),('request_match','compatibility','preference'))),F())
        history=call('/chats/'+result['chat_id']);assert history['recommendation']['provenance']==result['provenance']
        replay=call('/recommendations?pipeline=integrated',body);assert replay['replayed'] and replay['id']==result['id']
        events.append({'request':raw,'id':result['id'],'ordinal':result['development_continuation']['ordinal'],'history':True,'replay':True});print(json.dumps(events[-1]),flush=True)
        return result
    root=recommend('I need jeans.');current=root
    bases=[]
    for ordinal in range(10):
        proof=current['provenance']['phase2nd_mixed_selection'];base=tuple(tuple(x) for x in proof['decision']['selected']['key'] if x[0]!='outerwear');assert base not in bases;bases.append(base)
        control=current['development_continuation'];assert control['ordinal']==ordinal
        if ordinal==9:assert control['next_action'] is None;break
        a=control['next_action'];assert a;current=recommend(root['request_text'],a['submission_key'],a['refinement'])
    events.append({'check':'ten-result continuation','distinct_bases':len(bases),'cap':True})
    for raw in ("I'm going shopping.","I need an outfit for a job interview as the candidate.","I'd prefer blue trousers."):
        result=recommend(raw)
        if 'interview' in raw:assert result['mixed_wardrobe_display']['decision']['context']['interview_default']['inferred']
    url='/recommendations/'+root['id']+'/feedback'
    for vote in ('like','like','dislike','clear'):
        answer=call(url,{'wearer_profile_id':wearer,'verdict':vote},'PUT');assert answer['verdict']==(None if vote=='clear' else vote)
    # Explicitly exercise the existing P1 UI API in this disposable installation.
    call('/account/preferences/colours',{'preference_value':{'values':['blue']},'weight':1},'PUT');recommend('I need jeans.')
    call('/account/preferences/colours',{'preference_value':{'values':[]},'weight':1},'PUT')
    a=recommend('Recommend an outfit.');b=recommend('Recommend an outfit.')
    da=a['mixed_wardrobe_display']['decision'];db=b['mixed_wardrobe_display']['decision']
    assert da['personalization']['eligible_ties']>1 and da['selected']['key']!=db['selected']['key'] and da['selected']['score']==db['selected']['score']
    # Open a transferred pre-installation record through its original reader.
    transferred=snapshot['phase2nd_mixed_proofs'][0]['id'];assert call('/chats/'+transferred)['recommendation']['id']==transferred
    events.append({'check':'feedback/preferences/diversity/transferred history','pass':True})
    return {'result':'PASS','writes':'disposable installation only','checks':events,'gpu_inference':'NOT_RUN'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--frontend',default='http://127.0.0.1:3000');ap.add_argument('--backend',default='http://127.0.0.1:8000');ap.add_argument('--password-stdin',action='store_true');ap.add_argument('--allow-disposable-writes',action='store_true');ap.add_argument('--output',type=Path);a=ap.parse_args()
    import sys
    password=sys.stdin.readline().rstrip('\r\n') if a.password_stdin else getpass.getpass('Local installation password: ')
    result=verify(a.frontend,a.backend,password,a.allow_disposable_writes)
    if a.output:a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'result':result['result'],'checks':len(result['checks']),'gpu_inference':'NOT_RUN'}))
