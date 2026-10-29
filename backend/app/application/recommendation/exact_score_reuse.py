"""Session-owned bounded reuse of fully validated immutable score values.

No candidate, user identity, mandatory proof or provisional result is cached.
Each factory key includes ALL constructor arguments, including ordered reasons
and detail evidence. typed=True prevents invalid integers/bools from hitting a
previous Fraction-valued entry. Constructors and their validators run on misses;
exceptions are never cached. Eviction changes work only, never candidate sets.
"""
from functools import lru_cache
from fractions import Fraction
from app.domain.value_objects.recommendation_score import ScoreEvidence, ComponentScore


def exact_weighted(weights, contributions):
    return sum(weight*value for weight,value in zip(weights,contributions))


def exact_mean(values):
    return sum(values)/len(values)


def exact_preference(weights, values, denominator):
    return sum(weight*(value or Fraction(0)) for weight,value in zip(weights,values))/denominator


class ExactScoreReuse:
    # Test worker may disable reuse to isolate the other approved optimisations.
    # Production owns a fresh instance per scorer/session; no global value cache.
    enabled = True

    def __init__(self):
        self._evidence = lru_cache(maxsize=256,typed=True)(ScoreEvidence)
        self._component = lru_cache(maxsize=256,typed=True)(ComponentScore)
        self._weighted = lru_cache(maxsize=256,typed=True)(exact_weighted)
        self._fraction = lru_cache(maxsize=256,typed=True)(Fraction)
        self._mean = lru_cache(maxsize=256,typed=True)(exact_mean)
        self._preference = lru_cache(maxsize=256,typed=True)(exact_preference)
        self.evidence = self._evidence if self.enabled else ScoreEvidence
        self.component = self._component if self.enabled else ComponentScore
        self.weighted = self._weighted if self.enabled else exact_weighted
        self.fraction = self._fraction if self.enabled else Fraction
        self.mean = self._mean if self.enabled else exact_mean
        self.preference = self._preference if self.enabled else exact_preference
