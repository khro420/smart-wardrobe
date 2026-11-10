"""Pure field-aware description facts. No model, database, file or network calls."""
from fractions import Fraction
import re
import unicodedata

from app.domain.value_objects.garment_description_evidence import (
    DescriptionField, FIELDS, ORIGINS, CANONICAL_ENUMS, digest, seal_field, encode,
)

MISSING = object()
SETS = frozenset(('style', 'material', 'descriptive_tags'))
HEX_COLOUR = re.compile(r'^#[0-9a-fA-F]{6}$')
DECIMAL = re.compile(r'^(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)$')
RESERVED = ('rec:', 'owner_style_', 'saved_attribute_', 'garment_description_',
            'contextual_suitability_', 'appearance_evidence_', 'automatic_')


def _safe_digest(raw):
    if raw is MISSING:
        return digest({'missing': True})
    try:
        return digest(raw)
    except (TypeError, ValueError):
        return digest({'malformed_type': type(raw).__name__})


def _palette(raw):
    if type(raw) is not list or len(raw) > 5:
        raise ValueError('Invalid palette.')
    result, seen, total, complete = [], set(), Fraction(0), True
    for entry in raw:
        if type(entry) is not dict or not set(entry) <= {'hex', 'coverage'} or 'hex' not in entry:
            raise ValueError('Invalid palette entry.')
        colour = entry['hex']
        if not isinstance(colour, str) or not HEX_COLOUR.fullmatch(colour) or colour.lower() in seen:
            raise ValueError('Invalid palette colour.')
        colour = colour.lower()
        seen.add(colour)
        coverage = entry.get('coverage')
        if coverage is None:
            complete = False
        else:
            if isinstance(coverage, bool) or not isinstance(coverage, (str, int, float)):
                raise ValueError('Invalid palette coverage.')
            coverage = str(coverage)
            if not DECIMAL.fullmatch(coverage):
                raise ValueError('Invalid coverage precision or range.')
            total += Fraction(coverage)
        result.append({'hex': colour, 'coverage': coverage})
    if total > 1:
        raise ValueError('Palette coverage exceeds one.')
    # Sum below1 remains partial, not an invented renormalized measurement.
    return result, complete and total == 1


def classify(field, raw, policy, *, legacy=False):
    """Return state, recorded canonical values, completeness, fixed reason codes."""
    if field not in FIELDS:
        raise ValueError('Unknown description field.')
    if raw is MISSING or raw is None:
        return 'Absent', [], 'unknown', ['missing' if raw is MISSING else 'null']
    if isinstance(raw, str) and not raw.strip():
        return 'Unspecified', [], 'unknown', ['blank']
    if field == 'colour_palette':
        values, complete = _palette(raw)
        return ('Known' if values else 'KnownEmpty'), values, ('complete_recorded_set' if complete or not values else 'partial'), ([] if complete or not values else ['unobserved_palette_mass'])
    if field == 'colour_dominance':
        if type(raw) is not bool:
            raise ValueError('Dominance must be a boolean.')
        return 'Known', [raw], 'complete_recorded_set', []
    if field in SETS:
        raw = [raw] if isinstance(raw, str) else raw
        if type(raw) is not list or len(raw) > 20 or any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in raw):
            raise ValueError('Invalid recorded set.')
        if len(set(raw)) != len(raw):
            raise ValueError('Duplicate recorded values.')
        if not raw:
            return 'KnownEmpty', [], 'complete_recorded_set', []
        values = [policy.legacy_alias(field, v) if legacy else v for v in raw]
        if len(set(values)) != len(values):
            raise ValueError('Alias collision in recorded set.')
        if field == 'descriptive_tags':
            if any(v.casefold().startswith(RESERVED) for v in values):
                return 'Unrecognized', [], 'unknown', ['reserved_description_tag']
            return 'Known', values, 'complete_recorded_set', []
        known = [v for v in values if v in policy.values(field)]
        if field == 'material' and 'not sure' in values:
            return 'Unsure', known, 'partial', ['material_unsure']
        if len(known) != len(values):
            return 'Unrecognized', known, 'partial' if known else 'unknown', ['unsupported_value']
        return 'Known', known, 'complete_recorded_set', []
    if not isinstance(raw, str) or len(raw) > 100:
        raise ValueError('Invalid description scalar.')
    if field == 'garment_name':
        return 'Known', [unicodedata.normalize('NFC', raw)], 'complete_recorded_set', []
    value = policy.legacy_alias(field, raw) if legacy else raw
    if field in ('primary_colour', 'secondary_colour') and HEX_COLOUR.fullmatch(value):
        return 'Known', [value.lower()], 'complete_recorded_set', []
    if value not in policy.values(field):
        return 'Unrecognized', [], 'unknown', ['unsupported_value']
    return 'Known', [value], 'complete_recorded_set', []


