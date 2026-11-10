import sqlite3
import pytest
from tests.test_verified_subtype_registry import declared
from app.infrastructure.persistence.garment_subtype_repository import SqliteGarmentSubtypeStore
def journal():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    SqliteGarmentSubtypeStore.initialize(conn);return conn
def test_sql_ordinal_and_action_uniqueness_and_rollback():
    conn=journal();store=SqliteGarmentSubtypeStore();_,event,_=declared()
    store.append(conn,event)
    with pytest.raises(sqlite3.IntegrityError):store.append(conn,event)
    conn.rollback();assert conn.execute('SELECT count(*) FROM garment_subtype_events_v1').fetchone()[0]==0
def test_unregistered_existing_schema_is_never_repaired():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE garment_subtype_events_v1 (unsafe TEXT)')
    with pytest.raises(ValueError):SqliteGarmentSubtypeStore.initialize(conn)
