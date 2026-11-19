"""Additive noun-preservation revision; semantic v1 stays frozen for history."""
VERSION='mixed-hybrid-semantic-selection-1.1.0'
GRAMMAR='hybrid-semantic-intent-1.1.0'
GRAMMAR_SHA256='925bb8718bd60dc9f3751963340677ce8d1183594672234a705c01d2aa80733b'

def owns(version):
 from .personalization import base_version as personal
 from .fashion_contract import base_version as fashion
 from .semantic_frame_contract import VERSION as OLD_VERSION
 v=personal(version) or version
 return (fashion(v) or v) in (OLD_VERSION,VERSION)
