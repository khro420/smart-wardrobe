"""Real SQLite transactions/connections; no live recommendation orchestration."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
import json
import sqlite3
import threading
import pytest
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.infrastructure.persistence.recommendation_migrations import migrate_recommendations, RecommendationMigrationConflict
from app.domain.value_objects.outfit_candidate import OutfitCandidate, CandidateMember
from app.domain.value_objects.recommendation_persistence import RecommendationWrite, PersistenceConflict, WardrobeChanged
from app.domain.value_objects.recommendation_score import RecommendationScore, ComponentScore, ScoreEvidence


def connect(path):
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "persistence.db"
    monkeypatch.setattr(db, "DATABASE_PATH", path)
    db.initialise_database()
    with db.connection() as c:
        c.execute("INSERT INTO users VALUES('owner','owner@test','','Owner','active','now','now')")
        c.execute("INSERT INTO users VALUES('other','other@test','','Other','active','now','now')")
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES('job','owner','media','completed','now','now')")
        c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES('item','job','vest_dress',1,'media','media','{}','confirmed','now')")
        c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,attributes_json,created_at,updated_at) VALUES('garment','owner','item','media','Original dress','vest_dress','blue','{}','now','now')")
    snapshot = SqliteConfirmedGarmentQuery().get_confirmed_available_garments("owner")[0]
    candidate = OutfitCandidate((CandidateMember(snapshot, "one_piece", 1),))
    command = RecommendationWrite("owner", "homepage", "key", '{}', candidate, '{"structure":"v1"}')
    return path, SqliteRecommendationRepository(path), command


def assistant(command):
    one = ComponentScore(ScoreEvidence("request", Fraction(1), "Available"))
    absent = ComponentScore(ScoreEvidence("compatibility", None, "Unavailable"))
    score = RecommendationScore(one, absent, one, Fraction(1), "compatibility_deferred", "v1", (Fraction(7,10), Fraction(0), Fraction(3,10)))
    return replace(command, operation="assistant", request_text="Suggest an outfit", score=score)


def test_homepage_replay_history_and_scope(store):
    path, repo, cmd = store
    result = repo.persist(cmd)
    assert result["chat_id"] is None and result["total_score"] is None
    assert result["score_metadata"] is None
    assert repo.persist(cmd) == result
    with pytest.raises(PersistenceConflict):
        repo.persist(replace(cmd, request_json='{"changed":true}'))
    assert repo.persist(replace(cmd, submission_key="new"))["id"] != result["id"]
    with pytest.raises(LookupError):
        repo.get("other", result["id"])
    with connect(path) as c:
        c.execute("UPDATE garments SET name='Changed',status='archived' WHERE id='garment'")
    restored = repo.get("owner", result["id"])
    assert len(restored["items"]) == 1
    assert restored["items"][0]["name"] == "Original dress"
    assert not restored["items"][0]["currently_eligible"]
    assert restored["items"][0]["preferred_media_id"] is None
    assert repo.persist(cmd)["id"] == result["id"]  # Lost-response replay does not regenerate.


def test_assistant_actual_scores_and_independent_chat(store):
    path, repo, cmd = store
    result = repo.persist(assistant(cmd))
    assert result["chat_id"] and result["compatibility_score"] is None
    assert result["total_score"] == 1
    assert result["score_metadata"]["weights"][0] == {"numerator": 7, "denominator": 10}
    assert repo.persist(assistant(cmd))["id"] == result["id"]
    assert repo.persist(replace(assistant(cmd), submission_key="another"))["chat_id"] != result["chat_id"]
    # Operation is part of key scope.
    assert repo.persist(cmd)["id"] != result["id"]


def test_inactive_owner_cannot_write_or_replay(store):
    path, repo, cmd = store
    repo.persist(cmd)
    with connect(path) as c:
        c.execute("UPDATE users SET account_status='inactive' WHERE id='owner'")
    with pytest.raises(ValueError, match='Active authenticated owner'):
        repo.persist(cmd)


@pytest.mark.parametrize("stage", ["revalidated", "chat", "recommendation", "item", "snapshot", "metadata", "submission", "before_commit"])
def test_every_write_rolls_back(store, stage):
    path, _, cmd = store
    def fail(where, conn):
        if where == stage:
            raise RuntimeError("injected failure")
    with pytest.raises(RuntimeError):
        SqliteRecommendationRepository(path, fail).persist(assistant(cmd))
    with connect(path) as c:
        for table in ("nlp_chats", "recommendations", "recommendation_items", "recommendation_item_snapshots", "recommendation_metadata", "recommendation_submissions"):
            assert c.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("sql", [
    "UPDATE garments SET status='archived'",
    "UPDATE garments SET primary_colour='red'",
    "UPDATE garments SET custom_tags='[\"changed\"]'",
    "UPDATE garments SET style_tags='[\"classic\"]'",
    "UPDATE garments SET pattern='stripe'",
    "UPDATE garments SET attributes_json='{\"fit\":\"loose\"}'",
    "UPDATE garments SET attributes_json='{\"material\":[\"cotton\"]}'",
    "UPDATE garments SET preferred_media_id='changed-media'",
    "UPDATE garments SET updated_at='later'",
    "UPDATE garments SET user_id='other'",
    "UPDATE garments SET processing_item_id=NULL",
    "UPDATE processing_items SET review_status='accepted'",
    "UPDATE processing_jobs SET user_id='other'",
])
def test_changed_selected_evidence_rejected(store, sql):
    path, repo, cmd = store
    with connect(path) as c:
        c.execute(sql)
    with pytest.raises(WardrobeChanged):
        repo.persist(cmd)
    with connect(path) as c:
        assert c.execute("SELECT count(*) FROM recommendations").fetchone()[0] == 0


def test_concurrent_duplicates_and_changed_payload(store):
    path, repo, cmd = store
    barrier = threading.Barrier(4)
    def write(_):
        barrier.wait(timeout=5)
        return repo.persist(cmd)["id"]
    with ThreadPoolExecutor(4) as pool:
        assert len(set(pool.map(write, range(4)))) == 1
    with connect(path) as c:
        assert c.execute("SELECT count(*) FROM recommendations").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM recommendation_submissions").fetchone()[0] == 1


def test_concurrent_conflicting_payloads(store):
    _, repo, cmd = store
    barrier = threading.Barrier(2)
    def write(command):
        barrier.wait(timeout=5)
        try:
            return repo.persist(command)["id"]
        except PersistenceConflict:
            return "conflict"
    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(write, (cmd, replace(cmd, request_json='{"other":true}'))))
    assert outcomes.count("conflict") == 1


def test_revalidation_lock_blocks_other_writer(store):
    path, _, cmd = store
    reached, release, changed = threading.Event(), threading.Event(), threading.Event()
    def checkpoint(stage, conn):
        if stage == "revalidated":
            reached.set()
            assert release.wait(5)
    def edit():
        c = connect(path)
        try:
            c.execute("BEGIN IMMEDIATE")
            c.execute("UPDATE garments SET primary_colour='red'")
            c.commit()
            changed.set()
        finally:
            c.close()
    with ThreadPoolExecutor(2) as pool:
        writing = pool.submit(SqliteRecommendationRepository(path, checkpoint).persist, cmd)
        assert reached.wait(5)
        editing = pool.submit(edit)
        assert not changed.wait(.15)
        release.set()
        result = writing.result(5)
        editing.result(5)
    assert result["items"][0]["name"] == "Original dress" and changed.is_set()


def test_injected_query_does_not_commit_close_or_rollback(store):
    path, _, cmd = store
    c = connect(path)
    try:
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE garments SET name='Uncommitted'")
        query = SqliteConfirmedGarmentQuery(c)
        assert query.list_available_garment_ids("owner") == ["garment"]
        assert query.get_confirmed_available_garments("owner")[0].name == "Uncommitted"
        assert c.in_transaction
        with connect(path) as other:
            assert other.execute("SELECT name FROM garments").fetchone()[0] == "Original dress"
        c.rollback()
        assert query.get_confirmed_available_garments("owner")[0] == cmd.candidate.members[0].garment
    finally:
        c.close()
    assert SqliteConfirmedGarmentQuery().list_available_garment_ids("owner") == ["garment"]


def test_legacy_read_without_snapshot(store):
    path, repo, _ = store
    with connect(path) as c:
        c.execute("INSERT INTO recommendations(id,user_id,recommendation_type,status,created_at) VALUES('old','owner','homepage','available','now')")
        c.execute("INSERT INTO recommendation_items VALUES('old','garment','one_piece',1,'now')")
    item = repo.get("owner", "old")["items"][0]
    assert not item["snapshot_available"] and item["name"] is None


def test_foreign_keys_unique_order_and_chat(store):
    path, repo, cmd = store
    result = repo.persist(assistant(cmd))
    with connect(path) as c:
        assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("DELETE FROM recommendations WHERE id=?", (result["id"],))
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO recommendation_submissions VALUES('other','assistant','foreign','hash',?)", (result["id"],))
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO recommendations SELECT 'duplicate',user_id,chat_id,recommendation_type,status,created_at,expires_at,request_match_score,compatibility_score,preference_score,total_score FROM recommendations WHERE id=?", (result["id"],))


@pytest.mark.parametrize("conflict", [False, True])
def test_populated_migration_preserves_or_aborts(tmp_path, conflict):
    c = connect(tmp_path / "legacy.db")
    try:
        c.executescript(db.SCHEMA)
        c.execute("INSERT INTO users VALUES('owner','x@test','','Owner','active','now','now')")
        c.execute("INSERT INTO recommendations(id,user_id,recommendation_type,status,created_at) VALUES('old',?,'homepage','available','now')", ("missing" if conflict else "owner",))
        c.commit()
        before = tuple(c.execute("SELECT * FROM recommendations").fetchone())
        if conflict:
            with pytest.raises(RecommendationMigrationConflict):
                migrate_recommendations(c)
            assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='recommendation_submissions'").fetchone()
        else:
            migrate_recommendations(c)
            migrate_recommendations(c)
        assert tuple(c.execute("SELECT * FROM recommendations").fetchone()) == before
        assert not c.in_transaction
    finally:
        c.close()


@pytest.mark.parametrize("case", ["duplicate_chat", "foreign_chat", "missing_chat", "orphan_item", "foreign_item", "bad_order", "duplicate_order"])
def test_migration_conflict_audit_is_atomic(tmp_path, case):
    c = connect(tmp_path / "conflict.db")
    try:
        c.executescript(db.SCHEMA)
        for owner in ("owner", "other"):
            c.execute("INSERT INTO users VALUES(?,?, '',?,'active','now','now')", (owner, owner+'@test', owner))
        c.execute("INSERT INTO nlp_chats VALUES('chat',?,'request',NULL,NULL,'completed','now','now')", ("other" if case == "foreign_chat" else "owner",))
        chat = "missing" if case == "missing_chat" else "chat"
        c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at) VALUES('r','owner',?,'assistant','available','now')", (chat,))
        if case == "duplicate_chat":
            c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at) VALUES('s','owner','chat','assistant','available','now')")
        for identifier in ("a", "b"):
            c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,?,'media','old','vest_dress','{}','now','now')", (identifier, "other" if case == "foreign_item" else "owner"))
        if case in ("orphan_item", "foreign_item", "bad_order", "duplicate_order"):
            c.execute("INSERT INTO recommendation_items VALUES('r',?,'one_piece',?,'now')", ("missing" if case == "orphan_item" else "a", 0 if case == "bad_order" else 1))
        if case == "duplicate_order":
            c.execute("INSERT INTO recommendation_items VALUES('r','b','outerwear',1,'now')")
        c.commit()
        before = list(c.iterdump())
        with pytest.raises(RecommendationMigrationConflict):
            migrate_recommendations(c)
        assert list(c.iterdump()) == before
    finally:
        c.close()


@pytest.mark.parametrize("state", ["confirmed", "accepted", "pending", "rejected", "null", "missing"])
def test_transaction_query_strict_policy_and_legacy_ids(store, state):
    path, _, _ = store
    c = connect(path)
    try:
        c.execute("BEGIN IMMEDIATE")
        if state in ("null", "missing"):
            c.execute("UPDATE garments SET processing_item_id=?", (None if state == "null" else "missing",))
        else:
            c.execute("UPDATE processing_items SET review_status=?", (state,))
        query = SqliteConfirmedGarmentQuery(c)
        assert bool(query.get_confirmed_available_garments("owner")) == (state == "confirmed")
        assert query.list_available_garment_ids("owner") == ["garment"]
        assert query.get_confirmed_available_garments("other") == ()
        assert c.in_transaction
    finally:
        c.rollback()
        c.close()


def test_two_piece_order_snapshot_and_second_item_failure(store):
    path, _, cmd = store
    with connect(path) as c:
        c.execute("UPDATE garments SET category='short_sleeve_top'")
        c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES('second','job','trousers',1,'media','media','{}','confirmed','now')")
        c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES('bottom','owner','second','media','Trousers','trousers','{}','now','now')")
        snapshots = {g.garment_id:g for g in SqliteConfirmedGarmentQuery(c).get_confirmed_available_garments('owner')}
    cmd = replace(cmd, candidate=OutfitCandidate((CandidateMember(snapshots['garment'],'upper',1),CandidateMember(snapshots['bottom'],'lower',2))))
    count = 0
    def fail_second(stage, conn):
        nonlocal count
        if stage == 'item':
            count += 1
            if count == 2:
                raise RuntimeError('second item')
    with pytest.raises(RuntimeError):
        SqliteRecommendationRepository(path, fail_second).persist(cmd)
    with connect(path) as c:
        assert c.execute('SELECT count(*) FROM recommendation_items').fetchone()[0] == 0
    result = SqliteRecommendationRepository(path).persist(cmd)
    assert [(i['garment_id'],i['garment_role'],i['item_order']) for i in result['items']] == [('garment','upper',1),('bottom','lower',2)]
