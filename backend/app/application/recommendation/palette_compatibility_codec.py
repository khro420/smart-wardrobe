"""Exact C2 score/archive codec, independent of active policy loaders."""
from fractions import Fraction as F
from app.application.recommendation.palette_compatibility_policy import encode,decode,digest,RESOURCE_SHA256
from app.domain.value_objects.palette_compatibility import PROFILES,DECISION,WEIGHTS,Interval,PaletteDecision,PaletteCompatibilityComponent,PaletteError
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
from app.domain.value_objects.context_relevance import ratio,read_ratio

def evidence(v):
    return {'name':v.name,'value':ratio(v.value),'state':v.state,'observed':v.observed,'possible':v.possible,'reasons':list(v.reasons)}
def component(v):return {'summary':evidence(v.summary),'details':[evidence(d) for d in v.details]}
def exact(value,names):
    if type(value) is not dict or set(value)!=set(names):raise ValueError('Exact C2 archive schema required.')
def read_evidence(v):
    exact(v,('name','value','state','observed','possible','reasons'))
    if type(v['reasons']) is not list:raise ValueError('C2 reasons list required.')
    return ScoreEvidence(v['name'],None if v['value'] is None else read_ratio(v['value']),v['state'],v['observed'],v['possible'],tuple(v['reasons']))
def read_component(v):
    exact(v,('summary','details'))
    if type(v['details']) is not list:raise ValueError('C2 details list required.')
    return ComponentScore(read_evidence(v['summary']),tuple(read_evidence(d) for d in v['details']))

def score_data(score):
    if type(score.compatibility) is not PaletteCompatibilityComponent or score.profile_name not in PROFILES.values() or score.policy_version!=DECISION or score.weights!=WEIGHTS or score.compatibility.decision.policy_hash!=RESOURCE_SHA256:raise ValueError('Explicit selected C2 score required.')
    c=score.compatibility;d=c.decision;data=component(c)
    data.update(adapter_version=c.adapter_version,decision={'structure':d.structure,'policy_version':d.policy_version,'policy_hash':d.policy_hash,
        'atoms':[{'name':name,'lower':ratio(b.lower),'upper':ratio(b.upper)} for name,b in d.atoms],
        **{key:ratio(getattr(d,key)) for key in ('value','lower','upper','known_sum')},
        **{key:getattr(d,key) for key in ('basis','atomic_count','known_count','pair_count')}})
    return {'request_match':component(score.request_match),'compatibility':data,'preference':component(score.preference),
            'total':ratio(score.total),'profile_name':score.profile_name,'policy_version':score.policy_version,'weights':[ratio(w) for w in score.weights]}

def score_from_data(data):
    exact(data,('request_match','compatibility','preference','total','profile_name','policy_version','weights'))
    c=data['compatibility'];exact(c,('summary','details','adapter_version','decision'))
    if c['adapter_version']!='recorded-palette-component-1.0.0':raise ValueError('C2 adapter tag required.')
    d=c['decision'];exact(d,('structure','policy_version','policy_hash','atoms','value','lower','upper','known_sum','basis','atomic_count','known_count','pair_count'))
    if type(d['atoms']) is not list:raise ValueError('C2 atomic list required.')
    atoms=[]
    for a in d['atoms']:
        exact(a,('name','lower','upper'));atoms.append((a['name'],Interval(read_ratio(a['lower']),read_ratio(a['upper']))))
    raw=read_component({'summary':c['summary'],'details':c['details']});decision=PaletteDecision(raw,d['structure'],tuple(atoms),d['policy_hash'],d['policy_version'])
    result=RecommendationScore(read_component(data['request_match']),PaletteCompatibilityComponent(raw.summary,raw.details,decision=decision),read_component(data['preference']),
        read_ratio(data['total']),data['profile_name'],data['policy_version'],tuple(read_ratio(w) for w in data['weights']))
    if score_data(result)!=data:raise ValueError('C2 exact metadata does not reconstruct.')
    return result

def score_to_json(score):
    raw=encode(score_data(score))
    if len(raw)>262144:raise PaletteError('CompatibilityCapacityExceeded','C2 score exceeds unchanged256KiB.')
    if score_from_data(decode(raw,262144))!=score:raise ValueError('C2 exact replay mismatch.')
    return raw.decode()

def bounded_provenance(value):
    if type(value) is not dict or 'palette_compatibility' not in value:raise ValueError('C2 provenance requires selected evidence.')
    raw=encode(value)
    if len(raw)>1048576:raise PaletteError('CompatibilityCapacityExceeded','C2 provenance exceeds1MiB.')
    return raw.decode()

