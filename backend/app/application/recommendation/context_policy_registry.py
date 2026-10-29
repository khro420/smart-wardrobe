"""Closed, immutable policy data. Configuration can never select executable code."""
from dataclasses import dataclass
from pathlib import Path
from app.application.nlp.general_context_interpreter import read_json, keys, load_taxonomy
from app.domain.value_objects.general_context_request import Situation

CONFIG = Path(__file__).with_name('config')
SAVED_CONTRACT = 'saved_singleton_style_provisional_v1'
SAVED_LIMITS = 'This is a provisional appearance suggestion using saved labels, which may be unreviewed. It does not establish dress-code compliance, lab, PE, uniform, specialised activity, weather protection, comfort, shoes or accessories.'


def saved_note(label):
    return 'No dress code was supplied. This provisional '+label+' appearance suggestion uses saved casual/smart-casual styles, which may be unreviewed. No dress code was inferred.'
SOCIAL_NOTE = 'No dress code was supplied. This suggestion uses a limited casual/smart-casual appearance guideline; check your plans and any venue requirements.'
SOCIAL_LIMITS = 'This is an appearance suggestion, not confirmation of a venue dress code, weather protection, comfort, shoes or accessories.'
EVERYDAY = {
    'campus_day_appearance_v1': ('everyday.academic_attendance', 'campus', 'CA', ('university', 'campus'), (), 'ordinary academic attendance'),
    'shopping_appearance_v1': ('everyday.shopping', 'shopping', 'SH', (), (), 'ordinary shopping'),
    'casual_outing_appearance_v1': ('everyday.casual_outing', 'casual_outing', 'CO', (), ('friends',), 'an ordinary casual outing'),
}
EVERYDAY_LIMITS = 'This is a provisional everyday appearance suggestion, not proof of lab, PE, uniform, specialised activity, venue compliance, weather protection, comfort, shoes or accessories.'


def everyday_note(label):
    return 'No dress code was supplied. For '+label+', this provisional appearance guideline uses your reviewed casual/smart-casual style; no dress code was inferred.'


@dataclass(frozen=True)
class Predicate:
    identifier: str
    dress_code: str | None
    operator: str
    value: str | tuple[str, ...]
    role: str | None = None
    expressions: tuple = ()


@dataclass(frozen=True)
class Binding:
    identifier: str
    situation: str
    declaration_target: str
    roles: tuple[str, ...]
    assumed_role: str | None
    required_context: tuple[str, ...]
    evidence_contract: str
    predicates: tuple[Predicate, ...]
    unknown_rule: str
    unavailable_rule: str
    policy_version: str = 'wedding-guest-suitability-1.0.0'
    declaration_source: str = 'wedding_overrides_v1'
    allowed_venues: tuple[str, ...] = ()
    allowed_companions: tuple[str, ...] = ()
    unspecified_note: str | None = None
    limits_note: str | None = None
    parent_negative: str | None = None
    appearance_required: bool = False
    role_notes: tuple = ()


def freeze_expression(node, depth=1, budget=None):
    budget = [0] if budget is None else budget
    if depth > 3 or type(node) is not dict:
        raise ValueError('Unbounded predicate expression.')
    operator = node.get('operator')
    if operator in ('all', 'any'):
        keys(node, ('operator', 'children'))
        if type(node['children']) is not list or not 1 <= len(node['children']) <= 4:
            raise ValueError('Invalid predicate fan-out.')
        return (operator, tuple(freeze_expression(child, depth+1, budget) for child in node['children']))
    budget[0] += 1
    if budget[0] > 16:
        raise ValueError('Too many predicate atoms.')
    if operator == 'reviewed_style_in':
        keys(node, ('operator', 'values'))
        if node['values'] not in (['casual'], ['smart casual'], ['casual', 'smart casual']):
            raise ValueError('Unapproved style predicate.')
        return (operator, tuple(node['values']))
    if operator == 'reviewed_observation_equals':
        keys(node, ('operator', 'field', 'value'))
        if (node['field'] in ('collared_neckline', 'tailored_cut', 'structured_shape') and type(node['value']) is bool
                or node['field'] == 'condition_observation' and node['value'] == 'clean_intact'):
            return (operator, node['field'], node['value'])
    raise ValueError('Unapproved predicate/operator.')


