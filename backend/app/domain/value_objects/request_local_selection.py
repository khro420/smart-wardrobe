"""New exact-key envelope; never extends legacy attribute/refinement archives."""
from dataclasses import dataclass,field
from app.domain.value_objects.attribute_conditions import encode,decode,digest,exact
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent

VERSION='request-local-selection-proof-1.0.0'
CODEC_VERSION='request-local-selection-proof-2.0.0'
KEY='request_local_preference'
MAX_PROOF=4194304
POLICY={'version':'request_local_bounded_preference_v1','T_loss':'1/50','C_loss':'1/10','P_loss':'1/10','R_decrease':False}
SETTINGS={'preference':'P1','compatibility':'experimental_compatibility_decision_v1','contextual':False,'continuation':None,'evaluator':'base_request_v1'}
FIELDS=('version','intent','owner_id','wearer','settings','policy','attribute_policy','sources','preferences','source_revisions','eligibility','resources','decision','revision')

@dataclass(frozen=True)
class LocalSelectionProof:
    payload:bytes
    _expanded_payload:bytes=field(init=False,repr=False,compare=False,default=b'')
    def __post_init__(self):
        v=decode(self.payload,MAX_PROOF);exact(v,FIELDS)
        is_codec=v['version']==CODEC_VERSION
        if is_codec:
            from app.domain.value_objects.request_local_source_codec import unpack_sources
            wire=v
            v={**v,'version':VERSION,'sources':unpack_sources(v['sources'])}
            # Validate the unchanged logical contract without assigning the new
            # wire revision the historical meaning of a v1 revision.
            v['revision']=digest({**v,'revision':''})
            if wire['revision']!=digest({**wire,'revision':''}):raise ValueError('Changed codec proof bytes.')
        if v['version']!=VERSION or encode(v['policy'])!=encode(POLICY) or encode(v['settings'])!=encode(SETTINGS):raise ValueError('Unsupported local proof/profile/budgets.')
        intent=RequestLocalPreferenceIntent(encode(v['intent']))
        if v['intent']['source_kind']!='nlp':raise ValueError('Numerical fixture intents are not persistable.')
        from app.domain.value_objects.intended_wearer import IntendedWearer
        wearer=IntendedWearer(**v['wearer'])
        if wearer.account_id!=v['owner_id']:raise ValueError('Wrong local proof owner/wearer.')
        if type(v['sources']) is not list or not 1<=len(v['sources'])<=100 or type(v['preferences']) is not list or len(v['preferences'])>100:raise ValueError('Unbounded local source scope.')
        if not is_codec and v['revision']!=digest({**v,'revision':''}):raise ValueError('Changed local proof bytes.')
        if is_codec:
            # Immutable, instance-local decoded view; no cache grants authority.
            # Independent source/admission/score verification still runs.
            object.__setattr__(self,'_expanded_payload',encode(v))
    def to_dict(self):return decode(self.payload,MAX_PROOF)

    def expanded_dict(self):
        """Derived canonical v1 view; stored wire bytes/revision are untouched."""
        if self._expanded_payload:
            from app.domain.value_objects.request_local_source_codec import MAX_EXPANDED_BYTES
            return decode(self._expanded_payload,MAX_EXPANDED_BYTES+MAX_PROOF)
        return self.to_dict()

    @classmethod
    def with_source_codec(cls,value):
        """Explicit internal opt-in. Existing v1 constructors/readers remain."""
        from app.domain.value_objects.request_local_source_codec import pack_sources
        value={**value,'version':CODEC_VERSION,'sources':pack_sources(value['sources'])}
        value['revision']=digest({**value,'revision':''})
        return cls(encode(value))

@dataclass(frozen=True)
class LocalPreferenceWriteDraft:
    proof:LocalSelectionProof
    def __post_init__(self):
        if type(self.proof) is not LocalSelectionProof:raise ValueError('Typed local proof required.')

def fingerprint(intent,wearer,settings=SETTINGS,policy=POLICY):
    """Version seven is disjoint from all legacy fingerprint branches."""
    if type(intent) is not RequestLocalPreferenceIntent:raise ValueError('Typed local intent required.')
    return digest({'version':7,'operation':'assistant','owner_id':wearer.account_id,'wearer_profile_id':wearer.profile_id,
        'intent':intent.to_dict(),'settings':settings,'ranking_policy':policy,'continuation':None})
