"""Context18 admission/relevance on the complete, independently restored union."""
from dataclasses import asdict
from fractions import Fraction as F
import json
from types import SimpleNamespace
from . import core
from .context_intent import document
from app.application.recommendation.attribute_preference_codec import restore_request
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.context_bundle import ContextBundle
from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy, PROFILE
from app.application.recommendation.context_relevance_scorer import PreparedRelativeFacts
from app.application.recommendation.context_relevance_verifier import PublicAlignmentFacts
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.domain.value_objects.recommendation_score import RecommendationScore


def resources(*, interview_default=False):
    spec = EvaluatorSpecification.current('context_18_v1',interview_default=True) if interview_default else EvaluatorSpecification.current('context_18_v1')
    policy = ContextRelevancePolicy.load(bundle_id='context_18_v1')
    return {'evaluator': asdict(spec), 'bundle_sha256': ContextBundle.load('context_18_v1').manifest_sha256,
            'ranking_profile': PROFILE, 'policy_version': policy.policy_version, 'policy_sha256': policy.policy_sha256,
            'catalogue_version': policy.catalogue_version, 'catalogue_sha256': policy.catalogue_sha256,
            'preferences': 'p1', 'compatibility': 'c1', 'optional_policy': 'request_local_bounded_preference_v1'}


