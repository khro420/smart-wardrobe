"""Additive positive appearance-goal interpretation; Grammar 1.4 stays frozen."""
VERSION='mixed-hybrid-semantic-selection-1.4.1'
PROFILE='local_semantic_nlp_appearance_v1'
GRAMMAR='hybrid-semantic-intent-1.4.1'
GRAMMAR_SHA256='4506f77aa3411f2e5483b52c14e6491af54fb0b44cfb05ebb057fae7cb06166e'

def base(version):
 from .semantic_unified_contract import base as previous
 return previous(version)

def owns(version):
 from .semantic_unified_contract import owns as previous
 return base(version)==VERSION or previous(version)
