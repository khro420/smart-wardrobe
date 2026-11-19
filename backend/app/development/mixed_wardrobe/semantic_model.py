"""Extractive CPU NLP: pretrained NLI + dependency parsing; no generation/API."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,threading
from app.domain.value_objects.attribute_conditions import encode

ROOT=Path(__file__).resolve().parents[3]
ASSETS=ROOT/'models/semantic_nlp/nli'
MANIFEST=Path(__file__).with_name('semantic_model_manifest.json')
CONTEXTS={
 'ceremony.wedding':'Someone is getting married or attending a wedding.',
 'social.meal':'Someone is having dinner or eating a meal.',
 'social.date':'Someone is going on a romantic date.',
 'professional.job_interview':'Someone is participating in an employment interview.',
 'academic.presentation':'Someone is presenting or attending a presentation at university.',
 'everyday.academic_attendance':'Someone is going to uni, university classes or lectures.',
 'academic.library_study':'Someone is studying or revising in a library.',
 'academic.group_study':'People are studying together with classmates.',
 'everyday.shopping':'Someone is going shopping or going to buy some things.',
 'professional.office_day':'Someone is spending an ordinary day working at the office.',
 'professional.workplace_meeting':'Someone is attending a business meeting with colleagues.',
 'everyday.casual_outing':'Someone is hanging out casually with friends.',
 'social.birthday_gathering':'Someone is attending a birthday party.',
 'social.house_gathering':"Someone is visiting a friend's home.",
 'leisure.cinema_outing':'Someone is going to watch a movie at a cinema.',
 'social.cafe_meetup':'People are meeting at a cafe for coffee.',
 'leisure.city_sightseeing':'Someone is sightseeing and exploring the city.',
 'travel.journey':'Someone is travelling on a bus, train or flight.'}
LOCK=threading.RLock()
LOADED_FILES={}
GARMENTS={'shirt','top','trouser','trousers','pant','pants','jean','jeans','short','shorts','skirt','dress','jacket','blazer','coat','vest','sling','blouse','hoodie','sweater','cardigan'}

class ModelUnavailable(ValueError):pass

def _actor(token):
 for node in [token,*token.ancestors]:
  subjects=[c for c in node.children if c.dep_ in ('nsubj','nsubjpass')]
  if subjects:return any(c.lower_ in ('i','we') for c in subjects)
 return None

def _context_observations(doc,normalization):
 from app.application.nlp.natural_input_v1 import original_span
 people={'friend':'friends','friends':'friends','family':'family','colleague':'colleagues','classmate':'classmates'}
 venues={'hotel':'hotel','office':'office','restaurant':'restaurant','university':'university','uni':'university','campus':'university','library':'library','cinema':'cinema','cafe':'cafe','city':'city'}
 result=[]
 for token in doc:
  lemma=token.lemma_.lower();head=token.head
  if token.lower_ in ('today','tonight','tomorrow','later'):
   q=original_span(normalization,token.idx,token.idx+len(token))['text']
   entry={'slot':'temporal','value':token.lower_,'quote':q}
   if entry not in result:result.append(entry)
   continue
  companion=lemma in people and (head.lemma_=='with' and token.dep_=='pobj' or token.dep_ in ('dobj','obj') and head.lemma_=='meet')
  venue=lemma in venues and token.dep_=='pobj' and head.lemma_ in ('at','in','to','around')
  if not companion and not venue:continue
  slot,value=('companions',people[lemma]) if companion else ('venue',venues[lemma])
  start=min((x.idx for x in token.lefts if x.dep_=='det'),default=token.idx)
  q=original_span(normalization,start,token.idx+len(token))['text']
  entry={'slot':slot,'value':value,'quote':q}
  if entry not in result:result.append(entry)
 return result

def check_source_roles(raw,context,role):
 """Re-derive actor binding from source, never from a proposed role flag."""
 from app.application.nlp.compositional_input_v1 import normalize
 normalization=normalize(raw)
 with LOCK:
  ready();syntax,_,_=load();doc=syntax(normalization['normalized_text'])
 for token in doc:
  if token.lemma_=='marry' and _actor(token) is not False:raise ValueError('Own or ambiguous wedding role')
  if token.lower_=='wedding' and any(c.dep_=='poss' and c.lower_ in ('my','our') for c in token.children):raise ValueError('Own wedding role')
  if role in ('candidate','interviewer') and token.lemma_=='interview' and token.pos_=='VERB' and _actor(token) is False:raise ValueError('Other person interview role')
 return _context_observations(doc,normalization)

def identity():
 from app.shared_contracts.grammar_identity import canonical_bytes
 manifest=json.loads(MANIFEST.read_text())
 return {'version':'extractive-semantic-models-1.0.0','nli_model':manifest['model'],'nli_revision':manifest['revision'],
         'assets_sha256':hashlib.sha256(canonical_bytes(MANIFEST.read_bytes())).hexdigest(),'syntax_model':'en_core_web_sm-3.8.0','syntax_runtime':'spacy-3.8.18',
         'extractor_sha256':hashlib.sha256(canonical_bytes(Path(__file__).read_bytes())).hexdigest(),
         'ontology_sha256':hashlib.sha256(encode(CONTEXTS)).hexdigest(),'inference':'cpu-eval-dependency-focus-zero-shot-v1'}

@lru_cache(maxsize=1)
def load():
 try:
  manifest=json.loads(MANIFEST.read_text())
  for name,item in manifest['files'].items():
   p=ASSETS/name
   if not p.is_file() or p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
    raise ModelUnavailable('SemanticModelIntegrityFailure')
  import spacy,torch,importlib.metadata
  if importlib.metadata.version('spacy')!='3.8.18' or importlib.metadata.version('en-core-web-sm')!='3.8.0':raise ModelUnavailable('SemanticSyntaxVersionMismatch')
  base=spacy.util.get_package_path('en_core_web_sm')/'en_core_web_sm-3.8.0'
  for name,item in manifest['syntax']['files'].items():
   p=base/name
   if not p.is_file() or p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise ModelUnavailable('SemanticSyntaxIntegrityFailure')
  from transformers import AutoTokenizer,AutoModelForSequenceClassification
  syntax=spacy.load('en_core_web_sm')
  model=AutoModelForSequenceClassification.from_pretrained(ASSETS,local_files_only=True,trust_remote_code=False,use_safetensors=True).cpu().eval()
  tokenizer=AutoTokenizer.from_pretrained(ASSETS,local_files_only=True,trust_remote_code=False)
  for p in [*(ASSETS/n for n in manifest['files']),*(base/n for n in manifest['syntax']['files'])]:LOADED_FILES[p]=(p.stat().st_size,p.stat().st_mtime_ns)
  return syntax,tokenizer,model
 except (ImportError,OSError) as e:raise ModelUnavailable('SemanticModelUnavailable') from e

def ready():
 with LOCK:
  load()
  if any(not p.is_file() or (p.stat().st_size,p.stat().st_mtime_ns)!=v for p,v in LOADED_FILES.items()):raise ModelUnavailable('SemanticModelIntegrityFailure')
 return True

def _mode(token):
 chain=[token,*token.ancestors]
 for node in chain:
  if any(c.dep_=='neg' for c in node.children) or any(c.lower_ in ('no','neither') for c in node.children):return 'exclude'
  if node.lemma_.lower() in ('prefer','love','wish') or node.lemma_.lower()=='like' and any(c.lower_ in ('would',"'d") for c in node.children):return 'optional'
  if node.lemma_.lower() in ('want','need','give','wear','recommend','suggest'):break
 # Adverbial preferably modifies a noun/adjective rather than a verb.
 left=token.doc[max(token.sent.start,token.i-5):token.i]
 boundary=max((x.i for x in left if x.text in (',',';')),default=left.start-1)
 if any(x.lower_ in ('preferably','ideally') for x in left if x.i>boundary):return 'optional'
 return 'hard'

def propose(raw):
 if type(raw) is not str or not raw.strip() or len(raw)>500:raise ValueError('Invalid semantic input.')
 with LOCK:
  from app.application.nlp.compositional_input_v1 import normalize
  from app.application.nlp.natural_input_v1 import original_span
  normalization=normalize(raw)
  ready();syntax,tokenizer,model=load();doc=syntax(normalization['normalized_text'])
  def source(a,b):return original_span(normalization,a,b)
  conditions=[];ranges=[];normalized_ranges=[]
  for chunk in doc.noun_chunks:
   noun=chunk.root
   generic=noun.lemma_.lower() in ('one','anything','something') and (any(c.dep_ in ('amod','neg') for c in noun.children) or bool(conditions))
   if noun.lemma_.lower() not in GARMENTS and noun.lower_ not in GARMENTS and not generic:continue
   # Dependency modifiers, including same-head adjective OR, remain attached.
   selected={t.i for t in chunk}
   for child in noun.children:
    if child.dep_ in ('amod','compound','det','neg','relcl'):
     selected.update(t.i for t in child.subtree if t.pos_!='PUNCT')
   a,b=min(selected),max(selected)+1
   # A conjunction with a DIFFERENT garment belongs in its own clause.
   if any(doc[i].lemma_.lower() in GARMENTS for i in range(a,b) if i!=noun.i):a,b=chunk.start,chunk.end
   ns,ne=doc[a].idx,doc[b-1].idx+len(doc[b-1]);original=source(ns,ne);start,end=original['start'],original['end'];quote=original['text']
   if any(start<y and end>x for x,y in ranges):continue
   mode='exclude' if any(t.dep_=='neg' or t.lower_ in ('no','not','neither') for t in doc[a:b]) else _mode(noun)
   ranges.append((start,end));normalized_ranges.append((ns,ne));conditions.append({'quote':quote,'kind':mode})
  # Learned dependency heads separate a primary event from compound modifiers
  # (e.g. reunion type), possessions and clothing. Raw text is still validated
  # in full; none of those modifiers acquires permission by being omitted here.
  excluded={'amod','compound','poss','det','appos'}
  speech={'recommend','suggest','need','want','outfit','clothes','clothing','wear','give','help','find','choose','pick','throw','put'}
  focus=' '.join(t.text for t in doc if t.lemma_.lower() not in speech and (t.dep_ not in excluded or t.dep_=='compound' and t.head.pos_=='VERB') and not any(a<=t.idx and t.idx+len(t)<=b for a,b in normalized_ranges))
  scene=any(t.pos_ in ('NOUN','PROPN') and t.dep_ not in excluded and t.lemma_.lower() not in GARMENTS|{'outfit','clothes','clothing','thing','friend','buddy','afternoon','weekend','morning','evening','candidate','interviewer'} and not any(a<=t.idx and t.idx+len(t)<=b for a,b in normalized_ranges) for t in doc) or any(t.lemma_ in ('marry','shop','study','revise','interview','sightsee') for t in doc)
  import torch
  with torch.inference_mode():
   features=tokenizer([focus]*len(CONTEXTS),list(CONTEXTS.values()),padding=True,truncation=True,max_length=256,return_tensors='pt')
   logits=model(**features).logits
   index=int(logits[:,1].argmax())
  context=list(CONTEXTS)[index] if scene else 'none'
  role='unspecified';role_quote='';unsupported=[]
  for t in doc:
   if t.lower_ in ('candidate','interviewer','guest','bride','groom','bridesmaid','groomsman','presenter','attendee','graduate','employee','staff') and _actor(t) is not False:
    if role!='unspecified' and role!=t.lower_:unsupported.append('conflicting roles')
    role=t.lower_;role_quote=source(t.idx,t.idx+len(t))['text']
   if t.lemma_=='marry' and _actor(t) is not False:unsupported.append('wedding participant outside guest scope')
   if t.lower_=='wedding' and any(c.dep_=='poss' and c.lower_ in ('my','our') for c in t.children):unsupported.append('own wedding role not supported')
   if t.lemma_=='interview' and t.pos_=='VERB' and _actor(t) is True:
    passive=any(c.dep_ in ('auxpass','nsubjpass') for c in t.children)
    if passive:role='candidate';role_quote=source(min(c.idx for c in [t,*t.children] if c.dep_=='auxpass' or c==t),t.idx+len(t))['text']
    elif any(c.lemma_ in ('applicant','candidate') for c in t.children):role='interviewer';role_quote=source(t.idx,max(c.idx+len(c) for c in t.children))['text']
   if context=='academic.presentation' and _actor(t) is True and t.lemma_ in ('present','give','attend') and any(x.lemma_=='presentation' for x in t.subtree):
    role='attendee' if t.lemma_=='attend' else 'presenter';role_quote=source(t.idx,t.idx+len(t))['text']
  dress='unspecified';dress_quote='';formality='unspecified';formality_quote=''
  folded=raw.casefold()
  import re
  for m in re.finditer(r'\b(?:smart casual|black tie|formal|casual)\b',folded):
   if any(a<=m.start() and m.end()<=b for a,b in ranges):continue
   if 'dress code' in folded[max(0,m.start()-35):m.start()]:
    if dress!='unspecified' and dress!=m[0].replace(' ','_'):unsupported.append('conflicting formality')
    dress=m[0].replace(' ','_');dress_quote=raw[m.start():m.end()]
   else:
    if formality!='unspecified' and formality!=m[0].replace(' ','_'):unsupported.append('conflicting formality')
    formality=m[0].replace(' ','_');formality_quote=raw[m.start():m.end()]
  secondary=[source(chunk.start_char,chunk.end_char)['text'] for chunk in doc.noun_chunks if chunk.root.lemma_ not in GARMENTS and any(t.lemma_ in ('reunion','weekend','afternoon','morning','evening','friend','buddy') for t in chunk)][:3]
  slots={'context':context,'context_quote':raw if context!='none' else '', 'role':role,'role_quote':role_quote,'dress_code':dress,'dress_quote':dress_quote,
         'formality':formality,'formality_quote':formality_quote,'context_conditions':_context_observations(doc,normalization),'secondary':secondary,'conditions':conditions,'uncertain':False,'unsupported':unsupported}
  return {'version':'local-semantic-proposal-1.0.0','source_text':raw,'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'identity':identity(),'input_normalization':normalization,'slots':slots}
