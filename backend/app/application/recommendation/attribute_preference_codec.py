"""Versioned P2 archives, independent of active normalization/config loaders."""
from dataclasses import asdict
from fractions import Fraction as F
from types import MappingProxyType
import json,re
from app.domain.value_objects.attribute_preferences import AttributePreferenceSnapshot,PreferenceError,encode,decode,digest,exact,POLICY_HASH
from app.domain.value_objects.attribute_preference_evidence import ratio,read_ratio
from app.domain.value_objects.preference_snapshot import NormalizedPreference,NormalizedPreferenceSet
from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint,StructuredOutfitRequest
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence
from app.application.recommendation.attribute_preference_policy import AttributePreferencePolicy


def vocabulary(policy):
    from app.application.nlp.vocabulary import Vocabulary
    raw=policy.snapshot()['archive_bridge']['vocabulary'];entries=[];values={}
    for field,items in raw['fields'].items():
        values[field]=frozenset((v['kind'],v['value']) if field=='garment_categories' else v['value'] for v in items)
        entries.extend((field,v['value'],phrase,v.get('kind')) for v in items for phrase in v['aliases'])
    return Vocabulary(raw['version'],tuple(entries),MappingProxyType(values),MappingProxyType({k:tuple(v) for k,v in raw['category_groups'].items()}))


def freeze_normalized(value):
    return {'user_id':value.user_id,'preferences':[{'preference_id':p.preference_id,'preference_type':p.preference_type,
        'values':[asdict(v) if isinstance(v,GarmentCategoryConstraint) else v for v in p.values],'importance':ratio(p.importance)} for p in value.preferences],
        'diagnostics':[list(v) for v in value.diagnostics]}


