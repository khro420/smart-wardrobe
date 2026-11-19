"""Source actions precede garment compilation; activities are not instructions.

Only the closed transaction family and explicit outfit-advice relations are
recognized. Objects of a planned purchase are retained as activity arguments,
never silently turned into facts about garments in the existing wardrobe.
"""
import re
from app.application.nlp.compositional_request_v1 import NOUNS
from .semantic_frames import refuse

TRANSACTIONS={'buy','purchase','order','shop'}
ADVICE={'recommend','suggest','give','choose','pick','need','want','find'}
GENERIC={'outfit','clothes','clothing'}
CONTROLLERS={'go','head','plan','intend','want','need','be','off','wear'}

def bounds(text,token):
 cuts=list(re.finditer(r'[,;.!?]|\b(?:and|but|then)\b',text))
 return max((m.end() for m in cuts if m.end()<=token.idx),default=0),min((m.start() for m in cuts if m.start()>token.idx),default=len(text))

def negative(token):return [c for c in token.children if c.dep_=='neg' or c.lower_ in ('never','no')]
def subjects(token):
 # A parser may attach the participant to an auxiliary (e.g. going),
 # rather than the lexical predicate. Traverse only that auxiliary spine;
 # subjects of objects, complements and purpose clauses are never borrowed.
 result=[];pending=[token];seen=set()
 while pending:
  node=pending.pop()
  if node.i in seen:continue
  seen.add(node.i)
  result.extend(c for c in node.children if c.dep_ in ('nsubj','nsubjpass','csubj'))
  pending.extend(c for c in node.children if c.dep_ in ('aux','auxpass') and c.pos_=='AUX')
 return result
def objects(token):return [c for c in token.children if c.dep_ in ('dobj','obj')]
def span(token):return [token.idx,token.idx+len(token)]

def advice_frames(doc):
 result=[]
 for t in doc:
  if t.pos_!='VERB' or negative(t):continue
  if t.lemma_ in ADVICE and any(o.lemma_ in GENERIC or o.lower_ in GENERIC or o.lower_ in NOUNS for o in objects(t)):
   result.append(t)
  elif t.lemma_=='wear' and any(c.lower_ in ('i','we') for c in subjects(t)) and any(o.lower_ in ('what','which') or any(c.lower_ in ('what','which') for c in o.children) for o in objects(t)):
   result.append(t)
 return result

def advice_activity(token,frames):
 """A for-activity adjunct to wardrobe advice, not a product-goal infinitive."""
 for node in token.ancestors:
  if node.pos_=='ADP' and node.lemma_=='for':
   head=node.head
   if head in frames:return head
   if (head.lemma_ in GENERIC or head.lower_ in GENERIC or head.lower_ in NOUNS) and head.head in frames and head.dep_ in ('dobj','obj'):return head.head
  if node.pos_=='VERB':break
 return None

def actor(token,text):
 a,b=bounds(text,token);chain=[]
 for node in [token,*token.ancestors]:
  if not a<=node.idx<b:break
  chain.append(node)
  shopping_purpose=node.lemma_=='shop' and token.head==node and token.dep_ in ('advcl','xcomp') and any(c.dep_=='aux' and c.lower_=='to' for c in token.children)
  if node!=token and node.pos_=='VERB' and node.lemma_ not in CONTROLLERS and not shopping_purpose:return 'unresolved',[],chain
  # Need/want a product to buy is not a plan to perform an outing.
  if node!=token and node.lemma_ in ('need','want') and objects(node):return 'product_goal',[],chain
  ss=subjects(node)
  if ss:
   if len(ss)!=1:return 'unresolved',[],chain
   who='user' if ss[0].lower_ in ('i','we') else 'assistant' if ss[0].lower_=='you' else 'other'
   return who,[span(ss[0])],chain
  if node.head==node:break
 # No actor on an independent finite predicate denotes an imperative.
 if token.pos_=='VERB' and not any(a<=n.idx<b and n.pos_=='VERB' for n in token.ancestors):return 'assistant',[],chain
 if token.lower_=='shopping' and token.pos_=='NOUN' and (token.dep_=='ROOT' or token.dep_=='compound' and token.head.lemma_=='trip' and token.head.dep_=='ROOT'):return 'context_name',[],chain
 return 'unresolved',[],chain

def target_nodes(verb):
 nodes=list(objects(verb))
 if verb.lemma_=='shop':
  for child in verb.children:
   if child.dep_=='prep' and child.lemma_=='for':nodes.extend(t for t in child.children if t.dep_=='pobj')
 result=[];queue=list(nodes)
 while queue:
  t=queue.pop(0)
  if t in result:continue
  result.append(t)
  queue.extend(c for c in t.children if c.dep_=='conj' and c.pos_ in ('NOUN','PROPN','PRON'))
 return result

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
  if token.pos_=='NOUN' and token.dep_ not in ('ROOT','pobj','dobj','pcomp','xcomp','advcl') and not (token.dep_=='compound' and token.head.lemma_=='trip'):
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
  records.append(record)
 if records:
  # Never resolve a purchased-item pronoun into a real wardrobe garment.
  if any(t.lemma_=='wear' and any(o.lower_ in ('it','them','those') for o in objects(t)) for t in doc):refuse('semantic_requested_action_unresolved')
  for frame in frames:
   for child in frame.children:
    if child.dep_=='advmod' and child.lower_=='just':cover(*span(child),'outfit_advice_focus')
    if child.dep_=='advmod' and child.lower_=='instead' and any(r['kind']=='excluded_assistant_action' for r in records):cover(*span(child),'action_contrast')
 return {'version':'source-requested-actions-1.0.0','actions':records,'shopping_tokens':shopping,'coverage':coverage,'mask_spans':masks,
         'outfit_advice_spans':[span(t) for t in frames]}
