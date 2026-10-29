"""SELECT-only adapter over existing storage; no account API or migration changes."""
from contextlib import closing
import sqlite3
from app.application.ports.active_preference_query import ActivePreferenceQuery
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.infrastructure.config import DATABASE_PATH
from app.application.wardrobe.profile_service import current_profile_id


def read_active_preference_rows(conn,user_id):
    """One SELECT on the caller's already authenticated transaction; never BEGIN."""
    profile_id=current_profile_id()
    sql="SELECT id,user_id,preference_type,preference_value_json,weight,source,is_active FROM user_preferences WHERE user_id=? AND is_active=1"
    params=[user_id]
    if profile_id:
        sql+=" AND profile_id=?";params.append(profile_id)
    rows=conn.execute(sql+" ORDER BY preference_type,id",params).fetchall()
    return tuple(PreferenceSnapshot(row['id'],row['user_id'],row['preference_type'],row['preference_value_json'],
        None if row['weight'] is None else str(row['weight']),row['source'],bool(row['is_active'])) for row in rows)


class SqliteActivePreferenceQuery(ActivePreferenceQuery):
    def get_active_preferences(self,user_id):
        if not isinstance(user_id,str) or not user_id.strip():
            raise ValueError("Authenticated user context required.")
        with closing(sqlite3.connect(DATABASE_PATH.resolve().as_uri()+"?mode=ro",uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN")  # Consistent read snapshot; URI forbids writes/creation.
            account = conn.execute("SELECT id FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone()
            if account is None:
                raise ValueError("Active authenticated account required.")
            return read_active_preference_rows(conn,user_id)
