"""Local browser-test server with synthetic data in a disposable database only."""
import os
import tempfile
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

temporary = tempfile.TemporaryDirectory(prefix='wardrobe-browser-')
os.environ['SMART_WARDROBE_DATA_DIR'] = temporary.name
os.environ['SMART_WARDROBE_AI_MODE'] = 'development'
os.environ['SMART_WARDROBE_VTOFF_ENABLED'] = 'off'
os.environ['SMART_WARDROBE_HOMEPAGE_ENABLED'] = 'true'
os.environ['SMART_WARDROBE_ASSISTANT_ENABLED'] = 'true'
os.environ['SMART_WARDROBE_ASSISTANT_SUITABILITY_ENABLED'] = 'true'
os.environ['SMART_WARDROBE_ASSISTANT_EXECUTION_ENGINE'] = 'compact_exhaustive'
os.environ['SMART_WARDROBE_ASSISTANT_SCORING_PROFILE'] = 'experimental_compatibility_decision_v1'
os.environ['SMART_WARDROBE_TOKEN_SECRET'] = 'isolated-browser-test-secret-not-for-deployment'
os.environ['SMART_WARDROBE_ALLOW_DEV_IDENTITY'] = 'false'

from app.infrastructure.persistence.postgresql_repository import initialise_database,connection
from app.infrastructure.security import hash_password
from app.main import app
import uvicorn

initialise_database()
with connection() as c:
    for owner in ('browser-owner','browser-other'):
        c.execute("INSERT INTO users VALUES(?,?,?,'Browser test','active','now','now')",(owner,owner+'@example.test',hash_password('Browser-test-password-123')))

try:
    uvicorn.run(app,host='127.0.0.1',port=3101)
finally:
    temporary.cleanup()