def professional_binding(item, situations):
    keys(item, ('id','situation','declaration_target','roles','assumed_role','required_context','evidence_contract',
                'predicates','unknown_rule','unavailable_rule','policy_version','declaration_source','allowed_venues',
                'allowed_companions','unspecified_note','limits_note','parent_negative','appearance_required','role_notes'))
    interview = item['id'] == 'job_interview_appearance_v1'
    sid = 'professional.job_interview' if interview else 'academic.presentation'
    roles = ['candidate','interviewer'] if interview else ['presenter','attendee']
    notes = {} if interview else {
        'presenter':'No dress code was supplied. This provisional university-presenter suggestion uses reviewed smart-casual appearance; it does not establish a course requirement or infer a dress code.',
        'attendee':'No dress code was supplied. This provisional university-attendee suggestion uses reviewed casual/smart-casual appearance; it does not establish a course requirement or infer a dress code.'}
    if (item['situation'] != sid or item['declaration_target'] != sid or next(s.projection_occasion for s in situations if s.identifier == sid) != sid
            or item['roles'] != roles or item['assumed_role'] is not None or item['required_context'] != ['situation','role']
            or item['declaration_source'] != 'parent_negative_only_v1' or item['parent_negative'] != ('work' if interview else 'campus')
            or item['evidence_contract'] != ('owner_appearance_observations_v1' if interview else 'current_owner_reviewed_singleton_style_v1')
            or item['appearance_required'] is not interview or item['allowed_venues'] != (['company','office'] if interview else ['university'])
            or item['allowed_companions'] != [] or item['unspecified_note'] is not None or item['role_notes'] != notes
            or item['unknown_rule'] != ('IP05' if interview else 'AP06') or item['unavailable_rule'] != ('IP04' if interview else 'AP05')
            or item['policy_version'] != ('job-interview-appearance-1.0.0' if interview else 'university-presentation-appearance-1.0.0')
            or item['limits_note'] != 'This is a provisional appearance suggestion, not proof of dress-code compliance, professional suitability, current physical condition, wearer fit, shoes or accessories.'
            or type(item['predicates']) is not list or len(item['predicates']) != (2 if interview else 6)):
        raise ValueError('Unapproved professional/academic binding.')
    predicates, seen = [], set()
    for rule in item['predicates']:
        keys(rule, ('id','role','dress_code','expressions_by_member_role'))
        role, code = rule['role'], rule['dress_code']
        if role not in roles or code not in (('smart_casual',) if interview else (None,'casual','smart_casual')) or (role,code) in seen:
            raise ValueError('Unapproved role/code predicate.')
        seen.add((role,code))
        expected_id = 'IP01' if interview else 'AP01' if code is None and role == 'presenter' else 'AP02' if code is None else 'AP03' if code == 'casual' else 'AP04'
        expressions = rule['expressions_by_member_role']
        if rule['id'] != expected_id or type(expressions) is not dict or set(expressions) != {'upper','lower','one_piece','outerwear'}:
            raise ValueError('Incomplete role predicate.')
        style = ('smart casual',) if interview or code == 'smart_casual' or code is None and role == 'presenter' else ('casual',) if code == 'casual' else ('casual','smart casual')
        frozen = []
        for member, node in expressions.items():
            actual = freeze_expression(node)
            positive = ('reviewed_style_in', style)
            if interview:
                feature = ('reviewed_observation_equals', {'upper':'collared_neckline','lower':'tailored_cut','one_piece':'structured_shape','outerwear':'structured_shape'}[member], True)
                if member == 'outerwear':
                    feature = ('any',(feature,('reviewed_observation_equals','tailored_cut',True)))
                positive = ('all',(positive,feature,('reviewed_observation_equals','condition_observation','clean_intact')))
            if actual != positive:
                raise ValueError('Unapproved positive evidence expression.')
            frozen.append((member,actual))
        predicates.append(Predicate(rule['id'],code,'expression',(),role,tuple(frozen)))
    return Binding(item['id'],sid,sid,tuple(roles),None,('situation','role'),item['evidence_contract'],tuple(predicates),item['unknown_rule'],item['unavailable_rule'],
                   item['policy_version'],item['declaration_source'],tuple(item['allowed_venues']),(),None,item['limits_note'],item['parent_negative'],interview,tuple(notes.items()))


