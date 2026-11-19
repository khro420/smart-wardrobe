"""Own appearance goals become explicit recorded-style requirements, not facts."""
from . import semantic_unified_fragments as parent
from .semantic_requested_actions import bounds,subjects,objects,negative
legacy=parent.legacy

def goals(text,doc):
 result=[]
 for a,b,field,value in legacy.descriptor_matches(text):
  if field!='style':continue
  tokens=[t for t in doc if a<=t.idx and t.idx+len(t)<=b]
  if not tokens:continue
  # Canonical multi-token styles can be tagged as a nominal complement.
  # Follow only links within that exact matched style, or adjectival OR;
  # a garment object outside the style span cannot become an appearance fact.
  complements=[];indices={t.i for t in tokens}
  for token in tokens:
   node=token
   while node.head!=node and (node.dep_ in ('amod','compound') and node.head.i in indices or node.dep_=='conj' and node.head.pos_=='ADJ'):node=node.head
   if node.dep_ in ('acomp','oprd','attr','dobj','obj') and node.head.lemma_=='look' and node.head.pos_=='VERB':complements.append(node)
  if not complements:continue
  look=complements[0].head
  if any(n.head!=look for n in complements):legacy.refuse('semantic_modifier_scope')
  controller=look.head;start,end=bounds(text,look)
  if look.dep_!='xcomp' or not start<=controller.idx<end:continue
  if controller.lemma_=='prefer':legacy.refuse('semantic_optional_style_unavailable')
  if controller.lemma_ not in ('want','need','like'):continue
  actors=subjects(controller);aux=[t for t in controller.children if t.dep_ in ('aux','auxpass')]
  if len(actors)!=1 or actors[0].lower_ not in ('i','we') or subjects(look) or objects(controller):legacy.refuse('semantic_source_grounding')
  if controller.lemma_=='like' and (len(aux)!=1 or aux[0].lemma_!='would' or aux[0].dep_!='aux'):continue
  if controller.tag_=='VBD' or any(start<=v.idx<end and v.pos_=='VERB' for v in controller.ancestors):legacy.refuse('semantic_unsupported_requirement')
  if negative(look) or negative(controller):legacy.refuse('semantic_style_scope_unavailable')
  if not any(t.dep_=='aux' and t.lower_=='to' for t in look.children):continue
  if any(g['look_index']==look.i for g in result):legacy.refuse('semantic_style_scope_unavailable')
  result.append({'style':value,'style_span':[a,b],'look_index':look.i,'predicate_span':[look.idx,look.idx+len(look)],
   'controller_span':[controller.idx,controller.idx+len(controller)],'actor_span':[actors[0].idx,actors[0].idx+len(actors[0])],
   'binding':'own_positive_appearance_goal-1.0.0'})
 return result

def garments(text,doc):
 records=goals(text,doc);masked=list(text)
 for record in records:
  a,b=record['style_span'];masked[a:b]=' '*(b-a)
 hard,spans,optional,coverage,units,coarse=parent.garments(''.join(masked),doc)
 groups=hard.to_dict()['groups'] if hard else []
 for record in records:
  gid=f'g{len(groups)+1:02d}';cid=f'c{sum(len(g["conditions"]) for g in groups)+1:02d}';a,b=record['style_span']
  groups.append({'id':gid,'role':'all_selected','quantifier':'all_present','conditions':[{'id':cid,'attribute':'style','operator':'contains_any','values':[record['style']]}]})
  spans.append({'condition_id':cid,'source':'nlp','start':a,'end':b,'text':text[a:b]})
  for field,why in [('style_span','appearance_goal_style'),('predicate_span','appearance_goal_predicate'),('controller_span','appearance_goal_request')]:
   x,y=record[field];coverage.append({'start':x,'end':y,'reason':why})
  units.append({'start':a,'end':b,'kind':'appearance_goal','group_id':gid,**record})
 return legacy.AttributeConditions.from_dict({'version':'attribute-conditions-1.0.0','groups':groups}) if groups else None,spans,optional,coverage,units,coarse
