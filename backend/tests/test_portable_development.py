"""Portable authority is path-only transport, never new attribute permission."""
from pathlib import Path
import copy,gzip,hashlib,json,sqlite3
import pytest
from app.development.main_fixture.store import Store,FixtureError
from app.development.main_fixture.core import digest

ASSETS=Path(__file__).resolve().parents[2]/'assets/development'

def test_public_package_credentials_media_and_counts():
    manifest=json.loads((ASSETS/'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ASSETS/'manifest.json').read_bytes()).hexdigest()==(ASSETS/'manifest.sha256').read_text().strip()
    for name,h in manifest['files'].items():assert hashlib.sha256((ASSETS/name).read_bytes()).hexdigest()==h
    for name,h in manifest['media'].items():assert hashlib.sha256((ASSETS/'media'/name).read_bytes()).hexdigest()==h
    data=json.loads(gzip.decompress((ASSETS/'snapshot.json.gz').read_bytes()))['tables']
    assert len(data['garments'])==58 and sum(r['status']=='available' for r in data['garments'])==51
    assert all(r['password_hash']=='' for r in data['users']) and not data['revoked_access_tokens']
    assert all(r['signature']=='' for t in ('phase2nd_proofs','phase2nd_mixed_proofs') for r in data[t])
    media={r['id']:r for r in data['media_assets']}
    assert all(media[r['preferred_media_id']]['storage_key'] in manifest['media'] for r in data['garments'] if r['status']=='available')

@pytest.fixture
def portable(tmp_path):
    catalog=json.loads((ASSETS/'catalog.json').read_text(encoding='utf-8'));historical=json.loads((ASSETS/'historical-catalog.json').read_text(encoding='utf-8'))
    database=tmp_path/'smart_wardrobe.db';media=tmp_path/'media';media.mkdir();p=tmp_path/'catalog.json';p.write_text(json.dumps(catalog),encoding='utf-8')
    with sqlite3.connect(database) as c:
        c.execute('create table phase2nd_instance (id text,catalog_sha256 text)');c.execute('insert into phase2nd_instance values (?,?)',(catalog['instance_id'],digest(catalog)))
    return {'database':str(database),'media':str(media),'catalog':str(p),'catalog_sha256':digest(catalog),'proof_secret':'test-only-local-secret-not-a-real-credential','historical_catalogues':[historical]}

def test_portable_binding_works_without_source_machine_path(portable):
    s=Store(portable);assert len(s.accepted_catalogs)==2
    assert s.catalog['database']=='@local-database'

@pytest.mark.parametrize('field',['owner_id','profiles','garments','origin'])
def test_historical_transport_cannot_substitute_evidence(portable,field):
    changed=copy.deepcopy(portable);changed['historical_catalogues'][0][field]='forged'
    with pytest.raises(FixtureError,match='InvalidPortableHistoricalAuthority'):Store(changed)

def test_changed_local_instance_is_refused(portable):
    with sqlite3.connect(portable['database']) as c:c.execute("update phase2nd_instance set catalog_sha256='wrong'")
    with pytest.raises(FixtureError,match='UnboundFixtureDatabase'):Store(portable)
