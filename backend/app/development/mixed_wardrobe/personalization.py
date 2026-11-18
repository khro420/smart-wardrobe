"""Exact-score ties only. Exposure is not an inferred like or dislike."""
from collections import Counter
from dataclasses import asdict
from .core import digest,encoded
from .fashion_contract import versions as fashion_versions
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.application.recommendation.preference_normalizer import PreferenceNormalizer

ENV='SMART_WARDROBE_DEVELOPMENT_PERSONALIZATION_PROFILE'
PROFILE='explicit_preferences_diversity_v1'
FEEDBACK_TYPE='explicit_outfit_feedback_v1'
POLICY={'version':PROFILE,'history_limit':10,'feedback_limit':20,'tie_scope':'exact_T_R_C_P',
        'order':['explicit_dislike_last','base_exposure_count','explicit_like_first','garment_exposure_count','ordered_key'],
        'optional_requests':'unchanged','continuation':'unchanged','feedback_scope':'exact_base_only'}
POLICY_SHA256='0cf0026dccd1e9543b2ca5c3eb4d256b7a8513e3533127133dc3edcdae678853'

def versions():return {v:v.replace('mixed-fashion-','mixed-personalized-') for v in fashion_versions().values()}
def base_version(version):return next((a for a,b in versions().items() if b==version),None)

def preferences(catalog,wearer):
    if wearer!=catalog['original']['wearer']['profile_id']:raise ValueError('Foreign personalized wearer.')
    owner=catalog['fixture']['owner_id'];rows=tuple(PreferenceSnapshot(**p) for p in catalog['original']['preferences'])
    normal=PreferenceNormalizer().normalize(owner,rows)
    if any(reason!='zero_weight' for _,reason in normal.diagnostics):raise ValueError('Unsupported active personalized preference.')
    return rows

def base(key):return tuple(tuple(x) for x in key if x[0]!='outerwear')

def validate(data,owner,wearer):
    if digest(POLICY)!=POLICY_SHA256:raise ValueError('Unregistered personalization policy.')
    if not isinstance(data,dict) or set(data)!={'version','policy_sha256','owner','wearer','recent','feedback'}:raise ValueError('Invalid personalization snapshot.')
    if data['version']!=PROFILE or data['policy_sha256']!=POLICY_SHA256 or data['owner']!=owner or data['wearer']!=wearer:raise ValueError('Foreign personalization snapshot.')
    if type(data['recent']) is not list or len(data['recent'])>10 or type(data['feedback']) is not list or len(data['feedback'])>20:raise ValueError('Unbounded personalization snapshot.')
    seen=set()
    for rows,expected in ((data['recent'],{'id','base','created_at'}),(data['feedback'],{'id','base','verdict','created_at'})):
        if any(type(row) is not dict or set(row)!=expected for row in rows):raise ValueError('Invalid personalization source fields.')
    for row in data['recent']+data['feedback']:
        if not isinstance(row['id'],str) or not 1<=len(row['id'])<=100 or not isinstance(row['created_at'],str) or not 1<=len(row['created_at'])<=100:raise ValueError('Invalid personalization source.')
        key=row['base']
        if not isinstance(key,list) or len(key) not in (1,2) or any(type(x) is not list or len(x)!=2 or any(type(v) is not str or not 1<=len(v)<=100 for v in x) for x in key):raise ValueError('Invalid personalized base.')
        if tuple(x[0] for x in key) not in (('upper','lower'),('one_piece',)):raise ValueError('Unsupported personalized structure.')
        if 'verdict' in row and row['verdict'] not in ('like','dislike'):raise ValueError('Invalid explicit feedback.')
    for row in data['feedback']:
        b=base(row['base'])
        if b in seen:raise ValueError('Duplicate explicit base feedback.')
        seen.add(b)

def capture(store,c,owner,wearer):
    recent=[]
    rows=c.execute("select r.id,r.created_at from recommendations r join nlp_chats n on r.chat_id=n.id where r.user_id=? and r.profile_id=? and r.recommendation_type='assistant' and r.status in ('available','saved') and n.user_id=? and n.profile_id=? and n.status='completed' order by r.created_at desc,r.id desc limit 10",(owner,wearer,owner,wearer)).fetchall()
    for row in rows:
        key=[[i['garment_role'],i['garment_id']] for i in c.execute('select garment_role,garment_id from recommendation_items where recommendation_id=? order by item_order',(row['id'],)) if i['garment_role']!='outerwear']
        if tuple(x[0] for x in key) in (('upper','lower'),('one_piece',)):
            recent.append({'id':row['id'],'created_at':row['created_at'],'base':key})
    feedback=read_feedback(store,c,owner,wearer)
    data={'version':PROFILE,'policy_sha256':POLICY_SHA256,'owner':owner,'wearer':wearer,'recent':recent,'feedback':feedback}
    validate(data,owner,wearer);return data

def read_feedback(store,c,owner,wearer):
    import json,hmac
    rows=c.execute('select * from user_preferences where user_id=? and profile_id=? and preference_type=?',(owner,wearer,FEEDBACK_TYPE)).fetchall()
    if not rows:return []
    if len(rows)!=1 or rows[0]['source']!=FEEDBACK_TYPE or rows[0]['is_active']!=0 or rows[0]['weight']!=0:raise ValueError('Invalid explicit feedback storage.')
    text=rows[0]['preference_value_json']
    if len(text.encode())>32768:raise ValueError('Oversized explicit feedback.')
    data=json.loads(text)
    if set(data)!={'owner','wearer','entries','signature'} or data['owner']!=owner or data['wearer']!=wearer:raise ValueError('Foreign explicit feedback.')
    body={k:v for k,v in data.items() if k!='signature'}
    if not hmac.compare_digest(store.sign(body),data['signature']):raise ValueError('Changed explicit feedback.')
    validate({'version':PROFILE,'policy_sha256':POLICY_SHA256,'owner':owner,'wearer':wearer,'recent':[],'feedback':data['entries']},owner,wearer)
    return data['entries']

def choose(data,scores,selected,optional,seen):
    # Never replace a soft-preference choice or change continuation ordering.
    if optional or seen:return selected,{'profile':PROFILE,'applied':False,'reason':'request_policy_unchanged','eligible_ties':0}
    point=lambda s:(s.total,s.request_match.contribution,s.compatibility.contribution,s.preference.contribution)
    tied=[k for k,s in scores.items() if point(s)==point(scores[selected])]
    counts=Counter(base(r['base']) for r in data['recent']);items=Counter(g for r in data['recent'] for _,g in r['base'])
    votes={base(r['base']):r['verdict'] for r in data['feedback']}
    order=lambda k:(votes.get(base(k))=='dislike',counts[base(k)],votes.get(base(k))!='like',sum(items[g] for _,g in base(k)),k)
    chosen=min(tied,key=order)
    return chosen,{'profile':PROFILE,'policy_sha256':POLICY_SHA256,'applied':chosen!=selected,'reason':'exact_score_tie_only','eligible_ties':len(tied),'base_exposure_count':counts[base(chosen)],'explicit_feedback':votes.get(base(chosen)),'history_window':len(data['recent']),'scores_unchanged':True}
