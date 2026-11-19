"""Additive interpretation only; existing scoring and proof revisions stay registered."""
ENV = 'SMART_WARDROBE_DEVELOPMENT_SEMANTIC_PROFILE'
PROFILE = 'local_semantic_nlp_v1'
VERSION = 'mixed-hybrid-semantic-selection-1.0.0'
GRAMMAR = 'hybrid-semantic-intent-1.0.0'
GRAMMAR_SHA256 = 'febfd58be60089f55afea8ed2e453d04baf7b075e03bf210cbe065f7911a51fa'

def owns(version):
    from .personalization import base_version as personal
    from .fashion_contract import base_version as fashion
    v=personal(version) or version
    return (fashion(v) or v)==VERSION
