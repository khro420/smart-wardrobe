"""Transaction-aware mandatory category policy, shared by every usability boundary."""
from pathlib import Path
import hashlib,json
from contextlib import nullcontext
from fastapi import HTTPException
from app.application.ports.workflow_runtime import runtime,connection
from app.application.ports.recommendation_runtime import transaction_garment_query
from app.application.wardrobe.profile_service import require_active_profile,current_profile_id
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.wearer_category_eligibility import (
    POLICY_VERSION,EVIDENCE_VERSION,EligibilityWriteDraft,validate_policy,validate_evidence,encode,digest,KEY)
from app.shared_contracts.wearer_garment_query import WearerGarmentQuery

PROFILE='gender_category_v1'
ENVIRONMENT_KEY='SMART_WARDROBE_WEARER_CATEGORY_PROFILE'
RESOURCE=Path(__file__).with_name('config')/'wearer_category_policy.v1.json'
RESOURCE_SHA256='f0f202a03fcc2954bcd35411455bcafc95cdc91f26e049fa108a5d2d3fc1810e'

def configure(profile):
    if profile=='disabled':return None
    if profile not in (PROFILE,'gender_category_subtype_v2'):raise ValueError('Unknown wearer category profile.')
    resource=RESOURCE if profile==PROFILE else RESOURCE.with_name('wearer_category_policy.v2.json')
    expected=RESOURCE_SHA256 if profile==PROFILE else '25decaa55e80fee168606cc354f9a5519f59a7f5e489f6210aee64e31360b8bb'
    raw=resource.read_bytes()
    if len(raw)>16384 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Unregistered wearer category resource.')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate policy key.')
            result[k]=v
        return result
    return encode(validate_policy(json.loads(raw,object_pairs_hook=pairs)))

def policy():
    try:value=getattr(runtime(),'category_policy',None)
    except RuntimeError:return None  # Unconfigured legacy unit boundary; HTTP startup always binds runtime.
    return validate_policy(json.loads(value)) if value is not None else None

def fail(code,message):raise HTTPException(409,{'code':code,'message':message})

def _profile(conn,owner,profile_id):
    profile_id=profile_id or current_profile_id()
    if not profile_id:fail('WearerSelectionRequired','Choose the intended wearer before starting new work.')
    require_active_profile(conn,owner,profile_id)
    row=conn.execute('SELECT * FROM wardrobe_profile_details_v1 WHERE profile_id=?',(profile_id,)).fetchone()
    key=row['gender_identity'].strip().casefold() if row and type(row['gender_identity']) is str else None
    if not row or row['version']!='wearer-profile-details-1.0.0' or key not in ('male','female'):
        fail('WearerCategoryPolicyUnconfigured','Choose Male or Female in the selected wearer information before starting new work. Other descriptions have no approved category policy yet.')
    return profile_id,dict(row),key

def require_profile(owner,profile_id,conn=None):
    if policy() is None:return None
    with nullcontext(conn) if conn is not None else connection() as c:return _profile(c,owner,profile_id)

def effective_category(row):
    """A valid review supersedes detector output; contradictory mirrors do not."""
    r=dict(row)
    try:
        attrs=r['attributes'] if 'attributes' in r else json.loads(r.get('attributes_json') or '{}')
        if type(attrs) is not dict:return None
        category=r.get('category') or attrs.get('reviewed_category') or r.get('detected_category')
        if category not in GARMENT_STRUCTURE:return None
        role,layer=GARMENT_STRUCTURE[category]
        for name,expected in [('reviewed_category',category),('garment_type',role),('layering_index',layer)]:
            if name in attrs and attrs[name] is not None and attrs[name]!=expected:return None
        return category
    except (ValueError,TypeError):return None

def decision(category,key,selected_policy):
    if category not in GARMENT_STRUCTURE:return 'Unknown'
    return 'Permit' if category in selected_policy['allowed'][key] else 'Deny'

def row_decision(conn,owner,row,key,selected):
    state=decision(effective_category(row),key,selected)
    if state!='Permit' or selected['version']!='wearer-category-policy-2.0.0':return state
    from app.application.wardrobe.verified_subtype_service import source
    from app.domain.value_objects.verified_garment_subtype import decision as subtype_decision
    return subtype_decision(effective_category(row),key,source(conn,owner,row))

