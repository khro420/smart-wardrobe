"""Dependency-scoped optional suffixes over the frozen model/compiler.

No new surface vocabulary, score rule, evidence qualification or model asset.
Original model slots and every source projection are retained and reconstructed.
"""
from pathlib import Path
import copy,hashlib,re
from . import semantic_model,semantic_constraints as prior,semantic_frames
from .semantic_reliability_contract import GRAMMAR
from app.application.nlp.compositional_input_v1 import normalize
from app.application.nlp.compositional_request_v1 import CompositionalIntent
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.attribute_conditions import AttributeRequestError,AttributeConditions,encode,digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.garment_description_evidence import CANONICAL_ENUMS

PROPOSAL='source-scoped-semantic-proposal-1.0.0'
FIELDS={'version','source_text','source_sha256','identity','input_normalization','base_slots','slots','scope_changes','context_projection'}

def identity():
 from app.shared_contracts.grammar_identity import semantic_fingerprint
 from .semantic_reliability_contract import GRAMMAR_SHA256
 actual=semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(prior.identity()),Path(__file__).read_bytes()))
 if actual!=GRAMMAR_SHA256:raise ValueError('Unregistered semantic scope projection.')
 return actual

def model_identity():
 from app.shared_contracts.grammar_identity import canonical_bytes
 return {'models':semantic_model.identity(),'scope_projection':'source-scope-and-context-focus-1.0.0','projector_sha256':hashlib.sha256(canonical_bytes(Path(__file__).read_bytes())).hexdigest()}

def project(raw,slots):
 """Only a complete source suffix can be attached to a proven hard anchor."""
 if type(slots) is not dict or type(slots.get('conditions')) is not list or len(slots['conditions'])>8:
  semantic_frames.refuse('semantic_invalid_output')
 result=copy.deepcopy(slots);conditions=result['conditions'];changes=[]
 for c in conditions:
  if type(c) is not dict or set(c)!={'quote','kind'} or c['kind'] not in ('hard','optional','exclude'):semantic_frames.refuse('semantic_invalid_output')
  semantic_frames.span(raw,c['quote'])
 if any(c['kind']=='optional' for c in conditions):return result,changes
 normalization=normalize(raw)
 with semantic_model.LOCK:
  semantic_model.ready();syntax,_,_=semantic_model.load();doc=syntax(normalization['normalized_text'])
 markers=[t for t in doc if t.lower_=='preferably' and t.pos_=='ADV']
 if len(markers)!=1:return result,changes
 marker=markers[0]
 after=[t for t in doc if t.i>marker.i and not t.is_punct and not t.is_space]
 # A lone canonical colour is an existing bounded anaphor, never material,
 # OR, a comparative modifier or a newly invented garment requirement.
 if len(after)!=1 or after[0].lower_ not in CANONICAL_ENUMS['primary_colour']:return result,changes
 colour=after[0]
 # Colour is a closed schema value. A tagger may call e.g. "grey" a verb;
 # that tag cannot change the meaning of an otherwise complete colour suffix.
 if marker.dep_ not in ('advmod','amod'):return result,changes
 suffix=original_span(normalization,marker.idx,colour.idx+len(colour))
 start=suffix['start'];candidate=[]
 for c in conditions:
  a,b=semantic_frames.span(raw,c['quote'])
  if a<start<b:
   if c['kind']!='hard':return copy.deepcopy(slots),[]
   prefix=raw[a:start].rstrip(' \t\r\n,;')
   if not prefix:return copy.deepcopy(slots),[]
   changes.append({'rule':'detach_optional_suffix','before':c['quote'],'after':prefix,'original_start':a,'original_end':a+len(prefix)})
   c['quote']=prefix;b=a+len(prefix)
  if b<=start and c['kind']=='hard':candidate.append((a,c))
 if not candidate:return copy.deepcopy(slots),[]
 anchor=max(candidate,key=lambda x:x[0])[1]
 try:parsed=CompositionalIntent.capture('I need '+anchor['quote']).to_dict()
 except AttributeRequestError:return copy.deepcopy(slots),[]
 groups=parsed['hard_intent']['conditions']['groups'] if parsed['hard_intent'] else []
 if parsed['optional'] or len(groups)!=1 or groups[0]['role'] not in ('upper','lower') or groups[0]['quantifier']!='exists':return copy.deepcopy(slots),[]
 conditions.append({'quote':suffix['text'],'kind':'optional'})
 changes.append({'rule':'source_colour_anaphor','original_span':suffix,'anchor_quote':anchor['quote'],'anchor_role':groups[0]['role']})
 return result,changes

