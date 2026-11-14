import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException
from app.application.visualisation import activity_service as service


class ActivityTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE media_assets(id TEXT, user_id TEXT, status TEXT);
            CREATE TABLE visualisations(id TEXT,user_id TEXT,profile_id TEXT,status TEXT,progress_message TEXT,error_message TEXT,progress_percent INTEGER,created_at TEXT,updated_at TEXT,completed_at TEXT,output_media_id TEXT,output_kind TEXT,history_hidden INTEGER DEFAULT 0);
            CREATE TABLE group_visualisations(id TEXT,user_id TEXT,profile_id TEXT,status TEXT,progress_message TEXT,error_message TEXT,created_at TEXT,updated_at TEXT,output_media_id TEXT,history_hidden INTEGER DEFAULT 0);
            CREATE TABLE processing_jobs(id TEXT,user_id TEXT,profile_id TEXT,status TEXT,progress_message TEXT,error_message TEXT,progress_percent INTEGER,created_at TEXT,updated_at TEXT);
            INSERT INTO media_assets VALUES('media','owner','available');
            INSERT INTO visualisations(id,user_id,profile_id,status,created_at,updated_at,completed_at,output_media_id,output_kind) VALUES('result','owner','p','completed','1','2','2','media','generated');
            INSERT INTO group_visualisations(id,user_id,profile_id,status,created_at,updated_at) VALUES('group','owner','p','queued','3','3');
            INSERT INTO processing_jobs VALUES('job','owner','p','review_required','Review',NULL,100,'4','4');
            INSERT INTO processing_jobs VALUES('other','other','p','processing','Private',NULL,10,'5','5');
        ''')
        @contextmanager
        def connection():
            yield self.db
        self.patcher = patch.object(service, 'connection', connection)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()

    def test_activity_scoped_to_owner_and_wearer(self):
        self.assertEqual({j['id'] for j in service.list_activity('owner', 'p')}, {'job', 'group'})
        self.assertEqual(service.list_activity('owner', 'other'), [])

    def test_remove_hides_only_owners_completed_result(self):
        self.assertEqual([x['id'] for x in service.list_history('owner')], ['result'])
        with self.assertRaises(HTTPException):
            service.remove_history('other', 'single', 'result')
        service.remove_history('owner', 'single', 'result')
        self.assertEqual(service.list_history('owner'), [])
        self.assertEqual(self.db.execute("SELECT status FROM media_assets WHERE id='media'").fetchone()[0], 'available')
        with self.assertRaises(HTTPException):
            service.remove_history('owner', 'group', 'group')

    def test_group_history_and_other_users_are_isolated(self):
        self.db.execute("INSERT INTO group_visualisations(id,user_id,profile_id,status,created_at,updated_at,output_media_id) VALUES ('done','owner','p','completed','1','3','media')")
        self.db.execute("INSERT INTO group_visualisations(id,user_id,profile_id,status,created_at,updated_at,output_media_id) VALUES ('private','other','p','completed','1','3','media')")
        self.assertEqual([item['id'] for item in service.list_history('owner')], ['done', 'result'])
        self.assertEqual(service.list_history('other'), [])
        service.remove_history('owner', 'group', 'done')
        self.assertEqual([item['id'] for item in service.list_history('owner')], ['result'])
