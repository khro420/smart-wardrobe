"""One consistent wearer-scoped preference capture, also usable under writer lock."""
from contextlib import closing
from dataclasses import asdict
import sqlite3
from app.domain.value_objects.attribute_preferences import (
    AttributePreferenceSnapshot, PreferenceDocument, PreferenceError, TYPE, SOURCE, SNAPSHOT, uuid, encode, digest,
)
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.application.recommendation.attribute_preference_policy import RESOURCE_HASH
from app.application.wardrobe.profile_service import require_active_profile
from app.infrastructure.config import DATABASE_PATH


def capture_rows(conn, account_id, wearer,policy=None):
    if wearer is None or wearer.account_id!=account_id: raise PreferenceError('PreferenceInvalid','Explicit owned wearer context is required.')
    profile_id=uuid(wearer.profile_id)
    require_active_profile(conn,account_id,profile_id)
    rows=conn.execute('SELECT id,user_id,profile_id,preference_type,preference_value_json,weight,source,is_active FROM user_preferences WHERE user_id=? AND profile_id=? AND (is_active=1 OR preference_type=?) ORDER BY preference_type,id LIMIT 18',(account_id,profile_id,TYPE)).fetchall()
    if len(rows)>17: raise PreferenceError('PreferenceCapacityExceeded','Preference row capture exceeds its bound.')
    reserved=[r for r in rows if r['preference_type']==TYPE]
    legacy=[r for r in rows if r['preference_type']!=TYPE]
    if len(reserved)>1: raise PreferenceError('PreferenceInvalid','Duplicate P2 preference documents.',409)
    if len(legacy)>16: raise PreferenceError('PreferenceCapacityExceeded','Too many legacy preference rows.')
    document=None
    if reserved:
        r=reserved[0]
        if r['is_active']!=0 or r['source']!=SOURCE or r['weight']!=0: raise PreferenceError('PreferenceInvalid','Invalid P2 storage sentinel.',409)
        try:
            if type(r['preference_value_json']) is not str: raise PreferenceError('PreferenceInvalid','Invalid stored preference type.')
            document=PreferenceDocument(r['preference_value_json'].encode('utf-8')).to_dict()
        except (PreferenceError,UnicodeError) as exc:raise PreferenceError('PreferenceInvalid','Stored preference document is invalid; no repair was performed.',409) from exc
    try: old=[asdict(PreferenceSnapshot(r['id'],r['user_id'],r['preference_type'],r['preference_value_json'],None if r['weight'] is None else str(r['weight']),r['source'],bool(r['is_active']))) for r in legacy]
    except ValueError as exc:raise PreferenceError('PreferenceInvalid','Stored legacy preference data is invalid.',409) from exc
    snapshot=AttributePreferenceSnapshot.from_dict({'contract':SNAPSHOT,'account_id':account_id,'wearer_id':profile_id,'document':document,'legacy':old,'legacy_digest':digest(old),'revision':digest({'legacy':old,'document':document}),'policy':RESOURCE_HASH})
    from app.application.recommendation.attribute_preference_policy import require_policy
    from app.application.recommendation.attribute_preference_codec import build_archive_snapshot
    try:return build_archive_snapshot(snapshot,policy or require_policy())
    except PreferenceError:raise
    except ValueError as exc:raise PreferenceError('PreferenceInvalid','Stored legacy preferences cannot be captured; no repair was performed.',409) from exc


class SqliteAttributePreferenceQuery:
    def __init__(self,database_path=None,policy=None):
        self.database_path=database_path or DATABASE_PATH
        self.policy=policy

    def capture_locked(self,conn,account_id,wearer): return capture_rows(conn,account_id,wearer,self.policy)

    def capture(self,account_id,wearer):
        with closing(sqlite3.connect(self.database_path.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
            conn.row_factory=sqlite3.Row;conn.execute('BEGIN')
            if conn.execute("SELECT id FROM users WHERE id=? AND account_status='active'",(account_id,)).fetchone() is None:
                raise PreferenceError('PreferenceInvalid','Active authenticated account is required.')
            return capture_rows(conn,account_id,wearer,self.policy)
