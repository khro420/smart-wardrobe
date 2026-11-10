"""Pinned, default-off recorded-palette convention; archived restore needs no I/O."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from app.domain.value_objects.palette_compatibility import PROFILE,POLICY,PaletteError

ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_COMPATIBILITY_PROFILE'
RESOURCE_SHA256='2ecaecea5736252bfbb5f18c6e556f8abbbc03ffb66c8ff6a262b50e9dbb071f'
SEMANTIC_SHA256='814232380887c50ab8a2023798cd1350fbcb9043d5f65193fecc79702340d6bd'

def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def digest(value):return hashlib.sha256(encode(value)).hexdigest()
def decode(raw,limit=131072):
    if type(raw) not in (str,bytes) or len(raw.encode() if type(raw) is str else raw)>limit:raise ValueError('C2 encoding limit exceeded.')
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate C2 JSON key.')
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))

@dataclass(frozen=True)
class PalettePolicy:
    payload: bytes
    def __post_init__(self):
        if type(self.payload) is not bytes or len(self.payload)>32768 or digest(decode(self.payload,32768))!=SEMANTIC_SHA256:
            raise PaletteError('CompatibilityUnavailable','Unregistered recorded-palette policy.')
    @classmethod
    def load(cls):
        try:raw=(Path(__file__).with_name('config')/'palette_compatibility.v1.json').read_bytes()
        except OSError as exc:raise PaletteError('CompatibilityUnavailable','Missing recorded-palette policy.') from exc
        if hashlib.sha256(raw).hexdigest()!=RESOURCE_SHA256:raise PaletteError('CompatibilityUnavailable','Unregistered recorded-palette bytes.')
        return cls(raw)
    @classmethod
    def restore(cls,value):return cls(encode(value))
    def snapshot(self):return decode(self.payload,32768)
    @property
    def hash(self):return RESOURCE_SHA256
    def capabilities(self):return {'version':'palette-compatibility-capabilities-1.0.0','enabled':True,'profile':PROFILE,'policy':POLICY,'policy_sha256':self.hash,'default':'c1','explicit_selection_required':True,'independent_appropriateness_validation':'OPEN','source':'qualified_recorded_owner_palette','maximum_entries':5}

def configure(value='disabled',*,dependencies=False):
    if value=='disabled':return None
    if value!=PROFILE or not dependencies:raise PaletteError('CompatibilityUnavailable','C2 requires approved description, B1, context18 and decision dependencies.')
    return PalettePolicy.load()
