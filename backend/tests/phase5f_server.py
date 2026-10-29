"""Disposable Phase 5F workload. Synthetic pre-confirmed records, not onboarding."""
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporary = tempfile.TemporaryDirectory(prefix="phase5f-")
os.environ.update(SMART_WARDROBE_DATA_DIR=temporary.name, SMART_WARDROBE_DATABASE=str(Path(temporary.name)/"verification.db"), SMART_WARDROBE_AI_MODE="development",
                  SMART_WARDROBE_VTOFF_ENABLED="off", SMART_WARDROBE_HOMEPAGE_ENABLED="true",
                  SMART_WARDROBE_ASSISTANT_ENABLED="true", SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED="false",
                  SMART_WARDROBE_ALLOW_DEV_IDENTITY="false", SMART_WARDROBE_TOKEN_SECRET="isolated-phase5f-test-secret")
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.security import hash_password
from app.main import app
import uvicorn

db.initialise_database()
with db.connection() as c:
    for size in (1, 20, 50, 100, 200):
        owner = f"load-{size}"
        c.execute("INSERT INTO users VALUES(?,?,?,'Synthetic workload','active','now','now')",
                  (owner, owner+"@example.test", hash_password("Isolated-test-password-123")))
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES(?,?,'synthetic-media','completed','now','now')", (owner,owner))
        counts = (int(size*.4),int(size*.4),int(size*.1),size-int(size*.4)*2-int(size*.1))
        if size == 1: counts = (0,0,1,0)  # Separate functional-audit user, not a latency workload.
        first = None
        for (role, category), count in zip((("top","vest"),("bottom","trousers"),("dress","vest_dress"),("outerwear","long_sleeve_outwear")),counts):
            for index in range(count):
                identifier = f"{owner}-{role}-{index:04d}"
                first = first or identifier
                attrs = json.dumps({"style":["vintage"]})
                c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,?,?,1,'synthetic-media','synthetic-media',?,'confirmed','now')",(identifier,owner,category,attrs))
                c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,primary_colour,style_tags,attributes_json,additional_attributes,created_at,updated_at) VALUES(?,?,?,'synthetic-media',?,?,'blue','[\"vintage\"]',?,?,'now','now')",(identifier,owner,identifier,identifier,category,attrs,attrs))
        for index in range(0 if size == 1 else 1000):
            identifier = f"history-{owner}-{index:04d}"
            timestamp = (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=index)).isoformat()
            text = f"{'Campus' if index % 10 == 0 else 'Work'} vintage historical request {index}"
            c.execute("INSERT INTO nlp_chats VALUES(?,?,?,'outfit_recommendation','{}','completed',?,?)",(identifier,owner,text,timestamp,timestamp))
            c.execute("INSERT INTO recommendations(id,user_id,chat_id,recommendation_type,status,created_at) VALUES(?,?,?,'wardrobe_outfit','available',?)",(identifier,owner,identifier,timestamp))
            c.execute("INSERT INTO recommendation_items VALUES(?,?,'upper',1,?)",(identifier,first,timestamp))
try:
    uvicorn.run(app,host="127.0.0.1",port=3101,access_log=False)
finally:
    temporary.cleanup()
