"""New clause intent, unchanged mandatory facts, P1/C1 and bounded promotion.

First selection and independent reconstruction enumerate separate streams and
derive optional support through separate existing fact evaluators.
"""
from dataclasses import asdict
from fractions import Fraction as F
from types import SimpleNamespace
import hashlib,json
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
from app.domain.value_objects.attribute_conditions import encode,digest
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions,predicate,conjunction
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.request_local_selection_engine import public_scorers,public_score,FrozenQuery,LocalSelectionUnavailable,decision_document
from app.application.recommendation.request_local_bounded_ranking import PrimaryRecord,CompletedLedger,BoundedDecision,PromotionComparison,bounded_rank
from app.application.recommendation.request_local_preference_evidence import OptionalEvaluation
from app.application.recommendation.request_local_selection_verifier import IndependentStructural,_IndependentOptionalFacts,independent_optional
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.request_candidate_session import RequestCandidateSession
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.request_local_score_encoding import LocalScoreEncoding
from app.application.recommendation.decision_score_codec import score_to_json,score_from_json

def optional_first(candidate,intent,by_id,policy,scope):
    optional=intent.to_dict()['optional'];states=[];ledger=[]
    for member in candidate.members:
        if member.role!=optional['role']:continue
        row=by_id[member.garment.garment_id]
        if row.snapshot!=member.garment:raise ValueError('Foreign compositional optional member.')
        doc=row.description.to_dict();primitives=[]
        for p in optional['predicates']:
            record=doc['fields'][p['attribute']];fact=policy.fact(member.garment,doc,p['attribute'],'in',policy.primary_classifier())
            verdict=predicate(fact,p['attribute'],'in',p['values'])
            unresolved=record['state'] in ('Stale','Conflicting','Malformed','Unsure')
            state='Unknown' if unresolved else verdict.state;primitives.append(state)
            ledger.append(encode({'garment_id':member.garment.garment_id,'role':member.role,'predicate':p,'verdict':state,'fact_state':fact.state,'source':fact.source,'fact_values':list(fact.values),'record_state':record['state'],'reason':'unresolved_B0_record' if unresolved else verdict.reason}))
        states.append(conjunction(tuple(primitives)))
    value='Pass' if 'Pass' in states else 'Unknown' if 'Unknown' in states else 'Fail'
    if not states:ledger.append(encode({'reason':'preferred_role_absent','role':optional['role']}))
    return OptionalEvaluation(candidate.key,scope,{'Pass':'Satisfied','Unknown':'Unverifiable','Fail':'Unsatisfied'}[value],int(value=='Pass'),F(int(value=='Pass')),F(int(value!='Fail')),tuple(ledger))

