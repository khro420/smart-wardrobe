"""Default-off A1 definitions and one-time objective preparation.

This module never selects/persists an outfit or changes an interpreted request.
It reuses existing capability admission; objective availability cannot waive it.
There is no import from composition, a scorer, API or persistence into this module.
"""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.context_constraint_compiler import compile_context
from app.application.recommendation.context_policy_registry import ContextPolicyRegistry
from app.domain.value_objects.context_relevance import (
    RelativeObjective, ObjectiveResolution, require_digest, STYLE_OPERATOR,
    OBJECTIVE_VERSION, RESOLUTION_VERSION,
)
from app.domain.value_objects.general_context_request import GeneralContextRequest

CONFIG = Path(__file__).with_name('config')
MAX_CONFIGURATION_BYTES = 65536
POLICY_SHA256 = '54f4d6b59b3cd66abcad8764afd69e298ba59a027facc60cc8314287d63dc5e6'
CATALOGUE_SHA256 = 'ccfc5ba24af60d376cf295b25b8e26cb6df4afc738a4ea142a803c6aaa46e18b'
POLICY_VERSION = 'context-relevance-policy-1.0.0'
CATALOGUE_VERSION = 'context-relevance-objectives-1.0.0'
PROFILE = 'context_relevance_decision_v1'
SELECTION_MODE = 'best_evidenced_with_coverage_v1'
FALLBACK_MODE = 'baseline_disclosed_v1'
LEGACY_PROFILE = 'experimental_compatibility_decision_v1'

# Closed applicability/targets, expressly authorised as prototype conventions.
# Disclosure text belongs to the separately pinned catalogue bytes.
SCOPES = (
    ('everyday.shopping', 'shopping_appearance_v1', 'casual', (), ()),
    ('everyday.academic_attendance', 'campus_day_appearance_v1', 'casual', ('university', 'campus'), ()),
    ('everyday.casual_outing', 'casual_outing_appearance_v1', 'casual', (), ('friends',)),
    ('social.date', 'date_appearance_v1', 'smart casual', ('restaurant',), ()),
    ('social.meal', 'dinner_appearance_v1', 'smart casual', ('restaurant',), ('friends',)),
)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate policy key.')
        result[key] = value
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _read(path, expected_sha256):
    require_digest(expected_sha256)
    with Path(path).open('rb') as source:
        raw = source.read(MAX_CONFIGURATION_BYTES+1)
    if len(raw) > MAX_CONFIGURATION_BYTES:
        raise ValueError('Configuration exceeds 64 KiB.')
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError('Unapproved configuration hash.')
    try:
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite policy value.')))
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid bounded JSON configuration.') from exc
    pending, visited = [(data, 0)], 0
    while pending:
        node, depth = pending.pop()
        visited += 1
        if depth > 8 or visited > 2048:
            raise ValueError('Unbounded configuration tree.')
        children = node.values() if type(node) is dict else node if type(node) is list else ()
        pending.extend((child, depth+1) for child in children)
    return data, actual


def _keys(data, expected):
    if type(data) is not dict or set(data) != set(expected):
        raise ValueError('Incomplete or unexpected catalogue fields.')


def _expected_policy():
    return dict(version=POLICY_VERSION, profile=PROFILE, default_activation=False,
        objective_contract=OBJECTIVE_VERSION, resolution_contract=RESOLUTION_VERSION,
        operator=STYLE_OPERATOR, weights=['3/5', '1/5', '1/5'], selection_mode=SELECTION_MODE,
        fallback_mode=FALLBACK_MODE, fallback_profile=LEGACY_PROFILE,
        fallback_reasons=['objective_unavailable', 'no_point_relative_candidate'],
        duplicate_preferences='exact_duplicate_mask_keep_original_denominator_v1',
        maximum_configuration_bytes=65536, maximum_objectives=5,
        default_applicability=dict(role='unspecified', dress_code=None, formality=None),
        explicit_style_precedence=True, outerwear_in_base_R=False,
        human_appropriateness_validation='OPEN', authority='owner_approved_unvalidated_prototype_convention')