def require_categories(conn,owner,profile_id,rows):
    selected=policy()
    if selected is None:return None
    profile_id,details,key=_profile(conn,owner,profile_id)
    for row in rows:
        state=row_decision(conn,owner,row,key,selected)
        if state=='Unknown' and selected['version']=='wearer-category-policy-2.0.0':fail('WearerSubtypeUnresolved','The garment type is not confirmed for this wearer. Review its type before using it.')
        if state=='Unknown':fail('WearerCategoryUnresolved','A supported, consistent garment category is required before this item can be used. Review its category first.')
        if state=='Deny' and selected['version']=='wearer-category-policy-2.0.0' and effective_category(row) in selected['allowed'][key]:fail('WearerSubtypeNotPermitted','Blouses are not permitted for the selected male wearer.')
        if state=='Deny':fail('WearerCategoryNotPermitted','This garment category is not supported for the selected male wearer profile.')
    return details['revision']

def capabilities(owner,profile_id,conn=None):
    selected=policy()
    with nullcontext(conn) if conn is not None else connection() as c:
        require_active_profile(c,owner,profile_id)
        result={'version':'wearer-category-capabilities-1.0.0','enabled':selected is not None,'profile_id':profile_id,'configured':True,'policy_version':POLICY_VERSION if selected else None,'policy_sha256':digest(selected) if selected else None,'details_revision':None,'gender_key':None,'allowed_categories':sorted(GARMENT_STRUCTURE),'reason':None}
        if selected:
            try:_,details,key=_profile(c,owner,profile_id)
            except HTTPException as error:
                result.update(configured=False,allowed_categories=[],reason=error.detail);return result
            result.update(details_revision=details['revision'],gender_key=key,allowed_categories=selected['allowed'][key])
        if selected and selected['version']=='wearer-category-policy-2.0.0':
            from app.domain.value_objects.verified_garment_subtype import registry
            result.update(version='wearer-category-capabilities-2.0.0',policy_version=selected['version'],subtype_registry=registry())
            result['item_decisions']={row['id']:row_decision(c,owner,row,key,selected) for row in c.execute('SELECT * FROM garments WHERE user_id=?',(owner,))}
        return result

def annotations(conn,owner,profile_id,rows):
    cap=capabilities(owner,profile_id,conn)
    rows=[dict(r) for r in rows]
    strict_ids={r.garment_id for r in transaction_garment_query(conn).get_confirmed_available_garments(owner)} if any('category' in r for r in rows) else None
    result=[]
    for row in rows:
        category=effective_category(row)
        reason=None
        if cap['enabled'] and not cap['configured']:reason='WearerCategoryPolicyUnconfigured'
        elif cap['enabled'] and category is None:reason='WearerCategoryUnresolved'
        elif cap['enabled'] and category not in cap['allowed_categories']:reason='WearerCategoryNotPermitted'
        elif 'category' in row and row.get('id') not in strict_ids:reason='ConfirmedAvailableSourceRequired'
        if cap['enabled'] and cap['configured'] and policy()['version']=='wearer-category-policy-2.0.0':
            if 'id' not in row:
                # The orchestrator's extracted view precedes INSERT. It has no
                # subject/event history yet; never turn detector attributes into
                # an owner-confirmed subtype or manufacture a subject identity.
                if set(row)!={'detected_category','attributes_json'}:
                    raise ValueError('Expected the pre-persistence extracted candidate view.')
                from app.domain.value_objects.verified_garment_subtype import PARENTS
                state=decision(category,cap['gender_key'],policy())
                if state=='Permit' and cap['gender_key']=='male' and category in PARENTS:
                    state='Unknown'
            else:
                if type(row['id']) is not str or not row['id'].strip():
                    raise ValueError('Persisted eligibility requires a subject identity.')
                from app.application.wardrobe.verified_subtype_service import projection
                projected=projection(conn,owner,row);row['verified_subtype']=projected
                state=row_decision(conn,owner,row,cap['gender_key'],policy())
            if reason is None and state!='Permit':reason='WearerSubtypeNotPermitted' if state=='Deny' else 'WearerSubtypeUnresolved'
        result.append({**row,'wearer_category_eligibility':{'version':'wearer-category-availability-1.0.0','profile_id':profile_id,'usable':reason is None,'reason':reason}})
    return result

