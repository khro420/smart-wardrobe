"""Additive SQLite foundation. Never repair historical conflicts automatically."""


class RecommendationMigrationConflict(RuntimeError):
    pass


def migrate_recommendations(conn):
    # Caller must have finished earlier initializer DDL/DML first.
    if conn.in_transaction:
        raise RuntimeError("Recommendation migration requires its own transaction.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recommendation_migrations'").fetchone():
            if conn.execute("SELECT 1 FROM recommendation_migrations WHERE version=1").fetchone():
                conn.commit()
                return
        audits = (
            "SELECT 1 FROM recommendations WHERE chat_id IS NOT NULL GROUP BY chat_id HAVING COUNT(*)>1",
            "SELECT 1 FROM recommendations r LEFT JOIN users u ON u.id=r.user_id LEFT JOIN nlp_chats c ON c.id=r.chat_id WHERE u.id IS NULL OR (r.chat_id IS NOT NULL AND (c.id IS NULL OR c.user_id<>r.user_id))",
            "SELECT 1 FROM nlp_chats c LEFT JOIN users u ON u.id=c.user_id WHERE u.id IS NULL",
            "SELECT 1 FROM recommendation_items i LEFT JOIN recommendations r ON r.id=i.recommendation_id LEFT JOIN garments g ON g.id=i.garment_id WHERE r.id IS NULL OR g.id IS NULL OR g.user_id<>r.user_id OR i.item_order<1",
            "SELECT 1 FROM recommendation_items GROUP BY recommendation_id,item_order HAVING COUNT(*)>1",
        )
        if any(conn.execute(sql).fetchone() for sql in audits):
            raise RecommendationMigrationConflict("Historical recommendation integrity conflict; no records repaired.")
        statements = (
            "CREATE UNIQUE INDEX IF NOT EXISTS rec_one_chat ON recommendations(chat_id) WHERE chat_id IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS rec_item_order ON recommendation_items(recommendation_id,item_order)",
            "CREATE TABLE IF NOT EXISTS recommendation_metadata (recommendation_id TEXT PRIMARY KEY REFERENCES recommendations(id), provenance_json TEXT NOT NULL, score_json TEXT)",
            "CREATE TABLE IF NOT EXISTS recommendation_item_snapshots (recommendation_id TEXT NOT NULL, garment_id TEXT NOT NULL, display_json TEXT NOT NULL, PRIMARY KEY(recommendation_id,garment_id), FOREIGN KEY(recommendation_id,garment_id) REFERENCES recommendation_items(recommendation_id,garment_id))",
            "CREATE TABLE IF NOT EXISTS recommendation_submissions (user_id TEXT NOT NULL REFERENCES users(id), operation TEXT NOT NULL CHECK(operation IN ('homepage','assistant')), submission_key TEXT NOT NULL, fingerprint TEXT NOT NULL, recommendation_id TEXT NOT NULL UNIQUE REFERENCES recommendations(id), PRIMARY KEY(user_id,operation,submission_key))",
        )
        for sql in statements:
            conn.execute(sql)
        # Scope new ownership enforcement to foundation records. Do not change
        # the legacy writer's semantics or rebuild teammate-owned tables.
        checks = {
            "recommendation_submissions": "NOT EXISTS(SELECT 1 FROM recommendations r LEFT JOIN nlp_chats c ON c.id=r.chat_id WHERE r.id=NEW.recommendation_id AND r.user_id=NEW.user_id AND ((NEW.operation='homepage' AND r.chat_id IS NULL) OR (NEW.operation='assistant' AND c.user_id=NEW.user_id AND c.status='completed'))) OR EXISTS(SELECT 1 FROM recommendation_items i LEFT JOIN garments g ON g.id=i.garment_id WHERE i.recommendation_id=NEW.recommendation_id AND (g.id IS NULL OR g.user_id<>NEW.user_id OR i.item_order<1))",
        }
        for table, condition in checks.items():
            for event in ("INSERT", "UPDATE"):
                conn.execute(f"CREATE TRIGGER IF NOT EXISTS rec_integrity_{table}_{event.lower()} BEFORE {event} ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT,'recommendation ownership/reference violation'); END")
        conn.execute("CREATE TABLE IF NOT EXISTS recommendation_migrations(version INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO recommendation_migrations VALUES(1)")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