@dataclass(frozen=True)
class ObjectiveEntry:
    objective: RelativeObjective
    binding_id: str
    allowed_venues: tuple[str, ...]
    allowed_companions: tuple[str, ...]


@dataclass(frozen=True)
class ContextRelevancePolicy:
    policy_sha256: str
    catalogue_sha256: str
    grammar_sha256: str
    registry: ContextPolicyRegistry
    canonical_styles: tuple[str, ...]
    entries: tuple[ObjectiveEntry, ...]
    bundle_id: str = 'legacy_8_v1'
    policy_version: str = POLICY_VERSION
    catalogue_version: str = CATALOGUE_VERSION

    @classmethod
    def load(cls, policy_path=None, catalogue_path=None, *, expected_hashes=None, bundle_id='legacy_8_v1'):
        """Alternate server bundles require explicit identities; no client paths.

        A validated catalogue subset represents absent objectives, never a damaged
        file. Production defaults pin all five approved entries. There is no reload
        or implicit acceptance of an edited file under its old digest.
        """
        if bundle_id!='legacy_8_v1':
            if policy_path is not None or catalogue_path is not None or expected_hashes is not None:raise ValueError('Expanded bundle paths are server-allowlisted only.')
            from app.application.recommendation.context_bundle import ContextBundle
            bundle=ContextBundle.load(bundle_id)
            policy=bundle.read('application/recommendation/config/context_relevance_policy.v2.json')
            catalogue=bundle.read('application/recommendation/config/context_relevance_objectives.v2.json')
            expected=_expected_policy();expected.update(version=bundle.record['policy_version'],maximum_objectives=len(bundle.record['targets']))
            if policy!=expected:raise ValueError('Unapproved expanded mathematics.')
            registry=ContextPolicyRegistry.load(bundle_id=bundle_id)
            styles=tuple(sorted(Vocabulary.load().values['style']));entries=[]
            if catalogue['version']!=bundle.record['catalogue_version'] or len(catalogue['entries'])!=len(bundle.record['targets']):raise ValueError('Unapproved expanded catalogue.')
            for item in catalogue['entries']:
                binding=registry.binding_for(item['situation'])
                if (binding is None or binding.identifier!=item['binding_id'] or bundle.record['targets'].get(item['situation'])!=item['target']
                    or tuple(item['allowed_venues'])!=binding.allowed_venues or tuple(item['allowed_companions'])!=binding.allowed_companions or item['target'] not in styles):raise ValueError('Objective/admission scope mismatch.')
                objective=RelativeObjective(item['objective_id'],item['situation'],item['target'],item['authority'],item['explanation'],item['limitations'])
                entries.append(ObjectiveEntry(objective,binding.identifier,binding.allowed_venues,binding.allowed_companions))
            resources=bundle.record['resources']
            return cls(resources['application/recommendation/config/context_relevance_policy.v2.json'],resources['application/recommendation/config/context_relevance_objectives.v2.json'],bundle.record['grammar_sha256'],registry,styles,tuple(entries),bundle_id,policy['version'],catalogue['version'])
        if (policy_path is not None or catalogue_path is not None) and expected_hashes is None:
            raise ValueError('Alternate server bundle requires explicit expected hashes.')
        if expected_hashes is None:
            expected_hashes = (POLICY_SHA256, CATALOGUE_SHA256)
        if type(expected_hashes) is not tuple or len(expected_hashes) != 2:
            raise ValueError('Two exact configuration identities required.')
        policy, policy_hash = _read(policy_path or CONFIG/'context_relevance_policy.v1.json', expected_hashes[0])
        catalogue, catalogue_hash = _read(catalogue_path or CONFIG/'context_relevance_objectives.v1.json', expected_hashes[1])
        if _canonical(policy) != _canonical(_expected_policy()):
            raise ValueError('Unapproved relative policy semantics.')
        _keys(catalogue, ('version', 'policy_version', 'basis', 'entries'))
        if (catalogue['version'] != CATALOGUE_VERSION or catalogue['policy_version'] != POLICY_VERSION
                or catalogue['basis'] != 'unvalidated_normative_prototype'
                or type(catalogue['entries']) is not list or len(catalogue['entries']) > 5):
            raise ValueError('Unapproved objective catalogue contract.')
        registry = ContextPolicyRegistry.load()
        styles = tuple(sorted(Vocabulary.load().values['style']))
        entries, seen = [], set()
        for item in catalogue['entries']:
            _keys(item, ('situation', 'binding_id', 'objective_id', 'target', 'allowed_venues',
                         'allowed_companions', 'authority', 'explanation', 'limitations'))
            scope = next((s for s in SCOPES if s[0] == item['situation']), None)
            if scope is None or item['situation'] in seen:
                raise ValueError('Unknown or duplicate objective situation.')
            seen.add(item['situation'])
            sid, binding_id, target, venues, companions = scope
            if (item['binding_id'] != binding_id or item['target'] != target
                    or item['allowed_venues'] != list(venues) or item['allowed_companions'] != list(companions)
                    or item['authority'] != 'prototype_convention' or target not in styles):
                raise ValueError('Unapproved objective target/applicability/authority.')
            binding = registry.binding_for(sid)
            if (binding is None or binding.identifier != binding_id or binding.roles != ('unspecified',)
                    or binding.allowed_venues != venues or binding.allowed_companions != companions):
                raise ValueError('Objective and admission scopes disagree.')
            objective = RelativeObjective(item['objective_id'], sid, target, item['authority'],
                                          item['explanation'], item['limitations'])
            entries.append(ObjectiveEntry(objective, binding_id, venues, companions))
        grammar = Path(__file__).parents[1]/'nlp/config/context_grammar.v1.json'
        with grammar.open('rb') as source:
            grammar_raw = source.read(MAX_CONFIGURATION_BYTES+1)
        if len(grammar_raw) > MAX_CONFIGURATION_BYTES:
            raise ValueError('Unbounded interpretation grammar.')
        return cls(policy_hash, catalogue_hash, hashlib.sha256(grammar_raw).hexdigest(),
                   registry, styles, tuple(sorted(entries, key=lambda entry: entry.objective.situation)))

    @property
    def weights(self):
        return (Fraction(3, 5), Fraction(1, 5), Fraction(1, 5))

    def resolve(self, request):
        """One preparation, before candidate enumeration; no file/DB/model I/O.

        No fallback permission here implies an eligible garment. Phase B must
        independently require the existing complete hard-Pass candidate pool.
        """
        def result(state, reason, objective=None):
            return ObjectiveResolution(state, reason, self.policy_sha256, self.catalogue_sha256, objective)
        scopes={s[0] for s in SCOPES} if self.bundle_id=='legacy_8_v1' else {e.objective.situation for e in self.entries}
        if type(request) is not GeneralContextRequest or request.context.bundle_id!=self.bundle_id or request.context.situation.value not in scopes:
            return result('OutOfScope', 'existing_profile_retained')
        if request.context.grammar_sha256 != self.grammar_sha256 or request.context.taxonomy_sha256 != self.registry.taxonomy_hash:
            raise ValueError('Interpretation bundle identity mismatch; no baseline fallback.')
        plan = compile_context(self.registry, request)
        if not plan.available:
            return result('AdmissionUnavailable', plan.reason)
        if request.style is not None:
            if request.style not in self.canonical_styles:
                raise ValueError('Unsupported explicit style; no objective fallback.')
            objective = RelativeObjective('user-stated-style', request.context.situation.value, request.style,
                'explicit_user_style', 'Using your explicitly requested '+request.style+' style as the appearance goal.',
                'Alignment uses recorded styles, which may be unreviewed. Existing hard style and other requirements still apply; no dress code, comfort or independent fashion accuracy is established.')
            return result('Resolved', 'explicit_style_precedence', objective)
        frame = request.context
        if (frame.role.state != 'Unspecified' or frame.dress_code.state != 'Unspecified'
                or frame.formality.state != 'Unspecified' or request.formality is not None):
            return result('ObjectiveUnavailable', 'context_ranking_objective_unavailable')
        entry = next((entry for entry in self.entries if entry.objective.situation == frame.situation.value), None)
        if entry is None:
            return result('ObjectiveUnavailable', 'context_ranking_objective_unavailable')
        return result('Resolved', 'automatic_default', entry.objective)
