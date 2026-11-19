"""Versioned source-clause projection; older semantic proofs remain frozen."""
VERSION='mixed-hybrid-semantic-selection-1.2.0'
PROFILE='local_semantic_nlp_scope_v1'
GRAMMAR='hybrid-semantic-intent-1.2.0'
GRAMMAR_SHA256='15ffa621dfe75a994d0a8bb631f6d339dbe4882f4753d9588818658fd682eedf'

def base(version):
 from .personalization import base_version as personal
 from .fashion_contract import base_version as fashion
 v=personal(version) or version
 return fashion(v) or v

def owns(version):
 from .semantic_constraint_contract import owns as prior
 return base(version)==VERSION or prior(version)
