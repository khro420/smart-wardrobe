"""Separate outer interpretation. Base 1.6/1.7 code and identities stay frozen."""
from dataclasses import dataclass
from pathlib import Path
import json,os,subprocess,sys
from app.domain.value_objects.attribute_conditions import encode,decode,digest,exact,AttributeRequestError
from app.application.nlp.natural_input_v1 import normalize,original_span

VERSION='normalized-request-intent-1.0.0'
GRAMMAR='conversational-normalized-grammar-1.8.0'
ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_NORMALIZATION_PROFILE'
PROFILE='bounded_natural_input_v1'
MAX_INTENT=98304

def fingerprint():
    from app.shared_contracts.grammar_identity import semantic_fingerprint
    from app.application.nlp import natural_input_v1
    return semantic_fingerprint((GRAMMAR.encode(),Path(natural_input_v1.__file__).read_bytes(),Path(__file__).read_bytes(),Path(__file__).with_name('normalized_base_worker.py').read_bytes()))

def identity():
    from app.shared_contracts.normalized_grammar_registry import GRAMMAR_SHA256
    if fingerprint()!=GRAMMAR_SHA256:raise ValueError('Unregistered normalized grammar source.')
    return GRAMMAR_SHA256

def base_parse(text):
    # A fresh interpreter with explicit base-v1 selectors prevents process-global
    # subtype/language settings from changing archived normalized interpretation.
    env=os.environ.copy();env['SMART_WARDROBE_VERIFIED_SUBTYPE_PROFILE']='disabled';env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONPATH']=str(Path(__file__).resolve().parents[3])
    worker=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('normalized_base_worker.py'))],
        input=json.dumps({'text':text}),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env,timeout=15)
    if worker.returncode or len(worker.stdout.encode())>65536:raise ValueError('Frozen base interpretation worker failed.')
    value=json.loads(worker.stdout)
    if 'error' in value:raise AttributeRequestError(value['error'],value['reason'])
    return value

def document(raw):
    grammar=identity();mapping=normalize(raw)
    parsed=base_parse(mapping['normalized_text']);hard=parsed['hard'];local=parsed['local']
    hard_spans=[];optional_spans=[]
    if hard:
        for span in hard['spans']:
            hard_spans.append({**span,**original_span(mapping,span['start'],span['end'])} if span['source']=='nlp' else span)
    if local:
        optional_spans=[{**span,**original_span(mapping,span['start'],span['end'])} for span in local['optional']['spans']]
    value={'version':VERSION,'grammar_version':GRAMMAR,'grammar_sha256':grammar,'normalization':mapping,
           'base_grammar_version':'conversational-attribute-grammar-1.7.0' if local else 'conversational-attribute-grammar-1.6.0',
           'request':parsed['request'],'hard_intent':hard,'local_intent':local,
           'original_hard_spans':hard_spans,'original_optional_spans':optional_spans,'revision':''}
    value['revision']=digest(value)
    return value

@dataclass(frozen=True)
class NormalizedIntent:
    payload:bytes
    def __post_init__(self):
        v=decode(self.payload,MAX_INTENT)
        exact(v,('version','grammar_version','grammar_sha256','normalization','base_grammar_version','request','hard_intent','local_intent','original_hard_spans','original_optional_spans','revision'))
        if v!=document(v['normalization']['original_text']):raise ValueError('Normalized interpretation/map/provenance mismatch.')
    @classmethod
    def capture(cls,raw):return cls(encode(document(raw)))
    def to_dict(self):return decode(self.payload,MAX_INTENT)
    @property
    def raw(self):return self.to_dict()['normalization']['original_text']
    @property
    def normalized(self):return self.to_dict()['normalization']['normalized_text']
    @property
    def revision(self):return self.to_dict()['revision']
