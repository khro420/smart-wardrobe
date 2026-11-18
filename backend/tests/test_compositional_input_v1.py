"""Authored complete meanings, not HTTP acceptance or observed winners."""
import json,pytest
from app.application.nlp.compositional_request_v1 import CompositionalIntent
from app.domain.value_objects.attribute_conditions import AttributeRequestError,encode,digest

def g(role,quantifier,*conditions):return (role,quantifier,tuple(conditions))
def c(field,*values):return (field,tuple(sorted(values)))
def meaning(text):
    v=CompositionalIntent.capture(text).to_dict()
    groups=v['hard_intent']['conditions']['groups'] if v['hard_intent'] else []
    gs=[g(x['role'],x['quantifier'],*(c(y['attribute'],*y['values']) for y in x['conditions'])) for x in groups]
    optional=v['optional']
    os=None if optional is None else (optional['role'],tuple(c(y['attribute'],*y['values']) for y in optional['predicates']),optional['resolution']['state'])
    for spans in ('original_hard_spans','original_optional_spans'):
        for s in v[spans]:assert s['text']==text[s['start']:s['end']] and s['start']<s['end']
    for edit in v['normalization']['transformations']:assert edit['raw_text']==text[edit['raw_start']:edit['raw_end']]
    assert len(v['normalization']['character_map'])==len(v['normalization']['normalized_text'])
    return v,gs,os

@pytest.mark.parametrize('text,expected,optional',[
 ('i dont want shorts, give me trousers instead',[g('lower','none',c('category','shorts')),g('lower','exists',c('category','trousers'))],None),
 ('i want trousers but not blue ones',[g('lower','exists',c('category','trousers')),g('lower','none',c('primary_colour','blue'),c('category','trousers'))],None),
 ('pls give me a white top and black pants',[g('upper','exists',c('primary_colour','white')),g('lower','exists',c('primary_colour','black'),c('category','trousers'))],None),
 ('i need grey trousers, not a grey shirt',[g('lower','exists',c('primary_colour','grey'),c('category','trousers')),g('upper','none',c('primary_colour','grey'))],None),
 ('i want a casual outfit but no jeans',[g('all_selected','all_present',c('style','casual')),g('lower','none',c('category','trousers'),c('material','denim'))],None),
 ('id prefer a black shirt but i need jeans',[g('lower','exists',c('category','trousers'),c('material','denim'))],('upper',(c('primary_colour','black'),),'Active')),
 ('i want trousers preferably blue but no shorts',[g('lower','exists',c('category','trousers')),g('lower','none',c('category','shorts'))],('lower',(c('primary_colour','blue'),),'Active')),
 ('dont give me anything red, i prefer blue trousers',[g('all_selected','none',c('primary_colour','red'))],('lower',(c('primary_colour','blue'),c('category','trousers')),'Active')),
 ('i need black trousers but id prefer a white shirt',[g('lower','exists',c('primary_colour','black'),c('category','trousers'))],('upper',(c('primary_colour','white'),),'Active')),
 ("i need a shirt thats either black or white",[g('upper','exists',c('primary_colour','black','white'))],None),
 ('black or grey trousers please',[g('lower','exists',c('primary_colour','black','grey'),c('category','trousers'))],None),
 ('no shorts or skirts',[g('lower','none',c('category','shorts','skirt'))],None),
 ('hey can u suggest smth casual for today pls',[g('base','exists',c('style','casual'))],None),
 ('i need black trousers but i prefer blue trousers',[g('lower','exists',c('primary_colour','black'),c('category','trousers'))],('lower',(c('primary_colour','blue'),c('category','trousers')),'ContradictedByHard')),
])
def test_complete_authored_meanings(text,expected,optional):
    v,gs,os=meaning(text)
    assert v['request']=={'intent':'outfit_recommendation','occasion':None,'style':None,'colours':None,'garment_categories':None,'formality':None}
    assert gs==expected and os==optional
    assert v['normalization']['original_text']==text

