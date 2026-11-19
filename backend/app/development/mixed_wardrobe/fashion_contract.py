"""Server-owned, default-off scoring revision; grammar identities are unchanged."""
ENV = 'SMART_WARDROBE_DEVELOPMENT_FASHION_PROFILE'
PROFILE = 'fashion_compatibility_v2'
POLICY_VERSION = 'fashion-coherence-policy-2.0.0'

def versions():
    from .core import VERSION
    from .context_contract import VERSION as CONTEXT
    from .context_language_contract import VERSION as LANGUAGE
    from .interview_default_contract import VERSION as INTERVIEW
    from .semantic_frame_contract import VERSION as FRAMES
    from .semantic_constraint_contract import VERSION as NOUNS
    from .semantic_reliability_contract import VERSION as SCOPED
    from .semantic_structured_contract import VERSION as TYPED
    from .semantic_unified_contract import VERSION as UNIFIED
    from .semantic_appearance_contract import VERSION as APPEARANCE
    return {VERSION:'mixed-fashion-neutral-2.0.0',CONTEXT:'mixed-fashion-context-2.0.0',
            LANGUAGE:'mixed-fashion-language-2.0.0',INTERVIEW:'mixed-fashion-interview-2.0.0',
            FRAMES:'mixed-fashion-semantic-frames-1.0.0',NOUNS:'mixed-fashion-semantic-frames-1.1.0',
            SCOPED:'mixed-fashion-semantic-frames-1.2.0',TYPED:'mixed-fashion-semantic-frames-1.3.0',
            UNIFIED:'mixed-fashion-semantic-frames-1.4.0',APPEARANCE:'mixed-fashion-semantic-frames-1.4.1'}

def base_version(version):
    return next((old for old,new in versions().items() if new==version),None)
