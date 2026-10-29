"""Independent public relevance reconstruction and archived proof validation."""
from dataclasses import asdict
from fractions import Fraction as F
import hashlib,json
from app.application.recommendation.context_relevance_policy import PROFILE,POLICY_VERSION,POLICY_SHA256,CATALOGUE_SHA256,CATALOGUE_VERSION,SCOPES
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore
from app.domain.value_objects.context_relevance import RelativeObjective,read_ratio,bounded_json

# Historical identities and meanings are deliberately independent of the active
# loader constants. A future release must ADD an archived reader/revision here;
# replacing its current catalogue must not redefine an existing stored record.
ARCHIVED_REVISIONS=frozenset({(
    'context-relevance-policy-1.0.0','54f4d6b59b3cd66abcad8764afd69e298ba59a027facc60cc8314287d63dc5e6',
    'context-relevance-objectives-1.0.0','ccfc5ba24af60d376cf295b25b8e26cb6df4afc738a4ea142a803c6aaa46e18b')})
ARCHIVED_TARGETS={
    'everyday.shopping':'casual','everyday.academic_attendance':'casual',
    'everyday.casual_outing':'casual','social.date':'smart casual','social.meal':'smart casual'}


class PublicAlignmentFacts:
    def __init__(self,garments,objective):
        self.objective=objective
        mapper=GarmentEvidenceMapper()
        self.rows={}
        for garment in garments:
            evidence=mapper.classify(garment).style
            source=garment.saved_attribute_evidence
            good=(evidence.state=='Known' and len(evidence.values)==1
                and garment.contextual_suitability.review_state!='Malformed'
                and garment.contextual_suitability.state!='Malformed'
                and (source.state=='Absent' or source.current(garment)))
            self.rows[garment.garment_id]=(garment,int(evidence.values==(objective.target,)) if good and objective else None)

    def component(self,verified):
        values=[]
        for member in verified.candidate.members:
            if member.role=='outerwear':continue
            garment,value=self.rows[member.garment.garment_id]
            if garment!=member.garment:raise ValueError('Public reconstruction snapshot mismatch.')
            values.append(value)
        known=sum(value is not None for value in values)
        if known!=len(values):return ComponentScore(ScoreEvidence('relative_style_alignment',None,'Unknown',known,len(values)))
        summary=ScoreEvidence('relative_style_alignment',F(sum(values),len(values)),'Available',known,len(values),('recorded_label_alignment_not_fashion_confidence',))
        return ComponentScore(summary,(summary,))


