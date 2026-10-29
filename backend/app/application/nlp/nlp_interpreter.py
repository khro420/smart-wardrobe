"""Independent interpretation orchestration following report section 4.10.1."""
import logging
from app.application.nlp.request_preprocessor import RequestPreprocessor, InvalidRequestText
from app.application.nlp.intent_classifier import IntentClassifier
from app.application.nlp.request_field_extractor import RequestFieldExtractor, UnsupportedMeaning
from app.application.nlp.controlled_value_mapper import ControlledValueMapper
from app.application.nlp.structured_request_builder import StructuredRequestBuilder
from app.application.nlp.vocabulary import Vocabulary
from app.domain.value_objects.nlp_result import NLPOutcome


class NLPInterpreter:
    def __init__(self, vocabulary=None, preprocessor=None, classifier=None, extractor=None, mapper=None, builder=None):
        self.vocabulary = vocabulary or Vocabulary.load()
        self.preprocessor = preprocessor or RequestPreprocessor()
        self.classifier = classifier or IntentClassifier()
        self.extractor = extractor or RequestFieldExtractor(self.vocabulary)
        self.mapper = mapper or ControlledValueMapper(self.vocabulary)
        self.builder = builder or StructuredRequestBuilder()

    def interpret(self, request_text: object) -> NLPOutcome:
        original = request_text if isinstance(request_text, str) else None
        try:
            processed = self.preprocessor.preprocess(request_text)
        except InvalidRequestText as exc:
            return NLPOutcome("InvalidInput", "invalid_text", str(exc), original)
        except Exception:
            logging.getLogger(__name__).error("NLP preprocessing failed")
            return NLPOutcome("ProcessingError", "interpretation_failed", "The outfit request could not be interpreted. Please try again.", original)
        try:
            if not self.classifier.classify(processed.normalized):
                return NLPOutcome("UnsupportedRequest", "unsupported_intent", "Enter one supported outfit recommendation request.", original)
            matches = self.extractor.extract(processed.normalized)
            fields = self.mapper.map_values(matches)
            request = self.builder.build(fields)
            return NLPOutcome("Supported", "interpreted", "Outfit request interpreted.", original, request, matches)
        except UnsupportedMeaning as exc:
            return NLPOutcome("UnsupportedRequest", exc.reason, "This request contains conditions the current interpreter cannot represent. Submit one request using the supported vocabulary.", original)
        except Exception:
            # No original request text or exception details are logged/exposed.
            logging.getLogger(__name__).error("NLP interpretation failed")
            return NLPOutcome("ProcessingError", "interpretation_failed", "The outfit request could not be interpreted. Please try again.", original)
