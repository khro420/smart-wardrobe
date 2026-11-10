"""Description views and atomic-update preparation; transaction belongs to caller."""
import copy
import json
import math
from uuid import uuid4

from app.application.wardrobe.description_normalizer import (
    MISSING, SETS, RESERVED, normalise_field, classify, qualified,
)
from app.domain.value_objects.garment_description_evidence import (
    KEY, CONTRACT, UPDATE_CONTRACT, FIELDS, RESOURCE_HASHES, LIMIT,
    GarmentDescriptionEvidence, digest, encode, seal_field, exact_keys,
)

RAW_KEY = 'description_raw_suggestions_v1'
RAW_CONTRACT = 'garment-description-raw-source-1.0.0'
TOP = {'garment_name': 'name', 'category': 'category',
       'primary_colour': 'primary_colour', 'pattern': 'pattern'}
ATTR = {'style': 'style', 'material': 'material', 'silhouette': 'fit',
        'colour_temperature': 'color_temperature', 'colour_dominance': 'is_dominant',
        'descriptive_tags': 'custom_tags', 'secondary_colour': 'secondary_colour',
        'colour_palette': 'color_palette', 'neckline': 'neckline', 'sleeve_length': 'sleeve_length'}
VISUAL = frozenset(('style', 'pattern', 'silhouette', 'neckline', 'sleeve_length',
                    'primary_colour', 'secondary_colour', 'colour_palette',
                    'colour_temperature', 'colour_dominance'))
DEPENDENT = frozenset(('secondary_colour', 'colour_palette', 'colour_temperature', 'colour_dominance'))


class DescriptionUpdateError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def _json_object(value):
    if isinstance(value, dict):
        return copy.deepcopy(value)
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, RecursionError):
        return {}


def attributes(row):
    return _json_object(dict(row).get('attributes_json', dict(row).get('attributes')))


def category_media(row, attrs):
    row = dict(row)
    return (row.get('category') or attrs.get('reviewed_category') or row.get('detected_category'),
            row.get('preferred_media_id'))


def revision(row, account_id):
    row = dict(row)
    relevant = ('id', 'user_id', 'processing_item_id', 'attributes_json', 'additional_attributes',
                'attributes', 'category', 'detected_category', 'preferred_media_id', 'name',
                'primary_colour', 'secondary_colour', 'pattern', 'style_tags', 'custom_tags')
    return digest({'contract': 'garment-description-revision-1.0.0', 'account_id': account_id,
                   'row': {key: row[key] for key in relevant if key in row}})


def _raw_values(row, attrs):
    row = dict(row)
    values = {field: attrs.get(key, MISSING) for field, key in ATTR.items()}
    category, _ = category_media(row, attrs)
    values.update(garment_name=row.get('name', attrs.get('name', MISSING)), category=category,
                  primary_colour=row.get('primary_colour') or attrs.get('primary_colour', attrs.get('primary_color', MISSING)),
                  pattern=row.get('pattern') if row.get('pattern') is not None else attrs.get('pattern', MISSING))
    if 'secondary_colour' in row:
        values['secondary_colour'] = row['secondary_colour']
    for field, column in (('style', 'style_tags'), ('descriptive_tags', 'custom_tags')):
        if row.get(column) is not None:
            try:
                values[field] = json.loads(row[column]) if isinstance(row[column], str) else row[column]
            except (ValueError, TypeError):
                values[field] = {'invalid_column': True}
    tags = values['descriptive_tags']
    if isinstance(tags, str):
        tags = [tags]
    if isinstance(tags, list):
        for field, prefix in (('neckline', 'neckline: '), ('sleeve_length', 'sleeve length: ')):
            if field not in attrs:
                found = list(dict.fromkeys(v[len(prefix):] for v in tags if isinstance(v, str) and v.startswith(prefix)))
                values[field] = found[0] if len(found) == 1 else found if found else MISSING
    return values


def capture_suggestions(attrs):
    """Call before detector merge/role cleanup; preserve only raw suggestion channels."""
    return {'contract': RAW_CONTRACT,
            'visible_attributes': copy.deepcopy(attrs.get('fashionpedia_visible_attributes')),
            'flattened_silhouette': copy.deepcopy(attrs.get('fit')),
            'source_metadata': copy.deepcopy(attrs.get('attribute_suggestion_source'))}


