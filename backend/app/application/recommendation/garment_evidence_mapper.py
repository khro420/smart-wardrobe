"""Classification cache owned by one request session; never reads persistence."""
import re
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.colour_classifier import ColourClassifier
from app.domain.value_objects.request_candidate_evaluation import AttributeEvidence, GarmentRequestEvidence


class GarmentEvidenceMapper:
    def __init__(self, vocabulary=None, classifier=None):
        self.vocabulary = vocabulary or Vocabulary.load()
        self.classifier = classifier or ColourClassifier(self.vocabulary)
        self.style_aliases = {value: value for value in self.vocabulary.values["style"]}
        self.style_aliases.update({phrase:value for field,value,phrase,_ in self.vocabulary.entries if field == "style"})
        self._cache = {}

    @property
    def cache_size(self):
        return len(self._cache)

    def classify(self, garment):
        cached = self._cache.get(garment.garment_id)
        if cached is not None:
            if cached[0] != garment:
                raise ValueError("Conflicting garment evidence in one session.")
            return cached[1]
        tags = garment.style_tags
        if "style_tags" in garment.invalid_attributes:
            style = AttributeEvidence((),"Malformed","style_tags")
        elif tags is None:
            style = AttributeEvidence((),"Missing","style_tags")
        else:
            recognized, unrecognized = [], False
            for tag in tags:
                normalized = re.sub(r"\s+"," ",tag.strip().casefold())
                value = self.style_aliases.get(normalized)
                if value:
                    recognized.append(value)
                else:
                    unrecognized = True
            style = AttributeEvidence(tuple(recognized),"Unrecognized" if unrecognized else "Known","style_tags")
        evidence = GarmentRequestEvidence(self.classifier.classify(garment.primary_colour),style)
        self._cache[garment.garment_id] = (garment,evidence)
        return evidence
