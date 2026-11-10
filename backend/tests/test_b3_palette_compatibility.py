"""Hand-calculated C2 mechanical expectations, independent of fashion labels."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import json
import pytest
from tests.test_attribute_qualification import make_member,B0_POLICY
from app.application.wardrobe.description_normalizer import normalise_field
from app.application.wardrobe.description_projector import _document
from app.application.recommendation.palette_compatibility_preparation import PreparedPaletteCompatibility
from app.application.recommendation.palette_compatibility_scorer import public_component
from app.application.recommendation.palette_compatibility_policy import PalettePolicy,configure
from app.domain.value_objects.palette_compatibility import Interval,PaletteError

def member(gid,palette=None,category='vest',state='owner',styles=('casual',)):
    item=make_member(gid,category=category);item=replace(item,snapshot=replace(item.snapshot,style_tags=styles))
    if palette is None:return item
    if state in ('missing','stale','malformed','conflicting','unqualified_model'):
        return make_member(gid,'palette_colour','#0000ff',state=state,category=category)
    doc=item.description.to_dict()
    record=normalise_field('colour_palette',palette,B0_POLICY,origin='owner_selected',category=category,media_id='media-A',
        event_id='00000000-0000-4000-8000-000000000001',recorded_at='2026-11-06T00:00:00Z',source_revision='0'*64).to_dict()
    doc['fields']['colour_palette']=record
    return replace(item,description=_document(doc['subject'],doc['fields']))

BLUE=[{'hex':'#0000ff','coverage':'1'}]
RED=[{'hex':'#ff0000','coverage':'1'}]

CASES=json.loads((Path(__file__).parent/'fixtures/b3_palette_cases.v1.json').read_text(encoding='utf-8'))['cases']
@pytest.mark.parametrize('palette,low,high,value',[(c['palette'],F(c['colour_lower']),F(c['colour_upper']),F(c['compatibility'])) for c in CASES],ids=[c['id'] for c in CASES])
def test_hand_calculated_colour_intervals_and_actual_C_contribution(palette,low,high,value):
    pool=[member('A',palette),member('B',RED,'trousers')];p=PreparedPaletteCompatibility('owner-A',pool)
    public=public_component(p.facts,(('upper','A'),('lower','B')),p.policy)
    compact=p.compact(tuple(i.snapshot for i in pool),('upper','lower'),(0,1))
    assert public.decision.atoms[0][1]==Interval(low,high)
    assert public.contribution==compact.value==value
    assert (public.decision.lower,public.decision.upper)==(compact.lower,compact.upper)
    assert public.summary.state==('Available' if low==high else 'Unknown')

@pytest.mark.parametrize('state',['missing','stale','malformed','conflicting','unqualified_model'])
def test_unqualified_source_is_unknown_without_primary_or_secondary_fallback(state):
    pool=[member('A',BLUE,state=state),member('B',RED,'trousers')];p=PreparedPaletteCompatibility('owner-A',pool)
    c=p.compact(tuple(i.snapshot for i in pool),('upper','lower'),(0,1))
    assert c.intervals[0]==Interval(F(),F(1)) and c.raw.state=='Unknown'

@pytest.mark.parametrize('roles,categories',[(('upper','lower'),('vest','trousers')),(('upper','lower','outerwear'),('vest','trousers','long_sleeve_outwear')),(('one_piece',),('vest_dress',)),(('one_piece','outerwear'),('vest_dress','long_sleeve_outwear'))])
def test_four_structures_public_compact_exact_equivalence_and_no_pair(roles,categories):
    pool=tuple(member(str(i),BLUE,c) for i,c in enumerate(categories));p=PreparedPaletteCompatibility('owner-A',pool)
    key=tuple(zip(roles,(str(i) for i in range(len(pool)))))
    a=public_component(p.facts,key,p.policy);b=p.compact(tuple(v.snapshot for v in pool),roles,tuple(range(len(pool))))
    assert a.contribution==b.value==(F(1,2) if len(pool)==1 else F(1))
    assert (a.decision.basis,a.decision.pair_count)==(b.basis,b.pairs)
    if len(pool)==1:assert a.summary.state=='NotApplicable' and a.decision.atomic_count==0

def test_archived_policy_and_facts_need_no_current_loader(monkeypatch):
    from app.application.nlp.vocabulary import Vocabulary
    policy=PalettePolicy.load();pool=[member('A',BLUE),member('B',RED,'trousers')]
    current=PreparedPaletteCompatibility('owner-A',pool,policy)
    def blocked(*a,**k):raise AssertionError('Active resource loader in historical reconstruction')
    monkeypatch.setattr(PalettePolicy,'load',blocked);monkeypatch.setattr(Vocabulary,'load',blocked)
    restored=PreparedPaletteCompatibility('owner-A',pool,PalettePolicy.restore(policy.snapshot()),archived=True)
    assert restored.facts==current.facts

def test_defaults_scope_ownership_and_tampered_policy_are_rejected():
    assert configure() is None
    with pytest.raises(PaletteError):configure('recorded_palette_compatibility_v1')
    with pytest.raises(PaletteError):PreparedPaletteCompatibility('foreign',[member('A',BLUE)])
    with pytest.raises(PaletteError):PreparedPaletteCompatibility('owner-A',[member('A',BLUE)]*2)
    data=PalettePolicy.load().snapshot();data['default_activation']=True
    with pytest.raises(PaletteError):PalettePolicy.restore(data)
    for bounds in ((F(1),F()),(1,F(1)),(F(-1),F(1))):
        with pytest.raises(ValueError):Interval(*bounds)

@pytest.mark.parametrize('bad',[[{'hex':'#0000ff','coverage':'0.7'},{'hex':'#ff0000','coverage':'0.7'}],[{'hex':'#0000ff','coverage':'0.5'},{'hex':'#0000ff','coverage':'0.5'}]])
def test_invalid_palette_never_normalizes_into_qualified_mass(bad):
    item=member('A',bad);p=PreparedPaletteCompatibility('owner-A',[item])
    assert not p.facts['A'].palette
