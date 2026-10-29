"""Validate NFR fixture materialisation separately from timed service processes."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'storage/verification/phase5f2e3j16'

def test_frozen_wardrobes_and_history_fixture(tmp_path):
    run=tmp_path/'run';run.mkdir();database=tmp_path/'fixture.db'
    env={**os.environ,'SMART_WARDROBE_NFR_RUN':str(run),'SMART_WARDROBE_DATA_DIR':str(tmp_path),
         'SMART_WARDROBE_DATABASE':str(database),'SMART_WARDROBE_ALLOW_DEV_IDENTITY':'false'}
    subprocess.run([sys.executable,'-B',str(OUT/'prepare_runtime.py')],env=env,check=True,capture_output=True)
    with sqlite3.connect(database) as c:
        c.row_factory=sqlite3.Row
        for workload,expected in [('balanced-100',17710),('maximum-100',38148)]:
            rows=list(c.execute('SELECT * FROM garments WHERE user_id=?',('j10-'+workload,)));assert len(rows)==100
            counts={r:0 for r in ['top','bottom','dress','outerwear']}
            for row in rows:
                category=row['category'];role='outerwear' if category.endswith('outwear') else 'dress' if category.endswith('dress') else 'bottom' if category in ['trousers','shorts','skirt'] else 'top';counts[role]+=1
            t,b,d,o=(counts[k] for k in ['top','bottom','dress','outerwear'])
            assert (t*b+d)*(o+1)==expected
            assert c.execute("SELECT count(*) FROM garments g JOIN processing_items p ON p.id=g.processing_item_id JOIN processing_jobs j ON j.id=p.job_id WHERE g.user_id=? AND g.status='available' AND p.review_status='confirmed' AND j.user_id=g.user_id",('j10-'+workload,)).fetchone()[0]==100
        assert c.execute('SELECT count(*) FROM nlp_chats').fetchone()[0]==20000
        assert c.execute('SELECT count(*) FROM recommendation_item_snapshots').fetchone()[0]==20000
        for owner in ['history-owner','history-foreign']:
            assert c.execute('SELECT count(*) FROM nlp_chats WHERE user_id=?',(owner,)).fetchone()[0]==10000
            for status in ['available','saved']:assert c.execute('SELECT count(*) FROM recommendations WHERE user_id=? AND status=?',(owner,status)).fetchone()[0]==5000
        expected=json.loads((run/'history-expected.json').read_text())
        assert expected['empty_first']['total']==expected['many']['total']==10000
        assert expected['common_first']['total']==1000
        assert expected['no_match']['total']==0 and expected['few']['total']==2
        assert expected['percent']['total']==527 and expected['underscore']['total']==435
        assert len(expected['empty_next']['http_ids'])==50 and len(expected['empty_next']['browser_ids'])==100
        assert not set(expected['empty_first']['http_ids']) & set(expected['empty_next']['http_ids'])
        for target in expected.values():assert all(identifier.startswith('history-owner-') for identifier in target['browser_ids'])