def normalise_field(field, raw, policy, *, origin='legacy_selected_unverified',
                    category=None, media_id=None, event_id=None, recorded_at=None,
                    source_revision=None, dependencies=None, location=None):
    if origin not in ORIGINS or field not in FIELDS:
        raise ValueError('Unknown description origin or field.')
    try:
        if raw is not MISSING and len(encode(raw)) > 16384:
            raise ValueError('Optional raw field exceeds bound.')
        state, values, complete, reasons = classify(field, raw, policy, legacy=origin == 'legacy_selected_unverified')
    except (ValueError, TypeError, OverflowError):
        state, values, complete, reasons = 'Malformed', [], 'unknown', ['invalid_or_oversize_source']
    applicable = 'applicable'
    if category in ('shorts', 'trousers', 'skirt') and field in ('neckline', 'sleeve_length'):
        applicable, state = 'inapplicable', 'Inapplicable'
        reasons = ['bottom_field_inapplicable']
    elif field in ('neckline', 'sleeve_length') and category not in CANONICAL_ENUMS['category']:
        applicable = 'unknown'
        reasons = list(dict.fromkeys(reasons + ['unknown_role']))
    if field == 'sleeve_length' and values and isinstance(category, str):
        conflicts = (category.startswith('short_sleeve_') and values[0] in ('sleeveless', 'wrist-length')
                     or category.startswith('long_sleeve_') and values[0] in ('sleeveless', 'short'))
        if conflicts and applicable == 'applicable':
            state, reasons = 'Conflicting', ['category_sleeve_conflict']
    possible = values if state in ('Conflicting', 'Inapplicable') else []
    canonical = [] if state in ('Conflicting', 'Inapplicable') else values
    source_digest = _safe_digest(raw)
    location = location or '/recorded/' + field
    channel_value = values if values else None
    if origin in ('model_suggestion', 'legacy_selected_unverified'):
        if isinstance(raw, str) and len(raw) <= 100:
            channel_value = [raw]
        elif isinstance(raw, list) and len(raw) <= 20 and all(isinstance(v, str) and len(v) <= 100 for v in raw):
            channel_value = list(raw)
    channel = {'origin': origin, 'value': channel_value,
               'source_digest': source_digest, 'source_location': location,
               'event_id': event_id, 'recorded_at': recorded_at, 'source_revision': source_revision}
    selected, suggestion = (None, channel) if origin == 'model_suggestion' else (channel, None)
    if origin == 'model_suggestion' and (raw is MISSING or raw is None):
        suggestion = None
    elif origin == 'model_suggestion' and state not in ('Inapplicable', 'Unspecified'):
        possible, canonical = values, []
        state, complete = ('Malformed' if state == 'Malformed' else 'Unrecognized'), 'unknown'
        reasons = list(dict.fromkeys(reasons + ['unregistered_model_vocabulary']))
    record = {'state': state, 'canonical_values': canonical, 'possible_values': possible,
              'completeness': complete, 'applicability': applicable,
              'selected': selected, 'suggestion': suggestion,
              'source_refs': [{'location': location, 'digest': source_digest}],
              'binding': {'category': category, 'media_id': media_id, 'field_revision': '',
                          'dependency_revisions': dependencies or {}},
              'uncertainty_reasons': reasons}
    return DescriptionField.from_dict(seal_field(record))


def qualified(record):
    """Source qualification for future operations, never a suitability decision."""
    value = record.to_dict() if isinstance(record, DescriptionField) else record
    return (value['state'] in ('Known', 'KnownEmpty') and value['selected'] is not None
            and value['selected']['origin'] in ('owner_selected', 'owner_reported_label')
            and all(value['selected'][key] is not None for key in ('event_id', 'recorded_at', 'source_revision'))
            and value['applicability'] == 'applicable')
