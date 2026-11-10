"""Versioned read-only API projection of stored evidence, never historical rescoring."""
from dataclasses import dataclass,asdict
import json
from typing import Literal
from app.application.recommendation.decision_score_codec import score_from_json
from app.application.recommendation.assistant_scoring_selection import DEFERRED,DECISION


@dataclass(frozen=True)
class ExactRatio:
    numerator: int
    denominator: int

    @classmethod
    def of(cls,value):
        return None if value is None else cls(value.numerator,value.denominator)


@dataclass(frozen=True)
class ScoringDisplay:
    kind: Literal["Decision","Deferred","Unavailable"]
    profile_name: str | None = None
    policy_version: str | None = None
    policy_hash: str | None = None
    raw_state: str | None = None
    basis: Literal["Computed","PartiallyConventional","FullyConventional","NoPairReference"] | None = None
    raw_value: ExactRatio | None = None
    decision_contribution: ExactRatio | None = None
    lower: ExactRatio | None = None
    upper: ExactRatio | None = None
    known: int | None = None
    possible: int | None = None
    pair_count: int | None = None
    structure: str | None = None
    weights: tuple[ExactRatio,...] | None = None
    reason: str | None = None
    version: str = "assistant-scoring-display-1.0.0"


def display_for_record(record):
    metadata=record.get("score_metadata")
    metadata=metadata if isinstance(metadata,dict) else {}
    provenance=record.get("provenance")
    provenance=provenance if isinstance(provenance,dict) else {}
    profile=metadata.get("profile_name") or provenance.get("scoring_profile")
    if (metadata.get("profile_name") and provenance.get("scoring_profile")
            and metadata["profile_name"] != provenance["scoring_profile"]):
        return ScoringDisplay("Unavailable",reason="StoredScoringIdentityMismatch")
    if profile == DECISION:
        try:
            score=score_from_json(json.dumps(metadata,allow_nan=False))
            c=score.compatibility;d=c.decision
            # Scalars are display-only but must not contradict authoritative metadata.
            raw=record.get("compatibility_score")
            if (raw is None)!=(c.summary.value is None) or (raw is not None and raw!=float(c.summary.value)):
                raise ValueError("Stored raw scalar contradicts exact metadata.")
            return ScoringDisplay("Decision",profile,score.policy_version,d.policy_hash,c.summary.state,d.basis,
                ExactRatio.of(c.summary.value),ExactRatio.of(d.value),ExactRatio.of(d.lower),ExactRatio.of(d.upper),
                d.known_count,d.atomic_count,d.pair_count,d.structure,tuple(ExactRatio.of(w) for w in score.weights))
        except (ValueError,TypeError,KeyError,AttributeError,ZeroDivisionError):
            return ScoringDisplay("Unavailable",profile_name=profile,reason="StoredDecisionMetadataUnavailable")
    if profile == DEFERRED:
        if record.get("compatibility_score") is not None:
            return ScoringDisplay("Unavailable",profile_name=profile,reason="StoredDeferredMetadataInconsistent")
        return ScoringDisplay("Deferred",profile_name=profile,raw_state="Unavailable")
    return ScoringDisplay("Unavailable",reason="LegacyOrUnsupportedScoringMetadata")


