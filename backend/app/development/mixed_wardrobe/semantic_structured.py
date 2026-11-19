"""Source-grounded MiniLM selection and direct typed request compilation.

History re-derives the complete deterministic source graph and verifies a frozen
model decision, rather than rerunning a classifier or reparsing generated prose.
The writer separately repeats model inference under its existing write lock.
"""
from pathlib import Path
from dataclasses import replace
import copy,hashlib,json
from . import semantic_model,semantic_typed_source as source
from .semantic_frames import refuse
from .semantic_structured_contract import GRAMMAR
from app.domain.value_objects.attribute_conditions import AttributeConditions,encode,digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.general_context_request import GeneralContext,GeneralContextRequest,ContextSlot,SourceSpan
from app.domain.value_objects.request_local_preference import resolution_for
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.nlp.natural_input_v1 import original_span

PROPOSAL='typed-source-semantic-proposal-1.0.0'
FIELDS={'version','source_text','source_sha256','identity','analysis','selection','slots'}

def fingerprint():
 from app.shared_contracts.grammar_identity import semantic_fingerprint
 from .semantic_constraints import identity as parent
 from . import context_language,semantic_requested_actions
 from app.application.recommendation.context_bundle import ContextBundle
 p,_,_=source.resources()
 lexicon=encode({'descriptors':[(r.pattern,r.flags,f,v) for r,f,v in p.descriptors],
                 'noun_descriptors':p.language['noun_descriptors'],'nouns':source.NOUNS,
                 'canonical_enums':source.CANONICAL_ENUMS,'context_bundle':ContextBundle.load('context_18_v1').record})
 return semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(parent()),Path(__file__).read_bytes(),Path(source.__file__).read_bytes(),Path(semantic_requested_actions.__file__).read_bytes(),context_language.RESOURCE.read_bytes(),lexicon))

def identity():
 from .semantic_structured_contract import GRAMMAR_SHA256
 actual=fingerprint()
 if actual!=GRAMMAR_SHA256:raise ValueError('Unregistered typed semantic compiler.')
 return actual

def model_identity():
 return {'models':semantic_model.identity(),'compiler_sha256':identity(),'selection':'dependency-grounded-nli-1.0.0'}

def select(analysis):
 """The NLI model cannot invent a context without a complete source witness.

This revision refuses incompatible event heads before classification. A single
grounded policy is compared with the model ontology for diagnostic attribution;
unsupported/unresolved source events are never forced to the nearest label.
"""
 context=analysis['context'];text=analysis['normalization']['normalized_text']
 if context=='none':return {'grounded_candidates':[],'prediction':'none','unrestricted_prediction':None}
 with semantic_model.LOCK:
  semantic_model.ready();_,tokenizer,model=semantic_model.load()
  import torch
  with torch.inference_mode():
   features=tokenizer([text]*len(semantic_model.CONTEXTS),list(semantic_model.CONTEXTS.values()),padding=True,truncation=True,max_length=256,return_tensors='pt')
   logits=model(**features).logits[:,1]
   raw=list(semantic_model.CONTEXTS)[int(logits.argmax())]
 return {'grounded_candidates':[context],'prediction':context,'unrestricted_prediction':raw}

def propose(raw):
 analysis=source.analyze(raw);selection=select(analysis)
 return {'version':PROPOSAL,'source_text':raw,'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'identity':model_identity(),
         'analysis':analysis,'selection':selection,'slots':{'context':selection['prediction']}}