def validate_evidence(data,score,candidate=None,request=None):
    """Decode allowlisted archived revisions, never today's active catalogue."""
    required={'version','explanation_version','policy_version','policy_sha256','catalogue_version','catalogue_sha256',
        'requested_profile','actual_profile','selection_mode','fallback_reason','objective','coverage','strongest_unresolved',
        'selected_members','winning_key','numeric_ties','preference_denominator','preferences','relative_R','score_components','total','weights'}
    scoped=type(data) is dict and data.get('version')=='context-relevance-evidence-1.2.0'
    expanded=type(data) is dict and data.get('version') in ('context-relevance-evidence-1.1.0','context-relevance-evidence-1.2.0')
    if scoped:
        from app.domain.value_objects.context_relevance import require_digest
        required.add('selection_scope_sha256')
        require_digest(data.get('selection_scope_sha256'))
    record=None
    if expanded:
        from app.application.recommendation.context_bundle import archived_record
        required|={'bundle_id','bundle_sha256','context_plan'}
        record=archived_record(data.get('policy_version'),data.get('policy_sha256'),data.get('catalogue_version'),data.get('catalogue_sha256'),data.get('bundle_sha256'))
    if type(data) is not dict or set(data)!=required:raise ValueError('Exact ranking proof schema required.')
    bounded_json(data)
    if (data['version']!=('context-relevance-evidence-1.2.0' if scoped else 'context-relevance-evidence-1.1.0' if expanded else 'context-relevance-evidence-1.0.0') or data['explanation_version']!=('context-relevance-explanation-1.2.0' if scoped else 'context-relevance-explanation-1.1.0' if expanded else 'context-relevance-explanation-1.0.0')
        or (record is None if expanded else (data['policy_version'],data['policy_sha256'],data['catalogue_version'],data['catalogue_sha256']) not in ARCHIVED_REVISIONS)
        or data['requested_profile']!=PROFILE or data['actual_profile']!=score.profile_name):raise ValueError('Unapproved archived ranking identity.')
    if expanded:
        _validate_expanded_plan(data,record,request)
    components=tuple(c.contribution for c in (score.request_match,score.compatibility,score.preference))
    if tuple(read_ratio(x) for x in data['score_components'])!=components or read_ratio(data['total'])!=score.total or tuple(read_ratio(x) for x in data['weights'])!=score.weights:
        raise ValueError('Ranking proof and exact score disagree.')
    coverage=data['coverage']
    names={'hard_passed','point_candidates','unresolved_candidates','objective_unavailable_candidates','global_optimum_certified'}
    if scoped:names|={'already_seen','below_floor_points','unresolved_below_floor'}
    if type(coverage) is not dict or set(coverage)!=names or type(coverage['global_optimum_certified']) is not bool:raise ValueError('Invalid ranking coverage schema.')
    if any(type(coverage[k]) is not int or not 0<=coverage[k]<=1000000 for k in names-{'global_optimum_certified'}):raise ValueError('Invalid coverage counts.')
    partitions=('point_candidates','unresolved_candidates','objective_unavailable_candidates')+ (('already_seen','below_floor_points','unresolved_below_floor') if scoped else ())
    if coverage['hard_passed']<1 or coverage['hard_passed']!=sum(coverage[k] for k in partitions):raise ValueError('Incomplete coverage ledger.')
    if scoped and (coverage['objective_unavailable_candidates'] or data['selection_mode']!='best_evidenced_with_coverage_v1'):
        raise ValueError('Refinement cannot store a baseline or unavailable objective.')
    objective=RelativeObjective(**data['objective']) if data['objective'] is not None else None
    if objective:
        target=(record['targets'] if expanded else ARCHIVED_TARGETS).get(objective.situation)
        if target is None or objective.authority=='prototype_convention' and objective.target!=target:raise ValueError('Unapproved objective.')
        if objective.target not in ('casual','classic','formal','minimal','smart casual','sporty','streetwear','vintage','bohemian'):
            raise ValueError('Unsupported archived canonical target.')
        if request is not None and (objective.situation!=request.context.situation.value or objective.authority=='explicit_user_style' and objective.target!=request.style or objective.authority=='prototype_convention' and request.style is not None):raise ValueError('Objective and request disagree.')
    relative=data['selection_mode']=='best_evidenced_with_coverage_v1'
    if relative:
        if score.profile_name!=PROFILE or objective is None or data['fallback_reason'] is not None or coverage['point_candidates']<1 or coverage['objective_unavailable_candidates']:raise ValueError('Invalid relative selection state.')
        if read_ratio(data['relative_R'])!=score.request_match.contribution:raise ValueError('Relative R mismatch.')
    else:
        if data['selection_mode']!='baseline_disclosed_v1' or score.profile_name!='experimental_compatibility_decision_v1' or coverage['point_candidates'] or coverage['global_optimum_certified'] or data['relative_R'] is not None:raise ValueError('Invalid baseline state.')
        if data['fallback_reason']!=('objective_unavailable' if objective is None else 'no_point_relative_candidate'):raise ValueError('Invalid fallback reason.')
    members=data['selected_members']
    if type(members) is not list or not 1<=len(members)<=3 or type(data['numeric_ties']) is not int or not 1<=data['numeric_ties']<=coverage['hard_passed']:raise ValueError('Invalid members/ties.')
    if data['winning_key']!=[[m['role'],m['garment_id']] for m in members] or len({m['garment_id'] for m in members})!=len(members):raise ValueError('Winning identity mismatch.')
    for m in members:
        if set(m)!={'garment_id','role','snapshot_sha256','styles','match','source_state','origin','review_state'}:raise ValueError('Invalid member proof.')
        if m['match'] is not None and (type(m['match']) is not int or m['match'] not in (0,1)):raise ValueError('Invalid match value.')
    base=[m for m in members if m['role']!='outerwear']
    if relative:
        if any(m['match'] is None or len(m['styles'])!=1 or m['match']!=int(m['styles']==[objective.target]) or m['source_state'] not in ('Absent','Known') or m['review_state']=='Malformed' for m in base):raise ValueError('Unknown evidence cannot earn R.')
        if F(sum(m['match'] for m in base),len(base))!=score.request_match.contribution:raise ValueError('Base alignment arithmetic mismatch.')
    prefs=data['preferences']
    if type(prefs) is not list or len(prefs)>4:raise ValueError('Invalid preference proof.')
    denominator=F();kinds=set()
    for pref in prefs:
        if set(pref)!={'id','kind','values','weight','suppressed'} or pref['kind'] not in ('styles','colours','garment_categories','formality') or pref['kind'] in kinds:raise ValueError('Invalid preference test.')
        kinds.add(pref['kind']);weight=read_ratio(pref['weight'])
        if not 0<weight<=1:raise ValueError('Invalid importance.')
        denominator+=weight
        expected=relative and objective is not None and pref['kind']=='styles' and pref['values']==[objective.target]
        if type(pref['suppressed']) is not bool or pref['suppressed']!=expected:raise ValueError('Duplicate mask mismatch.')
    if read_ratio(data['preference_denominator'])!=denominator:raise ValueError('Preference denominator mismatch.')
    if prefs:
        if len(prefs)!=len(score.preference.details):raise ValueError('Preference detail coverage mismatch.')
        total=F();active=[]
        for pref,detail in zip(prefs,score.preference.details):
            if pref['kind']!=detail.name:raise ValueError('Preference detail identity mismatch.')
            if pref['suppressed']:
                if detail.state!='NotApplicable' or detail.value is not None:raise ValueError('Duplicate preference was paid twice.')
            else:
                active.append(detail)
                total+=read_ratio(pref['weight'])*(detail.value or F())
        expected_value=None if not active or all(d.value is None for d in active) else total/denominator
        if score.preference.summary.value!=expected_value:raise ValueError('Independent preference arithmetic mismatch.')
        if not active and score.preference.summary.state!='NotApplicable':raise ValueError('All-suppressed preference state mismatch.')
    blocker=data['strongest_unresolved']
    if bool(coverage['unresolved_candidates'])!=(blocker is not None):raise ValueError('Missing blocker certificate.')
    certified=relative
    if blocker is not None:
        if set(blocker)!={'key','R_low','R_high','optimistic'}:raise ValueError('Invalid blocker schema.')
        low,high=read_ratio(blocker['R_low']),read_ratio(blocker['R_high'])
        values=tuple(read_ratio(x) for x in blocker['optimistic'])
        if len(values)!=4 or any(not 0<=v<=1 for v in values) or not 0<=low<high<=1 or values[1]!=high or values[0]!=F(3,5)*high+F(1,5)*values[2]+F(1,5)*values[3]:raise ValueError('Invalid optimistic bound.')
        winner_key=tuple(-v for v in (score.total,*components))+(tuple(tuple(x) for x in data['winning_key']),)
        blocker_key=tuple(-v for v in values)+(tuple(tuple(x) for x in blocker['key']),)
        certified=relative and winner_key<blocker_key
    if coverage['global_optimum_certified']!=certified:raise ValueError('False optimality certificate.')
    if candidate is not None:
        if data['winning_key']!=[list(x) for x in candidate.key]:raise ValueError('Candidate identity mismatch.')
        mapper=GarmentEvidenceMapper()
        for saved,member in zip(members,candidate.members):
            digest=hashlib.sha256(json.dumps(asdict(member.garment),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            if saved['snapshot_sha256']!=digest or saved['styles']!=list(mapper.classify(member.garment).style.values):raise ValueError('Candidate snapshot mismatch.')
            g=member.garment
            if (saved['source_state'],saved['origin'],saved['review_state'])!=(g.saved_attribute_evidence.state,g.saved_attribute_evidence.origin,g.contextual_suitability.review_state):raise ValueError('Fabricated source/review provenance.')
        if relative and PublicAlignmentFacts(tuple(m.garment for m in candidate.members),objective).component(type('Verified',(),{'candidate':candidate})()).contribution!=score.request_match.contribution:
            raise ValueError('Actual source currency cannot establish relative R.')
    return data


def _validate_expanded_plan(data,record,request):
    """Use captured archived scope data, never load today's active catalogue."""
    if data['bundle_id']!='context_18_v1' or data['bundle_sha256']!=record['manifest_sha256']:raise ValueError('Unapproved archived bundle.')
    plan=data['context_plan']
    if type(plan) is not dict or set(plan)!={'request','bindings'}:raise ValueError('Invalid compound plan.')
    payload=plan['request'];frame=payload['context'];sid=frame['situation']['values'][0]
    from app.domain.value_objects.general_context_request import GeneralContext,ContextSlot,SourceSpan
    from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint
    from app.domain.value_objects.general_context_request import GeneralContextRequest
    fields={k:ContextSlot(v['state'],tuple(v['values']),tuple(SourceSpan(**span) for span in v['spans'])) if isinstance(v,dict) and set(v)=={'state','values','spans'} else v for k,v in frame.items()}
    typed=GeneralContext(**fields)
    rebuilt=GeneralContextRequest(intent=payload['intent'],occasion=payload['occasion'],style=payload['style'],colours=payload['colours'],garment_categories=tuple(GarmentCategoryConstraint(**c) for c in payload['garment_categories']) if payload['garment_categories'] else None,formality=payload['formality'],context=typed)
    normal=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'))
    if normal(rebuilt.to_dict())!=normal(payload) or typed.bundle_id!='context_18_v1' or typed.grammar_sha256!=record['grammar_sha256'] or typed.taxonomy_sha256!=record['taxonomy_sha256'] or sid not in record['targets']:raise ValueError('Invalid archived context frame.')
    if request is not None and normal(request.to_dict())!=normal(payload):raise ValueError('Ranking proof request mismatch.')
    scope=record['scopes'][sid]
    if (typed.activity.value!=scope['activity'] or tuple(typed.style.values)!=((payload['style'],) if payload['style'] else ())
        or tuple(typed.colours.values)!=tuple(payload['colours'] or ())
        or tuple(typed.categories.values)!=tuple(c['kind']+':'+c['value'] for c in payload['garment_categories'] or ())
        or typed.dress_code.value is not None and typed.formality.value is not None and typed.dress_code.value!=typed.formality.value
        or payload['formality']!=(typed.dress_code.value if typed.dress_code.value is not None else typed.formality.value)
        or payload['formality'] not in (None,'casual','smart_casual')):raise ValueError('Archived request projection mismatch.')
    if payload['occasion']!=scope['target'] or typed.role.state!='Unspecified' or typed.venue.state!='Unspecified' and typed.venue.value not in scope['venues'] or typed.companions.state!='Unspecified' and typed.companions.value not in scope['companions']:raise ValueError('Archived scope mismatch.')
    if any(getattr(typed,k).state!='Unspecified' for k in ('environment','soft_preferences','goals','unhandled')):raise ValueError('Unhandled archived condition.')
    expected=[scope['binding']]
    for facet in typed.facets.values:
        if facet.startswith('transport:'):
            if sid!='travel.journey':raise ValueError('Unapproved transport facet.')
            continue
        secondary={('social.date','meal:dinner'):'social.meal',('social.meal','celebration:birthday'):'social.birthday_gathering'}.get((sid,facet))
        if secondary not in record['scopes']:raise ValueError('Unapproved archived compound.')
        child=record['scopes'][secondary]
        if typed.venue.state!='Unspecified' and typed.venue.value not in child['venues'] or typed.companions.state!='Unspecified' and typed.companions.value not in child['companions']:raise ValueError('Archived secondary scope mismatch.')
        expected.append(child['binding'])
    if plan['bindings']!=expected or len(expected)>2:raise ValueError('Compound binding proof mismatch.')
    objective=data['objective']
    if objective is not None and (objective['situation']!=sid or objective['authority']=='prototype_convention' and (payload['style'] is not None or payload['formality'] is not None)):raise ValueError('Objective/request mismatch.')
