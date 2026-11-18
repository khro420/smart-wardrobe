"""Server-owned, default-off scoring revision; grammar identities are unchanged."""
ENV = 'SMART_WARDROBE_DEVELOPMENT_FASHION_PROFILE'
PROFILE = 'fashion_compatibility_v2'
POLICY_VERSION = 'fashion-coherence-policy-2.0.0'

def versions():
    from .core import VERSION
    from .context_contract import VERSION as CONTEXT
    from .context_language_contract import VERSION as LANGUAGE
    from .interview_default_contract import VERSION as INTERVIEW
    return {VERSION:'mixed-fashion-neutral-2.0.0',CONTEXT:'mixed-fashion-context-2.0.0',
            LANGUAGE:'mixed-fashion-language-2.0.0',INTERVIEW:'mixed-fashion-interview-2.0.0'}

def base_version(version):
    return next((old for old,new in versions().items() if new==version),None)
