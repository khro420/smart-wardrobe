import importlib.util
from contextlib import closing
import sqlite3
import shutil
import unittest
import uuid
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'install_demo_seed.py'
spec = importlib.util.spec_from_file_location('install_demo_seed', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class DemoInstallTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2] / 'tmp' / ('seed-install-test-' + uuid.uuid4().hex)
        root.mkdir(parents=True)
        self.root = root
        installer.seed = root / 'seed.db'
        installer.destination = root / 'live.db'
        installer.source_media = root / 'demo-media'
        installer.target_media = root / 'media'
        installer.source_media.mkdir()
        (installer.source_media / 'garment.png').write_bytes(b'demo image')
        with closing(sqlite3.connect(installer.seed)) as db:
            db.execute('CREATE TABLE media_assets(storage_key TEXT, status TEXT)')
            db.execute("INSERT INTO media_assets VALUES('garment.png','available')")
            db.commit()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_installs_images_and_never_overwrites_database(self):
        installer.main()
        self.assertEqual((installer.target_media / 'garment.png').read_bytes(), b'demo image')
        self.assertTrue(installer.destination.is_file())
        with self.assertRaises(SystemExit):
            installer.main()

    def test_conflicting_media_prevents_database_install(self):
        installer.target_media.mkdir()
        (installer.target_media / 'garment.png').write_bytes(b'personal image')
        with self.assertRaises(SystemExit):
            installer.main()
        self.assertFalse(installer.destination.exists())
        self.assertEqual((installer.target_media / 'garment.png').read_bytes(), b'personal image')
