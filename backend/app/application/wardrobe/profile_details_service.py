"""Owner-described profile information; an explicitly enabled category policy may consume it."""
import hashlib,json,unicodedata,uuid
from fastapi import HTTPException
from app.infrastructure.persistence.postgresql_repository import connection,utcnow
from app.application.wardrobe.profile_service import historical_profile,require_active_profile

VERSION='wearer-profile-details-1.0.0'

def _empty(profile_id):
    revision=hashlib.sha256((VERSION+':absent:'+profile_id).encode()).hexdigest()
    return {'version':VERSION,'profile_id':profile_id,'gender_identity':None,'revision':revision,'updated_at':None}

def _view(conn,profile_id):
    row=conn.execute('SELECT * FROM wardrobe_profile_details_v1 WHERE profile_id=?',(profile_id,)).fetchone()
    return dict(row) if row else _empty(profile_id)

def _header(profile_id,header):
    if header is not None and header!=profile_id:raise HTTPException(409,{'code':'WearerMismatch','message':'Choose the same wearer for this change.'})

def get(user_id,profile_id,header=None):
    with connection() as conn:
        historical_profile(conn,user_id,profile_id)
        _header(profile_id,header)
        return _view(conn,profile_id)

def update(user_id,profile_id,body,header=None):
    gender=body['gender_identity']
    if gender is not None:
        if type(gender) is not str or unicodedata.normalize('NFC',gender)!=gender or gender!=gender.strip() or not 1<=len(gender)<=60 or any(unicodedata.category(c).startswith('C') for c in gender):
            raise HTTPException(422,'Use a trimmed gender description of 1 to 60 characters, or leave it unspecified.')
    if body['version']!=VERSION:raise HTTPException(422,'Unknown profile-details version.')
    with connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        require_active_profile(conn,user_id,profile_id)
        _header(profile_id,header)
        old=_view(conn,profile_id)
        if body['expected_revision']!=old['revision']:raise HTTPException(409,{'code':'ProfileDetailsConflict','message':'This wearer information changed. Your edits are retained; reload before saving.'})
        value={'version':VERSION,'profile_id':profile_id,'gender_identity':gender,'revision':uuid.uuid4().hex,'updated_at':utcnow()}
        conn.execute('INSERT INTO wardrobe_profile_details_v1 (profile_id,version,gender_identity,revision,updated_at) VALUES (?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET version=excluded.version,gender_identity=excluded.gender_identity,revision=excluded.revision,updated_at=excluded.updated_at',(profile_id,VERSION,gender,value['revision'],value['updated_at']))
        return value