def _changed(record, state, reason):
    result = copy.deepcopy(record)
    result['state'] = state
    result['uncertainty_reasons'] = list(dict.fromkeys(result['uncertainty_reasons'] + [reason]))
    if len(result['uncertainty_reasons']) > 8:
        result['state'] = 'Malformed'
        result['uncertainty_reasons'] = ['too_many_uncertainty_reasons']
    return seal_field(result)


def _document(subject, records):
    value = {'contract': CONTRACT, 'normalizer_version': 'description-normalizer-1.0.0',
             'vocabulary_hash': RESOURCE_HASHES['garment_description_vocabulary.v1.json'],
             'registry_hash': RESOURCE_HASHES['model_vocabulary_registry.v1.json'],
             'subject': subject, 'revision': '', 'fields': records}
    value['revision'] = digest(value)
    return GarmentDescriptionEvidence.from_dict(value)


def _subject(row, account_id, candidate):
    row = dict(row)
    return {'account_id': account_id,
            'source_processing_item_id': row.get('id') if candidate else row.get('processing_item_id'),
            'garment_id': None if candidate else row.get('id')}


def _malformed(subject, category, media_id, reason):
    records = {}
    for field in FIELDS:
        record = normalise_field(field, None, None, category=category, media_id=media_id).to_dict()
        records[field] = _changed(record, 'Malformed', reason)
    return _document(subject, records)


def project(row, account_id, policy=None, *, candidate=False):
    """Read-only, deterministic; stored version reader needs no active normalizer loader."""
    row = dict(row)
    attrs = attributes(row)
    subject = _subject(row, account_id, candidate)
    category, media_id = category_media(row, attrs)
    for key in ('attributes_json', 'additional_attributes'):
        if key in row and row[key] is not None:
            try:
                parsed = json.loads(row[key]) if isinstance(row[key], str) else row[key]
                if not isinstance(parsed, dict):
                    raise ValueError('Invalid description container.')
            except (TypeError, ValueError, RecursionError):
                return _malformed(subject, category, media_id, 'invalid_stored_description') if policy is not None or KEY in attrs else None
    raw = _raw_values(row, attrs)
    stored = attrs.get(KEY)
    if stored is not None:
        try:
            document = GarmentDescriptionEvidence.from_dict(stored).to_dict()
            if document['subject'] != subject:
                raise ValueError('Wrong description subject.')
            mirror = _json_object(row.get('additional_attributes'))
            if 'additional_attributes' in row and mirror.get(KEY) != stored:
                raise ValueError('Description mirrors disagree.')
        except (ValueError, TypeError, OverflowError, RecursionError):
            return _malformed(subject, category, media_id, 'invalid_stored_description')
        records = document['fields']
        for field, record in records.items():
            binding = record['binding']
            if field in VISUAL and (binding['category'] != category or binding['media_id'] != media_id):
                records[field] = _changed(record, 'Stale', 'category_or_media_changed')
                continue
            selected = record['selected']
            if selected is not None:
                current = digest({'missing': True}) if raw[field] is MISSING else _digest_raw(raw[field])
                if current != selected['source_digest']:
                    records[field] = _changed(record, 'Stale', 'recorded_value_changed')
                    continue
            dependency = binding['dependency_revisions'].get('primary_colour')
            if dependency is not None and dependency != _digest_raw(raw['primary_colour']):
                records[field] = _changed(record, 'Stale', 'primary_colour_changed')
        return _document(subject, records)
    if policy is None:
        return None
    records = {}
    source = attrs.get(RAW_KEY)
    heads = source.get('visible_attributes') if isinstance(source, dict) else attrs.get('fashionpedia_visible_attributes')
    heads = heads if isinstance(heads, dict) else {}
    oversized_heads = len(heads) > 16
    for field in FIELDS:
        record = normalise_field(field, raw[field], policy, category=category, media_id=media_id).to_dict()
        if field in ('neckline', 'sleeve_length') and isinstance(raw[field], list) and len(raw[field]) > 1:
            record = _changed(record, 'Conflicting', 'competing_legacy_field_tags')
        head_name = {'silhouette': 'silhouette', 'neckline': 'neckline', 'sleeve_length': 'sleeve_length', 'pattern': 'pattern'}.get(field)
        head = heads.get(head_name)
        label = head.get('value') if isinstance(head, dict) else MISSING
        source_location = ('/description_raw_suggestions_v1/visible_attributes/' if isinstance(source, dict) else '/fashionpedia_visible_attributes/') + str(head_name) + '/value'
        if field == 'silhouette' and label is MISSING and isinstance(source, dict):
            label = source.get('flattened_silhouette', MISSING)
            source_location = '/description_raw_suggestions_v1/flattened_silhouette'
        if label is not MISSING and label is not None:
            suggestion = normalise_field(field, label, policy, origin='model_suggestion',
                                         category=category, media_id=media_id,
                                         location=source_location).to_dict()
            confidence = head.get('confidence') if isinstance(head, dict) else None
            bad_confidence = confidence is not None and (type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1)
            record['suggestion'] = suggestion['suggestion']
            record['possible_values'] = suggestion['possible_values']
            if record['state'] == 'Absent':
                record['state'] = 'Malformed' if oversized_heads or bad_confidence else suggestion['state']
                record['uncertainty_reasons'] = ['invalid_model_source'] if oversized_heads or bad_confidence else suggestion['uncertainty_reasons']
            record = seal_field(record)
        records[field] = record
    try:
        return _document(subject, records)
    except ValueError:
        return _malformed(subject, category, media_id, 'description_projection_over_budget')