@dataclass(frozen=True)
class ContextPolicyRegistry:
    version: str
    hash: str
    taxonomy_hash: str
    situations: tuple[Situation, ...]
    bindings: tuple[Binding, ...]
    bundle_id: str = 'legacy_8_v1'

    @classmethod
    def load(cls, registry_path=None, taxonomy_path=None, *, bundle_id='legacy_8_v1'):
        if bundle_id!='legacy_8_v1':
            from dataclasses import replace
            from app.application.recommendation.context_bundle import ContextBundle,APP
            bundle=ContextBundle.load(bundle_id)
            data=bundle.read('application/recommendation/config/context_policy_registry.v2.json')
            situations,taxonomy_hash=load_taxonomy(APP/'application/recommendation/config/situation_taxonomy.v2.json',approved_version='situation-taxonomy-'+bundle.record['registry_version'].removeprefix('context-registry-'))
            base=cls.load();original={b.identifier:b for b in base.bindings};bindings=[]
            if data['version']!=bundle.record['registry_version'] or len(data['bindings'])!=len(bundle.record['scopes']):raise ValueError('Invalid expanded binding count/version.')
            for item in data['bindings']:
                if item['id'] in original:
                    old=original[item['id']]
                    bindings.append(replace(old,allowed_venues=tuple(item.get('allowed_venues',old.allowed_venues)),allowed_companions=tuple(item.get('allowed_companions',old.allowed_companions)),policy_version=item.get('policy_version',old.policy_version)))
                    continue
                if (item['evidence_contract']!=SAVED_CONTRACT or item['declaration_source']!='ordinary_parent_negative_v1' or item['roles']!=['unspecified']
                    or item['required_context']!=['situation'] or item['parent_negative'] not in ('campus','work','party','casual_outing','travel')
                    or len(item['predicates'])!=3):raise ValueError('Invalid expanded ordinary policy.')
                predicates=[]
                for rule in item['predicates']:
                    code=rule['dress_code'];expected={None:['casual','smart casual'],'casual':['casual'],'smart_casual':['smart casual']}
                    if code not in expected or rule['operator']!='saved_style_in' or rule['values']!=expected[code]:raise ValueError('Invalid expanded positive predicate.')
                    predicates.append(Predicate(rule['id'],code,rule['operator'],tuple(rule['values'])))
                bindings.append(Binding(item['id'],item['situation'],item['declaration_target'],('unspecified',),None,('situation',),SAVED_CONTRACT,tuple(predicates),item['unknown_rule'],item['unavailable_rule'],item['policy_version'],item['declaration_source'],tuple(item['allowed_venues']),tuple(item['allowed_companions']),item['unspecified_note'],item['limits_note'],item['parent_negative']))
            return cls(data['version'],dict(bundle.resources)['application/recommendation/config/context_policy_registry.v2.json'],taxonomy_hash,situations,tuple(bindings),bundle_id)
        data, digest = read_json(registry_path or CONFIG/'context_policy_registry.v1.json')
        situations, taxonomy_hash = load_taxonomy(taxonomy_path or CONFIG/'situation_taxonomy.v1.json')
        keys(data, ('version', 'schema_version', 'default_activation', 'evidence_contracts', 'bindings'))
        if (data['version'] != 'context-registry-1.4.0' or data['schema_version'] != 'general-context-1.0.0'
                or data['default_activation'] is not False or data['evidence_contracts'] != ['current_owner_reviewed_singleton_style_v1','owner_appearance_observations_v1',SAVED_CONTRACT]
                or type(data['bindings']) is not list or len(data['bindings']) != 8):
            raise ValueError('Unapproved registry capability.')
        bindings = []
        for item in data['bindings']:
            if type(item) is dict and item.get('id') in ('job_interview_appearance_v1','university_presentation_appearance_v1'):
                bindings.append(professional_binding(item, situations))
                continue
            common = ('id', 'situation', 'declaration_target', 'roles', 'assumed_role', 'required_context', 'evidence_contract', 'predicates', 'unknown_rule', 'unavailable_rule')
            everyday = type(item) is dict and item.get('id') in EVERYDAY
            social = type(item) is dict and (item.get('id') in ('date_appearance_v1', 'dinner_appearance_v1') or everyday)
            keys(item, (*common, 'policy_version', 'declaration_source', 'allowed_venues', 'allowed_companions', 'unspecified_note', 'limits_note') if social else common)
            approved = {'wedding_guest_equivalent_v1': ('ceremony.wedding', 'wedding', 'W'),
                        'date_appearance_v1': ('social.date', 'date', 'DT'),
                        'dinner_appearance_v1': ('social.meal', 'dinner', 'DN')}
            approved.update({name: values[:3] for name,values in EVERYDAY.items()})
            if item['id'] not in approved:
                raise ValueError('Unapproved binding.')
            situation_id, target, prefix = approved[item['id']]
            if (item['situation'] != situation_id
                    or item['situation'] not in {s.identifier for s in situations} or item['declaration_target'] != target
                    or next(s.projection_occasion for s in situations if s.identifier == item['situation']) != item['declaration_target']
                    or item['roles'] != (['unspecified'] if social else ['unspecified', 'guest'])
                    or item['assumed_role'] != (None if social else 'guest')
                    or item['required_context'] != ['situation'] or item['evidence_contract'] not in data['evidence_contracts']
                    or item['unknown_rule'] != prefix+('2-04' if social else '04') or item['unavailable_rule'] != prefix+('2-05' if social else '05')
                    or type(item['predicates']) is not list or len(item['predicates']) != 3):
                raise ValueError('Unapproved or unresolved binding.')
            venues, companions, note, limits = (EVERYDAY[item['id']][3], EVERYDAY[item['id']][4], everyday_note(EVERYDAY[item['id']][5]), EVERYDAY_LIMITS) if everyday else (('restaurant',), ('friends',) if target == 'dinner' else (), SOCIAL_NOTE, SOCIAL_LIMITS)
            if social:
                note = saved_note(EVERYDAY[item['id']][5] if everyday else target)
                limits = SAVED_LIMITS
            if social and (item['policy_version'] != target+'-appearance-2.0.0'
                    or item['declaration_source'] != 'legacy_exact_declarations_v1'
                    or item['allowed_venues'] != list(venues)
                    or item['allowed_companions'] != list(companions)
                    or item['unspecified_note'] != note or item['limits_note'] != limits):
                raise ValueError('Unapproved context scope or explanation.')
            if item['evidence_contract'] != (SAVED_CONTRACT if social else 'current_owner_reviewed_singleton_style_v1'):
                raise ValueError('Unapproved binding evidence source.')
            predicates = []
            identifiers, codes = set(), set()
            for rule in item['predicates']:
                keys(rule, ('id', 'dress_code', 'operator', 'values' if social else 'value'))
                if (type(rule['id']) is not str or not rule['id'] or len(rule['id']) > 32
                        or rule['id'] in identifiers or rule['dress_code'] in codes
                        or rule['dress_code'] not in (None, 'casual', 'smart_casual')
                        or rule['operator'] != ('saved_style_in' if social else 'reviewed_style_equals')):
                    raise ValueError('Unapproved predicate/operator or duplicate rule.')
                code_ids = {None: '01', 'casual': '02', 'smart_casual': '03'} if social else {None: '01', 'smart_casual': '02', 'casual': '03'}
                expected_id = prefix+('2-' if social else '')+code_ids[rule['dress_code']]
                if rule['id'] != expected_id:
                    raise ValueError('Unresolved rule identifier.')
                if social:
                    expected_values = {None: ['casual', 'smart casual'], 'casual': ['casual'], 'smart_casual': ['smart casual']}[rule['dress_code']]
                    if rule['values'] != expected_values:
                        raise ValueError('Unapproved positive style set.')
                    value = tuple(rule['values'])
                else:
                    if rule['value'] not in ('smart casual', 'casual'):
                        raise ValueError('Unapproved reviewed style.')
                    value = rule['value']
                identifiers.add(rule['id'])
                codes.add(rule['dress_code'])
                predicates.append(Predicate(rule['id'], rule['dress_code'], rule['operator'], value))
            bindings.append(Binding(item['id'], item['situation'], item['declaration_target'], tuple(item['roles']), item['assumed_role'], tuple(item['required_context']), item['evidence_contract'], tuple(predicates), item['unknown_rule'], item['unavailable_rule'], **{
                name: tuple(item[name]) if name in ('allowed_venues', 'allowed_companions') else item[name]
                for name in ('policy_version', 'declaration_source', 'allowed_venues', 'allowed_companions', 'unspecified_note', 'limits_note') if social}))
        if {b.identifier for b in bindings} != {'wedding_guest_equivalent_v1','date_appearance_v1','dinner_appearance_v1','job_interview_appearance_v1','university_presentation_appearance_v1', *EVERYDAY}:
            raise ValueError('Missing or duplicate approved binding.')
        return cls(data['version'], digest, taxonomy_hash, tuple(situations), tuple(bindings))

    def binding_for(self, situation):
        return next((b for b in self.bindings if b.situation == situation), None)

    def capabilities(self):
        result={'version': self.version, 'situations': [
            {'id': s.identifier, 'label': s.label, 'policy_available': self.binding_for(s.identifier) is not None}
            for s in self.situations], 'limits': 'Ordinary campus, shopping, outings, date and dinner use exact declarations or provisional saved-style information, which may be unreviewed. Ordinary class excludes lab, PE and uniform requirements. Wedding and university-presentation policies still require their reviewed evidence; interviews additionally require reviewed construction and dated condition observations. Other recognised situations are unavailable.'}
        if self.bundle_id!='legacy_8_v1':
            from app.application.recommendation.context_bundle import ContextBundle
            grammar=ContextBundle.load(self.bundle_id).read('application/nlp/config/context_grammar.v2.json')
            expressions={item['situation']:item for item in grammar['expressions']}
            for item in result['situations']:
                if not item['policy_available']:continue
                situation=next(s for s in self.situations if s.identifier==item['id'])
                expression=expressions.get(item['id'])
                phrase=expression['anchors'][0] if expression else situation.phrases[0]
                example='Suggest an outfit for '+phrase
                if expression and expression['required_any'] and not any(word in phrase for word in expression['required_any']):
                    example+=' at '+('university' if 'university' in expression['required_any'] else expression['required_any'][0])
                item['example']=example
            result.update(bundle_id=self.bundle_id,limits='Ordinary contexts use provisional saved labels without a review requirement. Prototype appearance goals are unvalidated and do not establish dress-code compliance, comfort, weather protection, equipment or safety. Wedding/presentation/interview evidence remains strict. Unsupported modifiers are not ignored.')
        return result
