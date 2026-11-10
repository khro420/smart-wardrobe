"""Frozen finite labels against real B0 descriptions; no new evaluator as oracle."""
from tests.retained_evidence import review_path, review_reference
from dataclasses import replace
from pathlib import Path
import json
import pytest
from app.domain.value_objects.attribute_conditions import AttributeConditions,AttributeRequestError,VERSION,ANCHORS,encode
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.garment_description_evidence import FIELDS
from app.domain.value_objects.general_context_evidence import AppearanceEvidence,FEATURES
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
from app.application.wardrobe.description_policy import DescriptionPolicy
from app.application.wardrobe.description_normalizer import normalise_field
from app.application.wardrobe import description_projector as b0
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions

LABELS=json.loads((Path(__file__).parent/'fixtures/attribute_labels.v1.json').read_text(encoding='utf-8'))
FINITE=[case for case in LABELS['finite']['cases'] if case['case'] in ('positive','known_mismatch','missing','stale','conflicting','unqualified_model')]
B0_POLICY=DescriptionPolicy.load()
POLICY=AttributeEvidencePolicy.load()
FIELD_MAP={'palette_colour':'colour_palette','palette_coverage':'colour_palette','descriptive_tag':'descriptive_tags'}


def make_member(identifier,field=None,value=None,state='owner',category='vest'):
    if field=='category':category=value
    role,layer=GARMENT_STRUCTURE[category]
    primary=value if field=='primary_colour' else 'blue'
    name=('' if state=='missing' else value) if field=='garment_name' else 'Exact name'
    snapshot=ConfirmedGarmentSnapshot(identifier,'owner-A','available',category,name,'media-A',False,
        '2026-11-04T00:00:00Z',role,layer,primary_colour=primary,style_tags=('casual',))
    if state=='missing' and field=='category':snapshot=replace(snapshot,category='')
    if state=='missing' and field=='primary_colour':snapshot=replace(snapshot,primary_colour=None)
    row={'id':identifier,'user_id':'owner-A','processing_item_id':'item-'+identifier,'name':name,
         'category':category,'preferred_media_id':'media-A','primary_colour':primary,'attributes_json':'{}'}
    document=b0.project(row,'owner-A',B0_POLICY).to_dict()
    if field in ('condition','construction_collared','construction_structured','construction_tailored'):
        if state=='owner':
            features=dict.fromkeys(FEATURES,None)
            key={'construction_collared':'collared_neckline','construction_structured':'structured_shape','construction_tailored':'tailored_cut'}.get(field)
            if key:features[key]=value
            snapshot=replace(snapshot,appearance_evidence=AppearanceEvidence('Known',category,'media-A',tuple(features.items()),value if field=='condition' else 'clean_intact','2026-11-04T00:00:00Z'))
        elif state=='stale':
            snapshot=replace(snapshot,appearance_evidence=AppearanceEvidence('Known',category,'old-media',tuple(dict.fromkeys(FEATURES,True).items()),'clean_intact','2026-11-04T00:00:00Z'))
    elif field is not None and state!='missing':
        target=FIELD_MAP.get(field,field);raw=value
        if field in ('style','material','descriptive_tag'):raw=value if isinstance(value,list) else [value]
        if field in ('palette_colour','palette_coverage'):
            colour=value if isinstance(value,str) and value.startswith('#') else next((k for k,v in ANCHORS.items() if v==value),value)
            raw=[{'hex':colour,'coverage':'1'}]
        kwargs={} if state=='unqualified_model' else dict(event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-11-04T00:00:00Z',source_revision='0'*64)
        record=normalise_field(target,raw,B0_POLICY,origin='model_suggestion' if state=='unqualified_model' else 'owner_selected',category=category,media_id='media-A',**kwargs).to_dict()
        if state in ('stale','conflicting','malformed'):
            record=b0._changed(record,state.title(),{'stale':'category_or_media_changed','conflicting':'category_sleeve_conflict','malformed':'invalid_or_oversize_source'}[state])
        document['fields'][target]=record
    return ConfirmedGarmentDescription(snapshot,b0._document(document['subject'],document['fields']))


def condition(field,value,op=None,q='exists',role='all_selected'):
    if op is None:
        op='exact_hex' if isinstance(value,str) and value.startswith('#') else 'bool_eq' if type(value) is bool else 'contains_any' if field in ('style','material','palette_colour') else 'in'
    values=value if isinstance(value,list) and field in ('style','material','palette_colour','descriptive_tag') else [value]
    return AttributeConditions.from_dict({'version':VERSION,'groups':[{'id':'g01','role':role,'quantifier':q,'conditions':[{'id':'c01','attribute':field,'operator':op,'values':values}]}]})


@pytest.mark.parametrize('case',FINITE,ids=lambda c:c['id'])
def test_frozen_finite_qualification(case):
    field,value=case['attribute'],case['value']
    if case['expected']=='UnsupportedAttributeValue':
        with pytest.raises(AttributeRequestError):condition(field,value)
        return
    kind=case['case'];actual_value=case['known_other'] if kind=='known_mismatch' else value
    state='owner' if kind in ('positive','known_mismatch') else kind
    item=make_member('target',field,actual_value,state)
    prepared=PreparedAttributeConditions.prepare(condition(field,value),[item],POLICY)
    role={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}[item.snapshot.structural_role]
    assert prepared.evaluate_members(((role,'target'),))==case['expected']


def test_archived_policy_needs_no_file_loader(monkeypatch):
    from app.application.recommendation import attribute_evidence_policy as module
    snapshot=POLICY.snapshot()
    monkeypatch.setattr(module.Path,'open',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No active load')))
    restored=AttributeEvidencePolicy(encode(snapshot))
    assert restored.sha256==POLICY.sha256
    snapshot['model_sources'].append({'field':'pattern','confidence':0.99})
    with pytest.raises(AttributeRequestError):AttributeEvidencePolicy(encode(snapshot))


def test_named_primary_aliases_match_original_mapper():
    from app.application.recommendation.colour_classifier import ColourClassifier
    old=ColourClassifier();new=POLICY.primary_classifier()
    for raw in (*old.aliases,*old.anchors,'#abc','#123abc','not-colour',None):
        assert (old.classify(raw).state,old.classify(raw).values)==(new.classify(raw).state,new.classify(raw).values)


def test_current_material_label_does_not_promote_model_suggestion():
    item=make_member('A','material','cotton','unqualified_model')
    prepared=PreparedAttributeConditions.prepare(condition('material','cotton'),[item],POLICY)
    assert prepared.evaluate_members((('upper','A'),))=='Unknown'


MATRIX_PATH=review_reference(json.loads((Path(__file__).parent/'fixtures/attribute_sources.v1.json').read_text(encoding='utf-8'))['approved_scope_path']).parent/'B1-attribute-value-coverage.json'
MATRIX_ROWS=json.loads(MATRIX_PATH.read_text(encoding='utf-8'))['rows']


@pytest.mark.parametrize('row',MATRIX_ROWS,ids=lambda r:r['id'])
def test_every_original_matrix_row_retains_its_source_boundary(row):
    from app.domain.value_objects.attribute_conditions import FIELDS as REQUEST_FIELDS
    field,status,raw=row['attribute'],row['B1_status'],row['source_value']
    if field not in REQUEST_FIELDS:
        with pytest.raises(AttributeRequestError):condition(field,str(raw))
        if str(field).startswith('reserved_'):
            with pytest.raises(AttributeRequestError):condition('descriptive_tag',str(raw),op='exact_text')
        return
    if status=='ControlledUnknown':
        with pytest.raises(AttributeRequestError):condition(field,raw)
        requested='cotton' if field=='material' else 'clean_intact'
        item=make_member('row',field,raw)
        assert PreparedAttributeConditions.prepare(condition(field,requested),[item],POLICY).evaluate_members((('upper','row'),))=='Unknown'
        return
    if status=='Blocked':
        if field=='palette_colour':
            with pytest.raises(AttributeRequestError):condition(field,raw)
        else:
            requested={'pattern':'plain','neckline':'crew','sleeve_length':'short'}[field]
            item=make_member('row',field,raw,'unqualified_model')
            assert PreparedAttributeConditions.prepare(condition(field,requested),[item],POLICY).evaluate_members((('upper','row'),))=='Unknown'
        return
    value=raw if isinstance(raw,str) and raw.startswith('#') else row['canonical_value']
    if value in ('true','false'):value=value=='true'
    if value=='#RRGGBB_non_anchor':value='#123abc'
    if field=='garment_name':value='Exact \U0001f455 shirt'
    if field=='descriptive_tag':value='handmade literal'
    if field=='palette_coverage':
        from tests.test_attribute_candidate_selection import with_field
        item=with_field(make_member('row'),'colour_palette',[{'hex':'#0000ff','coverage':'0.500000'},{'hex':'#ffffff','coverage':'0.250000'}])
        rq=condition(field,{'colour':'blue','minimum':'0.500000'},op='coverage_ge')
    else:
        item=make_member('row',field,value);rq=condition(field,value,op='exact_text' if field in ('garment_name','descriptive_tag') else None)
    role={'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}[item.snapshot.structural_role]
    assert PreparedAttributeConditions.prepare(rq,[item],POLICY).evaluate_members(((role,'row'),))=='Pass'
    if row['source_layer']=='source_suffix_format_examples' and '(' in str(raw):
        target=FIELD_MAP.get(field,field);doc=item.description.to_dict()
        doc['fields'][target]=normalise_field(target,raw,B0_POLICY,category=item.snapshot.category,media_id=item.snapshot.preferred_media_id).to_dict()
        legacy=ConfirmedGarmentDescription(item.snapshot,b0._document(doc['subject'],doc['fields']))
        assert PreparedAttributeConditions.prepare(rq,[legacy],POLICY).evaluate_members(((role,'row'),))=='Unknown'
