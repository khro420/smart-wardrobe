"""Synthetic-source v1 selection. No production evidence policy is extended.

The reference and compact engines provide unchanged P1/C1 scores. Independent
verification enumerates a separate structural stream and uses truth bounds,
not the first pass's admission, cache, ranking or optional decisions.
"""
from dataclasses import dataclass, asdict
from fractions import Fraction as F
from types import SimpleNamespace
import hashlib, json

from app.application.nlp.compositional_request_v1 import CompositionalIntent, identity
from app.application.recommendation.attribute_evidence_policy import AttributeFact
from app.application.recommendation.attribute_condition_evaluator import predicate, conjunction
from app.application.recommendation.attribute_selection_verifier import _possibility
from app.application.recommendation.request_local_selection_engine import FrozenQuery, public_scorers, public_score
from app.application.recommendation.request_local_selection_verifier import IndependentStructural
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.decision_score_codec import score_to_json, score_from_json
from app.application.recommendation.request_local_bounded_ranking import PrimaryRecord, CompletedLedger, bounded_rank
from app.application.recommendation.request_local_preference_evidence import OptionalEvaluation
from app.application.recommendation.request_local_score_encoding import LocalScoreEncoding
from app.application.recommendation.attribute_preference_codec import restore_request
from app.domain.value_objects.attribute_conditions import ROLES
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot

VERSION = 'phase2nd-mixed-wardrobe-selection-1.0.0'
ORIGIN = 'synthetic_fixture_declaration'
GRAMMAR_SHA = 'f281fd86497f991fb58b1f36a99a72a43e93ad824d4718dcff4ac880bd153543'

class UnsupportedFixtureRequest(ValueError):pass

