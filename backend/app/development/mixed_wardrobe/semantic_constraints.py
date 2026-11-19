"""Preserve explicit hard shirt nouns without changing archived interpretation.

Category is a same-member predicate, never inferred from garment names/images.
The frozen semantic interpreter still owns extraction, coverage and polarity.
"""
from pathlib import Path
import re
from . import semantic_frames as previous
from .semantic_constraint_contract import GRAMMAR
from app.domain.value_objects.attribute_conditions import AttributeConditions,digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.application.nlp.natural_input_v1 import original_span
from app.domain.value_objects.request_local_preference import resolution_for

SHIRT_CATEGORIES=('long_sleeve_top','short_sleeve_top')

def identity():
 from app.shared_contracts.grammar_identity import semantic_fingerprint
 from .semantic_constraint_contract import GRAMMAR_SHA256
 actual=semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(previous.identity()),Path(__file__).read_bytes()))
 if actual!=GRAMMAR_SHA256:raise ValueError('Unregistered semantic noun-preservation contract.')
 return actual

def document(raw,proposal):
 grammar=identity();value=previous.document(raw,proposal)
 hard=value['hard_intent'];groups=hard['conditions']['groups'] if hard else []
 spans=list(hard['spans']) if hard else [];mapping=value['normalization'];text=mapping['normalized_text']
 counter=max((int(c['id'][1:]) for g in groups for c in g['conditions']),default=0)
 additions=[]
 for clause in proposal['slots']['conditions']:
  if clause['kind']=='optional' or not re.search(r'\bshirts?\b',clause['quote'],re.I):continue
  a,b=previous.span(raw,clause['quote'])
  nouns=[]
  for m in re.finditer(r'\bshirt\b',text):
   source=original_span(mapping,m.start(),m.end())
   if a<=source['start'] and source['end']<=b:nouns.append((m,source))
  if len(nouns)!=1:previous.refuse('semantic_modifier_scope')
  noun,source=nouns[0];quantifier='none' if clause['kind']=='exclude' else 'exists'
  candidates=[]
  for group in groups:
   ids={c['id'] for c in group['conditions']}
   sources=[original_span(mapping,s['start'],s['end']) for s in spans if s['condition_id'] in ids]
   if group['role']=='upper' and group['quantifier']==quantifier and sources and all(a<=s['start'] and s['end']<=b for s in sources):candidates.append(group)
  if not candidates and not groups and hard is None and quantifier=='exists':
   group={'id':'g01','role':'upper','quantifier':'exists','conditions':[]};groups.append(group);candidates=[group]
  if len(candidates)!=1:previous.refuse('semantic_modifier_scope')
  group=candidates[0];counter+=1;cid=f'c{counter:02d}'
  group['conditions'].append({'id':cid,'attribute':'category','operator':'in','values':list(SHIRT_CATEGORIES)})
  spans.append({'condition_id':cid,'source':'nlp','start':noun.start(),'end':noun.end(),'text':noun[0]})
  additions.append({'group_id':group['id'],'condition_id':cid,'categories':list(SHIRT_CATEGORIES),'original_span':source})
 if groups:
  from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
  policy=hard['policy_sha256'] if hard else AttributeEvidencePolicy.load().sha256
  bound=AttributeIntent.capture(text,None,AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':groups}),spans,grammar,policy)
  value['hard_intent']=bound.to_dict()
  value['original_hard_spans']=[{**s,**original_span(mapping,s['start'],s['end'])} for s in spans]
  if value['optional']:
   wish=value['optional'];wish['resolution']=resolution_for(bound,wish['role'],wish['binding'],wish['predicates'])
 value.update(version=GRAMMAR,grammar_version=GRAMMAR,grammar_sha256=grammar)
 value['semantic_metadata']['noun_constraints']=additions
 value.pop('revision');value['revision']=digest(value)
 return value
