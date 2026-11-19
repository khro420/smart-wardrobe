"""Unified, independently reconstructed context/clothing/style intent."""
from pathlib import Path
import hashlib,copy
from . import semantic_structured as old,semantic_unified_source as source,semantic_unified_fragments as fragments,semantic_unified_actions as actions
from .semantic_unified_contract import GRAMMAR
from .semantic_frames import refuse
from app.domain.value_objects.attribute_conditions import AttributeConditions,encode,digest
from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy

PROPOSAL='unified-outfit-source-proposal-1.0.0'

def fingerprint():
 from app.shared_contracts.grammar_identity import semantic_fingerprint
 return semantic_fingerprint((GRAMMAR.encode(),bytes.fromhex(old.identity()),*[Path(m.__file__).read_bytes() for m in (source,fragments,actions)],Path(__file__).read_bytes()))

def identity():
 from .semantic_unified_contract import GRAMMAR_SHA256
 value=fingerprint()
 if value!=GRAMMAR_SHA256:raise ValueError('Unregistered unified outfit compiler.')
 return value

def model_identity():
 return {'models':old.semantic_model.identity(),'compiler_sha256':identity(),'selection':'unified-outfit-typed-source-1.0.0'}

def propose(raw):
 analysis=source.analyze(raw);selection=old.select(analysis)
 return {'version':PROPOSAL,'source_text':raw,'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'identity':model_identity(),'analysis':analysis,'selection':selection,'slots':{'context':selection['prediction']}}

def document(raw,proposal):
 if type(proposal) is not dict or set(proposal)!=old.FIELDS or len(encode(proposal))>98304:refuse('semantic_invalid_output')
 if proposal['version']!=PROPOSAL or proposal['source_text']!=raw or proposal['source_sha256']!=hashlib.sha256(raw.encode()).hexdigest() or proposal['identity']!=model_identity():refuse('semantic_source_grounding')
 analysis=source.analyze(raw)
 if analysis!=proposal['analysis']:refuse('semantic_source_grounding')
 context=analysis['context'];selection=proposal['selection']
 if type(selection) is not dict or set(selection)!={'grounded_candidates','prediction','unrestricted_prediction'} or selection['prediction']!=context or selection['grounded_candidates']!=([context] if context!='none' else []) or selection['unrestricted_prediction'] not in (*old.semantic_model.CONTEXTS,None) or proposal['slots']!={'context':context}:refuse('semantic_source_grounding')
 # Reuse the frozen context/request constructor, then explicitly bind the
 # new producer identity. This consumes typed data, never generated English.
 value=old.compile_graph(raw,analysis,copy.deepcopy(proposal));grammar=identity()
 value.update(version=GRAMMAR,grammar_version=GRAMMAR,grammar_sha256=grammar)
 if analysis['hard']:
  value['hard_intent']=AttributeIntent.capture(analysis['normalization']['normalized_text'],None,AttributeConditions.from_dict(analysis['hard']),analysis['hard_spans'],grammar,AttributeEvidencePolicy.load().sha256).to_dict()
 style=any(c['attribute']=='style' for g in (analysis['hard'] or {}).get('groups',[]) for c in g['conditions'])
 clothing=bool(analysis['hard'] or analysis['optional'] or analysis['coarse_categories'])
 style_only=style and not analysis['optional'] and all(g['role']=='all_selected' and g['quantifier']=='all_present' and all(c['attribute']=='style' for c in g['conditions']) for g in analysis['hard']['groups'])
 value['semantic_metadata']['intent_route']='combined' if context!='none' and clothing else 'context_only' if context!='none' else 'style_only' if style_only else 'clothing_only' if clothing else 'neutral_outfit'
 value['semantic_metadata']['compilation']='unified-typed-context-clothing-style-1.0.0'
 value.pop('revision',None);value['revision']=digest(value)
 return value