def encoded(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def digest(v):
    return hashlib.sha256(encoded(v)).hexdigest()

@dataclass(frozen=True)
class FixtureRow:
    snapshot: ConfirmedGarmentSnapshot
    declaration: dict

@dataclass(frozen=True)
class OriginalRow:
    snapshot: ConfirmedGarmentSnapshot
    description: object
    declaration: dict
    policy: object


def rows_from_catalog(catalog, gender):
    from app.development.main_fixture.core import rows_from_catalog as fixture_rows
    from app.application.recommendation.request_local_selection_verifier import restore_sources
    from app.application.recommendation.request_local_soft_workflow import resource_identities
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    if catalog['version']!='mixed-wardrobe-scope-1.0.0' or encoded(catalog['resources'])!=encoded(resource_identities()):raise ValueError('Unregistered mixed scoring resources.')
    if set(catalog)!={'version','fixture','original','available_ids','attribute_policy','resources'}:raise ValueError('Unknown mixed scope fields.')
    fixture=catalog['fixture'];original=catalog['original'];owner=fixture['owner_id']
    if set(original)!={'owner_id','wearer','source_table','eligibility','preferences'}:raise ValueError('Unknown original scope fields.')
    if original['owner_id']!=owner or original['wearer']['profile_id'] not in fixture['profiles']:raise ValueError('Foreign mixed scope.')
    from app.domain.value_objects.request_local_source_codec import unpack_sources
    original={**original,'sources':unpack_sources(original['source_table']) if original['source_table'] is not None else []}
    if not original['sources']:
        from app.domain.value_objects.wearer_category_eligibility import validate_evidence
        validate_evidence(original['eligibility'],owner,original['wearer']['profile_id'])
        if original['eligibility']['account_count']!=0 or original['eligibility']['usable_ids']:raise ValueError('Missing original sources.')
        originals=()
    else:originals=restore_sources(original)
    policy=AttributeEvidencePolicy(encoded(catalog['attribute_policy']))
    rows=list(fixture_rows(fixture,gender))
    for item in originals:
        g=item.snapshot
        attrs={'category':g.category,'primary_colour':g.primary_colour,'pattern':g.pattern,'material':g.material,'silhouette':g.fit,'style':g.style_tags}
        rows.append(OriginalRow(g,item.description.to_dict(),json.loads(encoded(attrs)),policy))
    ids=[r.snapshot.garment_id for r in rows]
    if len(ids)!=len(set(ids)) or len(catalog['available_ids'])>100:raise ValueError('Duplicate/unbounded mixed scope.')
    expected={s['snapshot']['garment_id'] for s in original['sources']}|{e['row']['id'] for e in fixture['garments']}
    if not expected<=set(catalog['available_ids']):raise ValueError('Incomplete available account scope.')
    return tuple(rows)


def preferences_from_catalog(catalog,wearer):
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    owner=catalog['fixture']['owner_id']
    captured=tuple(PreferenceSnapshot(**p) for p in catalog['original']['preferences'])
    pinned=tuple(PreferenceSnapshot(p['id'],owner,p['preference_type'],p['preference_value_json'],None if p['weight'] is None else str(p['weight']),p['source'],bool(p['is_active'])) for p in catalog['fixture']['profiles'][wearer].get('preferences',[]))
    if sorted(encoded(asdict(p)) for p in captured)!=sorted(encoded(asdict(p)) for p in pinned):raise ValueError('Mixed preference representations disagree.')
    return captured


def fact(row,field,revision,operator='in'):
    if isinstance(row,OriginalRow):
        if field=='verified_subtype':return AttributeFact('Unqualified')
        return row.policy.fact(row.snapshot,row.description,field,operator,row.policy.primary_classifier())
    from app.development.main_fixture.core import fact as fixture_fact
    return fixture_fact(row,field,revision)

def first_hard(key, groups, rows, revision):
    states=[]
    for group in groups:
        members=[]
        for role,gid in key:
            if role not in ROLES[group['role']]: continue
            facts=[fact(rows[gid],c['attribute'],revision,c['operator']) for c in group['conditions']]
            if any(f.applicability=='inapplicable' for f in facts): continue
            members.append(conjunction(tuple(predicate(f,c['attribute'],c['operator'],c['values']).state for f,c in zip(facts,group['conditions']))))
        q=group['quantifier']
        states.append(('Pass' if 'Pass' in members else 'Unknown' if 'Unknown' in members else 'Fail') if q=='exists' else
                      ('Fail' if 'Pass' in members else 'Unknown' if 'Unknown' in members else 'Pass') if q=='none' else
                      conjunction(members) if members else 'Fail')
    return conjunction(states)

def independent_hard(key, groups, rows, revision):
    # Independent interval/quantifier reconstruction; no first-pass verdicts.
    bounds=[]
    for group in groups:
        members=[]
        for role,gid in key:
            if role not in ROLES[group['role']]: continue
            fs=[fact(rows[gid],c['attribute'],revision,c['operator']) for c in group['conditions']]
            if any(f.applicability=='inapplicable' for f in fs): continue
            ps=[_possibility(f,c['attribute'],c['operator'],c['values']) for f,c in zip(fs,group['conditions'])]
            members.append((all(p=={True} for p in ps),all(True in p for p in ps)))
        if group['quantifier']=='exists': bounds.append((any(x[0] for x in members),any(x[1] for x in members)))
        elif group['quantifier']=='none': bounds.append((not any(x[1] for x in members),not any(x[0] for x in members)))
        else: bounds.append((bool(members) and all(x[0] for x in members),bool(members) and all(x[1] for x in members)))
    return 'Pass' if all(x[0] for x in bounds) else 'Fail' if not all(x[1] for x in bounds) else 'Unknown'

def optional_value(key, optional, rows, scope, independent):
    lower=[];upper=[];ledger=[]
    for role,gid in key:
        if role!=optional['role']: continue
        ls=[];us=[]
        for c in optional['predicates']:
            f=fact(rows[gid],c['attribute'],scope,c['operator'])
            if independent:
                p=_possibility(f,c['attribute'],c['operator'],c['values']);l=p=={True};u=True in p
            else:
                s=predicate(f,c['attribute'],c['operator'],c['values']).state;l=s=='Pass';u=s!='Fail'
            ls.append(l);us.append(u)
            ledger.append(encoded({'garment_id':gid,'role':role,'predicate':c,'state':'Pass' if l else 'Fail' if not u else 'Unknown','fact_state':f.state,'source':f.source,'values':f.values}))
        lower.append(all(ls));upper.append(all(us))
    l=any(lower);u=any(upper)
    return OptionalEvaluation(key,scope,'Satisfied' if l else 'Unsatisfied' if not u else 'Unverifiable',int(l),F(l),F(u),tuple(ledger))

def select(catalog, raw, wearer_id, engine='reference', *, independent=False, seen=(), floor='0', _fashion=None, _personalization=None, _interpret=None):
    if identity()!=GRAMMAR_SHA: raise ValueError('Unregistered fixture grammar.')
    data=CompositionalIntent.capture(raw).to_dict() if _interpret is None else _interpret(raw)
    if 'context' in data['request']: raise UnsupportedFixtureRequest('Contextual fixture requests are not supported.')
    if wearer_id not in catalog['fixture']['profiles']: raise ValueError('Foreign fixture wearer.')
    rows=rows_from_catalog(catalog,catalog['fixture']['profiles'][wearer_id]['gender']);by_id={r.snapshot.garment_id:r for r in rows}
    request=restore_request(data['request']);owner=catalog['fixture']['owner_id'];scope=digest(catalog)
    read_preferences=preferences_from_catalog
    if _personalization is not None:
        from .personalization import preferences as read_preferences,validate,choose
        validate(_personalization,owner,wearer_id)
    fashion=_fashion(rows,request,scope,independent) if _fashion else None
    groups=data['hard_intent']['conditions']['groups'] if data['hard_intent'] else []
    supported={'category','primary_colour','secondary_colour','material','pattern','sleeve_length','silhouette','style'}
    if any(c['attribute'] not in supported for g in groups for c in g['conditions']) or data['optional'] and any(c['attribute'] not in supported for c in data['optional']['predicates']):raise UnsupportedFixtureRequest('Unsupported mixed attribute.')
    scores={};candidates={};failed=unknown=seen_count=0;precomputed={}
    if independent:
        stream=RequestCandidateSession(IndependentStructural(rows),request,RequestConstraintEvaluator())
    else:
        query=FrozenQuery(owner,[r.snapshot for r in rows])
        if engine=='compact_exhaustive':
            from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
            from app.infrastructure.persistence.recommendation_repository_adapter import encode as score_encode
            audit=[];outcome=CompactExhaustiveScorer(query,SimpleNamespace(get_active_preferences=lambda who:read_preferences(catalog,wearer_id)),audit=audit.append).rank(owner,request)
            if not outcome.complete: raise ValueError('Incomplete compact fixture enumeration.')
            for r in audit:
                if r['verified']: precomputed[tuple(tuple(k) for k in r['key'])]=score_from_json(score_encode(r['score']))
        elif engine!='reference': raise ValueError('Unsupported fixture engine.')
        stream=RequestCandidateEngine(query).generate_candidates(owner,request)
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    preferences=read_preferences(catalog,wearer_id)
    scorers=public_scorers(owner,preferences);gate=ScoringEligibilityGate(stream,owner,request)
    try:
        for item in stream:
            v=gate.verify(item);key=v.candidate.key
            state=(independent_hard if independent else first_hard)(key,groups,by_id,scope)
            if state=='Fail': failed+=1;continue
            if state=='Unknown': unknown+=1;continue
            score=precomputed[key] if precomputed else public_score(v,scorers)
            if fashion is not None:score=fashion.apply(key,score)
            base=tuple(x for x in key if x[0]!='outerwear')
            if base in seen or score.request_match.contribution<F(floor): seen_count+=1;continue
            scores[key]=score;candidates[key]=v.candidate
        result=stream.result
        completed=CompletedLedger(result.examined,len(scores),result.failed+failed+seen_count,result.unknown+unknown,result.complete)
    finally: stream.close()
    counts=asdict(completed)
    if not scores:
        return {'status':'InsufficientEvidence' if counts['unknown'] else 'RefinementExhausted' if seen else 'NoMatchingCandidates','mandatory':counts,'intent':data}
    order=lambda k:(-scores[k].total,-scores[k].request_match.contribution,-scores[k].compatibility.contribution,-scores[k].preference.contribution,k)
    baseline=min(scores,key=order);selected=baseline;optional=data['optional'];optionals={};eligible=[]
    if optional:
        if seen: raise ValueError('Soft continuation is unsupported.')
        optionals={k:optional_value(k,optional,by_id,scope,independent) for k in scores}
        if independent:
            b=scores[baseline]
            for k,s in scores.items():
                if optional['resolution']['state']=='Active' and optionals[k].support and s.total+F(1,50)>=b.total and s.compatibility.contribution+F(1,10)>=b.compatibility.contribution and s.preference.contribution+F(1,10)>=b.preference.contribution and s.request_match.contribution>=b.request_match.contribution: eligible.append(k)
            if eligible: selected=min(eligible,key=order)
        else:
            encoding=LocalScoreEncoding()
            points=tuple(PrimaryRecord(k,s.request_match.contribution,s.compatibility.contribution,s.preference.contribution,s.total,scope,encoding.encode(s).encode()) for k,s in scores.items())
            decision=bounded_rank(lambda:iter(points),completed,lambda key:optionals[key],resolution=optional['resolution']['state'])
            selected=decision.selected.key;eligible=[x.primary.key for x in decision.optional_ledger if not x.reasons]
    personal_display=None
    if _personalization is not None:selected,personal_display=choose(_personalization,scores,selected,optional,seen)
    all_scores=[{'key':k,'score':json.loads(score_to_json(scores[k]))} for k in sorted(scores)]
    def entry(k): return {'key':[list(x) for x in k],'score':json.loads(score_to_json(scores[k]))}
    opt=optionals.get(selected)
    return {**({'personalization':personal_display} if personal_display is not None else {}),**({'fashion':fashion.describe(selected)} if fashion is not None else {}),'status':'Selected','intent':data,'mandatory':counts,'candidate_scores_sha256':digest(all_scores),
        'baseline':entry(baseline),'selected':entry(selected),'eligible_promotion_count':len(eligible),
        'optional':None if opt is None else {'state':opt.state,'resolution':optional['resolution'],'ledger':[json.loads(x) for x in opt.ledger],
            'counts':{s:sum(v.state==s for v in optionals.values()) for s in ('Satisfied','Unsatisfied','Unverifiable')}},
        'explanation':'exact_score_tie_diversity' if personal_display and personal_display['applied'] else 'qualified_bounded_promotion' if selected!=baseline else 'original_baseline_retained',
        'items':[{'role':role,'garment_id':gid,'name':by_id[gid].snapshot.name,'media_id':by_id[gid].snapshot.preferred_media_id,'attributes':by_id[gid].declaration,'source':'normal_B0_B1' if isinstance(by_id[gid],OriginalRow) else ORIGIN} for role,gid in selected]}