def with_scoring_display(record):
    display=asdict(display_for_record(record))
    provenance=record.get('provenance')
    if isinstance(provenance,dict) and 'context_relevance' in provenance and 'attribute_preference' not in provenance and 'palette_compatibility' not in provenance:
        try:
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            from app.domain.value_objects.context_relevance import ratio
            score=score_from_json(json.dumps(record['score_metadata']))
            proof=validate_evidence(provenance['context_relevance'],score)
            display=dict(version='assistant-scoring-display-2.0.0',kind='ContextRelevance',profile_name=score.profile_name,
                policy_version=score.policy_version,selection_mode=proof['selection_mode'],fallback_reason=proof['fallback_reason'],
                objective=proof['objective'],coverage=proof['coverage'],numeric_ties=proof['numeric_ties'],
                selected_members=proof['selected_members'],preferences=proof['preferences'],preference_denominator=proof['preference_denominator'],
                components=[dict(name=name,state=component.summary.state,raw_value=ratio(component.summary.value),
                    contribution=ratio(component.contribution),weight=ratio(weight),weighted=ratio(weight*component.contribution),
                    reasons=list(component.summary.reasons)) for name,component,weight in zip(('R','C','P'),(score.request_match,score.compatibility,score.preference),score.weights)],
                compatibility_basis=score.compatibility.decision.basis,total=ratio(score.total))
            if proof['version'] in ('context-relevance-evidence-1.1.0','context-relevance-evidence-1.2.0','context-relevance-evidence-1.3.0'):
                display.update(version='assistant-scoring-display-2.1.0',bundle_id=proof['bundle_id'],context_plan=proof['context_plan'])
            if proof['version']=='context-relevance-evidence-1.2.0' or proof['version']=='context-relevance-evidence-1.3.0' and 'refinement' in provenance:
                from app.application.recommendation.refinement_verifier import validate_refinement
                from app.domain.value_objects.recommendation_refinement import step_key,REQUEST_VERSION
                refinement=provenance['refinement']
                validate_refinement(refinement,proof,score,record['id'],record['request_text'],proof['context_plan']['request'],user_id=record.get('user_id'),wearer_profile_id=record.get('profile_id'))
                ordinal=refinement['ordinal']
                display.update(version='assistant-scoring-display-2.2.0',refinement={
                    **{key:refinement[key] for key in ('root_id','parent_id','ordinal','excluded_categories','root_R','root_total','mode','total_vs_root')},
                    'version':'recommendation-refinement-lineage-1.0.0',
                    'next_action':dict(submission_key=step_key(refinement['root_id'],ordinal+1),
                        refinement=dict(version=REQUEST_VERSION,kind='alternative',parent_recommendation_id=record['id'])) if ordinal<9 else None,
                    'limit_reached':ordinal==9,
                    'certificate_universe':'remaining_permitted_pool' if ordinal else 'initial_permitted_pool'})
        except (ValueError,TypeError,KeyError,AttributeError):
            display=dict(version='assistant-scoring-display-2.0.0',kind='Unavailable',reason='StoredRelativeMetadataUnavailable')
    result={**record,'scoring_display':display}
    if isinstance(provenance,dict) and 'attribute_selection' in provenance:
        from app.application.recommendation.attribute_selection_verifier import validate_selection
        from app.domain.value_objects.attribute_conditions import ROLES
        evidence=validate_selection(provenance['attribute_selection'],record['user_id'],record['profile_id'],provenance['attribute_base_scope_sha256'],record.get('items')).to_dict()
        intent=evidence['intent'];groups=[]
        roles={m['garment_id']:m['role'] for m in evidence['selected_evidence']}
        for group in intent['conditions']['groups']:
            ids={c['id'] for c in group['conditions']}
            observations=[r for r in evidence['decisions']['member_results'] if r['condition_id'] in ids and roles[r['garment_id']] in ROLES[group['role']]]
            conditions=[]
            for c in group['conditions']:
                states=[r['state'] for r in observations if r['condition_id']==c['id']]
                state='Pass' if 'Pass' in states else 'Unknown' if 'Unknown' in states else 'Fail'
                conditions.append({**c,'state':state,'reason_codes':list(dict.fromkeys(r['reason'] for r in observations if r['condition_id']==c['id'])),
                    'spans':[s for s in intent['spans'] if s['condition_id']==c['id']]})
            members=[{'garment_id':r['garment_id'],'role':roles[r['garment_id']],'condition_id':r['condition_id'],
                'state':r['state'],'source_kind':r['source_kind'],'source_revision':r['source_revision'],'reason_codes':[r['reason']]} for r in observations]
            groups.append({'id':group['id'],'role':group['role'],'quantifier':group['quantifier'],'state':'Pass','conditions':conditions,'member_results':members})
        result['attribute_display']={'version':'assistant-attribute-display-1.0.0','intent_sha256':intent['intent_sha256'],
            'wearer_profile_id':evidence['wearer_profile_id'],'groups':groups,'outcome':'Selected',
            'source_limitations':['Matches use recorded descriptions and dated observations. Unqualified model suggestions do not prove these requirements.']}
    if isinstance(provenance,dict) and 'attribute_preference' in provenance and 'palette_compatibility' not in provenance:
        result['scoring_display']=preference_display(record)
    if isinstance(provenance,dict) and 'palette_compatibility' in provenance:
        from app.application.recommendation.palette_compatibility_codec import display as palette_display
        result['scoring_display']=palette_display(record)
    if isinstance(provenance,dict) and 'garment_wording' in provenance:
        from app.application.nlp.garment_wording_guidance import validate as validate_wording
        from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
        result['garment_wording']=validate_wording(provenance['garment_wording'],record['request_text'],AttributeIntent.from_dict(provenance['attribute_selection']['intent']))
    if isinstance(provenance,dict) and 'garment_refinement' in provenance:
        from app.application.recommendation.garment_only_refinement_verifier import descriptor
        result['garment_continuation']=descriptor(record)
    return result