def compile_graph(raw,a,proposal):
 grammar=identity();mapping=a['normalization'];text=mapping['normalized_text'];context=a['context']
 hard=AttributeIntent.capture(text,None,AttributeConditions.from_dict(a['hard']),a['hard_spans'],grammar,AttributeEvidencePolicy.load().sha256) if a['hard'] else None
 optional=copy.deepcopy(a['optional'])
 if optional:
  positives=[g for g in a['hard']['groups'] if g['role']==optional['role'] and g['quantifier']=='exists'] if a['hard'] else []
  if optional['binding']['kind']=='explicit_role' and len(positives)==1:optional['binding']={'kind':'mandatory_group','group_id':positives[0]['id']}
  optional['resolution']=resolution_for(hard,optional['role'],optional['binding'],optional['predicates'])
 request=StructuredOutfitRequest(garment_categories=tuple(GarmentCategoryConstraint(**v) for v in a['coarse_categories']) or None);effective=request;default=None
 def slot(value,ranges):
  if value is None:return ContextSlot()
  values=tuple(value) if isinstance(value,list) else (value,)
  return ContextSlot('Known',values,tuple(SourceSpan(x,y,text[x:y]) for x,y in ranges))
 if context!='none':
  from app.application.recommendation.context_bundle import ContextBundle
  from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
  _,registry,_=source.resources();event=next(s for s in registry.situations if s.identifier==context);bundle=ContextBundle.load('context_18_v1')
  observed={}
  for observation in a['observations']:
   from .semantic_frames import span
   # Observation quotes are raw-source spans; convert only through the stored
   # normalization map. No synthetic canonical-English offsets are introduced.
   x,y=span(raw,observation['quote']);positions=[i for i,(u,v) in enumerate(mapping['character_map']) if x<=u and v<=y]
   if not positions:refuse('semantic_source_grounding')
   name=observation['slot'];value=observation['value']
   if name in observed and observed[name][0]!=value:refuse('semantic_clarification_required')
   observed[name]=(value,[[min(positions),max(positions)+1]])
  if event.venue and 'venue' not in observed:observed['venue']=(event.venue,a['event_spans'])
  fields={name:slot(value,ranges) for name,(value,ranges) in observed.items()}
  fields.update(situation=slot(context,a['event_spans']),activity=slot(event.activity,a['event_spans']),
                role=slot(a['role'],[a['role_span']]) if a['role']!='unspecified' else ContextSlot())
  for item in a['appearance']:fields[item['slot']]=slot(item['value'],[[item['start'],item['end']]])
  if a['facets']:
   ranges=[]
   for facet in a['facets']:
    word=facet.split(':')[1];start=text.find(word)
    if start<0:refuse('semantic_source_grounding')
    ranges.append([start,start+len(word)])
   fields['facets']=slot(a['facets'],ranges)
  frame=GeneralContext(text,grammar_sha256=bundle.record['grammar_sha256'],taxonomy_sha256=bundle.record['taxonomy_sha256'],version='general-context-1.1.0',bundle_id='context_18_v1',**fields)
  formality=frame.dress_code.value or frame.formality.value
  request=GeneralContextRequest(occasion=event.projection_occasion,formality=formality,context=frame)
  inferred=context=='professional.job_interview' and frame.dress_code.state=='Unspecified' and frame.formality.state=='Unspecified'
  effective=replace(request,formality='smart_casual') if inferred else request
  evaluator=EvaluatorSpecification.current('context_18_v1',interview_default=inferred).construct();plan=evaluator.plan(effective)
  if not evaluator.supports(effective):refuse('unsupported_context_'+plan.reason)
  if context=='professional.job_interview':
   from .interview_default import MESSAGE
   default={'version':'interview-appearance-default-1.0.0','inferred':inferred,'origin':'approved_policy_default' if inferred else 'user_specified',
            'effective_formality':effective.formality,'verified_dress_code':False,'message':MESSAGE if inferred else None,
            'policy_binding':plan.binding.identifier,'policy_version':plan.binding.policy_version,'predicate':plan.predicate.identifier}
 else:
  appearance={x['slot']:x['value'] for x in a['appearance']}
  if appearance.get('dress_code'):refuse('semantic_clarification_required')
  request=replace(request,formality=appearance.get('formality'));effective=request
 value={'version':GRAMMAR,'grammar_version':GRAMMAR,'grammar_sha256':grammar,'normalization':mapping,'request':request.to_dict(),
        'hard_intent':hard.to_dict() if hard else None,'optional':optional,'semantic_proposal':proposal,
        'semantic_metadata':{'primary':context,'secondary':a['secondary'],'role':a['role'],'model_is_not_garment_evidence':True,
         'compilation':'typed-slots-no-canonical-English','context_resource_identity':'shared-context18-schema-and-vocabulary-not-producer'},
        'original_hard_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in hard.to_dict()['spans']] if hard else [],
        'original_optional_spans':[{**s,**original_span(mapping,s['start'],s['end'])} for s in optional['spans']] if optional else [],
        'original_context_spans':[{'slot':n,'value':v['values'],**original_span(mapping,s['start'],s['end'])} for n,v in request.to_dict().get('context',{}).items() if isinstance(v,dict) and 'spans' in v for s in v['spans']]}
 if default:value.update(evaluation_request=effective.to_dict(),interview_default=default)
 value=json.loads(encode(value));value['revision']=digest(value);return value

def document(raw,proposal):
 if type(proposal) is not dict or set(proposal)!=FIELDS or len(encode(proposal))>98304:refuse('semantic_invalid_output')
 if proposal['version']!=PROPOSAL or proposal['source_text']!=raw or proposal['source_sha256']!=hashlib.sha256(raw.encode()).hexdigest() or proposal['identity']!=model_identity():refuse('semantic_source_grounding')
 analysis=source.analyze(raw)
 if analysis!=proposal['analysis']:refuse('semantic_source_grounding')
 context=analysis['context'];selection=proposal['selection']
 if type(selection) is not dict or set(selection)!={'grounded_candidates','prediction','unrestricted_prediction'} or selection['prediction']!=context or selection['grounded_candidates']!=([context] if context!='none' else []) or selection['unrestricted_prediction'] not in (*semantic_model.CONTEXTS,None) or proposal['slots']!={'context':context}:refuse('semantic_source_grounding')
 return compile_graph(raw,analysis,copy.deepcopy(proposal))
