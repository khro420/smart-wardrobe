"""Bounded wedding grammar; other requests delegate to the unchanged v1 NLP."""
from types import MappingProxyType
import hashlib
from pathlib import Path
import re
from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.nlp.vocabulary import Vocabulary
from app.application.nlp.request_field_extractor import RequestFieldExtractor, UnsupportedMeaning
from app.application.nlp.controlled_value_mapper import ControlledValueMapper
from app.application.nlp.request_preprocessor import InvalidRequestText
from app.domain.value_objects.contextual_outfit_request import ContextualOutfitRequest, WeddingContext
from app.domain.value_objects.nlp_result import NLPOutcome

VERSION = 'contextual-nlp-1.0.0'
CODE = r'smart casual|casual|formal|black tie'


class ContextualNLPInterpreter:
    def __init__(self):
        self.legacy = NLPInterpreter()
        base = self.legacy.vocabulary
        values = dict(base.values)
        values['occasion'] = values['occasion'] | {'wedding'}
        self.vocabulary = Vocabulary(VERSION, (*base.entries, ('occasion', 'wedding', 'wedding', None)),
                                     MappingProxyType(values), base.groups)
        self.extractor = RequestFieldExtractor(self.vocabulary)
        self.mapper = ControlledValueMapper(self.vocabulary)
        self.hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def interpret(self, request_text):
        try:
            processed = self.legacy.preprocessor.preprocess(request_text)
        except InvalidRequestText:
            return self.legacy.interpret(request_text)
        text = processed.normalized
        if not re.search(r'\bwedding\b', text):
            return self.legacy.interpret(request_text)
        # v1 has historical encoding-specific punctuation handling. Correct real
        # Unicode punctuation only in the new grammar; do not rewrite v1.
        text = text.replace('\u2019', "'").replace('\u2018', "'")
        text = re.sub('[\u2010-\u2014]', ' ', text)
        try:
            # Safeguards run on original normalized text, before any grammar spans
            # are consumed. Unsupported modifiers are never silently dropped.
            if re.search(r"\b(?:no|not|without|avoid|excluding|except|don't|never)\b", text):
                raise UnsupportedMeaning('negation')
            if re.search(r'\b(?:or|either|instead)\b', text):
                raise UnsupportedMeaning('alternatives')
            if len(re.findall(r'\bwedding\b', text)) != 1:
                raise UnsupportedMeaning('multiple_requests')
            working = list(text)
            def consume(match):
                working[match.start():match.end()] = ' ' * (match.end() - match.start())
            situation = re.match(r"(?:please\s+)?(?:i'm|im|i am)\s+(?:going to|attending)\b", text)
            if situation:
                consume(situation)
            elif not self.legacy.classifier.classify(text):
                raise UnsupportedMeaning('unsupported_intent')
            roles = list(re.finditer(r'\bas (?:a|the) (guest|bride|groom|bridesmaid|groomsman)\b', text))
            if len(roles) > 1:
                raise UnsupportedMeaning('conflicting_role')
            role = roles[0].group(1) if roles else 'unspecified'
            for match in roles:
                consume(match)
            codes = []
            for pattern in (rf'\b(?:the )?dress code is ({CODE})\b', rf'\b({CODE}) (?=wedding\b)'):
                for match in re.finditer(pattern, text):
                    codes.append(match.group(1).replace(' ', '_'))
                    consume(match)
            matches = self.extractor.extract(''.join(working))
            fields = self.mapper.map_values(matches)
            codes.extend(fields['formality'])
            if len(set(codes)) > 1:
                raise UnsupportedMeaning('conflicting_formality')
            if fields['occasion'] != ('wedding',):
                raise UnsupportedMeaning('conflicting_occasion')
            code = codes[0] if codes else None
            context = WeddingContext(role, 'guest' if role == 'unspecified' else None, code)
            request = ContextualOutfitRequest(occasion='wedding', style=next(iter(fields['style']), None),
                colours=fields['colours'] or None, garment_categories=fields['garment_categories'] or None,
                formality=code, context=context)
            return NLPOutcome('Supported', 'context_interpreted', 'Wedding context interpreted.', request_text, request, matches)
        except UnsupportedMeaning as error:
            return NLPOutcome('UnsupportedRequest', error.reason,
                              'This situation contains an unsupported or conflicting condition.', request_text)

