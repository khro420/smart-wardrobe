"""Atomic explicit-wearer settings, isolated from the legacy preference API."""
from types import SimpleNamespace
from uuid import uuid4
from app.domain.value_objects.attribute_preferences import DOCUMENT, UPDATE, TYPE, SOURCE, PreferenceDocument, PreferenceError, digest, encode, exact, uuid, HASH, validate_families
from app.application.recommendation.attribute_preference_policy import current_policy,require_policy
from app.application.recommendation.attribute_preference_normalizer import compose
from app.infrastructure.persistence.attribute_preference_query_adapter import capture_rows
from app.application.ports.workflow_runtime import connection,utcnow


def capabilities():
    policy=current_policy()
    return policy.capabilities() if policy else {'contract':'attribute-preference-capabilities-1.0.0','enabled':False}


def _wearer(user_id,profile_id,header=None):
    uuid(profile_id)
    if header is not None and header!=profile_id: raise PreferenceError('WearerMismatch','Wearer path and header disagree.')
    return SimpleNamespace(account_id=user_id,profile_id=profile_id)


def _view(snapshot):
    v=snapshot.to_dict()
    try:effective=compose(snapshot).families()
    except ValueError as exc:raise PreferenceError('PreferenceInvalid','Stored legacy preferences cannot be composed; no repair was performed.',409) from exc
    return {'contract':'attribute-preferences-view-1.0.0','wearer_id':v['wearer_id'],'revision':v['revision'],'document':v['document'],
            'effective':effective,'legacy_digest':v['legacy_digest'],'policy':v['policy']}


def get(user_id,profile_id,header=None):
    require_policy();wearer=_wearer(user_id,profile_id,header)
    with connection() as conn:
        conn.execute('BEGIN');return _view(capture_rows(conn,user_id,wearer))


def update(user_id,profile_id,body,header=None):
    require_policy();wearer=_wearer(user_id,profile_id,header)
    exact(body,('contract','wearer_id','expected_revision','action_id','families'))
    if body['contract']!=UPDATE or body['wearer_id']!=profile_id: raise PreferenceError('WearerMismatch','Preference body and wearer path disagree.')
    uuid(body['action_id']);validate_families(body['families'])
    if type(body['expected_revision']) is not str or not HASH.fullmatch(body['expected_revision']) or len(encode(body))>32768:
        raise PreferenceError('PreferenceInvalid','Invalid preference action revision or size.')
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        snapshot=capture_rows(conn,user_id,wearer);v=snapshot.to_dict();doc=v['document'];action=None if doc is None else doc['last_action']
        input_digest=digest(body)
        if action is not None and action['action_id']==body['action_id']:
            if action['input_digest']==input_digest and action['legacy_digest']==v['legacy_digest']: return _view(snapshot)
            raise PreferenceError('PreferenceConflict','This preference action key has different input or legacy scope.',409)
        if body['expected_revision']!=v['revision']: raise PreferenceError('PreferenceConflict','Preferences changed. Reload before applying.',409)
        previous={} if doc is None else doc['families']
        if body['families']==previous:return _view(snapshot)
        new=PreferenceDocument.from_dict({'contract':DOCUMENT,'families':body['families'],'last_action':{'action_id':body['action_id'],'input_digest':input_digest,'prior_revision':v['revision'],'legacy_digest':v['legacy_digest']}})
        now=utcnow()
        if doc is None:
            conn.execute('INSERT INTO user_preferences (id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active,created_at,updated_at) VALUES (?,?,?,?,?,0,?,0,?,?)',(str(uuid4()),user_id,profile_id,TYPE,new.payload.decode(),SOURCE,now,now))
        else:
            conn.execute('UPDATE user_preferences SET preference_value_json=?,updated_at=? WHERE user_id=? AND profile_id=? AND preference_type=?',(new.payload.decode(),now,user_id,profile_id,TYPE))
        return _view(capture_rows(conn,user_id,wearer))