def preference_display(record):
    """Use captured inputs for explanation; current preferences grant no history authority."""
    try:
        from app.application.recommendation.attribute_preference_verifier import validate,conditions_from
        from app.domain.value_objects.attribute_preferences import PROFILE,digest
        from app.domain.value_objects.context_relevance import ratio
        source=record['provenance'];saved=source['attribute_preference'];refinement=source.get('refinement')
        score=score_from_json(json.dumps(record['score_metadata']))
        validate(saved,score,record['user_id'],record['profile_id'],conditions=conditions_from(source),items=record.get('items'),
            request_text=record.get('request_text'),exclusions=refinement['excluded_categories'] if refinement else source.get('garment_refinement',{}).get('excluded_categories',()))
        result=dict(version='assistant-scoring-display-3.0.0',kind='AttributePreference',profile_name=PROFILE,policy_version=score.policy_version,
            preference_ledger=saved['ledger'],preference_snapshot_revision=saved['snapshot']['revision'],
            components=[dict(name=name,state=component.summary.state,raw_value=ratio(component.summary.value),contribution=ratio(component.contribution),
                weight=ratio(weight),weighted=ratio(weight*component.contribution),reasons=list(component.summary.reasons))
                for name,component,weight in zip(('R','C','P'),(score.request_match,score.compatibility,score.preference),score.weights)],
            compatibility_basis=score.compatibility.decision.basis,total=ratio(score.total))
        relative=source.get('context_relevance')
        if relative is not None:
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            validate_evidence(relative,score)
            if relative['preference_snapshot_sha256']!=saved['snapshot']['revision'] or relative['preference_ledger_sha256']!=digest(saved['ledger']):raise ValueError('P2 proof/ledger mismatch.')
            result.update({k:relative[k] for k in ('selection_mode','fallback_reason','objective','coverage','numeric_ties','selected_members')})
            if 'bundle_id' in relative:result.update(bundle_id=relative['bundle_id'],context_plan=relative['context_plan'])
        if refinement is not None:
            from app.application.recommendation.refinement_verifier import validate_refinement
            from app.domain.value_objects.recommendation_refinement import step_key,REQUEST_VERSION
            validate_refinement(refinement,relative,score,record['id'],record['request_text'],saved['ledger']['request'],user_id=record['user_id'],wearer_profile_id=record['profile_id'])
            ordinal=refinement['ordinal']
            result['refinement']={**{k:refinement[k] for k in ('root_id','parent_id','ordinal','excluded_categories','root_R','root_total','mode','total_vs_root')},
                'version':'recommendation-refinement-lineage-1.0.0','next_action':dict(submission_key=step_key(refinement['root_id'],ordinal+1),
                    refinement=dict(version=REQUEST_VERSION,kind='alternative',parent_recommendation_id=record['id']),preference_profile=PROFILE) if ordinal<9 else None,
                'limit_reached':ordinal==9,'certificate_universe':'remaining_permitted_pool' if ordinal else 'initial_permitted_pool'}
        return result
    except (ValueError,TypeError,KeyError,AttributeError):
        return dict(version='assistant-scoring-display-3.0.0',kind='Unavailable',reason='StoredPreferenceMetadataUnavailable')
