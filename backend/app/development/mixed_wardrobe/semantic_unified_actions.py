"""Versioned action binding, retaining strict purchase-command semantics."""
from .semantic_requested_actions import (TRANSACTIONS,ADVICE,GENERIC,CONTROLLERS,bounds,negative,subjects,objects,span,advice_frames,advice_activity,target_nodes,refuse,actor as previous_actor)

def departure_activity(token,text):
 if token.lower_!='shopping' or token.pos_!='NOUN' or token.dep_ not in ('npadvmod','advmod','punct'):return False
 host=token.head;people=subjects(host);a,b=bounds(text,token)
 if host.lemma_ not in ('head','go') or host.pos_!='VERB' or not a<=host.idx<b or negative(host):return False
 if len(people)!=1 or people[0].lower_ not in ('i','we'):return False
 # A nominal activity follows the particle of a self-departure predicate.
 # No actor, arbitrary preposition or unsupported modifier is discarded.
 return any(p.dep_=='prt' and p.i+1==token.i and p.head==host for p in host.children)

def actor(token,text):
 if departure_activity(token,text):
  return 'user',[span(subjects(token.head)[0])],[token,token.head]
 return previous_actor(token,text)

def analyze(doc,text):
 frames=advice_frames(doc);coverage=[];masks=[];records=[];shopping=[]
 chunks={c.root.i:c for c in doc.noun_chunks}
 def cover(a,b,reason,mask=False):
  coverage.append({'start':a,'end':b,'reason':reason})
  if mask:masks.append([a,b])
 transactions=[t for t in doc if t.lemma_ in TRANSACTIONS and t.pos_=='VERB' or t.lower_=='shopping' and t.pos_=='NOUN']
 for token in transactions:
  neg=negative(token);advice=advice_activity(token,frames)
  who,actor_spans,chain=actor(token,text)
  if advice is not None:who='outfit_activity'
  # The registered shopping-trip event is a nominal occasion. A shopping
  # bag/assistant modifier is not evidence of an activity.
  if token.pos_=='NOUN' and not departure_activity(token,text) and token.dep_ not in ('ROOT','pobj','dobj','pcomp','xcomp','advcl') and not (token.dep_=='compound' and token.head.lemma_=='trip'):
   refuse('semantic_requested_action_unresolved')
  if neg:
   if len(neg)!=1 or who!='assistant' or not frames:refuse('semantic_requested_action_unresolved')
   kind='excluded_assistant_action'
  elif who in ('user','outfit_activity','context_name'):
   kind='user_shopping_activity'
  elif who=='assistant':refuse('semantic_unsupported_requested_action')
  else:refuse('semantic_requested_action_unresolved')
  targets=[]
  for obj in target_nodes(token):
   chunk=chunks.get(obj.i);a,b=(chunk.start_char,chunk.end_char) if chunk else tuple(span(obj))
   # Retain only a nominal argument. Relative/conditional predicates remain
   # outside this span and must independently pass complete source coverage.
   if any(t.pos_=='VERB' and t.dep_ not in ('amod','compound') for t in doc if a<=t.idx<b):refuse('semantic_requested_action_unresolved')
   targets.append({'span':[a,b],'text':text[a:b],'role':'purchase_target_not_wardrobe_requirement'})
   cover(a,b,'purchase_activity_target',True)
  if token.lemma_ in ('buy','purchase','order') and not targets:refuse('semantic_requested_action_unresolved')
  oblique=[]
  if token.lemma_!='shop':
   # A purpose PP may modify the transaction or its nominal product object.
   for head in [token,*target_nodes(token)]:
    for prep in head.children:
     if prep.dep_!='prep' or prep.lemma_!='for':continue
     for obj in prep.children:
      if obj.dep_!='pobj':continue
      chunk=chunks.get(obj.i);a,b=(chunk.start_char,chunk.end_char) if chunk else tuple(span(obj))
      oblique.append({'span':[a,b],'text':text[a:b],'head_span':span(head),'role':'purpose_or_beneficiary_not_purchase_object'})
      # An excluded action's purpose is not a positive outfit occasion.
      # A positive purchase's purpose remains visible to context validation.
      if kind=='excluded_assistant_action':cover(a,b,'excluded_action_argument',True)
  record={'predicate':token.lemma_,'verb_span':span(token),'actor':who,'actor_spans':actor_spans,'kind':kind,'targets':targets,
          'oblique_arguments':oblique,
          'negation_spans':[span(t) for t in neg],'clause_span':list(bounds(text,token)),
          'binding':'source_dependency_action_occasion_v1','interpretation':'explicit_outfit_activity' if advice else 'outfit_assistant_context_declaration' if kind=='user_shopping_activity' else 'excluded_transaction_not_clothing'}
  if kind=='excluded_assistant_action':
   cover(*span(token),'excluded_assistant_transaction',True)
   for t in neg:cover(*span(t),'excluded_action_negation',True)
  else:
   shopping.append(token.i)
   # A departure predicate with an explicit self subject is an event carrier,
   # not a new outfit requirement (the existing language resource admits off).
   for node in chain:
    if node.lemma_=='off' and subjects(node):cover(*span(node),'shopping_departure_carrier')
    # In a copular departure, spaCy makes `off` a sibling of the purpose
    # infinitive, not its ancestor. License that modifier only on the same
    # positive self-subject governor and with an explicit destination PP.
    # Other modifiers and destination meanings still need source coverage.
    if who=='user' and node.lemma_=='be' and not negative(node) and token.head==node and token.dep_ in ('advcl','xcomp') and any(c.dep_=='aux' and c.lower_=='to' for c in token.children):
     for child in node.children:
      if child.lemma_=='off' and child.dep_=='advmod' and any(p.dep_=='prep' and p.lemma_ in ('to','for') and any(o.dep_=='pobj' for o in p.children) for p in child.children):
       cover(*span(child),'shopping_departure_carrier')
  if departure_activity(token,text):
   for particle in token.head.children:
    if particle.dep_=='prt':cover(*span(particle),'self_departure_particle')
  records.append(record)
 if records:
  # Never resolve a purchased-item pronoun into a real wardrobe garment.
  if any(t.lemma_=='wear' and any(o.lower_ in ('it','them','those') for o in objects(t)) for t in doc):refuse('semantic_requested_action_unresolved')
  for frame in frames:
   for child in frame.children:
    if child.dep_=='advmod' and child.lower_=='just':cover(*span(child),'outfit_advice_focus')
    if child.dep_=='advmod' and child.lower_=='instead' and any(r['kind']=='excluded_assistant_action' for r in records):cover(*span(child),'action_contrast')
 return {'version':'source-requested-actions-1.1.0','actions':records,'shopping_tokens':shopping,'coverage':coverage,'mask_spans':masks,
         'outfit_advice_spans':[span(t) for t in frames]}
