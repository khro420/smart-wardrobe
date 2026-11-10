"""P2 immutable selected evidence and independent archived reconstruction."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import json
from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot,PreferenceError,POLICY_HASH,DECISION,PROFILE,encode,digest,exact,HASH
from app.domain.value_objects.attribute_preference_evidence import AttributePreferenceEvidence,AttributePreferenceWriteDraft,EVIDENCE,preference_scope,ratio,read_ratio


def build(prepared,candidate,score,base_scope,garment_hash,description_hash,request_hash,*,exclusions=()):
    from app.application.recommendation.attribute_preference_codec import projected_snapshot
    from app.application.recommendation.context_relevance_scorer import snapshot_hash
    relative=score.request_match.summary.name=='relative_style_alignment'
    ledger=prepared.public(candidate,relative=relative).to_dict()
    selected=[]
    for member in candidate.candidate.members:
        item=prepared.by_id[member.garment.garment_id]
        selected.append({'role':member.role,'snapshot_sha256':snapshot_hash(member.garment),
            'legacy_snapshot':projected_snapshot(member.garment),'description':item.description.to_dict()})
    scope={'legacy_base_scope_sha256':base_scope,'garment_snapshot_sha256':garment_hash,'description_collection_sha256':description_hash,
           'request_sha256':request_hash,'preference_scope_sha256':preference_scope(prepared.snapshot,base_scope,garment_hash,description_hash,request_hash)}
    value={'contract':EVIDENCE,'decision':DECISION,'policy':POLICY_HASH,'snapshot':prepared.snapshot.to_dict(),'scope':scope,'selected':selected,'ledger':ledger,'revision':''}
    value['revision']=digest(value)
    evidence=AttributePreferenceEvidence.from_dict(value)
    validate(evidence.to_dict(),score,prepared.account_id,prepared.snapshot.to_dict()['wearer_id'],conditions=prepared.conditions,exclusions=exclusions)
    return AttributePreferenceWriteDraft(evidence)


def conditions_from(provenance):
    source=provenance.get('attribute_selection')
    if source is None:return None
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    return AttributeIntent.from_dict(source['intent']).conditions


def validate(value,score,user,wearer,*,conditions=None,items=None,request_text=None,exclusions=()):
    from app.domain.value_objects.palette_compatibility import PROFILES
    if score.profile_name in (PROFILES[True,False],PROFILES[True,True]):
        from app.application.recommendation.palette_compatibility_selection import legacy_score
        score=legacy_score(score)
    from app.application.recommendation.attribute_preference_codec import restore_snapshot,restore_request,archived_legacy_component
    from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
    from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
    from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence
    from app.domain.value_objects.context_relevance import RelativeObjective
    from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
    evidence=AttributePreferenceEvidence.from_dict(value);data=evidence.to_dict();snapshot=AttributePreferenceSnapshot.from_dict(data['snapshot'])
    if score.profile_name!=PROFILE or score.policy_version!=DECISION or data['snapshot']['account_id']!=user or data['snapshot']['wearer_id']!=wearer:
        raise PreferenceError('PreferenceInvalid','P2 score/account/wearer evidence mismatch.')
    ledger=data['ledger']
    exact(ledger,('contract','snapshot_revision','configured_denominator','request','conditions_sha256','objective','relative','original_text','decision','effective','raw','families'))
    if ledger['contract']!='attribute-preference-ledger-1.0.0' or type(ledger['relative']) is not bool or type(ledger['original_text']) is not str or not 1<=len(ledger['original_text'])<=500:
        raise PreferenceError('PreferenceInvalid','Invalid P2 decision ledger identity.')
    if request_text is not None and ledger['original_text']!=request_text:raise PreferenceError('PreferenceInvalid','P2 original request text mismatch.')
    if ledger['conditions_sha256']!=(conditions.sha256 if conditions is not None else None):raise PreferenceError('PreferenceInvalid','P2 hard-condition binding mismatch.')
    request=restore_request(ledger['request']);objective=RelativeObjective(**ledger['objective']) if ledger['objective'] is not None else None
    if ledger['relative']!=(score.request_match.summary.name=='relative_style_alignment') or ledger['relative'] and objective is None:
        raise PreferenceError('PreferenceInvalid','P2 relative decision mode mismatch.')
    pool=[];members=[]
    for position,row in enumerate(data['selected'],1):
        exact(row,('role','snapshot_sha256','legacy_snapshot','description'))
        if type(row['snapshot_sha256']) is not str or not HASH.fullmatch(row['snapshot_sha256']):raise PreferenceError('PreferenceInvalid','Invalid captured source snapshot hash.')
        g=restore_snapshot(row['legacy_snapshot'])
        if g.user_id!=user:raise PreferenceError('PreferenceInvalid','Foreign P2 selected source.')
        description=GarmentDescriptionEvidence.from_dict(row['description'])
        pool.append(ConfirmedGarmentDescription(g,description));members.append(CandidateMember(g,row['role'],position))
    candidate=OutfitCandidate(tuple(members))
    prepared=PreparedAttributePreferences(snapshot,pool,conditions=conditions,objective=objective,request=request,original_text=ledger['original_text'])
    signature=tuple((m.role,m.garment.garment_id) for m in members)
    original=archived_legacy_component(prepared,signature)
    actual=prepared.evaluate(signature,original,relative=ledger['relative'])
    if actual.to_dict()!=ledger or actual.score!=score.preference:raise PreferenceError('PreferenceInvalid','Stored P2 utilities/weights/masks do not reconstruct exactly.')
    from app.application.recommendation.refinement_verifier import request_digest
    if request_digest(ledger['original_text'],request,exclusions)!=data['scope']['request_sha256']:
        raise PreferenceError('PreferenceInvalid','P2 original request scope mismatch.')
    if items is not None:
        stored={i['garment_id']:i for i in items}
        if set(stored)!={m.garment.garment_id for m in members}:raise PreferenceError('PreferenceInvalid','P2 selected item identities disagree.')
        for m in members:
            item=stored[m.garment.garment_id]
            if item.get('name')!=m.garment.name or item.get('category')!=m.garment.category:raise PreferenceError('PreferenceInvalid','P2 historical item snapshots disagree.')
    return evidence


def validate_relative(data,score,candidate=None,request=None):
    """Reuse the old R source/context reader; certify P2's full bounds separately."""
    from app.application.recommendation.context_relevance_verifier import validate_evidence
    from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence
    from app.domain.value_objects.context_relevance import bounded_json
    required={'version','explanation_version','policy_version','policy_sha256','catalogue_version','catalogue_sha256','requested_profile','actual_profile',
        'preference_profile','preference_snapshot_sha256','preference_ledger_sha256','selection_mode','fallback_reason','objective','coverage','strongest_unresolved',
        'selected_members','winning_key','numeric_ties','preference_denominator','relative_R','score_components','total','weights'}
    if 'bundle_id' in data:required|={'bundle_id','bundle_sha256','context_plan'}
    if 'selection_scope_sha256' in data:required.add('selection_scope_sha256')
    if 'attribute_scope_sha256' in data:required|={'attribute_scope_sha256','attribute_selection_sha256'}
    exact(data,required);bounded_json(data)
    if data['version']!='context-relevance-evidence-2.0.0' or data['explanation_version']!='context-relevance-explanation-2.0.0' or data['preference_profile']!=PROFILE or data['actual_profile']!=score.profile_name or score.profile_name!=PROFILE:
        raise PreferenceError('PreferenceInvalid','Unknown P2 ranking proof identity.')
    for key in ('preference_snapshot_sha256','preference_ledger_sha256'):
        if type(data[key]) is not str or not HASH.fullmatch(data[key]):raise PreferenceError('PreferenceInvalid','Invalid P2 ranking evidence digest.')
    if tuple(read_ratio(v) for v in data['score_components'])!=(score.request_match.contribution,score.compatibility.contribution,score.preference.contribution) or read_ratio(data['total'])!=score.total or tuple(read_ratio(v) for v in data['weights'])!=score.weights:
        raise PreferenceError('PreferenceInvalid','P2 ranking proof and score disagree.')
    denominator=read_ratio(data['preference_denominator'])
    if not 0<=denominator<=10:raise PreferenceError('PreferenceInvalid','Invalid P2 configured denominator.')
    coverage=data['coverage'];scoped='selection_scope_sha256' in data
    names={'hard_passed','point_candidates','unresolved_candidates','objective_unavailable_candidates','global_optimum_certified'}
    if scoped:names|={'already_seen','below_floor_points','unresolved_below_floor'}
    exact(coverage,names)
    if type(coverage['global_optimum_certified']) is not bool or any(type(coverage[k]) is not int or not 0<=coverage[k]<=1000000 for k in names-{'global_optimum_certified'}):raise PreferenceError('PreferenceInvalid','Invalid P2 coverage counts.')
    if not coverage['hard_passed'] or coverage['hard_passed']!=sum(coverage[k] for k in names-{'hard_passed','global_optimum_certified'}):raise PreferenceError('PreferenceInvalid','Incomplete P2 coverage partition.')
    relative=data['selection_mode']=='best_evidenced_with_coverage_v1';blocker=data['strongest_unresolved']
    if bool(coverage['unresolved_candidates'])!=(blocker is not None):raise PreferenceError('PreferenceInvalid','Missing P2 unresolved blocker.')
    certified=relative
    if blocker is not None:
        exact(blocker,('key','R_low','R_high','optimistic'))
        low,high=read_ratio(blocker['R_low']),read_ratio(blocker['R_high']);values=tuple(read_ratio(v) for v in blocker['optimistic'])
        if len(values)!=4 or any(not 0<=v<=1 for v in values) or not 0<=low<high<=1 or values[1]!=high or values[0]!=F(3,5)*high+F(1,5)*values[2]+F(1,5)*values[3]:raise PreferenceError('PreferenceInvalid','Invalid P2 optimistic decision bound.')
        win=tuple(-v for v in (score.total,score.request_match.contribution,score.compatibility.contribution,score.preference.contribution))+(tuple(tuple(v) for v in data['winning_key']),)
        other=tuple(-v for v in values)+(tuple(tuple(v) for v in blocker['key']),)
        certified=relative and win<other
    if coverage['global_optimum_certified']!=certified:raise PreferenceError('PreferenceInvalid','False P2 global optimum certificate.')
    # The temporary zero-P projection invokes the unchanged reader only for R,
    # selected source identity and archived context schema. The real P2 bounds
    # and full coverage above are validated against the unmodified new proof.
    old={k:v for k,v in data.items() if k not in ('preference_profile','preference_snapshot_sha256','preference_ledger_sha256')}
    attribute='attribute_scope_sha256' in old
    old['version']='context-relevance-evidence-1.3.0' if attribute else 'context-relevance-evidence-1.2.0' if scoped else 'context-relevance-evidence-1.1.0' if 'bundle_id' in old else 'context-relevance-evidence-1.0.0'
    old['explanation_version']=old['version'].replace('evidence','explanation')
    old['preferences']=[];old['preference_denominator']=ratio(F())
    policy='context_relevance_decision_v1' if relative else 'experimental_compatibility_decision_v1'
    no_p=ComponentScore(ScoreEvidence('preference',None,'NoPreferences'))
    proxy=replace(score,preference=no_p,total=F(3,5)*score.request_match.contribution+F(1,5)*score.compatibility.contribution,profile_name=policy)
    old['actual_profile']=policy;old['score_components']=[ratio(score.request_match.contribution),ratio(score.compatibility.contribution),ratio(F())];old['total']=ratio(proxy.total)
    old['coverage']=dict(coverage)
    if relative:
        old['coverage']['hard_passed']-=coverage['unresolved_candidates'];old['coverage']['unresolved_candidates']=0;old['coverage']['global_optimum_certified']=True;old['strongest_unresolved']=None
    elif blocker is not None:
        b=dict(blocker);values=[read_ratio(v) for v in b['optimistic']];values[3]=F();values[0]=F(3,5)*values[1]+F(1,5)*values[2]
        b['optimistic']=[ratio(v) for v in values];old['strongest_unresolved']=b
    validate_evidence(old,proxy,candidate,request)
    return data