def _digest_raw(value):
    if value is MISSING:
        return digest({'missing': True})
    try:
        return digest(value)
    except (ValueError, TypeError):
        return digest({'malformed_type': type(value).__name__})


def view(row, account_id, policy=None, *, candidate=False):
    description = project(row, account_id, policy, candidate=candidate)
    if description is None:
        return None
    value = description.to_dict()
    editable = policy is not None and not any('invalid_stored_description' in record['uncertainty_reasons'] for record in value['fields'].values())
    return {'contract': CONTRACT, 'update_contract': UPDATE_CONTRACT, 'editable': editable,
            'revision': revision(row, account_id), 'evidence': value,
            'source_qualified': {field: qualified(record) for field, record in value['fields'].items()}}


def prepare_update(row, account_id, payload, policy, *, candidate=False):
    """Validate under the caller's lock; return trusted legacy input and typed plan."""
    action = payload.get('description_update')
    if action is None:
        return payload, None
    if policy is None:
        raise DescriptionUpdateError('DescriptionUnavailable')
    try:
        stored = attributes(row).get(KEY)
        if stored is not None:
            current = project(row, account_id, policy, candidate=candidate).to_dict()
            if any('invalid_stored_description' in record['uncertainty_reasons'] for record in current['fields'].values()):
                raise DescriptionUpdateError('Stored description evidence is invalid; no repair was performed.', 409)
        exact_keys(action, ('contract', 'expected_revision', 'operations'))
        if action['contract'] != UPDATE_CONTRACT or len(encode(action)) > LIMIT:
            raise ValueError('Invalid description update/version/size.')
        if action['expected_revision'] != revision(row, account_id):
            raise DescriptionUpdateError('Description changed. Reload before applying.', 409)
        operations = action['operations']
        if type(operations) is not dict or not operations or not set(operations) <= set(FIELDS):
            raise ValueError('Unknown description operation.')
        result = copy.deepcopy(payload)
        manual = dict(result.get('attributes') or {})
        plan = {}
        for field, operation in operations.items():
            if type(operation) is not dict:
                raise ValueError('Invalid field operation.')
            kind = operation.get('kind')
            exact_keys(operation, ('kind', 'value') if kind == 'set' else ('kind',))
            target = TOP.get(field) or ATTR[field]
            if (field in TOP and target in payload) or (field not in TOP and target in manual):
                raise ValueError('Legacy and typed operations conflict.')
            if kind == 'set':
                raw = operation['value']
                if field in SETS and type(raw) is not list:
                    raise ValueError('Use a canonical value set.')
                if field == 'colour_palette' and (type(raw) is not list or any(type(e) is not dict or e.get('coverage') is not None and type(e.get('coverage')) is not str for e in raw)):
                    raise ValueError('Use exact decimal-string coverage.')
                state, values, _, _ = classify(field, raw, policy)
                if state not in ('Known', 'KnownEmpty'):
                    raise ValueError('Use a canonical supported value or uncertainty operation.')
                raw = values if field in SETS or field == 'colour_palette' else values[0]
            elif kind == 'clear' and field not in ('garment_name', 'category'):
                raw = None
            elif kind == 'empty' and field in SETS | {'colour_palette'}:
                raw = []
            elif kind == 'unsure' and field == 'material':
                raw = ['not sure']
            else:
                raise ValueError('Unsupported field operation.')
            plan[field] = raw
            if field in TOP:
                result[target] = raw
            else:
                # Keep the pre-existing palette/snapshot numeric encoding; the
                # new selected channel retains the exact submitted decimals.
                manual[target] = [{**e, 'coverage': float(e['coverage']) if e['coverage'] is not None else None} for e in raw] if field == 'colour_palette' and raw is not None else raw
                if field == 'descriptive_tags':
                    previous = _raw_values(row, attributes(row))['descriptive_tags']
                    previous = [] if previous is MISSING or previous is None else [previous] if isinstance(previous, str) else previous
                    if type(previous) is not list or any(not isinstance(tag, str) for tag in previous):
                        raise DescriptionUpdateError('Stored tags require explicit repair.', 409)
                    protected = [tag for tag in previous if tag.casefold().startswith(RESERVED)]
                    combined = list(dict.fromkeys(protected + (raw or [])))
                    if len(combined) > 20:
                        raise ValueError('Preserved declarations and literal tags exceed the tag limit.')
                    manual[target] = combined
        result['attributes'] = manual
        return result, plan
    except DescriptionUpdateError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise DescriptionUpdateError(str(exc)) from exc


