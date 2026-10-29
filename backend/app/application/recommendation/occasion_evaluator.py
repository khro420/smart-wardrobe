"""All worn constituents need explicit owner-declared occasion suitability."""
from app.domain.value_objects.request_candidate_evaluation import MandatoryCondition


def evaluate_condition(candidate,field,value,parser):
    if value not in parser.policy.values(field):
        raise ValueError("Suitability policy unavailable.")
    states = tuple((item.garment.garment_id,parser.parse(item.garment).state_for(field,value)) for item in candidate.members)
    state = "Fail" if any(s == "Fail" for _,s in states) else "Unknown" if any(s == "Unknown" for _,s in states) else "Pass"
    return MandatoryCondition(field,value,state,tuple(identifier for identifier,s in states if s == state))


class OccasionEvaluator:
    def __init__(self,parser):
        self.parser = parser

    def evaluate(self,candidate,value):
        return evaluate_condition(candidate,"occasion",value,self.parser)
