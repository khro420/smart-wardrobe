"""Install a verified development export without replacing any existing data."""
from pathlib import Path
import argparse,base64,getpass,gzip,hashlib,hmac,json,os,secrets,shutil,sqlite3,sys,tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sign(secret,v):return hmac.new(secret.encode(),b'phase2n-proof-v1\0'+encode(v),hashlib.sha256).hexdigest()

def install(storage,password=None,password_stdin=False):
    assets=ROOT/'assets/development';manifest=json.loads((assets/'manifest.json').read_text(encoding='utf-8'))
    expected=(assets/'manifest.sha256').read_text().strip()
    if sha(assets/'manifest.json')!=expected or manifest['format']!='portable-development-package-1.0.0':raise ValueError('Invalid portable manifest.')
    storage=Path(storage).resolve()
    if storage.exists():
        marker=storage/'installation.private.json'
        if marker.is_file() and json.loads(marker.read_text())['package_sha256']==expected and (storage/'smart_wardrobe.db').is_file():
            print('Existing portable installation retained; credentials and records were not changed.');return
        raise ValueError('Destination already exists. No database/media/configuration was overwritten; select a new empty destination.')
    for name,value in manifest['files'].items():
        if Path(name).name!=name or sha(assets/name)!=value:raise ValueError('Changed portable file: '+name)
    for name,value in manifest['media'].items():
        if Path(name).name!=name or sha(assets/'media'/name)!=value:raise ValueError('Changed portable media: '+name)
    if password is None:
        password=sys.stdin.readline().rstrip('\r\n') if password_stdin else getpass.getpass('Create a NEW local account password (not published): ')
        if not password_stdin and password!=getpass.getpass('Confirm local password: '):raise ValueError('Passwords differ; nothing installed.')
    if not isinstance(password,str) or len(password)<8:raise ValueError('Choose a local password of at least eight characters.')
    with gzip.open(assets/'snapshot.json.gz','rb') as f:raw=f.read(256*1024*1024+1)
    if len(raw)>256*1024*1024:raise ValueError('Unbounded portable snapshot.')
    data=json.loads(raw);assert data['format']=='portable-development-snapshot-1.0.0'
    storage.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.wardrobe-install-',dir=storage.parent))
    c=None
    try:
        database=stage/'smart_wardrobe.db';media=stage/'media';media.mkdir();authority=stage/'phase2nd';authority.mkdir()
        for name in manifest['media']:shutil.copy2(assets/'media'/name,media/name)
        c=sqlite3.connect(database);c.row_factory=sqlite3.Row
        triggers=[s for s in data['schema'] if s.lstrip().upper().startswith('CREATE TRIGGER')]
        c.executescript(';\n'.join(s for s in data['schema'] if s not in triggers)+';');c.execute('BEGIN IMMEDIATE')
        from app.infrastructure.security import hash_password
        local_hash=hash_password(password);proof_secret=secrets.token_hex(32)
        for table,rows in data['tables'].items():
            for source in rows:
                row={k:base64.b64decode(v['$sqlite_blob']) if type(v) is dict and set(v)=={'$sqlite_blob'} else v for k,v in source.items()}
                if table=='users':row['password_hash']=local_hash
                if table in ('phase2nd_proofs','phase2nd_mixed_proofs'):row['signature']=sign(proof_secret,json.loads(row['proof_json']))
                if table=='user_preferences' and row['preference_type']=='explicit_outfit_feedback_v1':
                    value=json.loads(row['preference_value_json']);body={k:v for k,v in value.items() if k!='signature'};value['signature']=sign(proof_secret,body);row['preference_value_json']=encode(value).decode()
                columns=','.join('"'+k+'"' for k in row)
                c.execute('insert into "'+table+'" ('+columns+') values ('+','.join('?' for _ in row)+')',tuple(row.values()))
        catalog=json.loads((assets/'catalog.json').read_text(encoding='utf-8'));historical=json.loads((assets/'historical-catalog.json').read_text(encoding='utf-8'))
        catalog_sha=hashlib.sha256(encode(catalog)).hexdigest()
        c.execute('update phase2nd_instance set catalog_sha256=?',(catalog_sha,))
        # Restore the exact immutable source state before installing runtime
        # triggers. Every trigger is present before validation/publication.
        for sql in triggers:c.execute(sql)
        c.commit()
        assert c.execute('pragma quick_check').fetchone()[0]=='ok' and not c.execute('pragma foreign_key_check').fetchall()
        assert c.execute("select count(*) from garments where status='available'").fetchone()[0]==51
        required=c.execute("select m.storage_key from garments g join media_assets m on g.preferred_media_id=m.id where g.status='available'").fetchall()
        assert all((media/r[0]).is_file() for r in required)
        cfg={'database':str(database),'media':str(media),'catalog':str(authority/'catalog.json'),'catalog_sha256':catalog_sha,'profile':'phase2nd_main_fixture_v1','proof_secret':proof_secret,'historical_catalogues':[historical]}
        (authority/'catalog.json').write_bytes(encode(catalog))
        from app.development.main_fixture.store import Store as FixtureStore
        from app.development.mixed_wardrobe.store import Store as MixedStore
        # MAC rekeying is not accepted as proof of correctness: fully reconstruct
        # every transferred fixture selection before publishing this install.
        verified=0
        for table,store in (('phase2nd_proofs',FixtureStore(cfg)),('phase2nd_mixed_proofs',MixedStore(cfg))):
            for row in c.execute('select * from '+table+' order by created_at,id'):
                store.verify_record(c,row,row['owner_id']);verified+=1
        c.close()
        cfg.update(database=str(storage/'smart_wardrobe.db'),media=str(storage/'media'),catalog=str(storage/'phase2nd/catalog.json'))
        (authority/'runtime.private.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
        marker={'package_sha256':expected,'verified_historical_proofs':verified,'counts':manifest['counts'],'media':len(manifest['media']),'authentication':'fresh local password and signing keys; no source credentials reused','historical_transport':'original proof contents/IDs/scores retained; fresh local import MACs','missing_older_media_records':manifest['missing_older_media_records']}
        (stage/'installation.private.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
        stage.rename(storage)
        print(json.dumps({'installed':str(storage),'garments':58,'available':51,'saved_outfits':6,'media':len(manifest['media']),'verified_historical_proofs':verified,'account':data['tables']['users'][0]['email'],'password':'the new password you supplied; never stored in plaintext','missing_older_media_records':manifest['missing_older_media_records']}))
    except BaseException:
        if c is not None:c.close()
        # Delete only this positively identified temporary installation.
        if stage.resolve().parent==storage.parent and stage.name.startswith('.wardrobe-install-'):shutil.rmtree(stage)
        raise

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--storage',type=Path,default=ROOT/'storage/portable-development');ap.add_argument('--password-stdin',action='store_true');args=ap.parse_args()
    install(args.storage,password_stdin=args.password_stdin)