def finish_update(row, account_id, attrs, category, media_id, plan, policy, now,
                  *, candidate=False, name=None, primary_colour=MISSING, pattern=MISSING):
    """Call after old owner-style validation. Produces no event for unchanged fields."""
    if plan is None:
        return
    before = project(row, account_id, policy, candidate=candidate).to_dict()
    records = before['fields']
    new_row = {**dict(row), 'attributes_json': json.dumps(attrs), 'category': category,
               'preferred_media_id': media_id}
    for key, value in (('name', name), ('primary_colour', primary_colour), ('pattern', pattern)):
        if value is not MISSING and value is not None or key in plan or key == 'name' and 'garment_name' in plan:
            new_row[key] = value
    # Mirrored tag/style/secondary columns are written after this preparation.
    for column in ('style_tags', 'custom_tags', 'secondary_colour'):
        new_row.pop(column, None)
    raw = _raw_values(new_row, attrs)
    old_category, old_media = category_media(row, attributes(row))
    old_primary = _raw_values(row, attributes(row))['primary_colour']
    primary_changed = _digest_raw(old_primary) != _digest_raw(raw['primary_colour'])
    event_id = str(uuid4())
    old_revision = revision(row, account_id)
    for field in FIELDS:
        if field in plan:
            dependencies = {'primary_colour': _digest_raw(raw['primary_colour'])} if field in DEPENDENT else {}
            fresh = normalise_field(field, plan[field] if field in ('colour_palette', 'descriptive_tags') else raw[field], policy, origin='owner_selected',
                                     category=category, media_id=media_id, event_id=event_id,
                                     recorded_at=now, source_revision=old_revision,
                                     dependencies=dependencies).to_dict()
            if field in ('colour_palette', 'descriptive_tags'):
                fresh['selected']['source_digest'] = _digest_raw(raw[field])
                fresh['source_refs'][0]['digest'] = _digest_raw(raw[field])
            fresh['suggestion'] = records[field]['suggestion']
            records[field] = seal_field(fresh)
        elif field in VISUAL and (category != old_category or media_id != old_media):
            records[field] = _changed(records[field], 'Stale', 'category_or_media_changed')
        elif primary_changed and field in DEPENDENT:
            records[field] = _changed(records[field], 'Stale', 'primary_colour_changed')
    try:
        attrs[KEY] = _document(before['subject'], records).to_dict()
    except ValueError as exc:
        raise DescriptionUpdateError('Description update exceeds evidence encoding limits.') from exc


def transfer(attrs, account_id, processing_item_id, garment_id):
    """Materialization preserves original source/event identity; no human event created."""
    if KEY not in attrs:
        return
    try:
        document = GarmentDescriptionEvidence.from_dict(attrs[KEY]).to_dict()
        if document['subject'] != {'account_id': account_id, 'source_processing_item_id': processing_item_id, 'garment_id': None}:
            raise ValueError('Wrong candidate description subject.')
        document['subject']['garment_id'] = garment_id
        attrs[KEY] = _document(document['subject'], document['fields']).to_dict()
    except (ValueError, TypeError) as exc:
        raise DescriptionUpdateError('Invalid candidate description evidence.', 409) from exc
