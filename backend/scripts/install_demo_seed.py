"""Install the public demo without overwriting an existing local database."""
from pathlib import Path
from contextlib import closing
import hashlib
import shutil
import sqlite3

storage = Path(__file__).resolve().parents[2] / 'storage'
seed = storage / 'smart_wardrobe.seed.db'
destination = storage / 'smart_wardrobe.db'
source_media = storage / 'demo-media'
target_media = storage / 'media'


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.digest()


def main():
    if any(path.exists() for path in (destination, Path(str(destination) + '-wal'), Path(str(destination) + '-shm'))):
        raise SystemExit('A local database or SQLite sidecar already exists. Stop the backend, back it up and move it aside before installing the demo; this script never overwrites it.')
    if not seed.is_file():
        raise SystemExit('The demo seed database is missing.')
    with closing(sqlite3.connect(f'file:{seed.as_posix()}?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise SystemExit('The demo seed database failed its integrity check.')
        files = [row[0] for row in db.execute("SELECT storage_key FROM media_assets WHERE status='available'")]
    for key in files:
        if Path(key).name != key or not (source_media / key).is_file():
            raise SystemExit('The demo image bundle is incomplete or contains an invalid path. Pull all repository files and try again.')
        existing = target_media / key
        if existing.exists() and (not existing.is_file() or digest(existing) != digest(source_media / key)):
            raise SystemExit('A local media file conflicts with the demo. No database was installed.')
    target_media.mkdir(parents=True, exist_ok=True)
    for key in files:
        if not (target_media / key).exists():
            shutil.copy2(source_media / key, target_media / key)
    # Exclusive create prevents accidental replacement if another process starts.
    with seed.open('rb') as src, destination.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    print(f'Demo installed with {len(files)} garment images. Sign in as demo@example.test using the demo password in README.md.')


if __name__ == '__main__':
    main()
