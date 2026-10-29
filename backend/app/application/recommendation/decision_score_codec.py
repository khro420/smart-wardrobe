"""Explicit offline replay of versioned decision metadata, never a live reader.

SQL REAL columns are display-only; exact metadata is authoritative for replay.
No raw NULL-to-zero fallback or legacy-payload inference is permitted here.
"""
from dataclasses import asdict
from fractions import Fraction as F
import json
from app.domain.value_objects.recommendation_score import ScoreEvidence, ComponentScore, RecommendationScore
from app.domain.value_objects.compatibility_decision import CompatibilityDecision, DecisionCompatibilityComponent
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.application.recommendation.rule_based_compatibility_policy import _unique


def _ratios(value,reader):
    if isinstance(value,dict):
        if set(value)=={'numerator','denominator'}:return reader(value)
        return {k:_ratios(v,reader) for k,v in value.items()}
    if isinstance(value,list):return [_ratios(v,reader) for v in value]
    return value


def fraction(value):
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {"numerator", "denominator"}
            or any(type(x) is not int for x in value.values()) or value["denominator"] <= 0):
        raise ValueError("Exact fraction metadata required.")
    return F(value["numerator"], value["denominator"])


def evidence(value):
    return ScoreEvidence(**{**value, "value": fraction(value["value"])})


def component(value):
    if set(value) != {"summary", "details"}:
        raise ValueError("Unexpected raw component metadata.")
    return ComponentScore(evidence(value["summary"]), tuple(evidence(x) for x in value["details"]))


def score_from_json(text):
    data = json.loads(text, object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if not isinstance(data, dict) or set(data) != {"request_match", "compatibility", "preference", "total", "profile_name", "policy_version", "weights"}:
        raise ValueError("Versioned recommendation score metadata required.")
    if data['profile_name']=='context_relevance_decision_v1':
        from dataclasses import replace
        from app.domain.value_objects.context_relevance import read_ratio,bounded_json
        from app.application.recommendation.context_relevance_policy import POLICY_VERSION
        from app.application.recommendation.context_bundle import ARCHIVES
        bounded_json(data)
        if data['policy_version'] not in {POLICY_VERSION,*[r['policy_version'] for r in ARCHIVES.values()]} or data['request_match']['summary']['name']!='relative_style_alignment' or data['request_match']['summary']['state']!='Available':
            raise ValueError('Invalid archived relative score contract.')
        numeric=_ratios(data,lambda value:{'numerator':read_ratio(value).numerator,'denominator':read_ratio(value).denominator})
        baseline=CompatibilityDecisionPolicy.load()
        numeric.update(profile_name=baseline.name,policy_version=baseline.version)
        return replace(score_from_json(json.dumps(numeric)),profile_name='context_relevance_decision_v1',policy_version=data['policy_version'])
    c = data["compatibility"]
    if set(c) != {"summary", "details", "decision", "adapter_version"} or c["adapter_version"] != "compatibility-decision-component-1.0.0":
        raise ValueError("Explicit decision adapter tag required.")
    d = dict(c["decision"])
    d["raw"] = component(d["raw"])
    for field in ("value", "lower", "upper", "known_sum"):
        d[field] = fraction(d[field])
    decision = CompatibilityDecision(**d)
    policy = CompatibilityDecisionPolicy.load()
    if (decision.policy_version, decision.policy_hash) != (policy.version, policy.hash):
        raise ValueError("Decision policy identity mismatch.")
    adapted = DecisionCompatibilityComponent(evidence(c["summary"]), tuple(evidence(x) for x in c["details"]), decision=decision)
    result = RecommendationScore(component(data["request_match"]), adapted, component(data["preference"]),
                                 fraction(data["total"]), data["profile_name"], data["policy_version"],
                                 tuple(fraction(x) for x in data["weights"]))
    if (result.profile_name, result.policy_version, result.weights) != (policy.name, policy.version, policy.weights):
        raise ValueError("Decision scoring profile mismatch.")
    return result


def score_to_json(score):
    if not isinstance(score, RecommendationScore) or not isinstance(score.compatibility, DecisionCompatibilityComponent):
        raise ValueError("Explicit decision score required.")
    if score.profile_name=='context_relevance_decision_v1':
        from dataclasses import replace
        from app.domain.value_objects.context_relevance import ratio,bounded_json
        baseline=CompatibilityDecisionPolicy.load()
        old=json.loads(score_to_json(replace(score,profile_name=baseline.name,policy_version=baseline.version)))
        old.update(profile_name=score.profile_name,policy_version=score.policy_version)
        exact=_ratios(old,lambda value:ratio(F(value['numerator'],value['denominator'])))
        text=bounded_json(exact)
        if score_from_json(text)!=score:raise ValueError('Relative metadata replay mismatch.')
        return text
    text = json.dumps(asdict(score), sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=lambda x: {"numerator": x.numerator, "denominator": x.denominator} if isinstance(x, F) else None)
    if score_from_json(text) != score:
        raise ValueError("Decision metadata replay mismatch.")
    return text
