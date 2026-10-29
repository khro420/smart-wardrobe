"""Recommendation-local immutable objective definitions, not persisted score proof.

No scorer, public payload, shared write contract or live selector consumes these
definitions until separately approved integration. Objective resolution is not
garment eligibility or a measured judgement of fashion appropriateness.
"""
from dataclasses import dataclass
import re
import json
from fractions import Fraction

MAX_EXACT_DIGITS = 4096
MAX_PROOF_BYTES = 262144


class RelativeEncodingLimit(ValueError):
    """New-profile proof cannot be represented exactly within its explicit budget."""


def exact_text(integer):
    if type(integer) is not int or abs(integer) >= 10**MAX_EXACT_DIGITS:
        raise RelativeEncodingLimit('Exact integer exceeds the new-profile 4096-digit budget.')
    return str(integer)


def ratio(value):
    return None if value is None else {'numerator': exact_text(value.numerator), 'denominator': exact_text(value.denominator)}


def read_ratio(value):
    if type(value) is not dict or set(value) != {'numerator','denominator'}:
        raise ValueError('Exact string ratio required.')
    a,b=value['numerator'],value['denominator']
    if any(type(s) is not str or len(s)>MAX_EXACT_DIGITS or re.fullmatch('0|[1-9][0-9]*',s) is None for s in (a,b)) or b=='0':
        raise ValueError('Invalid bounded exact ratio.')
    answer=Fraction(int(a),int(b))
    if ratio(answer)!=value:
        raise ValueError('Canonical reduced ratio required.')
    return answer


def bounded_json(value):
    text=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    limit=294912 if type(value) is dict and value.get('version')=='context-relevance-evidence-1.2.0' else MAX_PROOF_BYTES
    if len(text.encode('utf-8'))>limit:
        raise RelativeEncodingLimit('New-profile encoding exceeds 256 KiB.')
    return text


def _unique(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('Duplicate proof key.')
        result[key]=value
    return result


def read_proof(text):
    if type(text) is not str or len(text.encode('utf-8'))>294912:
        raise RelativeEncodingLimit('Invalid or oversized ranking proof.')
    value=json.loads(text,object_pairs_hook=_unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
    limit=294912 if type(value) is dict and value.get('version')=='context-relevance-evidence-1.2.0' else MAX_PROOF_BYTES
    if len(text.encode('utf-8'))>limit:raise RelativeEncodingLimit('Oversized archived ranking proof.')
    return value

OBJECTIVE_VERSION = 'context-relevance-objective-1.0.0'
RESOLUTION_VERSION = 'context-relevance-resolution-1.0.0'
STYLE_OPERATOR = 'base_member_canonical_style_mean_v1'


def require_digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Exact SHA-256 identity required.')


@dataclass(frozen=True)
class RelativeObjective:
    identifier: str
    situation: str
    target: str
    authority: str
    explanation: str
    limitations: str
    operator: str = STYLE_OPERATOR
    version: str = OBJECTIVE_VERSION

    def __post_init__(self):
        for field, maximum in (('identifier', 128), ('situation', 100), ('target', 64),
                               ('explanation', 1200), ('limitations', 1200)):
            value = getattr(self, field)
            if type(value) is not str or not value or value != value.strip() or len(value) > maximum:
                raise ValueError('Invalid bounded objective field: '+field)
        if (self.authority not in ('prototype_convention', 'explicit_user_style')
                or self.operator != STYLE_OPERATOR or self.version != OBJECTIVE_VERSION):
            raise ValueError('Unapproved objective contract/operator/authority.')
        expected = 'prototype.'+self.situation if self.authority == 'prototype_convention' else 'user-stated-style'
        if self.identifier != expected:
            raise ValueError('Objective identity does not match its authority.')

    @property
    def semantic_test(self):
        """The exact predicate identity for future duplicate-P comparison."""
        return ('style', (self.target,), 'base_members', 'mean')


@dataclass(frozen=True)
class ObjectiveResolution:
    state: str
    reason: str
    policy_sha256: str
    catalogue_sha256: str
    objective: RelativeObjective | None = None
    version: str = RESOLUTION_VERSION

    def __post_init__(self):
        require_digest(self.policy_sha256)
        require_digest(self.catalogue_sha256)
        allowed = {
            'Resolved': ('automatic_default', 'explicit_style_precedence'),
            'ObjectiveUnavailable': ('context_ranking_objective_unavailable',),
            'AdmissionUnavailable': ('required_context_missing', 'unsupported_role', 'unsupported_constraint',
                                     'unsupported_dress_code', 'conflicting_context', 'invalid_context_projection',
                                     'capability_not_enabled'),
            'OutOfScope': ('existing_profile_retained',),
        }
        if (type(self.state) is not str or type(self.reason) is not str
                or self.version != RESOLUTION_VERSION or self.state not in allowed
                or self.reason not in allowed[self.state]
                or (self.state == 'Resolved') != (type(self.objective) is RelativeObjective)
                or self.state != 'Resolved' and self.objective is not None):
            raise ValueError('Invalid objective-resolution contract/state.')
        if self.objective is not None:
            expected = 'explicit_user_style' if self.reason == 'explicit_style_precedence' else 'prototype_convention'
            if self.objective.authority != expected:
                raise ValueError('Resolution reason and objective authority disagree.')

    @property
    def baseline_fallback_eligible_reason(self):
        """A reason only; a later ranker must still require a hard-Pass pool."""
        return 'objective_unavailable' if self.state == 'ObjectiveUnavailable' else None
