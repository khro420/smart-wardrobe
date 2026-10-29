"""Independent formality declarations, without style inference or hierarchy."""
from app.application.recommendation.occasion_evaluator import evaluate_condition


class FormalityEvaluator:
    def __init__(self,parser):
        self.parser = parser

    def evaluate(self,candidate,value):
        return evaluate_condition(candidate,"formality",value,self.parser)
