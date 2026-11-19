"""Source-grounded semantic slots compiled into unchanged deterministic contracts.

The pretrained models interpret input. The frozen grammar is an OUTPUT compiler,
not the natural-language recognizer. Every locked/history pass validates the
untrusted proposal afresh; model outputs never qualify garment evidence.
"""
from pathlib import Path
import hashlib,json,re
from . import context_language,interview_default,semantic_model
from .semantic_frame_contract import GRAMMAR
from app.application.nlp.compositional_request_v1 import CompositionalIntent,NOUNS
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.attribute_conditions import AttributeRequestError,AttributeConditions,digest,encode
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS

ROLES={'guest','bride','groom','bridesmaid','groomsman','presenter','attendee','candidate','interviewer','graduate','employee','staff'}
CODES={'unspecified','casual','smart_casual','formal','black_tie'}
# Validation vocabulary: it cannot choose a context or generate an attribute.
WORDS=set("i i'm im i'd id i'll ill ive i've am are is it's its was were be been being have has had got get getting go going gonna heading head attend attending spend spending spent take taking to for at in on of from into out off with and but then so a an the my our your his her their some few things something anything outfit outfits clothes clothing wear wearing should could would can you me we we're later today tonight tomorrow this next weekend afternoon morning evening week day please pls plz hey hi well okay ok suggest recommend give gimme help find choose pick put throw need want wants buy buying grab grabbing purchase purchasing shop shops shopping studying study revising revise library uni university campus class classes lecture lectures presentation dinner lunch supper meal meals eat eating food restaurant friends friend buddy buddies pal pals mate mates cousin sister brother colleague colleagues classmates classmate aunt uncle niece nephew close best wedding weddings married marrying marry work working workplace office business job employment interview interviewed interviewing applicants meeting date cafe coffee cinema movie movies film watching watch see sightseeing city sights landmarks journey travel traveling travelling train bus flight trip birthday party gathering celebration house place reunion social casual outing plans planning intending scheduled will not no don't dont without except never can't cant cannot won't wont as candidate interviewer guest presenter attendee bride groom graduate bridesmaid groomsman staff employee code dress formal smart tie prefer preferably love ideally definitely really only just either or instead than rather fine any many thing up they them he she that that's thats there it also actually".split())
NEG=re.compile(r"\b(?:no|not|never|without|except|don't|dont|can't|cant|cannot|won't|wont)\b")
SOFT=re.compile(r'\b(?:prefer|preferably|love|ideally|wish)\b')
WORDS.update({'what','which','having','mall'})
WITNESSES={
 'ceremony.wedding':{'wedding','married','marrying'},'social.meal':{'dinner','lunch','supper','meal','food','eat','eating','restaurant'},
 'social.date':{'date'},'professional.job_interview':{'interview','interviewed','interviewing'},
 'academic.presentation':{'presentation','presenting'},'everyday.academic_attendance':{'class','classes','lecture','lectures','university','uni','campus'},
 'academic.library_study':{'library'},'academic.group_study':{'group','classmates'},'everyday.shopping':{'shopping','shop','shops','mall','buy','buying'},
 'professional.office_day':{'office','work'},'professional.workplace_meeting':{'meeting','colleagues'},'everyday.casual_outing':{'friends','friend','buddy','buddies','mates','pals','outing'},
 'social.birthday_gathering':{'birthday'},'social.house_gathering':{'house','place'},'leisure.cinema_outing':{'cinema','film','movie','movies'},
 'social.cafe_meetup':{'cafe','coffee'},'leisure.city_sightseeing':{'sightseeing','sights','landmarks'},'travel.journey':{'journey','travel','travelling','traveling','trip','bus','train','flight'}}

def refuse(reason):raise AttributeRequestError('UnsupportedRequest',reason)
def lower(s):return s.casefold().replace('\u2019',"'").replace('\u2018',"'")

