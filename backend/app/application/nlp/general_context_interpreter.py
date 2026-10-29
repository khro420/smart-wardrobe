"""Compositional, span-preserving interpretation independent of outfit eligibility."""
from pathlib import Path
import hashlib
import json
import re
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.nlp.request_field_extractor import RequestFieldExtractor, UnsupportedMeaning
from app.application.nlp.controlled_value_mapper import ControlledValueMapper
from app.domain.value_objects.general_context_request import ContextSlot, SourceSpan, GeneralContext, GeneralContextRequest, Situation
from app.domain.value_objects.nlp_result import NLPOutcome

GRAMMAR = Path(__file__).with_name('config')/'context_grammar.v1.json'
TAXONOMY = Path(__file__).parents[1]/'recommendation/config/situation_taxonomy.v1.json'


def read_json(path):
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError('Configuration exceeds its bounded schema size.')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate configuration key.')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs), hashlib.sha256(raw).hexdigest()


def keys(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError('Incomplete or unknown configuration fields.')


def strings(value, limit=32):
    if (type(value) is not list or not 0 < len(value) <= limit
            or any(type(v) is not str or not v or len(v) > 100 for v in value)
            or len(set(value)) != len(value)):
        raise ValueError('Invalid bounded vocabulary.')


def load_taxonomy(path=None, *, approved_version='situation-taxonomy-1.3.0'):
    taxonomy, digest = read_json(path or TAXONOMY)
    keys(taxonomy, ('version', 'situations'))
    if taxonomy['version'] != approved_version or type(taxonomy['situations']) is not list or not 1 <= len(taxonomy['situations']) <= 32:
        raise ValueError('Invalid taxonomy schema.')
    situations, phrases = [], set()
    for item in taxonomy['situations']:
        keys(item, ('id', 'label', 'phrases', 'activity', 'venue', 'projection_occasion'))
        for key in ('id', 'label', 'projection_occasion'):
            strings([item[key]])
        strings(item['phrases'])
        for key in ('activity', 'venue'):
            if item[key] is not None:
                strings([item[key]])
        if phrases.intersection(item['phrases']):
            raise ValueError('Ambiguous taxonomy phrases.')
        phrases.update(item['phrases'])
        situations.append(Situation(item['id'], item['label'], tuple(item['phrases']), item['activity'], item['venue'], item['projection_occasion']))
    if len({s.identifier for s in situations}) != len(situations):
        raise ValueError('Duplicate situation.')
    return tuple(situations), digest


def phrase_pattern(phrase):
    return r'(?<!\w)' + r'\s+'.join(map(re.escape, phrase.split())) + r'(?!\w)'


class GeneralContextInterpreter:
    def __init__(self, bundle_id='legacy_8_v1'):
        self.legacy = NLPInterpreter()
        self.vocabulary = self.legacy.vocabulary
        self.bundle_id=bundle_id
        if bundle_id!='legacy_8_v1':
            from app.application.recommendation.context_bundle import ContextBundle, APP
            bundle=ContextBundle.load(bundle_id)
            self.situations,self.taxonomy_hash=load_taxonomy(APP/'application/recommendation/config/situation_taxonomy.v2.json',approved_version='situation-taxonomy-'+bundle.record['registry_version'].removeprefix('context-registry-'))
            self.grammar=bundle.read('application/nlp/config/context_grammar.v2.json')
            self.grammar_hash=bundle.record['grammar_sha256']
            self.extractor=RequestFieldExtractor(self.vocabulary);self.mapper=ControlledValueMapper(self.vocabulary)
            self.hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            return
        self.situations, self.taxonomy_hash = load_taxonomy()
        self.grammar, self.grammar_hash = read_json(GRAMMAR)
        keys(self.grammar, ('version', 'frames', 'roles', 'dress_codes', 'venues', 'temporal', 'goals', 'temporal_contract'))
        if (self.grammar['version'] != 'context-grammar-1.3.0'
                or self.grammar['frames'] != ['going', 'attending', 'having', 'meeting', 'wanting', 'command', 'going_out', 'outfit_question', 'presenting', 'being_interviewed', 'conducting_interview']
                or self.grammar['temporal_contract'] != 'current_wardrobe_no_forecast_or_future_availability'):
            raise ValueError('Unapproved compositional grammar.')
        for key in ('roles', 'venues', 'temporal', 'goals'):
            strings(self.grammar[key])
        if self.grammar['dress_codes'] != {'smart casual': 'smart_casual', 'casual': 'casual', 'formal': 'formal', 'black tie': 'black_tie'}:
            raise ValueError('Unapproved dress code vocabulary.')
        self.extractor = RequestFieldExtractor(self.vocabulary)
        self.mapper = ControlledValueMapper(self.vocabulary)
        self.hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def interpret(self, request_text):
        if self.bundle_id!='legacy_8_v1':
            from app.application.nlp.context_expression_matcher import interpret_expanded
            return interpret_expanded(self,request_text)
        if not isinstance(request_text, str) or not request_text.strip() or len(request_text) > 500:
            return self.legacy.interpret(request_text)
        # A one-character fold preserves every offset into the actual input.
        text = request_text.lower().replace('\u2019', "'").replace('\u2018', "'")
        text = re.sub('[-_\u2010-\u2014]', ' ', text)
        if len(text) != len(request_text):
            return NLPOutcome('UnsupportedRequest', 'unsupported_text_encoding', 'This text cannot be interpreted safely.', request_text)
        events = []
        for situation in self.situations:
            for phrase in situation.phrases:
                events.extend((m, situation) for m in re.finditer(phrase_pattern(phrase), text))
        refinements = {('interview.unspecified','professional.job_interview'), ('presentation.unspecified','academic.presentation'),
                       ('everyday.academic_attendance','academic.presentation')}
        events = [(m,s) for m,s in events if not any(
            other.start() <= m.start() and m.end() <= other.end() and ((s.identifier,t.identifier) in refinements
                or s.identifier == t.identifier and (other.start(),other.end()) != (m.start(),m.end()))
            for other,t in events)]
        # A university venue in an existing context is not a second campus day.
        # Likewise the approved dinner companion frame is not a separate outing.
        events = [(m,s) for m,s in events if not (
            s.identifier == 'everyday.academic_attendance'
            and any(t.identifier not in ('everyday.academic_attendance', 'everyday.shopping', 'everyday.casual_outing') for _,t in events)
            and re.search(r'\b(?:at|in) (?:a |the )?$', text[:m.start()])
            or s.identifier == 'everyday.casual_outing' and m.group() == 'meeting friends'
            and any(t.identifier == 'social.meal' and re.fullmatch(r'\s+for\s+(?:a\s+)?', text[m.end():other.start()]) for other,t in events))]
        if not events:
            return self.legacy.interpret(request_text)
        try:
            if re.search(r"\b(?:no|not|without|avoid|excluding|except|don't|never)\b", text):
                raise UnsupportedMeaning('negation')
            if re.search(r'\b(?:or|either|instead)\b', text):
                raise UnsupportedMeaning('alternatives')
            if len(events) != 1:
                raise UnsupportedMeaning('multiple_requests')
            event_match, situation = events[0]
            working = list(text)
            slots = {}
            def consume(match):
                working[match.start():match.end()] = ' ' * (match.end()-match.start())
            def slot(name, observations):
                if not observations:
                    return
                values = tuple(dict.fromkeys(v for _, v in observations))
                slots[name] = ContextSlot('Known' if len(values) == 1 or name in ('temporal', 'soft_preferences', 'goals') else 'Conflicting', values,
                    tuple(SourceSpan(m.start(), m.end(), request_text[m.start():m.end()]) for m, _ in observations))
                for m, _ in observations:
                    consume(m)
            prefix = re.match(r"\s*(?:please\s+)?(?:(?:i'm|im|i am)\s+(?:going(?:\s+out\s+for|\s+to|\s+on)?|attending|meeting|presenting|being(?=\s+interviewed)|conducting|interviewing|in the audience)|i\s+(?:have|want)|what should i wear)\b", text)
            if prefix:
                if situation.identifier.startswith('everyday.') and re.search(r'\b(?:presenting|conducting|interviewing|being|audience)\b', prefix.group()):
                    raise UnsupportedMeaning('unrecognized_condition')
                consume(prefix)
            elif not self.legacy.classifier.classify(text):
                raise UnsupportedMeaning('unsupported_intent')
            slot('situation', [(event_match, situation.identifier)])
            # Activity is the lexically expressed event/action, never a user role.
            if situation.activity is not None:
                slots['activity'] = ContextSlot('Known', (situation.activity,), slots['situation'].spans)
            if situation.venue is not None:
                slots['venue'] = ContextSlot('Known', (situation.venue,), slots['situation'].spans)
            role_choices = '|'.join(map(re.escape, self.grammar['roles']))
            roles = [(m, m.group(1)) for m in re.finditer(r'\bas (?:a|an|the) ('+role_choices+r')\b', text)]
            if situation.identifier in ('professional.job_interview','interview.unspecified','academic.presentation','presentation.unspecified'):
                for pattern, role in ((r'\bbeing interviewed\b','candidate'), (r'\bconducting\b','interviewer'),
                                      (r'\bpresenting\b','presenter'), (r'\bin the audience\b','attendee')):
                    roles.extend((m,role) for m in re.finditer(pattern,text))
            slot('role', roles)
            if len(roles) > 1:
                raise UnsupportedMeaning('conflicting_role')
            code_choices = '|'.join(phrase_pattern(p) for p in self.grammar['dress_codes'])
            codes = []
            for pattern in (r'\b(?:the )?dress code is ('+code_choices+r')', r'('+code_choices+r')\s+(?='+phrase_pattern(event_match.group())+r')'):
                for m in re.finditer(pattern, text):
                    code = self.grammar['dress_codes'][re.sub(r'\s+', ' ', m.group(1))]
                    codes.append((m, code))
            slot('dress_code', codes)
            if len({v for _, v in codes}) > 1:
                raise UnsupportedMeaning('conflicting_formality')
            slot('temporal', [(m, word) for word in self.grammar['temporal'] for m in re.finditer(phrase_pattern(word), text)])
            if len(slots.get('temporal', ContextSlot()).values) > 1:
                raise UnsupportedMeaning('conflicting_time')
            venues = [(m, venue) for venue in self.grammar['venues'] for m in re.finditer(r'\b(?:at|in) (?:a |the )?('+phrase_pattern(venue)+r')', text)]
            prior_venue = slots.get('venue')
            slot('venue', venues)
            if prior_venue and venues:
                current_venue = slots['venue']
                values = tuple(dict.fromkeys((*prior_venue.values, *current_venue.values)))
                slots['venue'] = ContextSlot('Known' if len(values) == 1 else 'Conflicting', values, (*prior_venue.spans, *current_venue.spans))
            if situation.identifier == 'presentation.unspecified' and slots.get('venue',ContextSlot()).value == 'university':
                situation = next(s for s in self.situations if s.identifier == 'academic.presentation')
                slots['situation'] = ContextSlot('Known',(situation.identifier,),(*slots['situation'].spans,*slots['venue'].spans))
            slot('goals', [(m, goal) for goal in self.grammar['goals'] for m in re.finditer(phrase_pattern(goal), text)])
            slot('companions', [(m, 'friends') for m in re.finditer(r'\bfriends\b', text)])
            # Soft language is represented but has no new ranking semantics.
            soft = []
            for field, value, phrase, _ in self.vocabulary.entries:
                if field not in ('style', 'colours'):
                    continue
                for m in re.finditer(r'\bprefer\s+'+phrase_pattern(phrase), text):
                    soft.append((m, field+':'+value))
            slot('soft_preferences', soft)
            matches = self.extractor.extract(''.join(working))
            fields = self.mapper.map_values(matches)
            if fields['occasion']:
                raise UnsupportedMeaning('conflicting_occasion')
            for field, name in (('style', 'style'), ('colours', 'colours'), ('garment_categories', 'categories'), ('formality', 'formality')):
                relevant = [m for m in matches if m.field == field]
                if relevant:
                    slots[name] = ContextSlot('Known', tuple(dict.fromkeys((m.kind+':' if m.kind else '')+m.canonical_value for m in relevant)),
                        tuple(SourceSpan(m.start, m.end, request_text[m.start:m.end]) for m in relevant))
            code = slots.get('dress_code', ContextSlot()).value
            formality = next(iter(fields['formality']), None)
            if code is not None and formality is not None and code != formality:
                raise UnsupportedMeaning('conflicting_formality')
            frame = GeneralContext(request_text, **slots, grammar_sha256=self.grammar_hash, taxonomy_sha256=self.taxonomy_hash)
            request = GeneralContextRequest(occasion=situation.projection_occasion,
                style=next(iter(fields['style']), None), colours=fields['colours'] or None,
                garment_categories=fields['garment_categories'] or None, formality=code if code is not None else formality, context=frame)
            return NLPOutcome('Supported', 'context_interpreted', 'Situation understood; policy availability is checked separately.', request_text, request, matches)
        except UnsupportedMeaning as error:
            return NLPOutcome('UnsupportedRequest', error.reason, 'This situation contains an unsupported or conflicting condition.', request_text)
