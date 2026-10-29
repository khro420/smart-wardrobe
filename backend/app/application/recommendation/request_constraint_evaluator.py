"""Minimum collective constraints; no compatibility or preference scoring."""
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.domain.value_objects.request_candidate_evaluation import MandatoryCondition, RequestEvaluation


class RequestConstraintEvaluator:
    def __init__(self, mapper=None, vocabulary=None, optimized=True):
        self.vocabulary = vocabulary or Vocabulary.load()
        self.mapper = mapper or GarmentEvidenceMapper(self.vocabulary)
        self.optimized = optimized

    def supports(self, request):
        if request.occasion is not None or request.formality is not None:
            return False
        if request.style is not None and request.style not in self.vocabulary.values["style"]:
            return False
        if request.colours is not None and any(value not in self.vocabulary.values["colours"] for value in request.colours):
            return False
        return not request.garment_categories or all((item.kind,item.value) in self.vocabulary.values["garment_categories"] for item in request.garment_categories)

    def evaluate(self, candidate, request):
        if not self.supports(request):
            raise ValueError("Request requires an unavailable policy.")
        conditions = []
        for constraint in request.garment_categories or ():
            members = self.vocabulary.groups[constraint.value] if constraint.kind == "group" else (constraint.value,)
            ids = tuple(item.garment.garment_id for item in candidate.members if item.garment.category in members)
            conditions.append(MandatoryCondition("garment_categories",constraint.kind+":"+constraint.value,"Pass" if ids else "Fail",ids))
        # Provable category failure short-circuits expensive evidence work.
        # It cannot change aggregate Fail precedence or any emitted candidate.
        if self.optimized and any(item.state == "Fail" for item in conditions):
            return RequestEvaluation(tuple(conditions))
        if request.colours or request.style:
            evidence = [(item,self.mapper.classify(item.garment)) for item in candidate.members]
        else:
            evidence = []
        for colour in request.colours or ():
            ids = tuple(item.garment.garment_id for item,value in evidence if colour in value.colour.values)
            unknown = any(value.colour.state != "Known" for _,value in evidence)
            conditions.append(MandatoryCondition("colours",colour,"Pass" if ids else "Unknown" if unknown else "Fail",ids))
        if request.style:
            base = [(item,value.style) for item,value in evidence if item.role != "outerwear"]
            ids = tuple(item.garment.garment_id for item,value in base if request.style in value.values)
            unknown = any(value.state != "Known" for _,value in base)
            conditions.append(MandatoryCondition("style",request.style,"Pass" if ids else "Unknown" if unknown else "Fail",ids))
        return RequestEvaluation(tuple(conditions))