@pytest.mark.parametrize('a,b',[
 ('PLS GIVE ME A WHITE TOP AND BLACK PANTS!!!','I need white top and black trousers.'),
 ('I need gray trousers, not a grey shirt','i want grey trousers but not a gray top'),
 ('looking for black trousers rather than blue ones','i need black trousers, not blue ones'),
 ('I need a shirt that is either white or black','black or white shirt'),
 ('I need trousers preferably blue but no shorts','i want trousers, preferably blue, no shorts'),
 ('id prefer black top but i want trousers',"i'd prefer black shirt and i need trousers"),
])
def test_equivalent_composed_structures(a,b):assert meaning(a)[1:]==meaning(b)[1:]

@pytest.mark.parametrize('text',[
 'I need black trousers but no trousers','I need shorts and no shorts',
 'black top or blue trousers','I want trousers but not blue ones or maybe green',
 'id prefer cotton shirt but i need trousers','I prefer black trousers and I prefer white top',
 'I need trousers but anything is fine','I need trousers with magical pockets',
 'ur black trousers please','I need trousers and preferably black',
 'I need trousers preferably blue or red','no red or blue clothes',
 'can u recommend something thats not too formal','an outfit for a wedding but nothing too flashy',
 'I need trousers but','I need trousers,','not blue ones',
 'I need a shirt that is either waterproof or cotton',
])
def test_no_requirement_dropped_or_guessed(text):
    with pytest.raises((AttributeRequestError,ValueError)):CompositionalIntent.capture(text)

@pytest.mark.parametrize('text,situation',[
 ('gimme an outfit for a job interview','professional.job_interview'),
 ('im going shopping pls suggest an outfit','everyday.shopping'),
])
def test_context_retained_without_inventing_role(text,situation):
    v=CompositionalIntent.capture(text).to_dict();ctx=v['request']['context']
    assert ctx['situation']['values']==[situation] and ctx['role']['state']=='Unspecified'
    assert v['optional'] is None

@pytest.mark.parametrize('part',['map','optional','hard','clause','transform'])
def test_intent_tampering_not_accepted_with_a_recomputed_digest(part):
    v=CompositionalIntent.capture('pls i need trousers preferably black but no shorts').to_dict()
    if part=='map':v['normalization']['character_map'][0]=[0,0]
    elif part=='optional':v['optional']['role']='upper'
    elif part=='hard':v['hard_intent']['conditions']['groups'][0]['conditions'][0]['values']=['shorts']
    elif part=='clause':v['clauses'].pop()
    else:v['normalization']['transformations']=[]
    v['revision']='';v['revision']=digest(v)
    with pytest.raises(ValueError):CompositionalIntent(encode(v))

def test_all_three_historical_fingerprints_stay_exact():
    from app.application.nlp.conversational_context_interpreter import fingerprint
    from app.application.nlp.request_local_soft_parser import isolated_fingerprint
    from app.application.nlp.normalized_request_v1 import identity
    assert fingerprint()=='e869b32876d3335781a8b10c7b13a6b2905402ce021aca5db6a6413bde53b0ae'
    assert isolated_fingerprint()=='899f67e37b3a39a24cfb766ea0384c42e42ff69701a84ba14597d6fd59eb4b67'
    assert identity()=='c46688062562c228039e331635e4566db869238ae6b51c62e716bcf543040a59'

@pytest.mark.parametrize('polite,plain',[
 ('pls id prefer black shirt but please i need jeans',"i'd prefer black shirt but i need jeans"),
 ('pls dont give me shorts, please give me trousers instead',"don't give me shorts, give me trousers instead"),
 ('hey please i prefer blue trousers','i prefer blue trousers'),
 ('I need trousers but please no shorts, please i prefer blue trousers','I need trousers but no shorts, i prefer blue trousers'),
])
def test_polite_markers_do_not_change_clause_polarity(polite,plain):
    assert meaning(polite)[1:]==meaning(plain)[1:]
