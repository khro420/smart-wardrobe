import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException
from app.application.visualisation import group_visualisation_service as service


class GroupAccessTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('CREATE TABLE group_visualisations (id TEXT, user_id TEXT, status TEXT, progress_message TEXT, error_message TEXT, output_media_id TEXT, updated_at TEXT)')
        self.db.execute("INSERT INTO group_visualisations VALUES ('job', 'owner', 'processing', NULL, NULL, NULL, '')")
        @contextmanager
        def connection():
            yield self.db
        self.patch = patch.object(service, 'connection', connection)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.db.close()

    def test_group_result_is_owner_scoped(self):
        self.assertEqual(service.get('owner', 'job')['status'], 'processing')
        with self.assertRaises(HTTPException) as caught:
            service.get('another-user', 'job')
        self.assertEqual(caught.exception.status_code, 404)

    def test_only_owner_can_cancel(self):
        with patch.object(service, 'utcnow', return_value='now'):
            with self.assertRaises(HTTPException):
                service.cancel('another-user', 'job')
            self.assertEqual(service.get('owner', 'job')['status'], 'processing')
            service.cancel('owner', 'job')
        self.assertEqual(service.get('owner', 'job')['status'], 'cancelled')
