"""Additive source graph / typed compilation contract; archived readers frozen."""
VERSION='mixed-hybrid-semantic-selection-1.3.0'
PROFILE='local_semantic_nlp_structured_v1'
GRAMMAR='hybrid-semantic-intent-1.3.0'
GRAMMAR_SHA256='117e744e2ea823327f34f9afa371ad591dbb9472f094de53b5ffed440ae888e3'

def base(version):
 from .semantic_reliability_contract import base as previous
 return previous(version)

def owns(version):
 from .semantic_reliability_contract import owns as previous
 return base(version)==VERSION or previous(version)
