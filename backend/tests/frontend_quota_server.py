"""Loopback-only browser fixture; all data lives in a fresh temporary directory."""
import os
import sys
import tempfile
from pathlib import Path
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

temporary=tempfile.TemporaryDirectory(prefix='wardrobe-quota-browser-')
os.environ.update(SMART_WARDROBE_DATA_DIR=temporary.name, SMART_WARDROBE_AI_MODE='development',
                  SMART_WARDROBE_VTOFF_ENABLED='off', SMART_WARDROBE_ALLOW_DEV_IDENTITY='false',
                  SMART_WARDROBE_HOMEPAGE_ENABLED='true', SMART_WARDROBE_ASSISTANT_ENABLED='true',
                  SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED='false',
                  SMART_WARDROBE_TOKEN_SECRET='disposable-quota-browser-secret')
from PIL import Image
from app.infrastructure.persistence.postgresql_repository import initialise_database,connection
from app.infrastructure.security import hash_password
from app.infrastructure.media.protected_media_store import store_media_bytes
from app.main import app
import uvicorn

initialise_database()
with connection() as c:
    c.execute("INSERT INTO users VALUES('quota-owner','quota@example.test',?,'Quota test','active','now','now')",(hash_password('Quota-test-password-123'),))
buffer=BytesIO(); Image.new('RGB',(256,256),'blue').save(buffer,'PNG')
media=store_media_bytes(buffer.getvalue(),'quota-owner','wardrobe_source')


def insert_garment(c, identifier):
    c.execute("INSERT INTO garments(id,user_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,'quota-owner',?,?,'vest','{}','now','now')",(identifier,media,'Existing '+identifier))


@app.post('/_test/quota/setup/{used}')
def setup(used:int):
    assert 0<=used<=101
    with connection() as c:
        for table in ['outfit_items','outfits','garments','processing_items','processing_jobs']:
            c.execute('DELETE FROM '+table)
        for index in range(used): insert_garment(c,'quota-existing-'+str(index))
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES('quota-job','quota-owner',?,'review_required','now','now')",(media,))
        for index in range(2):
            c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'quota-job','vest',1,?,?,'{}','accepted','now')",('quota-new-'+str(index),media,media))
    return {'used':used}


@app.post('/_test/quota/fill')
def fill():
    # Explicit test fixture mutation simulates a second client winning capacity.
    with connection() as c: insert_garment(c,'quota-other-tab')
    return {'ok':True}


try:
    uvicorn.run(app,host='127.0.0.1',port=3101)
finally:
    temporary.cleanup()