def select(catalog, raw, wearer_id, engine='reference', *, independent=False, seen=(), floor='0', _interpret=None, _fashion=None, _personalization=None):
    # Only registered server-owned proof revisions select an interpreter.
    # Existing v2 callers retain the frozen Phase2O interpretation by default.
    data = document(raw) if _interpret is None else _interpret(raw)
    request = restore_request(data.get('evaluation_request',data['request']))
    if wearer_id not in catalog['fixture']['profiles']:
        raise ValueError('Foreign contextual wearer.')
    rows = core.rows_from_catalog(catalog, catalog['fixture']['profiles'][wearer_id]['gender'])
    by_id = {r.snapshot.garment_id: r for r in rows}
    owner = catalog['fixture']['owner_id']
    scope = core.digest(catalog)
    default = bool(data.get('interview_default',{}).get('inferred'))
    spec = EvaluatorSpecification.current('context_18_v1',interview_default=True) if default else EvaluatorSpecification.current('context_18_v1')
    evaluator = spec.construct()
    fashion = _fashion(rows,request,scope,independent,evaluator) if _fashion else None
    settings = resources(interview_default=default)
    groups = data['hard_intent']['conditions']['groups'] if data['hard_intent'] else []
    supported = {'category','primary_colour','secondary_colour','material','pattern','sleeve_length','silhouette','style'}
    if any(c['attribute'] not in supported for g in groups for c in g['conditions']):
        raise core.UnsupportedFixtureRequest('Unsupported contextual attribute.')
    read_preferences=core.preferences_from_catalog
    if _personalization is not None:
        from .personalization import preferences as read_preferences,validate,choose
        validate(_personalization,owner,wearer_id)
    preferences = read_preferences(catalog, wearer_id)
    normalized = PreferenceNormalizer().normalize(owner, preferences)
    policy = ContextRelevancePolicy.load(bundle_id='context_18_v1')
    resolution = policy.resolve(request)
    objective = resolution.objective
    public_facts = PublicAlignmentFacts(tuple(r.snapshot for r in rows), objective) if independent else None
    prepared = None if independent else PreparedRelativeFacts(tuple(r.snapshot for r in rows), request, normalized, policy)
    precomputed = {}
    if independent:
        stream = core.RequestCandidateSession(core.IndependentStructural(rows), request, spec.construct())
    else:
        query = core.FrozenQuery(owner, [r.snapshot for r in rows])
        if engine == 'compact_exhaustive':
            from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer
            from app.infrastructure.persistence.recommendation_repository_adapter import encode
            audit = []
            outcome = CompactExhaustiveScorer(query, SimpleNamespace(get_active_preferences=lambda _: preferences), evaluator_type=spec, audit=audit.append).rank(owner, request)
            if not outcome.complete:
                raise ValueError('Incomplete contextual compact enumeration.')
            precomputed = {tuple(tuple(k) for k in r['key']): core.score_from_json(encode(r['score'])) for r in audit if r['verified']}
        elif engine != 'reference':
            raise ValueError('Unsupported contextual engine.')
        stream = core.RequestCandidateEngine(query, evaluator_specification=spec).generate_candidates(owner, request)
    gate = core.ScoringEligibilityGate(stream, owner, request)
    scorers = core.public_scorers(owner, preferences)
    legacy, points, unknown_bounds, candidates = {}, {}, {}, {}
    failed = unknown = skipped = 0
    try:
        for item in stream:
            verified = gate.verify(item)
            key = verified.candidate.key
            state = (core.independent_hard if independent else core.first_hard)(key, groups, by_id, scope)
            if state == 'Fail':
                failed += 1
                continue
            if state == 'Unknown':
                unknown += 1
                continue
            baseline = precomputed[key] if precomputed else core.public_score(verified, scorers)
            if fashion is not None:baseline=fashion.apply(key,baseline)
            legacy[key] = baseline
            candidates[key] = verified.candidate
            if objective is None:
                continue
            if independent:
                r = public_facts.component(verified)
                values = [public_facts.rows[gid][1] for role, gid in key if role != 'outerwear']
                low = F(sum(v for v in values if v is not None), len(values))
                high = low + F(sum(v is None for v in values), len(values))
                p = PreferenceScorer.independent_component(baseline.preference, normalized, objective)
                score = RecommendationScore(r, baseline.compatibility, p, F(3,5)*r.contribution + F(1,5)*baseline.compatibility.contribution + F(1,5)*p.contribution, PROFILE, policy.policy_version, policy.weights)
            else:
                roles = tuple(role for role, _ in key)
                indexes = tuple(prepared.by_id[gid] for _, gid in key)
                low, high, _, _ = prepared.bounds(roles, indexes)
                # Public exact score conversion is unchanged; no compact or
                # first-pass score is borrowed by the independent verifier.
                p = PreferenceScorer.independent_component(baseline.preference, normalized, objective)
                score = prepared.public(verified, baseline) if low == high else None
            if low == high:
                points[key] = fashion.retag(score) if fashion is not None else score
            else:
                unknown_bounds[key] = (F(3,5)*high + F(1,5)*baseline.compatibility.contribution + F(1,5)*p.contribution, high, baseline.compatibility.contribution, p.contribution)
        result = stream.result
        if not result.complete:
            raise ValueError('Incomplete contextual candidate scope.')
    finally:
        stream.close()
    relative = bool(points)
    scores = points if relative else legacy
    # Ordinary contextual continuation is point-relative only, as in the
    # existing continuation contract. No baseline/Unknown-R continuation.
    if seen and not relative:
        return {'status': 'RefinementUnavailable', 'intent': data}
    scores = {k: s for k, s in scores.items() if tuple(x for x in k if x[0] != 'outerwear') not in seen and s.request_match.contribution >= F(floor)}
    skipped = (len(points) if relative else len(legacy)) - len(scores)
    counts = asdict(core.CompletedLedger(result.examined, len(scores), result.failed + failed + skipped, result.unknown + unknown + (len(unknown_bounds) if relative else 0), result.complete))
    admission = asdict(core.CompletedLedger(result.examined, len(legacy), result.failed + failed, result.unknown + unknown, result.complete))
    context = {'resources': settings, 'summary': evaluator.summary(request), 'objective_resolution': asdict(resolution),
               'selection_mode': 'best_evidenced_with_coverage_v1' if relative else 'baseline_disclosed_v1',
               'fallback_reason': None if relative else 'objective_unavailable' if objective is None else 'no_point_relative_candidate',
               'coverage': {'mandatory_passed': len(legacy), 'point_candidates': len(points), 'unresolved_candidates': len(unknown_bounds), 'seen_or_below_floor': skipped},
               'ranking_pool': counts}
    if data.get('interview_default'):
        context['interview_default']=data['interview_default']
    if not scores:
        return {'status': 'InsufficientEvidence' if counts['unknown'] else 'RefinementExhausted' if seen else 'NoMatchingCandidates', 'mandatory': admission, 'intent': data, 'context': json.loads(core.encoded(context))}
    order = lambda k: (-scores[k].total, -scores[k].request_match.contribution, -scores[k].compatibility.contribution, -scores[k].preference.contribution, k)
    baseline = selected = min(scores, key=order)
    optional = data['optional']
    optionals, eligible = {}, []
    if optional:
        if seen:
            raise ValueError('Soft contextual continuation is unsupported.')
        optionals = {k: core.optional_value(k, optional, by_id, scope, independent) for k in scores}
        if independent:
            b = scores[baseline]
            eligible = [k for k, s in scores.items() if optional['resolution']['state'] == 'Active' and optionals[k].support and s.total + F(1,50) >= b.total and s.compatibility.contribution + F(1,10) >= b.compatibility.contribution and s.preference.contribution + F(1,10) >= b.preference.contribution and s.request_match.contribution >= b.request_match.contribution]
            if eligible:
                selected = min(eligible, key=order)
        else:
            encoding = core.LocalScoreEncoding()
            records = tuple(core.PrimaryRecord(k, s.request_match.contribution, s.compatibility.contribution, s.preference.contribution, s.total, scope, encoding.encode(s).encode()) for k, s in scores.items())
            ranked = core.bounded_rank(lambda: iter(records), core.CompletedLedger(**counts), lambda k: optionals[k], resolution=optional['resolution']['state'])
            selected = ranked.selected.key
            eligible = [x.primary.key for x in ranked.optional_ledger if not x.reasons]
    personal_display=None
    if _personalization is not None:selected,personal_display=choose(_personalization,scores,selected,optional,seen)
    def entry(k):
        return {'key': [list(x) for x in k], 'score': json.loads(core.score_to_json(scores[k]))}
    selected_values = (-scores[selected].total, -scores[selected].request_match.contribution, -scores[selected].compatibility.contribution, -scores[selected].preference.contribution, selected)
    context['global_optimum_certified'] = relative and selected == baseline and all(selected_values < (*(-v for v in values), k) for k, values in unknown_bounds.items())
    context['selected_evidence'] = evaluator.explain(candidates[selected], request)
    # Dataclass explanation tuples must have the same meaning before and after
    # the JSON proof round trip. Never loosen the archived equality check.
    context = json.loads(core.encoded(context))
    opt = optionals.get(selected)
    return {**({'personalization':personal_display} if personal_display is not None else {}),**({'fashion':fashion.describe(selected)} if fashion is not None else {}),'status': 'Selected', 'intent': data, 'mandatory': admission, 'context': context,
            'candidate_scores_sha256': core.digest([{'key': k, 'score': json.loads(core.score_to_json(scores[k]))} for k in sorted(scores)]),
            'baseline': entry(baseline), 'selected': entry(selected), 'eligible_promotion_count': len(eligible),
            'optional': None if opt is None else {'state': opt.state, 'resolution': optional['resolution'], 'ledger': [json.loads(x) for x in opt.ledger], 'counts': {s: sum(v.state == s for v in optionals.values()) for s in ('Satisfied','Unsatisfied','Unverifiable')}},
            'explanation': 'exact_score_tie_diversity' if personal_display and personal_display['applied'] else 'qualified_bounded_promotion' if selected != baseline else 'original_baseline_retained',
            'items': [{'role': role, 'garment_id': gid, 'name': by_id[gid].snapshot.name, 'media_id': by_id[gid].snapshot.preferred_media_id, 'attributes': by_id[gid].declaration, 'source': 'normal_B0_B1' if isinstance(by_id[gid], core.OriginalRow) else core.ORIGIN} for role, gid in selected]}
