"""Existing-route owner review; independent namespace and transactional writes."""
from dataclasses import asdict
import hashlib
import hmac
import json
from fastapi import HTTPException
from app.domain.value_objects.general_context_evidence import KEY, AppearanceEvidence, project_appearance_evidence


def revision(row):
    values = [row[k] for k in ('id', 'user_id', 'category', 'preferred_media_id', 'style_tags', 'attributes_json', 'additional_attributes')]
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode()).hexdigest()


def view(row):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import _snapshot
    garment = _snapshot(row)
    evidence = garment.appearance_evidence
    return {'revision': revision(row), 'current': evidence.current(garment), **asdict(evidence)}


def invalidate(attrs):
    attrs.pop(KEY, None)


def save(conn, row, payload, now):
    if not hmac.compare_digest(payload['revision'], revision(row)):
        raise HTTPException(409, 'Garment evidence changed. Reload and review before retrying.')
    try:
        attrs = json.loads(row['attributes_json'])
        mirror = json.loads(row['additional_attributes']) if row['additional_attributes'] is not None else {}
        if type(attrs) is not dict or type(mirror) is not dict or attrs.get(KEY) != mirror.get(KEY):
            raise ValueError('Inconsistent mirrors.')
    except (ValueError, TypeError):
        raise HTTPException(422, 'Stored appearance evidence needs explicit repair before review.') from None
    action = payload['appearance_review']
    if action.get('withdraw') is True:
        attrs.pop(KEY, None); mirror.pop(KEY, None)
    else:
        raw = {'schema_version': '1.0.0', 'source': 'owner_review', 'category': row['category'],
               'media_id': row['preferred_media_id'], 'construction_features': action['construction_features'],
               'condition_observation': action['condition_observation'], 'reviewed_at': now}
        if project_appearance_evidence(raw, True).state != 'Known':
            raise HTTPException(422, 'Invalid appearance review.')
        attrs[KEY] = raw; mirror[KEY] = raw
    conn.execute('UPDATE garments SET attributes_json=?,additional_attributes=?,updated_at=? WHERE id=?',
                 (json.dumps(attrs), json.dumps(mirror), now, row['id']))
