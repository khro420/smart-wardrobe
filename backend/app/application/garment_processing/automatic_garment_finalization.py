"""Pure readiness assessment; the existing wardrobe writer owns all transactions."""
import json
import math
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY, project_saved_attribute_evidence

MODE = 'automatic_structural_v1'
MANUAL = 'manual_review_v1'
KEY = 'automatic_garment_admission_v1'
VERSION = 'automatic-garment-admission-1.0.0'


def record(owner, job, item, state='prepared', reason=None, garment_id=None):
    return {'version': VERSION, 'mode': MODE, 'owner_id': owner, 'job_id': job,
            'item_id': item, 'state': state, 'reason': reason, 'garment_id': garment_id}


def current(raw, item, owner):
    return (isinstance(raw, dict) and set(raw) == {'version','mode','owner_id','job_id','item_id','state','reason','garment_id'}
            and raw.get('state') in ('prepared', 'incomplete', 'blocked', 'saved')
            and (raw.get('reason') is None or isinstance(raw.get('reason'), str) and len(raw['reason']) <= 100)
            and (raw.get('garment_id') is None or isinstance(raw.get('garment_id'), str) and 0 < len(raw['garment_id']) <= 100)
            and ((raw['state'] == 'saved' and raw['garment_id'] is not None and raw['reason'] is None)
                 or raw['state'] != 'saved' and raw['garment_id'] is None)
            and raw == record(owner, item['job_id'], item['id'], raw['state'], raw['reason'], raw['garment_id']))


def readiness(item, attrs, owner):
    if not current(attrs.get(KEY), item, owner):
        return 'invalid_admission_record'
    if attrs[KEY]['state'] == 'saved':
        return 'candidate_not_ready'
    category = attrs.get('reviewed_category') or item['detected_category']
    if category not in GARMENT_STRUCTURE:
        return 'category_missing_or_unsupported'
    if item['review_status'] not in ('pending', 'accepted'):
        return 'candidate_not_ready'
    confidence = item['confidence']
    if isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        return 'invalid_processing_metadata'
    if item['preferred_media_id'] not in (item['crop_media_id'], item['vtoff_media_id']) or not item['preferred_media_id']:
        return 'representation_unavailable'
    source = project_saved_attribute_evidence(attrs.get(SOURCE_KEY), SOURCE_KEY in attrs, attrs.get('style'),
                                              category, item['preferred_media_id'], owner)
    if source.state != 'Known':
        return 'stale_or_malformed_saved_source'
    return None


def projection(items, owner):
    entries = [(item, json.loads(item['attributes_json'])) for item in items]
    if not entries or not any(KEY in attrs for _, attrs in entries):
        return {'mode': MANUAL, 'state': 'manual', 'reason': None, 'garment_ids': []}
    if not all(current(attrs.get(KEY), item, owner) for item, attrs in entries):
        return {'mode': MODE, 'state': 'blocked', 'reason': 'invalid_admission_record', 'garment_ids': []}
    records = [attrs[KEY] for _, attrs in entries]
    if all(r['state'] == 'saved' and r['garment_id'] for r in records):
        return {'mode': MODE, 'state': 'saved', 'reason': None, 'garment_ids': [r['garment_id'] for r in records]}
    first = next((r for r in records if r['state'] in ('blocked', 'incomplete')), records[0])
    return {'mode': MODE, 'state': first['state'], 'reason': first['reason'], 'garment_ids': []}