def select(owner,intent,rows,preferences,engine,*,wearer_scope,independent=False,policy=None):
    if type(wearer_scope) is not str or not wearer_scope:raise ValueError('Explicit compositional wearer scope required.')
    data=intent.to_dict();request=StructuredOutfitRequest(**data['request']);policy=policy if policy is not None else AttributeEvidencePolicy.load()
    hard=AttributeIntent.from_dict(data['hard_intent']) if data['hard_intent'] else None
    facts=IndependentAttributeVerifier.prepare(hard.conditions,rows,policy) if hard else None
    scorers=public_scorers(owner,preferences);scores={};candidates={};failed=unknown=0
    if independent:
        stream=RequestCandidateSession(IndependentStructural(rows),request,RequestConstraintEvaluator())
    else:
        prepared=PreparedAttributeConditions.prepare(hard.conditions,rows,policy) if hard else None
        query=FrozenQuery(owner,[r.snapshot for r in rows])
        if engine=='compact_exhaustive':
            from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
            from app.infrastructure.persistence.recommendation_repository_adapter import encode as old_encode
            audit=[];result=CompactExhaustiveScorer(query,SimpleNamespace(get_active_preferences=lambda who:preferences),attribute_context=prepared,attribute_verifier=facts,audit=audit.append).rank(owner,request)
            if not result.complete:raise ValueError('Incomplete compositional compact scope.')
            scores={tuple(tuple(k) for k in r['key']):score_from_json(old_encode(r['score'])) for r in audit if r['verified']}
        elif engine!='reference':raise ValueError('Unsupported compositional engine.')
        stream=RequestCandidateEngine(query,attribute_context=prepared,attribute_verifier=facts).generate_candidates(owner,request)
    try:
        gate=ScoringEligibilityGate(stream,owner,request)
        for item in stream:
            if independent:
                state=facts.decision(item.candidate.key) if facts else 'Pass'
                if state=='Fail':failed+=1;continue
                if state=='Unknown':unknown+=1;continue
            v=gate.verify(item);candidates[v.candidate.key]=v.candidate
            if independent or engine=='reference':scores[v.candidate.key]=public_score(v,scorers)
        r=stream.result
        completion=CompletedLedger(r.examined,len(candidates),r.failed+failed,r.unknown+unknown,r.complete)
    finally:stream.close()
    if set(scores)!=set(candidates):raise ValueError('Compositional compact/admission set mismatch.')
    if not candidates:raise LocalSelectionUnavailable(completion)
    if not data['optional']:
        key=min(scores,key=lambda k:(-scores[k].total,-scores[k].request_match.contribution,-scores[k].compatibility.contribution,-scores[k].preference.contribution,k))
        score=scores[key]
        return candidates[key],score,{'selected_key':[list(k) for k in key],'score':json.loads(score_to_json(score)),'mandatory':asdict(completion)}
    scope=digest({'version':'compositional-optional-scope-1.0.0','owner':owner,'wearer_scope':wearer_scope,'intent':intent.revision,'sources':[{'snapshot':asdict(r.snapshot),'description':r.description.to_dict()} for r in sorted(rows,key=lambda r:r.snapshot.garment_id)],'policy':policy.sha256})
    encoding=LocalScoreEncoding();points=tuple(PrimaryRecord(k,s.request_match.contribution,s.compatibility.contribution,s.preference.contribution,s.total,scope,encoding.encode(s).encode()) for k,s in scores.items())
    by_id={r.snapshot.garment_id:r for r in rows};resolution=data['optional']['resolution']['state']
    if not independent:
        decision=bounded_rank(lambda:iter(points),completion,lambda key:optional_first(candidates[key],intent,by_id,policy,scope),resolution=resolution)
    else:
        # Original independent policy reconstruction, with the unchanged exact
        # budgets; it never uses the first-pass selector, ledgers or verdicts.
        baseline=min(points,key=lambda p:p.original_key);eligible=[];comparisons=[]
        optional_facts=_IndependentOptionalFacts(intent,by_id,policy,scope)
        for point in points:
            optional=independent_optional(candidates[point.key],intent,by_id,policy,scope,prepared=optional_facts);reasons=[]
            if resolution!='Active':reasons.append('inactive_optional_intent')
            elif not optional.support:reasons.append('no_qualified_match')
            if point.t+F(1,50)<baseline.t:reasons.append('T_loss_above_budget')
            if point.c+F(1,10)<baseline.c:reasons.append('C_loss_above_budget')
            if point.p+F(1,10)<baseline.p:reasons.append('P_loss_above_budget')
            if point.r<baseline.r:reasons.append('R_would_decrease')
            if not reasons:eligible.append(point)
            comparisons.append(PromotionComparison(point,optional,tuple(reasons)))
        selected=min(eligible,key=lambda p:p.original_key) if eligible else baseline
        decision=BoundedDecision(baseline,selected,completion,tuple(sorted(comparisons,key=lambda p:p.primary.key)),hashlib.sha256(b''.join(sorted(p.identity() for p in points))).hexdigest())
    return candidates[decision.selected.key],scores[decision.selected.key],decision_document(decision)