def context_focus(raw,slots):
 """Mask exact garment phrases; retain modifiers, syntax and negation."""
 normalization=normalize(raw);text=normalization['normalized_text'];mapping=normalization['character_map']
 ranges=[semantic_frames.span(raw,c['quote']) for c in slots['conditions']]
 return ' '.join(''.join(' ' if any(a<=x and y<=b for a,b in ranges) else char for char,(x,y) in zip(text,mapping)).split())

def predict_context(focus):
 with semantic_model.LOCK:
  semantic_model.ready();_,tokenizer,model=semantic_model.load()
  import torch
  with torch.inference_mode():
   features=tokenizer([focus]*len(semantic_model.CONTEXTS),list(semantic_model.CONTEXTS.values()),padding=True,truncation=True,max_length=256,return_tensors='pt')
   index=int(model(**features).logits[:,1].argmax())
 return list(semantic_model.CONTEXTS)[index]

def contextual_slots(raw,base,slots,record):
 """History rechecks source focus and frozen label, not a new classification.

The signed record owns its model result; initial writes independently repeat
classification under the write lock. Existing deterministic source guards still
validate the projected context against the entire unchanged original request.
"""
 slots=copy.deepcopy(slots)
 if base['context']=='none':
  if record is not None:semantic_frames.refuse('semantic_source_grounding')
  return slots
 if type(record) is not dict or set(record)!={'version','focus','base_context','prediction'} or record['version']!='retain-context-modifiers-1.0.0' or record['base_context']!=base['context'] or record['focus']!=context_focus(raw,slots) or record['prediction'] not in semantic_model.CONTEXTS:
  semantic_frames.refuse('semantic_source_grounding')
 slots.update(context=record['prediction'],context_quote=raw)
 return slots

def propose(raw):
 base=semantic_model.propose(raw);slots,changes=project(raw,base['slots'])
 context=None
 if base['slots']['context']!='none':
  focus=context_focus(raw,slots)
  context={'version':'retain-context-modifiers-1.0.0','focus':focus,'base_context':base['slots']['context'],'prediction':predict_context(focus)}
 slots=contextual_slots(raw,base['slots'],slots,context)
 return {'version':PROPOSAL,'source_text':raw,'source_sha256':base['source_sha256'],'identity':model_identity(),'input_normalization':base['input_normalization'],
         'base_slots':base['slots'],'slots':slots,'scope_changes':changes,'context_projection':context}

def document(raw,proposal):
 grammar=identity()
 if type(proposal) is not dict or set(proposal)!=FIELDS or len(encode(proposal))>65536:semantic_frames.refuse('semantic_invalid_output')
 if proposal['version']!=PROPOSAL or proposal['source_text']!=raw or proposal['source_sha256']!=hashlib.sha256(raw.encode()).hexdigest() or proposal['identity']!=model_identity() or proposal['input_normalization']!=normalize(raw):semantic_frames.refuse('semantic_source_grounding')
 slots,changes=project(raw,proposal['base_slots'])
 slots=contextual_slots(raw,proposal['base_slots'],slots,proposal['context_projection'])
 if slots!=proposal['slots'] or changes!=proposal['scope_changes']:semantic_frames.refuse('semantic_source_grounding')
 base={'version':'local-semantic-proposal-1.0.0','source_text':raw,'source_sha256':proposal['source_sha256'],'identity':semantic_model.identity(),'input_normalization':proposal['input_normalization'],'slots':slots}
 value=prior.document(raw,base)
 hard=value['hard_intent']
 if hard:
  value['hard_intent']=AttributeIntent.capture(hard['original_text'],None,AttributeConditions.from_dict(hard['conditions']),hard['spans'],grammar,hard['policy_sha256']).to_dict()
 value.update(version=GRAMMAR,grammar_version=GRAMMAR,grammar_sha256=grammar,semantic_proposal=copy.deepcopy(proposal))
 value['semantic_metadata']['scope_projection']=copy.deepcopy(changes)
 value.pop('revision');value['revision']=digest(value)
 return value
