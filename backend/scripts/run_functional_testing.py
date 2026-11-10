"""Start one local worker with the explicit synthetic functional-testing profile.

No model accuracy or performance acceptance is implied. Uses normal application
composition, authentication, repositories and review APIs; no dependency overrides.
"""
import argparse
import os
from pathlib import Path
import secrets
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True,
                        help='Independent disposable directory; never a shared database.')
    parser.add_argument('--port', type=int, default=8600)
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    profile = backend / 'deployment' / 'functional-testing.env.example'
    for line in profile.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key] = value
    data = args.data_dir.resolve()
    data.mkdir(parents=True, exist_ok=True)
    os.environ['SMART_WARDROBE_DATA_DIR'] = str(data)
    os.environ['SMART_WARDROBE_DATABASE'] = str(data / 'wardrobe.sqlite')
    # A caller can supply a persistent test secret. Otherwise tokens deliberately
    # expire across server restarts. Never print the generated secret.
    os.environ.setdefault('SMART_WARDROBE_TOKEN_SECRET', secrets.token_urlsafe(48))
    sys.path.insert(0, str(backend))
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=args.port,
                workers=1, reload=False)


if __name__ == '__main__':
    main()