def archived_normalize(user,rows,policy):
    """Pinned P1 interpretation bridge, checked against original at capture time.

    This only reconstructs P2's inherited inputs; the actual P1 normalizer and
    its score/history paths remain unchanged. No current loader is invoked.
    """
    from app.application.recommendation.preference_normalizer import precise_weight,InvalidPreferenceData
    vocab=vocabulary(policy);aliases={}
    for field in ('colours','style','formality'):
        aliases[field]={v:v for v in vocab.values[field]}
        aliases[field].update({phrase:v for f,v,phrase,_ in vocab.entries if f==field})
    def canonical(field,value):return aliases[field].get(re.sub(r'\s+',' ',value.strip().casefold())) if type(value) is str else None
    enabled=policy.snapshot()['archive_bridge']['suitability']['enabled_formality']
    prefs=[];diagnostics=[];seen=set()
    for row in rows:
        if row.user_id!=user:raise InvalidPreferenceData('Archived preference ownership mismatch.')
        if not row.is_active:diagnostics.append((row.preference_id,'inactive'));continue
        kind=row.preference_type
        if kind not in ('colours','styles','garment_categories','formality','style_note'):diagnostics.append((row.preference_id,'unsupported_type'));continue
        importance=F(1) if row.weight is None else precise_weight(row.weight)
        if not importance:diagnostics.append((row.preference_id,'zero_weight'));continue
        if kind in seen:raise InvalidPreferenceData('Duplicate positive-weight archived preference type.')
        seen.add(kind)
        raw=json.loads(row.value_json,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite legacy JSON')))
        if type(raw) is not dict:raise InvalidPreferenceData('Invalid archived preference value.')
        normalized_kind=kind
        if kind=='style_note':
            value=canonical('style',raw.get('value')) if set(raw)=={'value'} else None
            if value is None:diagnostics.append((row.preference_id,'unsupported_style_note'));continue
            values=(value,);normalized_kind='styles'
        else:
            if set(raw)!={'values'} or type(raw['values']) is not list or not raw['values']:raise InvalidPreferenceData('Invalid archived preference values.')
            if kind=='garment_categories':
                values=[]
                for value in raw['values']:
                    exact(value,('kind','value'));constraint=GarmentCategoryConstraint(**value)
                    if (constraint.kind,constraint.value) not in vocab.values[kind]:raise InvalidPreferenceData('Unsupported archived category.')
                    values.append(constraint)
            else:
                values=tuple(canonical('style' if kind=='styles' else kind,v) for v in raw['values'])
                if any(v is None for v in values):raise InvalidPreferenceData('Unsupported archived preference value.')
                if kind=='formality' and any(v not in enabled for v in values):diagnostics.append((row.preference_id,'unavailable_formality_capability'));continue
        prefs.append((kind,NormalizedPreference(row.preference_id,normalized_kind,tuple(values),importance)))
    if any(kind=='styles' for kind,_ in prefs):
        diagnostics.extend((p.preference_id,'structured_styles_precedence') for kind,p in prefs if kind=='style_note')
        prefs=[(kind,p) for kind,p in prefs if kind!='style_note']
    return NormalizedPreferenceSet(user,tuple(sorted((p for _,p in prefs),key=lambda p:p.preference_type)),tuple(sorted(diagnostics)))


def build_archive_snapshot(snapshot,policy):
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    value=snapshot.to_dict();rows=snapshot.legacy_rows()
    current=PreferenceNormalizer().normalize(value['account_id'],rows)
    restored=archived_normalize(value['account_id'],rows,policy)
    if restored!=current:raise PreferenceError('PreferenceInvalid','Archived inheritance does not reproduce the accepted P1 input contract.')
    value['archive']={'policy_snapshot':policy.snapshot(),'normalized_legacy':freeze_normalized(current)}
    return AttributePreferenceSnapshot.from_dict(value)


def normalized_from_archive(snapshot):
    value=snapshot.to_dict();archive=value.get('archive')
    if archive is None:raise PreferenceError('PreferenceInvalid','Captured archive resources are missing.')
    policy=AttributePreferencePolicy.restore(archive['policy_snapshot'])
    normalized=archived_normalize(value['account_id'],snapshot.legacy_rows(),policy)
    if freeze_normalized(normalized)!=archive['normalized_legacy']:raise PreferenceError('PreferenceInvalid','Archived normalized inputs disagree with their immutable raw capture.')
    return normalized


def legacy_digest(snapshot):
    """Exact existing digest representation, including unchanged legacy raw JSON."""
    from app.domain.value_objects.recommendation_refinement import digest as legacy_hash
    v=snapshot.to_dict();normalized=normalized_from_archive(snapshot)
    return legacy_hash({'raw':v['legacy'],'normalized':freeze_normalized(normalized)})


def archived_scorer(snapshot):
    """Reuse original P1 fact and score methods with frozen constructor inputs."""
    from app.application.recommendation.preference_scorer import PreferenceScorer
    from app.application.recommendation.colour_classifier import ColourClassifier
    from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
    from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
    from app.application.recommendation.suitability_policy import SuitabilityPolicy
    from app.application.recommendation.exact_score_reuse import ExactScoreReuse
    policy=AttributePreferencePolicy.restore(snapshot.to_dict()['archive']['policy_snapshot']);bridge=policy.snapshot()['archive_bridge'];vocab=vocabulary(policy)
    classifier=object.__new__(ColourClassifier)
    classifier.aliases=MappingProxyType({phrase:value for f,value,phrase,_ in vocab.entries if f=='colours'})
    classifier.anchors=MappingProxyType(dict(bridge['colour_anchors']))
    raw=bridge['suitability'];suitability=SuitabilityPolicy(raw['version'],raw['reserved_prefix'],raw['enabled_occasions'],raw['enabled_formality'])
    scorer=object.__new__(PreferenceScorer)
    scorer.mapper=GarmentEvidenceMapper(vocabulary=vocab,classifier=classifier);scorer._reuse=ExactScoreReuse()
    scorer.suitability=SuitabilityEvidenceParser(suitability);scorer.vocabulary=vocab;scorer._prepared=None;scorer._facts={}
    scorer.fact_hits=scorer.fact_misses=0
    scorer._empty={state:ComponentScore(ScoreEvidence('preference',None,state)) for state in ('NoPreferences','NoSupportedPreferences')}
    return scorer


def archived_legacy_component(prepared,members):
    """Independent historical aggregation over original P1 fact primitives.

    A historical read does not fabricate a new eligibility-gate seal or grant
    action permission. Current ranking still invokes the original P1 scorer.
    """
    scorer=prepared.old_scorer;prefs=prepared.composed.legacy
    if not prefs.preferences:return ComponentScore(ScoreEvidence('preference',None,'NoSupportedPreferences' if prefs.diagnostics else 'NoPreferences'))
    matches,denominator=scorer._prepare(prefs);details=[]
    for index,(p,values) in enumerate(zip(prefs.preferences,matches)):
        kind=p.preference_type
        selected=[prepared.by_id[gid].snapshot for role,gid in members if kind!='styles' or role!='outerwear']
        facts=[scorer._fact(index,p,values,g) for g in selected]
        if kind=='garment_categories':detail=ScoreEvidence(kind,F(int(any(f[0] for f in facts))),'Available',1,1)
        elif kind in ('colours','styles'):
            matched=sum(f[0] for f in facts);known=sum(f[1] for f in facts)
            if kind=='colours' and matched:detail=ScoreEvidence(kind,F(1),'Available',known,len(facts))
            elif not known and not matched:detail=ScoreEvidence(kind,None,'Unknown',0,len(facts))
            else:detail=ScoreEvidence(kind,F(int(matched>0)) if kind=='colours' else F(matched,len(facts)), 'Available' if known==len(facts) else 'Partial',known,len(facts))
        else:
            goals=tuple(zip(*(f[0] for f in facts)))
            if any(all(v=='Pass' for v in row) for row in goals):detail=ScoreEvidence(kind,F(1),'Available',1,1)
            elif all(any(v=='Fail' for v in row) for row in goals):detail=ScoreEvidence(kind,F(),'Available',1,1)
            else:detail=ScoreEvidence(kind,None,'Unknown',0,1)
        details.append(detail)
    value=sum((p.importance*(d.value or F()) for p,d in zip(prefs.preferences,details)),F())/denominator
    summary=ScoreEvidence('preference',None,'Unknown',0,sum(d.possible for d in details)) if all(d.value is None for d in details) else ScoreEvidence('preference',value,'Available' if all(d.state=='Available' for d in details) else 'Partial',sum(d.observed for d in details),sum(d.possible for d in details))
    return ComponentScore(summary,tuple(details))


def projected_snapshot(garment):
    value=asdict(garment)
    # These optional description channels are already captured independently in
    # B0 evidence and are irrelevant to the original four P1 fact primitives.
    for key in ('secondary_colour','colour_palette','pattern','fit','material','colour_temperature','is_dominant'):value.pop(key)
    if len(encode(value))>16384:raise PreferenceError('PreferenceCapacityExceeded','Selected legacy fact projection exceeds16KiB.')
    return value


def restore_snapshot(value):
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
    from app.domain.value_objects.general_context_evidence import AppearanceEvidence
    from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
    fields={f.name for f in __import__('dataclasses').fields(ConfirmedGarmentSnapshot)}-{'secondary_colour','colour_palette','pattern','fit','material','colour_temperature','is_dominant'}
    exact(value,fields);v=dict(value)
    contextual=dict(v['contextual_suitability'])
    for name in ('reviewed_styles','wedding_decisions'):contextual[name]=tuple(contextual[name])
    v['contextual_suitability']=ContextualGarmentEvidence(**contextual)
    appearance=dict(v['appearance_evidence']);appearance['features']=tuple(tuple(pair) for pair in appearance['features'])
    v['appearance_evidence']=AppearanceEvidence(**appearance)
    v['saved_attribute_evidence']=SavedAttributeEvidence(**v['saved_attribute_evidence'])
    return ConfirmedGarmentSnapshot(**v)


def restore_request(value):
    if 'context' in value:
        from app.application.recommendation.refinement_verifier import rebuild_request
        return rebuild_request(value)
    exact(value,('intent','occasion','style','colours','garment_categories','formality'));v=dict(value)
    if v['garment_categories']:v['garment_categories']=tuple(GarmentCategoryConstraint(**c) for c in v['garment_categories'])
    return StructuredOutfitRequest(**v)


def bounded_provenance(value):
    if type(value) is not dict or 'attribute_preference' not in value:raise PreferenceError('PreferenceInvalid','P2 provenance requires its immutable sidecar.')
    core={k:v for k,v in value.items() if k not in ('attribute_preference','attribute_selection')}
    if len(encode(core))>368640:raise PreferenceError('PreferenceCapacityExceeded','P2 core provenance exceeds360KiB.')
    raw=encode(value)
    if len(raw)>1048576:raise PreferenceError('PreferenceCapacityExceeded','P2 provenance exceeds1MiB.')
    return raw.decode('utf-8')