def capture(owner,profile_id,conn=None):
    selected=policy()
    if selected is None:return None
    with nullcontext(conn) if conn is not None else connection() as c:
        if conn is None:c.execute('BEGIN')
        profile_id,details,key=_profile(c,owner,profile_id)
        query=transaction_garment_query(c)
        rows=tuple(query.get_confirmed_available_garments(owner))
        if len(rows)>100:fail('WardrobeCapacityExceeded','The account wardrobe exceeds the supported 100-garment limit.')
        descriptions=tuple(query.get_confirmed_garment_descriptions(owner,runtime().description_policy)) if runtime().description_policy is not None else ()
        raw={r['id']:dict(r) for r in c.execute('SELECT * FROM garments WHERE user_id=?',(owner,))}
        from app.application.recommendation.refinement_verifier import snapshot_digest
        from app.domain.value_objects.attribute_selection_evidence import description_digest
        facts=[{k:raw[g.garment_id].get(k) for k in ('id','category','attributes_json','additional_attributes','preferred_media_id','updated_at')} for g in sorted(rows,key=lambda r:r.garment_id)]
        sources=tuple(query.get_confirmed_garment_subtypes(owner)) if selected['version']=='wearer-category-policy-2.0.0' else ()
        source_map={s.garment_id:s.to_dict() for s in sources}
        from app.domain.value_objects import verified_garment_subtype as subtype
        decisions={g.garment_id:decision(effective_category(raw[g.garment_id]),key,selected) for g in rows}
        if sources:
            decisions={gid:state if state!='Permit' else subtype.decision(raw[gid]['category'],key,source_map[gid]) for gid,state in decisions.items()}
        usable=tuple(g for g in rows if decisions[g.garment_id]=='Permit')
        ids={g.garment_id for g in usable}
        document={'version':EVIDENCE_VERSION,'policy':selected,'policy_sha256':digest(selected),'owner_id':owner,'profile_id':profile_id,'details_revision':details['revision'],'gender_key':key,'account_count':len(rows),'account_source_sha256':digest({'snapshots':snapshot_digest(rows),'descriptions':description_digest(descriptions) if descriptions else None,'raw_category_sources':digest(facts)}),'usable_ids':sorted(ids)}
        if selected['version']=='wearer-category-policy-2.0.0':
            document.update(version='wearer-category-eligibility-evidence-2.0.0',subtype_sources=[s.to_dict() for s in sources],subtype_registry=subtype.registry(),subtype_decisions=decisions)
            document['account_source_sha256']=digest({'original':document['account_source_sha256'],'subtype_sources':document['subtype_sources']})
        document['scope_sha256']=digest(document)
        return WearerGarmentQuery(owner,rows,descriptions,usable,tuple(d for d in descriptions if d.snapshot.garment_id in ids),EligibilityWriteDraft(encode(document)),sources,tuple(s for s in sources if s.garment_id in ids))

def revalidate(conn,owner,profile_id,draft):
    current=capture(owner,profile_id,conn)
    if current is None:
        if draft is not None:fail('WearerEligibilityChanged','The wearer category policy changed. Start a fresh request.')
        return None
    if type(draft) is not EligibilityWriteDraft or current.eligibility!=draft:fail('WearerEligibilityChanged','The wearer information or account source changed. Start a fresh request.')
    return current

def check_request(request,intent,scope):
    if scope is None:return
    allowed=set(scope.eligibility.to_dict()['policy']['allowed'][scope.eligibility.to_dict()['gender_key']])
    groups={'top':{c for c,(r,_) in GARMENT_STRUCTURE.items() if r=='top'},'bottom':{c for c,(r,_) in GARMENT_STRUCTURE.items() if r=='bottom'},'dress':{c for c,(r,_) in GARMENT_STRUCTURE.items() if r=='dress'},'outerwear':{c for c,(r,_) in GARMENT_STRUCTURE.items() if r=='outerwear'}}
    def assert_possible(possible):
        if possible and not possible&allowed:fail('WearerCategoryNotPermitted','This garment category is not supported for the selected male wearer profile. Choose another wearer or change the request.')
    for item in getattr(request,'garment_categories',None) or ():
        assert_possible(groups.get(item.value,{item.value}) if item.kind=='group' else {item.value})
    if intent:
        from app.domain.value_objects.attribute_conditions import ROLES
        rolemap={'upper':'top','lower':'bottom','one_piece':'dress','outerwear':'outerwear'}
        for group in intent.conditions.to_dict()['groups']:
            if group['quantifier']=='none':continue
            possible={c for c,(r,_) in GARMENT_STRUCTURE.items() if r in {rolemap[x] for x in ROLES[group['role']]}}
            for condition in group['conditions']:
                if condition['attribute']=='verified_subtype' and scope.eligibility.to_dict()['gender_key']=='male' and set(condition['values'])=={'blouse'}:fail('WearerSubtypeNotPermitted','Blouses are not permitted for the selected male wearer. Choose another wearer or change the request.')
                if condition['attribute']=='category':possible&=set(condition['values'])
            assert_possible(possible)

def check_parent(repository,owner,parent_id,scope):
    if scope is None:return
    parent=repository.get(owner,parent_id,profile_id=scope.eligibility.to_dict()['profile_id'])
    archived=parent.get('provenance',{}).get(KEY)
    if archived is None or archived.get('scope_sha256')!=scope.eligibility.to_dict()['scope_sha256']:
        fail('WearerEligibilityChanged','The wearer category scope changed or predates this policy. Start a fresh request.')
