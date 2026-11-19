"""Additive source graph / typed compilation contract; archived readers frozen."""
VERSION='mixed-hybrid-semantic-selection-1.3.0'
PROFILE='local_semantic_nlp_structured_v1'
GRAMMAR='hybrid-semantic-intent-1.3.0'
GRAMMAR_SHA256='ea22cb9d0967594d03074117d7e67f832f1eb9e5392e4fdc4731683fc760df4c'

def base(version):
 from .semantic_reliability_contract import base as previous
 return previous(version)

def owns(version):
 from .semantic_reliability_contract import owns as previous
 return base(version)==VERSION or previous(version)
