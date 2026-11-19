"""Narrow, auditable model transport normalization; never visual verification.

Historical readers stay strict. Only this new observation envelope permits
stable deduplication of byte-identical labels in bounded attribute value arrays.
"""
from copy import deepcopy
from hashlib import sha256
import json
from typing import Literal
from pydantic import Field, model_validator
from . import observation_v11 as visual
from .contract import Frozen, Digest, Short

VERSION = 'outfit-review-observation-1.1.1'
NORMALIZER = 'identical-attribute-label-dedup-1.0.0'
FIELDS = ('colours', 'pattern', 'sleeve_length', 'sleeve_state', 'style')


class LabelDedup(Frozen):
    path: Short
    before: tuple[Short, ...] = Field(min_length=2, max_length=4)
    after: tuple[Short, ...] = Field(min_length=1, max_length=4)


class Normalization(Frozen):
    version: Literal['identical-attribute-label-dedup-1.0.0'] = NORMALIZER
    raw_sha256: Digest
    normalized_json_sha256: Digest
    changes: tuple[LabelDedup, ...] = Field(max_length=120)
    basis: Literal['identical_labels_only_not_visual_verification'] = 'identical_labels_only_not_visual_verification'


def normalize(raw: str):
    if len(raw.encode('utf-8')) > 65536:
        raise ValueError('Oversized model observation')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict) or value.get('version') != visual.VERSION:
        raise ValueError('Normalization requires the current model prediction contract')
    items = value.get('items')
    if type(items) is not list or len(items) > 24:
        raise ValueError('Invalid or oversized item inventory')
    changes = []
    for index, item in enumerate(items):
        if type(item) is not dict:
            raise ValueError('Invalid item')
        for field in FIELDS:
            fact = item.get(field)
            if type(fact) is not dict:
                continue  # Strict typed validation below diagnoses missing facts.
            labels = fact.get('values')
            if type(labels) is not list or len(labels) > 4 or any(type(v) is not str for v in labels):
                raise ValueError('Invalid or oversized attribute values')
            distinct = list(dict.fromkeys(labels))
            if labels != distinct:
                changes.append(LabelDedup(path=f'/items/{index}/{field}/values', before=tuple(labels), after=tuple(distinct)))
                fact['values'] = distinct
    canonical = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    # All other original validation, including contradictory observed values,
    # unsupported labels and Unknown/value consistency, remains in force.
    prediction = visual.parse_prediction(canonical)
    record = Normalization(raw_sha256=sha256(raw.encode('utf-8')).hexdigest(),
                           normalized_json_sha256=sha256(canonical.encode('utf-8')).hexdigest(), changes=tuple(changes))
    return prediction, record


class Observation(visual.Observation):
    version: Literal['outfit-review-observation-1.1.1'] = VERSION
    normalization: Normalization

    @model_validator(mode='after')
    def raw_binding(self):
        prediction, record = normalize(self.raw_response)
        if prediction != self.prediction or record != self.normalization:
            raise ValueError('Prediction or normalization differs from original raw source')
        return self


def observe(image, run, raw):
    prediction, record = normalize(raw)
    return Observation(image=image, run=run, raw_response=raw, prediction=prediction, normalization=record)


def decoding_schema():
    """Express existing state/cardinality invariants in the model-facing schema.

    Uncertain alternatives remain representable. Uniqueness is still validated
    independently; exact repeated labels are covered by the explicit normalizer.
    """
    schema = deepcopy(visual.Prediction.model_json_schema())
    for name in ('ColourFact', 'PatternFact', 'SleeveFact', 'RollFact', 'StyleFact'):
        definition = schema['$defs'][name]
        branches = []
        for state in ('unknown', 'observed', 'uncertain'):
            branch = deepcopy(definition)
            branch['properties']['state'] = {'type': 'string', 'const': state}
            labels = branch['properties']['values']
            labels['minItems'] = 0 if state == 'unknown' else 1
            labels['maxItems'] = 0 if state == 'unknown' else 1 if state == 'observed' and name in ('PatternFact', 'SleeveFact', 'RollFact') else 4
            branches.append(branch)
        schema['$defs'][name] = {'anyOf': branches}
    return schema
