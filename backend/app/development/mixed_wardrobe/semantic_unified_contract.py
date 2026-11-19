"""Additive unified outfit intent; all prior grammar readers remain registered."""
VERSION='mixed-hybrid-semantic-selection-1.4.0'
PROFILE='local_semantic_nlp_unified_v1'
GRAMMAR='hybrid-semantic-intent-1.4.0'
GRAMMAR_SHA256='f53bef4649a293652936482c16535f93ac98458b9743c46e93a46780044bfbff'

def base(version):
 from .semantic_structured_contract import base as previous
 return previous(version)

def owns(version):
 from .semantic_structured_contract import owns as previous
 return base(version)==VERSION or previous(version)
