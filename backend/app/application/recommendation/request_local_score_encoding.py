"""Private per-pass encoding of independently computed immutable C1 scores.

Wire format and full score_from_json replay are unchanged. No candidate result,
admission, first-pass cache, garment object or connection is retained here.
"""
from collections import OrderedDict
from dataclasses import fields
from fractions import Fraction
import json
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
from app.domain.value_objects.compatibility_decision import CompatibilityDecision,DecisionCompatibilityComponent
from app.application.recommendation.decision_score_codec import score_from_json,score_to_json
from app.application.recommendation.assistant_scoring_selection import DECISION

_CLASSES=(ScoreEvidence,ComponentScore,RecommendationScore,CompatibilityDecision,DecisionCompatibilityComponent)
_FIELDS={cls:tuple((f.name,json.dumps(f.name)) for f in sorted(fields(cls),key=lambda f:f.name)) for cls in _CLASSES}


class _UnsupportedEncoding(Exception):pass


class LocalScoreEncoding:
    """At most 256 exact typed leaf keys/texts, owned by one scoring pass."""
    def __init__(self,*,limit=256):
        if type(limit) is not int or not 0<=limit<=256:raise ValueError('Bounded local score encoding required.')
        self.limit=limit;self._cache=OrderedDict()
        self._json=json.JSONEncoder(sort_keys=True,separators=(',',':'),allow_nan=False)
        self.hits=self.misses=self.replays=0

    @property
    def cache_size(self):return len(self._cache)

    def _remember(self,key,build):
        if key in self._cache:
            self.hits+=1;self._cache.move_to_end(key);return self._cache[key]
        self.misses+=1;text=build()
        if self.limit:
            self._cache[key]=text
            if len(self._cache)>self.limit:self._cache.popitem(last=False)
        return text

    def _value(self,value):
        kind=type(value)
        if kind is Fraction:
            # Typed key: bool/int/float equality can never disguise a change.
            if type(value.numerator) is not int or type(value.denominator) is not int:raise _UnsupportedEncoding()
            return self._remember(('fraction',value.numerator,value.denominator),lambda:self._json.encode({'numerator':value.numerator,'denominator':value.denominator}))
        if kind is ScoreEvidence:
            if type(value.name) is not str or type(value.state) is not str or type(value.observed) is not int or type(value.possible) is not int or type(value.reasons) is not tuple or any(type(x) is not str for x in value.reasons):raise _UnsupportedEncoding()
            if value.value is None:ratio=None
            elif type(value.value) is Fraction and type(value.value.numerator) is int and type(value.value.denominator) is int:ratio=(value.value.numerator,value.value.denominator)
            else:raise _UnsupportedEncoding()
            key=('evidence',value.name,ratio,value.state,value.observed,value.possible,value.reasons)
            return self._remember(key,lambda:self._object(value))
        if kind in _FIELDS:return self._object(value)
        if kind is tuple:return '['+','.join(self._value(v) for v in value)+']'
        if value is None or kind in (str,int,bool,float):return self._json.encode(value)
        raise _UnsupportedEncoding()

    def _object(self,value):
        return '{'+','.join(key+':'+self._value(getattr(value,name)) for name,key in _FIELDS[type(value)])+'}'

    def encode(self,score):
        # Keep all other public profiles/subclasses on their unchanged codecs.
        if type(score) is not RecommendationScore or type(score.compatibility) is not DecisionCompatibilityComponent or score.profile_name!=DECISION:
            return score_to_json(score)
        try:text=self._value(score)
        except _UnsupportedEncoding:return score_to_json(score)
        self.replays+=1
        if score_from_json(text)!=score:raise ValueError('Decision metadata replay mismatch.')
        return text
