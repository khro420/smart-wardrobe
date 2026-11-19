"""Source-bound outfit-wide facts and request frames; no wardrobe inference."""
from . import semantic_typed_source as legacy
from .semantic_requested_actions import bounds,subjects,objects,negative

OUTFITS={'outfit','clothes','clothing'}
GENERIC=OUTFITS|{'something'}

def head_for(doc,a,b):
 tokens=[t for t in doc if a<=t.idx and t.idx+len(t)<=b]
 for token in reversed(tokens):
  node=token
  for _ in range(5):
   if node.lower_ in GENERIC or node.lower_ in legacy.NOUNS:return node
   if node.dep_ in ('amod','compound','conj') and node.head!=node:node=node.head;continue
   if node.dep_=='pobj' and node.head.lemma_=='with':node=node.head.head;continue
   break
 return None

def garments(text,doc):
 additions=[];extra=[];masks=[];units=[]
 # Comparative `like` is not the positive modal request predicate. These
 # relations require similarity state which this contract does not provide.
 if any(t.lemma_=='like' and t.pos_ in ('ADP','SCONJ') or t.pos_=='ADJ' and sum(c.lower_=='as' for c in t.children)>1 for t in doc):legacy.refuse('semantic_unsupported_requirement')
 matches=legacy.descriptor_matches(text)
 def cover(a,b,why):extra.append({'start':a,'end':b,'reason':why})
 for a,b,field,value in matches:
  if field not in ('style','sleeve_length'):continue
  head=head_for(doc,a,b)
  if head is None:
   if field=='sleeve_length':legacy.refuse('semantic_sleeve_target_clarification')
   continue
  outfit_style=field=='style' and head.lower_ in GENERIC
  generic_sleeve=field=='sleeve_length' and head.lower_=='something'
  if not outfit_style and not generic_sleeve:continue
  start,end=bounds(text,head);body=text[start:end]
  if legacy.SOFT.search(body):legacy.refuse('semantic_optional_style_unavailable' if outfit_style else 'unsupported_compositional_preference')
  if legacy.NEG.search(body):legacy.refuse('semantic_style_scope_unavailable' if outfit_style else 'semantic_sleeve_target_clarification')
  if any(g['head']==head.i and g['field']==field for g in additions):legacy.refuse('semantic_style_scope_unavailable' if outfit_style else 'semantic_modifier_scope')
  additions.append({'head':head.i,'field':field,'value':value,'span':[a,b],'role':'all_selected','quantifier':'all_present' if outfit_style else 'exists'})
  masks.append((a,b));cover(a,b,'explicit_outfit_style' if outfit_style else 'explicit_generic_sleeve')
  cover(head.idx,head.idx+len(head),'explicit_attribute_target')
 masked=list(text)
 for a,b in masks:masked[a:b]=' '*(b-a)
 hard,spans,optional,coverage,old_units,coarse=legacy.garments(''.join(masked),doc)
 gs=hard.to_dict()['groups'] if hard else []
 for item in additions:
  gid=f'g{len(gs)+1:02d}';cid=f'c{sum(len(g["conditions"]) for g in gs)+1:02d}';a,b=item['span']
  condition={'id':cid,'attribute':item['field'],'operator':'contains_any' if item['field']=='style' else 'in','values':[item['value']]}
  gs.append({'id':gid,'role':item['role'],'quantifier':item['quantifier'],'conditions':[condition]})
  spans.append({'condition_id':cid,'source':'nlp','start':a,'end':b,'text':text[a:b]})
  units.append({'start':a,'end':b,'kind':'outfit_style' if item['field']=='style' else 'generic_sleeve','group_id':gid,'target_span':[doc[item['head']].idx,doc[item['head']].idx+len(doc[item['head']])]})
 hard=legacy.AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':gs}) if gs else None
 combined=coverage+extra
 # Request predicates are licensed by grammatical roles, never by adding
 # an unconstrained speech-word whitelist. Every other modifier stays visible.
 for verb in doc:
  if verb.lemma_ not in ('show','like') or verb.pos_!='VERB' or negative(verb) or verb.dep_ not in ('ROOT','conj'):continue
  a,b=bounds(text,verb)
  if any(a<=v.idx<b and v.pos_=='VERB' for v in verb.ancestors):continue
  actors=subjects(verb);aux=[c for c in verb.children if c.dep_ in ('aux','auxpass')]
  targets=[c for c in objects(verb) if c.lower_ in GENERIC or c.lower_ in legacy.NOUNS]
  if len(targets)!=1:continue
  if verb.lemma_=='like':
   if len(actors)!=1 or actors[0].lower_ not in ('i','we') or len(aux)!=1 or aux[0].lemma_!='would' or aux[0].dep_!='aux':continue
  else:
   if actors and (len(actors)!=1 or actors[0].lower_!='you'):continue
   if any(c.dep_=='auxpass' or c.lemma_ not in ('can','could','would','do') for c in aux):continue
   recipients=[c for c in verb.children if c.dep_ in ('dative','iobj')]
   if any(c.lower_ not in ('me','us') for c in recipients):continue
  target=targets[0]
  bound=any(c['start']<=target.idx and target.idx+len(target)<=c['end'] for c in combined)
  if not bound and target.lower_ not in OUTFITS:continue
  cover(verb.idx,verb.idx+len(verb),'validated_outfit_request_frame')
  cover(target.idx,target.idx+len(target),'outfit_request_target')
  units.append({'start':verb.idx,'end':target.idx+len(target),'kind':'outfit_request','predicate':verb.lemma_,'target_span':[target.idx,target.idx+len(target)]})
 return hard,spans,optional,coverage+extra,old_units+units,coarse
