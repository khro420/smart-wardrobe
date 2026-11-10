"""Pinned default-off P2 policy; no resource reads inside enumeration or history."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
from app.domain.value_objects.attribute_preferences import PROFILE, PreferenceError, decode, AXES, POLICY_HASH, POLICY_SEMANTIC_HASH, encode, digest

ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_PREFERENCE_PROFILE'
RESOURCE_HASH=POLICY_HASH


@dataclass(frozen=True)
class AttributePreferencePolicy:
    payload: bytes
    archived: bool=False

    def __post_init__(self):
        if type(self.payload) is not bytes or len(self.payload)>65536:
            raise PreferenceError('PreferenceUnavailable','Unregistered P2 resource.')
        v=decode(self.payload,65536)
        if (digest(v)!=POLICY_SEMANTIC_HASH if self.archived else hashlib.sha256(self.payload).hexdigest()!=RESOURCE_HASH):
            raise PreferenceError('PreferenceUnavailable','Unregistered P2 resource.')
        if v['model_sources'] or v['measured_sources'] or v['default_activation'] is not False:
            raise PreferenceError('PreferenceUnavailable','Unapproved P2 source policy.')

    @classmethod
    def load(cls,path=None):
        try:
            with (Path(path) if path else Path(__file__).with_name('config')/'attribute_preference_policy.v1.json').open('rb') as f: raw=f.read(65537)
        except OSError as exc: raise PreferenceError('PreferenceUnavailable','Missing P2 resource.') from exc
        return cls(raw)

    def capabilities(self):
        value=decode(self.payload,65536)
        return {'contract':'attribute-preference-capabilities-1.0.0','enabled':True,'profile':PROFILE,'policy':RESOURCE_HASH,
                'families':list(AXES),'axes':value['axes'],'values':value['finite'],'dynamic':value['dynamic'],'limits':value['limits']}

    @classmethod
    def restore(cls,value):return cls(encode(value),archived=True)

    def snapshot(self):return decode(self.payload,65536)


_policy=None


def configure(value='disabled', *, dependencies=False):
    global _policy
    _policy=None
    if value=='disabled': return None
    if value!=PROFILE or not dependencies: raise PreferenceError('PreferenceUnavailable','P2 requires the approved description, B1, context18 and decision profiles.')
    _policy=AttributePreferencePolicy.load()
    return _policy


def current_policy(): return _policy


def require_policy():
    if _policy is None: raise PreferenceError('PreferenceUnavailable','Soft attribute preferences are unavailable.')
    return _policy
