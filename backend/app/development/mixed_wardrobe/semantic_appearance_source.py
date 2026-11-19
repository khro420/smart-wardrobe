"""1.4.1 appearance acquisition; 1.4 remains immutable for historical reconstruction.

Context grounding below is retained from the frozen typed kernel. Only garment
fragment acquisition and source action binding are versioned extension points.
"""
import re,json
from .semantic_typed_source import (NEG,SOFT,resources,semantic_model,normalize,original_span,refuse,AttributeConditions,descriptor_matches)
from .semantic_appearance_fragments import garments

def analyze(raw):
 if type(raw) is not str or not raw.strip() or len(raw)>500:refuse('semantic_invalid_input')
 if re.search(r'[0-9"\u201c\u201d]',raw) or any(ord(c)<32 and c not in '\r\n\t' for c in raw):refuse('semantic_unsupported_requirement')
 mapping=normalize(raw);text=mapping['normalized_text']
 with semantic_model.LOCK:
  semantic_model.ready();syntax,_,_=semantic_model.load();doc=syntax(text)
 from . import semantic_appearance_actions as semantic_requested_actions
 actions=semantic_requested_actions.analyze(doc,text)
 target_text=list(text)
 for a,b in actions['mask_spans']:
  for i in range(a,b):
   if text[i] not in ',;.!?':target_text[i]=' '
 hard,spans,optional,coverage,units,coarse=garments(''.join(target_text),doc)
 coverage.extend(actions['coverage'])
 occupied=lambda t:any(s['start']<=t.idx and t.idx+len(t)<=s['end'] for s in coverage)
 free=[t for t in doc if not occupied(t)];lemmas={t.lemma_.lower() for t in free};words={t.lower_ for t in free}
 event=[];negated=[];details=[]
 def mark(t,why):coverage.append({'start':t.idx,'end':t.idx+len(t),'reason':why})
 def candidates(ident,ts):
  ts=list(ts)
  if not ts:return
  affirmative=[]
  for t in ts:
   chain=[t,*t.ancestors];negative=False
   for node in chain:
    if node.pos_=='VERB' or node==t:
     if any(c.dep_=='neg' or c.lower_=='no' for c in node.children):negative=True
     if node.pos_=='VERB':break
   (negated if negative else affirmative).append(t)
   mark(t,'negated_event' if negative else 'event_anchor')
   if negative:
    for node in chain:
     for c in node.children:
      if c.dep_=='neg':mark(c,'negated_event_operator')
     if node.pos_=='VERB':break
  if affirmative:event.append((ident,affirmative))
 # These relations represent the existing context ontology, not sentences.
 # In particular a location is not itself a presentation, meal or purchase.
 ts=lambda *ws:[t for t in free if t.lemma_.lower() in ws or t.lower_ in ws]
 candidates('ceremony.wedding',ts('wedding','marry'))
 candidates('social.date',ts('date'))
 candidates('social.meal',ts('dinner','lunch','supper','meal','eat'))
 candidates('professional.job_interview',ts('interview'))
 candidates('academic.presentation',ts('presentation','present'))
 studying=ts('study','revise','revision');library=ts('library');group=ts('group','classmate')
 if studying and library:candidates('academic.library_study',studying)
 elif studying and group or 'project' in lemmas and group:candidates('academic.group_study',studying or group)
 attendance=ts('lecture','class')
 if attendance:candidates('everyday.academic_attendance',attendance)
 elif not studying and not ts('presentation','present','reunion'):
  candidates('everyday.academic_attendance',ts('university','uni','college','campus'))
 candidates('everyday.shopping',[doc[i] for i in actions['shopping_tokens']])
 meetings=ts('meeting','meet');professional=ts('work','workplace','office','business','colleague')
 if meetings and professional and not group:candidates('professional.workplace_meeting',meetings)
 elif not ts('interview','presentation','present'):candidates('professional.office_day',ts('office'))
 birthday=ts('birthday');candidates('social.birthday_gathering',birthday)
 home=[t for t in ts('house','place','home') if any(c.dep_=='poss' and c.lemma_ in ('friend','friends') for c in t.children) or 'gathering' in lemmas]
 candidates('social.house_gathering',home)
 candidates('leisure.cinema_outing',ts('cinema','movie','film'))
 candidates('social.cafe_meetup',ts('cafe','coffee'))
 candidates('leisure.city_sightseeing',ts('sightseeing','sightsee','sight','landmark'))
 if not ts('mall','shop','shopping','buy','purchase') and not ts('city','sightseeing','sightsee'):candidates('travel.journey',ts('travel','journey','bus','train','flight','trip'))
 people=ts('friend','friends','mate','pal','buddy','pals')
 if not event and people and any(t.lemma_ in ('meet','hang','chill','go','outing') for t in free):candidates('everyday.casual_outing',people)
 ids={ident for ident,_ in event}
 def same_nominal_event(left,right):
  for start,end in ((left,right),(right,left)):
   # A purpose PP on the event predicate can describe its direct object:
   # have [dinner] [for birthday]. Coordination is deliberately excluded.
   if start.dep_ in ('dobj','obj') and start.head.pos_=='VERB' and end.dep_=='pobj' and end.head.lemma_=='for' and end.head.head==start.head:return True
   current=start;seen=set()
   while current not in seen:
    if current==end:return True
    seen.add(current)
    if current.head==current:break
    if current.dep_ in ('compound','amod') or current.dep_=='pobj' and current.head.lemma_=='for' or current.dep_=='prep' and current.lemma_=='for' and current.head.pos_=='NOUN':
     current=current.head
    else:break
  return False
 # Registered compound facets refine one event; unrelated event heads refuse.
 for primary,modifier in [('social.date','social.meal'),('social.meal','social.birthday_gathering')]:
  if primary in ids and modifier in ids:
   p=[t for ident,ts_ in event if ident==primary for t in ts_];m=[t for ident,ts_ in event if ident==modifier for t in ts_]
   if not all(any(same_nominal_event(a,b) for a in p) for b in m):refuse('semantic_clarification_required')
   ids.remove(modifier)
 if len(ids)>1:refuse('semantic_clarification_required')
 context=next(iter(ids),'none');anchors=[t for ident,ts_ in event if ident==context for t in ts_]
 if context=='none' and negated:refuse('semantic_clarification_required')
 _,registry,_=resources();situation=next((s for s in registry.situations if s.identifier==context),None)
 observations=semantic_model._context_observations(doc,mapping)
 if context=='none' and any(o['slot']!='temporal' for o in observations):refuse('semantic_clarification_required')
 if context in ('everyday.academic_attendance','academic.presentation') and not any(o['slot']=='venue' for o in observations):
  institution=ts('university','uni','campus','college')
  if institution:
   t=institution[0];observations.append({'slot':'venue','value':'university','quote':original_span(mapping,t.idx,t.idx+len(t))['text']})
 # Normalize companion aliases only in a real companion relation, not possessor.
 for t in people:
  if (t.dep_=='pobj' and t.head.lemma_=='with' or t.dep_ in ('dobj','obj') and t.head.lemma_=='meet') and not any(x['slot']=='companions' for x in observations):
   observations.append({'slot':'companions','value':'friends','quote':original_span(mapping,t.idx,t.idx+len(t))['text']})
 if home and context=='social.house_gathering':observations.append({'slot':'venue','value':'friend_home','quote':original_span(mapping,home[0].idx,home[0].idx+len(home[0]))['text']})
 role='unspecified';role_span=None
 explicit=[t for t in free if t.lower_ in ('candidate','interviewer','presenter','attendee','guest','bride','groom','bridesmaid','groomsman','graduate')]
 if len({t.lower_ for t in explicit})>1:refuse('semantic_role_clarification')
 if explicit:role=explicit[0].lower_;role_span=[explicit[0].idx,explicit[0].idx+len(explicit[0])]
 if context=='none' and role!='unspecified':refuse('semantic_role_clarification')
 if context=='professional.job_interview':
  for t in ts('interview'):
   if t.pos_ in ('NOUN','PROPN'):
    nominal={t,*[c for c in t.children if c.dep_=='compound']}
    if any(x.dep_=='poss' and x.head in nominal and x.lower_ not in ('my','our') for x in t.subtree):refuse('semantic_role_clarification')
    host=next((x for x in t.ancestors if x.pos_=='VERB'),None)
    if host is not None and host.lemma_ not in ('recommend','suggest','pick','choose','need','want','find','give') and semantic_model._actor(t) is False:refuse('semantic_role_clarification')
   if t.pos_=='VERB':
    if semantic_model._actor(t) is not True:refuse('semantic_role_clarification')
    inferred='candidate' if any(c.dep_ in ('auxpass','nsubjpass') for c in t.children) else 'interviewer' if any(c.lemma_ in ('candidate','applicant') for c in t.children) else None
    if inferred:
     if role!='unspecified' and role!=inferred:refuse('semantic_role_clarification')
     role=inferred;role_span=[t.idx,t.idx+len(t)]
  if role not in ('candidate','interviewer') or not (lemmas&{'job','employment','applicant','candidate'}):refuse('semantic_role_clarification')
 if context=='academic.presentation':
  if not lemmas&{'university','uni','campus'}:refuse('semantic_clarification_required')
  if role=='unspecified':
   verbs=[t for t in free if t.lemma_ in ('present','give','attend') and semantic_model._actor(t) is True and any(x.lemma_=='presentation' for x in t.subtree)]
   if verbs:role='attendee' if verbs[0].lemma_=='attend' else 'presenter';role_span=[verbs[0].idx,verbs[0].idx+len(verbs[0])]
  if role not in ('presenter','attendee'):refuse('semantic_role_clarification')
 if context=='ceremony.wedding':
  if role not in ('unspecified','guest'):refuse('semantic_role_clarification')
  for t in ts('wedding','marry'):
   if t.lemma_=='marry' and semantic_model._actor(t) is not False or any(c.dep_=='poss' and c.lower_ in ('my','our','own') for c in t.children) or 'own' in words:refuse('semantic_role_clarification')
 for t in explicit:mark(t,'explicit_role')
 if role_span:coverage.append({'start':role_span[0],'end':role_span[1],'reason':'event_role'})
 formality=None;dress=None;appearance=[]
 for m in re.finditer(r'\b(?:smart casual|black tie|formal|casual)\b',text):
  if any(s['start']<=m.start() and m.end()<=s['end'] for s in coverage):continue
  tokens=[t for t in doc if m.start()<=t.idx<m.end()]
  # Adjective on a social event describes the approved event, not clothing.
  if all(t.head.lemma_ in ('outing','gathering') or t.lemma_=='casual' and t.pos_=='ADV' for t in tokens):continue
  prefix=text[max(0,m.start()-30):m.start()]
  if NEG.search(prefix):refuse('semantic_unsupported_requirement')
  value=m[0].replace(' ','_');field='dress_code' if 'dress code' in prefix else 'formality' if context!='none' else 'style'
  if field=='dress_code':
   if dress and dress!=value:refuse('semantic_clarification_required')
   dress=value
  else:
   if formality and formality!=value:refuse('semantic_clarification_required')
   formality=value
  appearance.append({'slot':field,'value':value,'start':m.start(),'end':m.end()});coverage.append({'start':m.start(),'end':m.end(),'reason':field})
 if context=='none' and formality and not words&{'outfit','clothes','clothing'}:refuse('semantic_clarification_required')
 if context=='none':
  # The B1-enabled predecessor treats neutral "formal/casual outfit" as an
  # all-present style requirement, not the contextual formality projection.
  # Keep that evidence and R-applicability contract in the direct compiler.
  gs=hard.to_dict()['groups'] if hard else []
  for item in appearance:
   if item['slot']!='style':continue
   cid=f'c{sum(len(g["conditions"]) for g in gs)+1:02d}'
   gs.append({'id':f'g{len(gs)+1:02d}','role':'all_selected','quantifier':'all_present',
              'conditions':[{'id':cid,'attribute':'style','operator':'contains_any','values':[item['value'].replace('_',' ')]}]})
   spans.append({'condition_id':cid,'source':'nlp','start':item['start'],'end':item['end'],'text':text[item['start']:item['end']]})
  hard=AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':gs}) if gs else None
 # Slot spans and event vocabulary are consumed in their grammatical scope.
 for obs in observations:
  for t in doc:
   if obs['quote'].casefold().find(t.text.casefold())>=0 and t.lemma_ in ('family','friend','colleague','classmate','hotel','office','restaurant','university','uni','campus','library','cinema','cafe','city','today','tonight','tomorrow','later'):mark(t,'context_'+obs['slot'])
 if context!='none':
  # Lexical inventory is reused from the registered ontology/Phase2P rules;
  # it can license event modifiers, never unconsumed clothing predicates.
  from . import context_language
  rules=json.loads(context_language.RESOURCE.read_text()) if hasattr(context_language,'RESOURCE') else {}
  vocabulary=set()
  for entry in rules.get('rules',[]):
   if entry.get('situation')==context:vocabulary.update(re.findall('[a-z]+',entry['pattern']+' '+entry['canonical']))
  examples=' '.join(situation.phrases)+' '+semantic_model.CONTEXTS[context]
  vocabulary.update(t.lemma_.lower() for t in syntax(examples))
  # Existing schema observations/facets have a bounded relational meaning.
  vocabulary.update({'study','revise','revision'} if context=='academic.library_study' else ())
  if context=='social.meal' and 'reunion' in lemmas:vocabulary.update({'reunion','college','university','class'})
  if context=='social.meal' and birthday:vocabulary.add('birthday')
  if context=='social.date' and 'dinner' in lemmas:vocabulary.add('dinner')
  if context=='everyday.shopping':vocabulary.update({'mall','thing','buy','purchase'})
  if context=='social.house_gathering':vocabulary.update({'house','place','home','gathering','friend','casual'})
  if context=='academic.presentation':vocabulary.update({'uni','university','presentation','presenter','attendee','present','give','attend'})
  if context=='professional.job_interview':vocabulary.update({'job','employment','applicant','candidate','interviewer','interview'})
  if context in ('professional.office_day','professional.workplace_meeting'):vocabulary.update({'work','workplace','business','office','colleague','meeting','meet','ordinary','day'})
  if context=='academic.group_study':vocabulary.update({'group','project','study','classmate','meeting'})
  if context=='everyday.casual_outing':vocabulary.update({'friend','pal','mate','buddy','casually','outing','out'})
  if context=='travel.journey':vocabulary.update({'train','bus','flight'})
  for t in free:
   reserved=any(x<=t.idx and t.idx+len(t)<=y for x,y,_,_ in descriptor_matches(text))
   event_adjective=t.lemma_=='casual' and t.head.lemma_ in ('outing','gathering')
   garment_modifier=t.dep_ in ('amod','compound') and t.head.lemma_ in ('outfit','clothes','clothing','garment') and not occupied(t)
   if garment_modifier:refuse('semantic_unaccounted_meaning')
   if t.lemma_.lower() in vocabulary and not NEG.fullmatch(t.lower_) and t.dep_!='neg' and not SOFT.fullmatch(t.lower_) and t.lower_ not in ('or','either') and (not reserved or event_adjective):mark(t,'grounded_event_lexeme')
  # A possessor/third-party event host is not an additional outfit condition.
  # Reuse the archived person vocabulary only in these dependency roles.
  from .semantic_frames import WORDS
  for t in free:
   if t.lemma_.lower() in WORDS and t.pos_=='NOUN' and (t.dep_=='poss' and t.head.lemma_ in vocabulary or t.dep_=='nsubj' and any(x.lemma_.lower() in vocabulary for x in t.head.subtree)):
    mark(t,'event_possessor_or_host')
  if dress:
   for t in free:
    if t.lemma_ in ('dress','code'):mark(t,'explicit_dress_code_marker')
 # Closed grammatical/speech words are scoped to a complete recognized intent.
 if coarse and (context!='none' or hard is not None or optional is not None or len(coarse)>1):refuse('semantic_modifier_scope')
 meaningful=any(u['kind']=='outfit_request' for u in units) or bool(coarse) or hard is not None or optional is not None or context!='none' or formality is not None
 speech={'need','want','wear','recommend','suggest','give','choose','pick','help','find','outfit','clothes','clothing','please','hey','hi','go','head','have','get','attend','visit','spend','plan','intend','watch','see','meet','take','be','do','will','can','could','would','should','for','tomorrow','today','tonight','later'}
 if context=='none':speech-= {'go','head','attend','visit','spend','plan','intend','watch','see','meet','take'}
 if not meaningful:
  meaningful=bool(words&{'outfit','clothes','clothing','wear'} and lemmas&{'recommend','suggest','give','need','want','pick','choose','wear'})
 if not meaningful:refuse('semantic_clarification_required')
 for t in doc:
  if occupied(t):continue
  if t.is_punct or t.is_space:mark(t,'punctuation');continue
  if t.lower_ in ('or','not','no','never','except','without') or t.dep_=='neg':refuse('semantic_unconsumed_operator')
  if t.lower_ in ('if','unless','whether','than','might','maybe','perhaps','possibly'):refuse('semantic_unsupported_requirement')
  if t.pos_ in ('DET','PRON','AUX','ADP','CCONJ','SCONJ','PART') and t.lower_ not in ('either','both','all','every','another','other','different'):mark(t,'grammatical_link');continue
  if t.lemma_.lower() in speech or t.lower_ in speech:mark(t,'speech_frame');continue
  refuse('semantic_unaccounted_meaning')
 facets=[]
 if context=='social.date' and 'dinner' in lemmas:facets.append('meal:dinner')
 if context=='social.meal' and birthday:facets.append('celebration:birthday')
 if context=='travel.journey':
  modes=lemmas&{'train','bus','flight'}
  if len(modes)>1:refuse('semantic_clarification_required')
  facets.extend('transport:'+m for m in sorted(modes))
 return {'normalization':mapping,'context':context,'event_spans':[[t.idx,t.idx+len(t)] for t in anchors],
         'role':role,'role_span':role_span,'observations':observations,'appearance':appearance,'facets':facets,
         'hard':hard.to_dict() if hard else None,'hard_spans':spans,'optional':optional,'coverage':sorted(coverage,key=lambda v:(v['start'],v['end'],v['reason'])),
         'secondary':['reunion'] if context=='social.meal' and 'reunion' in lemmas else [],'units':units,'coarse_categories':coarse,'requested_actions':actions}