def identity():
 from app.shared_contracts.grammar_identity import semantic_fingerprint
 from .semantic_frame_contract import GRAMMAR_SHA256
 h=semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(context_language.identity()),bytes.fromhex(interview_default.identity()),Path(__file__).read_bytes(),Path(semantic_model.__file__).read_bytes(),semantic_model.MANIFEST.read_bytes()))
 if h!=GRAMMAR_SHA256:raise ValueError('Unregistered hybrid semantic interpreter.')
 return h

def span(raw,q):
 if type(q) is not str or not q.strip():refuse('semantic_source_grounding')
 found=list(re.finditer(re.escape(q),raw))
 if len(found)!=1:refuse('semantic_source_grounding')
 return found[0].span()

def validate(raw,p):
 if type(raw) is not str or not raw.strip() or len(raw)>500 or any(ord(c)<32 and c not in '\r\n\t' for c in raw):refuse('semantic_invalid_input')
 if any(ord(c)>127 and c not in '\u2018\u2019\u201c\u201d\u2013\u2014\u2026' for c in raw) or re.search(r'\d',raw):refuse('semantic_unsupported_requirement')
 if any(c in raw for c in ('"','\u201c','\u201d')):refuse('semantic_unsupported_requirement')
 if type(p) is not dict or set(p)!={'version','source_text','source_sha256','identity','input_normalization','slots'} or len(encode(p))>24576:refuse('semantic_invalid_output')
 if p['version']!='local-semantic-proposal-1.0.0' or p['source_text']!=raw or p['source_sha256']!=hashlib.sha256(raw.encode()).hexdigest() or p['identity']!=semantic_model.identity():refuse('semantic_source_grounding')
 from app.application.nlp.compositional_input_v1 import normalize
 if p['input_normalization']!=normalize(raw):refuse('semantic_source_grounding')
 s=p['slots']
 if type(s) is not dict or set(s)!={'context','context_quote','role','role_quote','dress_code','dress_quote','formality','formality_quote','context_conditions','secondary','conditions','uncertain','unsupported'}:refuse('semantic_invalid_output')
 if any(type(s[k]) is not str for k in ('context','role','dress_code','formality')):refuse('semantic_invalid_output')
 if s['context'] not in (*semantic_model.CONTEXTS,'none') or s['role'] not in ROLES|{'unspecified'} or s['dress_code'] not in CODES or s['formality'] not in CODES:refuse('semantic_invalid_output')
 if type(s['uncertain']) is not bool or type(s['unsupported']) is not list or len(s['unsupported'])>8:refuse('semantic_invalid_output')
 if s['uncertain']:refuse('semantic_clarification_required')
 if s['unsupported']:refuse('semantic_unsupported_requirement')
 if s['context']!='none':span(raw,s['context_quote'])
 elif s['context_quote']:refuse('semantic_source_grounding')
 if type(s['secondary']) is not list or len(s['secondary'])>3:refuse('semantic_invalid_output')
 for q in s['secondary']:span(raw,q)
 if re.search(r'\b(?:maybe|perhaps|possibly|warmer|cooler|waterproof|weatherproof|similar|more|less|rain|snow|temperature|look like)\b',lower(raw)):refuse('semantic_unsupported_requirement')
 for name,qname in [('role','role_quote'),('dress_code','dress_quote'),('formality','formality_quote')]:
  if s[name]=='unspecified':
   if s[qname]:refuse('semantic_source_grounding')
  else:
   a,b=span(raw,s[qname]);e=lower(raw[a:b]);before=lower(raw[max(0,a-45):a])
   if NEG.search(e) or re.search(r"(?:not|no|don't|dont)\s+(?:exactly\s+)?(?:a\s+)?$",before):refuse('semantic_unsupported_requirement')
   if name in ('dress_code','formality') and s[name].replace('_',' ') not in e:refuse('semantic_source_grounding')
   if name=='role' and not (s[name] in e or s[name]=='candidate' and 'interviewed' in e or s[name]=='interviewer' and 'interviewing' in e or s[name]=='presenter' and e in ('presenting','giving') or s[name]=='attendee' and e in ('attend','attending')):refuse('semantic_role_clarification')
 if s['context']=='professional.job_interview' and s['role'] not in ('candidate','interviewer'):refuse('semantic_role_clarification')
 explicit_roles=re.findall(r'\bas (?:an? |the )?('+ '|'.join(sorted(ROLES))+r')\b',lower(raw))
 if explicit_roles and set(explicit_roles)!={s['role']}:refuse('semantic_role_clarification')
 try:observations=semantic_model.check_source_roles(raw,s['context'],s['role'])
 except semantic_model.ModelUnavailable:raise
 except ValueError:refuse('semantic_role_clarification')
 if type(s['context_conditions']) is not list or s['context_conditions']!=observations:refuse('semantic_source_grounding')
 if s['context']=='none' and observations:refuse('semantic_clarification_required')
 w=set(re.findall(r"[a-z]+",lower(raw)))
 if s['context']=='none' and s['formality']!='unspecified' and not w&{'outfit','clothes','clothing'}:refuse('semantic_clarification_required')
 if s['context']=='none' and not s['conditions'] and not (w&{'outfit','clothes','clothing'} and w&{'recommend','suggest','give','need','want','pick','choose'} or 'wear' in w and w&{'what','should','can'}):refuse('semantic_clarification_required')
 if s['context']!='none' and not w&WITNESSES[s['context']]:refuse('semantic_source_grounding')
 if s['context']=='none' and w&{'wedding','married','shopping','library','interview','dinner','presentation'}:refuse('semantic_clarification_required')
 if w&{'wedding','married','marrying'} and s['context']!='ceremony.wedding':refuse('semantic_clarification_required')
 if w&{'dinner','lunch','supper','meal'} and s['context'] not in ('social.meal','social.date','ceremony.wedding'):refuse('semantic_clarification_required')
 if 'date' in w and s['context']!='social.date':refuse('semantic_clarification_required')
 if 'library' in w and not w&{'study','studying','revise','revising'}:refuse('semantic_clarification_required')
 if 'reunion' in w and s['context']=='everyday.academic_attendance':refuse('semantic_clarification_required')
 if 'then' in w:refuse('semantic_clarification_required')
 if s['context']=='academic.presentation' and not w&{'university','uni','campus'}:refuse('semantic_clarification_required')
 if s['context']=='professional.workplace_meeting' and not w&{'work','workplace','office','business','colleagues'}:refuse('semantic_clarification_required')
 if s['context']=='professional.job_interview' and not w&{'job','employment','position','applicants','candidates'}:refuse('semantic_clarification_required')
 if s['context']=='everyday.shopping' and 'mall' in w and not w&{'buy','buying','shop','shopping','purchase','purchasing','grab','grabbing'}:refuse('semantic_clarification_required')
 if type(s['conditions']) is not list or len(s['conditions'])>8:refuse('semantic_invalid_output')
 occupied=[];cues=[];conditions=[]
 for c in s['conditions']:
  if type(c) is not dict or set(c)!={'quote','kind'} or c['kind'] not in ('hard','optional','exclude'):refuse('semantic_invalid_output')
  a,b=span(raw,c['quote'])
  if any(a<y and b>x for x,y in occupied):refuse('semantic_modifier_scope')
  occupied.append((a,b));prefix=lower(raw[:a]);boundary=max((m.end() for m in re.finditer(r'[,;.!?]|\b(?:and|but)\b',prefix)),default=0)
  near=prefix[boundary:];neg=list(NEG.finditer(near));soft=list(SOFT.finditer(near))
  # A negated preference is not a hard exclusion; negating a necessity does
  # not prohibit the garment either. Neither meaning has an approved policy.
  negated_need=any(re.search(r'\bneed\b',near[m.end():]) for m in neg)
  if (neg or NEG.search(lower(c['quote']))) and (soft or SOFT.search(lower(c['quote'])) or negated_need):
   refuse('semantic_polarity_mismatch')
  if len(neg)+len(list(NEG.finditer(lower(c['quote']))))>1:refuse('semantic_polarity_mismatch')
  if c['kind']=='optional':
   if soft:
    m=soft[-1];cues.append((boundary+m.start(),boundary+m.end()))
   else:
    m=re.match(r'(?:preferably|ideally)\b',lower(c['quote']))
    if not m:refuse('semantic_polarity_mismatch')
    cues.append((a,a+m.end()))
  elif c['kind']=='exclude':
   if not neg and not NEG.search(lower(c['quote'])):refuse('semantic_polarity_mismatch')
   if neg:
    m=neg[-1];cues.append((boundary+m.start(),boundary+m.end()))
  elif neg or soft or NEG.search(lower(c['quote'])):refuse('semantic_polarity_mismatch')
  conditions.append((c['kind'],a,b,c['quote']))
 if sum(k=='optional' for k,_,_,_ in conditions)>1:refuse('multiple_compositional_preferences')
 coverage=occupied+cues
 for name,qname in [('role','role_quote'),('dress_code','dress_quote'),('formality','formality_quote')]:
  if s[name]!='unspecified':coverage.append(span(raw,s[qname]))
 covered=lambda a,b:any(x<=a and b<=y for x,y in coverage)
 descriptors={v for k,vs in CANONICAL_ENUMS.items() if k in ('primary_colour','material','pattern','silhouette','sleeve_length','style') for v in vs if re.fullmatch('[a-z]+',v)}|set(NOUNS)|{'pants','striped','sleeved','denim','cotton','grey','gray'}
 for m in re.finditer(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?",raw):
  t=lower(m[0]);plain=t.removesuffix("'s")
  if covered(*m.span()):continue
  if t in descriptors or t in {'or','prefer','preferably','love','ideally'}:refuse('semantic_omitted_condition')
  if plain not in WORDS:
   from app.application.nlp.conversational_context_interpreter import load_language
   if not any(a.start()<=m.start() and m.end()<=a.end() for pattern in load_language()['function_frames'] for a in re.finditer(pattern,raw,re.I)):
    refuse('semantic_unaccounted_meaning')
 for m in NEG.finditer(lower(raw)):
  if not covered(*m.span()):refuse('semantic_unconsumed_negation')
 return s,conditions,cues

def document(raw,proposal):
 grammar=identity();s,conditions,cues=validate(raw,proposal)
 text='';mapping=[];edits=[]
 def append(value,source):
  nonlocal text
  a,b=source;text+=value;mapping.extend([[a,b] for _ in value]);edits.append({'stage':'hybrid_semantic_compiler_1_0','rule':'grounded_slot_compile','raw_start':a,'raw_end':b,'raw_text':raw[a:b],'after':value})
 if s['context']!='none':
  from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
  reg=ContextPolicyRegistry.load(bundle_id='context_18_v1');event=next(v for v in reg.situations if v.identifier==s['context'])
  event_text=event.phrases[0]
  # Serialize the institution as a venue, not an attributive event modifier:
  # the archived input rewriter treats that attributive form inconsistently.
  # This is an output encoding of the already validated university scope.
  if s['context']=='academic.presentation':event_text='presentation at university'
  if s['context']=='social.date' and 'dinner' in lower(raw):event_text='dinner date'
  if s['context']=='travel.journey':
   modes=set(re.findall(r'\b(?:train|bus|flight)\b',lower(raw)))
   if len(modes)>1:refuse('semantic_clarification_required')
   if modes:event_text=next(iter(modes))+' journey'
  if s['formality']!='unspecified':
   append('I need a ',span(raw,s['context_quote']));append(s['formality'].replace('_',' '),span(raw,s['formality_quote']));append(' outfit for '+event_text,span(raw,s['context_quote']))
  else:append('I need an outfit for '+event_text,span(raw,s['context_quote']))
  if s['role']!='unspecified':append(' as the '+s['role'],span(raw,s['role_quote']))
  if s['dress_code']!='unspecified':append(', the dress code is '+s['dress_code'].replace('_',' '),span(raw,s['dress_quote']))
  for observation in s['context_conditions']:
   if s['context']=='academic.presentation' and observation['slot']=='venue' and observation['value']=='university':continue
   prefix={'companions':' with ','venue':' at ','temporal':' '}[observation['slot']]
   append(prefix+observation['value'],span(raw,observation['quote']))
 elif s['formality']!='unspecified':
  append('I need a ',(0,len(raw)));append(s['formality'].replace('_',' '),span(raw,s['formality_quote']));append(' outfit',(0,len(raw)))
 elif not conditions:append('Recommend an outfit',(0,len(raw)))
 for kind,a,b,q in sorted(conditions,key=lambda c:c[0]=='optional'):
  if text:append(', ',(a,b))
  if kind=='exclude':
   short=re.sub(r'^(?:no|not|without)\s+','',q,flags=re.I);a+=len(q)-len(short);q=short
  if kind=='optional':
   short=re.sub(r'^(?:preferably|ideally)\s+','',q,flags=re.I);a+=len(q)-len(short);q=short
  optional_prefix="I'd prefer "
  if kind=='optional':
   try:explicit=CompositionalIntent.capture("I'd prefer "+q).to_dict()['optional']
   except AttributeRequestError:explicit=None
   if explicit is None:optional_prefix='preferably '
  prefix={'hard':'I need ','exclude':"I don't want ",'optional':optional_prefix}[kind]
  append(prefix,cues[-1] if kind=='optional' else (a,b));text+=q;mapping.extend([[i,i+1] for i in range(a,b)])
 append('.',(max(0,len(raw)-1),len(raw)))
 if len(text)>500:refuse('semantic_encoding_limit')
 value=CompositionalIntent.capture(text).to_dict() if s['context']=='none' else (interview_default.document if s['context']=='professional.job_interview' else context_language.document)(text)
 if s['context']!='none' and value['request']['context']['situation']['values']!=[s['context']]:refuse('semantic_context_collision')
 if s['context']=='social.meal' and 'birthday' in lower(raw) and 'celebration:birthday' not in value['request']['context']['facets']['values']:refuse('semantic_unsupported_requirement')
 joined=context_language.compose({'original_text':raw,'normalized_text':text,'character_map':mapping,'transformations':edits},value['normalization']);joined['version']='raw-hybrid-semantic-map-1.0.0'
 hard=value['hard_intent'];optional=value['optional']
 if hard:hard=AttributeIntent.capture(joined['normalized_text'],None,AttributeConditions.from_dict(hard['conditions']),hard['spans'],grammar,hard['policy_sha256']).to_dict()
 context=value['request'].get('context',{})
 result={**value,'version':'hybrid-semantic-intent-1.0.0','grammar_version':GRAMMAR,'grammar_sha256':grammar,'normalization':joined,'hard_intent':hard,'semantic_proposal':proposal,
  'semantic_metadata':{'primary':s['context'],'secondary':s['secondary'],'role':s['role'],'dress_code':s['dress_code'],'formality':s['formality'],'model_is_not_garment_evidence':True},
  'original_hard_spans':[{**x,**original_span(joined,x['start'],x['end'])} for x in hard['spans']] if hard else [],
  'original_optional_spans':[{**x,**original_span(joined,x['start'],x['end'])} for x in optional['spans']] if optional else [],
  'original_context_spans':[{'slot':n,'value':v['values'],**original_span(joined,x['start'],x['end'])} for n,v in context.items() if isinstance(v,dict) and 'spans' in v for x in v['spans']]}
 result.pop('revision',None);result=json.loads(encode(result));result['revision']=digest(result);return result