def build_archive(prepared,verified,score,wearer,request_text,request,exclusions=()):
    from app.application.recommendation.attribute_preference_codec import projected_snapshot
    from app.application.recommendation.refinement_verifier import snapshot_digest,request_digest
    from app.application.recommendation.context_relevance_scorer import snapshot_hash
    from app.domain.value_objects.palette_compatibility import EVIDENCE,PaletteWriteDraft
    rows=[]
    for m in verified.candidate.members:
        rows.append({'role':m.role,'snapshot_sha256':snapshot_hash(m.garment),'snapshot':projected_snapshot(m.garment),'description':prepared.by_id[m.garment.garment_id].description.to_dict()})
    value={'contract':EVIDENCE,'policy_snapshot':prepared.policy.snapshot(),'account_id':prepared.user,'wearer_id':wearer.profile_id,
        'collection_sha256':prepared.collection_sha256,'strict_snapshot_sha256':snapshot_digest(v.snapshot for v in prepared.collection),
        'original_text':request_text,'request':request.to_dict(),'excluded_categories':list(exclusions),'request_sha256':request_digest(request_text,request,exclusions),
        'selected':rows,'score_sha256':digest(score_data(score))}
    value['revision']=digest(value)
    return PaletteWriteDraft(encode(value),prepared.collection_sha256)

def display(record):
    from app.application.recommendation.palette_compatibility_verifier import validate_archive,validate_relative
    from app.application.recommendation.decision_score_codec import score_from_json
    from app.application.recommendation.refinement_verifier import validate_refinement
    from app.domain.value_objects.recommendation_refinement import step_key,REQUEST_VERSION
    source=record['provenance'];score=score_from_json(encode(record['score_metadata']).decode())
    saved=validate_archive(source['palette_compatibility'],score,record['user_id'],record['profile_id'],items=record.get('items'),request_text=record.get('request_text'))
    d=score.compatibility.decision
    result={'version':'assistant-scoring-display-4.0.0','kind':'PaletteCompatibility','profile_name':score.profile_name,'policy_version':score.policy_version,
        'compatibility_profile':'recorded_palette_compatibility_v1','compatibility_basis':d.basis,
        'palette':{'state':score.compatibility.summary.state,'lower':ratio(d.lower),'upper':ratio(d.upper),'contribution':ratio(d.value),
                  'known':d.known_count,'possible':d.atomic_count,'pair_count':d.pair_count,'policy_sha256':d.policy_hash},
        'components':[{'name':name,'state':c.summary.state,'raw_value':ratio(c.summary.value),'contribution':ratio(c.contribution),'weight':ratio(w),'weighted':ratio(w*c.contribution),'reasons':list(c.summary.reasons)} for name,c,w in zip(('R','C','P'),(score.request_match,score.compatibility,score.preference),score.weights)],
        'total':ratio(score.total),'source_limitations':['Recorded owner-selected palette fractions; unresolved mass remains unknown.','The midpoint is a prototype decision convention, not measured fashion compatibility.','Independent fashion evaluation remains OPEN.']}
    relative=source.get('context_relevance')
    if relative is not None:
        validate_relative(relative,score)
        result.update({k:relative[k] for k in ('selection_mode','fallback_reason','objective','coverage','numeric_ties','selected_members')})
        if 'bundle_id' in relative:result.update(bundle_id=relative['bundle_id'],context_plan=relative['context_plan'])
    if 'attribute_preference' in source:
        from app.application.recommendation.attribute_preference_verifier import validate,conditions_from
        p=source['attribute_preference'];proof=source.get('refinement')
        validate(p,score,record['user_id'],record['profile_id'],conditions=conditions_from(source),items=record.get('items'),request_text=record.get('request_text'),exclusions=proof['excluded_categories'] if proof else source.get('garment_refinement',{}).get('excluded_categories',()))
        result.update(preference_ledger=p['ledger'],preference_snapshot_revision=p['snapshot']['revision'])
    refinement=source.get('refinement')
    if refinement is not None:
        validate_refinement(refinement,relative,score,record['id'],record['request_text'],saved['request'],user_id=record['user_id'],wearer_profile_id=record['profile_id'])
        ordinal=refinement['ordinal'];p2='attribute_preference' in source
        action={'submission_key':step_key(refinement['root_id'],ordinal+1),'refinement':{'version':REQUEST_VERSION,'kind':'alternative','parent_recommendation_id':record['id']},'compatibility_profile':'recorded_palette_compatibility_v1'} if ordinal<9 else None
        if action is not None and p2:action['preference_profile']='attribute_preference_decision_v2'
        result['refinement']={**{k:refinement[k] for k in ('root_id','parent_id','ordinal','excluded_categories','root_R','root_total','mode','total_vs_root')},
            'version':'recommendation-refinement-lineage-1.0.0','next_action':action,'limit_reached':ordinal==9,
            'certificate_universe':'remaining_permitted_pool' if ordinal else 'initial_permitted_pool'}
    return result
