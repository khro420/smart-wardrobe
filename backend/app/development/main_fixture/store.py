"""Opt-in fixture store. Separate tables/proofs; old readers are untouched.

Every write independently reconstructs the complete pinned scope under SQLite's
write lock. Captured synthetic history never becomes owner/model evidence.
"""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, hmac, json, sqlite3, uuid
from .core import VERSION, ORIGIN, encoded, digest, select, GRAMMAR_SHA

PROFILE='phase2nd_main_fixture_v1'
PORTABLE_CATALOG='phase2nd-portable-catalog-1.0.0'
MAX_PROOF=4*1024*1024
SCHEMA='''
CREATE TABLE phase2nd_instance (id TEXT PRIMARY KEY, catalog_sha256 TEXT NOT NULL);
CREATE TABLE phase2nd_proofs (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id), wearer_id TEXT NOT NULL REFERENCES wardrobe_profiles(id),
 receipt TEXT NOT NULL, fingerprint TEXT NOT NULL, parent_id TEXT REFERENCES phase2nd_proofs(id), ordinal INTEGER NOT NULL,
 proof_json TEXT NOT NULL, proof_sha256 TEXT NOT NULL, signature TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(owner_id, receipt));
'''

class FixtureError(ValueError):
    def __init__(self,code,status=409): self.code,self.status=code,status;super().__init__(code)

class Store:
    def __init__(self,config):
        self.config=dict(config);self.database=Path(config['database']).resolve();self.media=Path(config['media']).resolve()
        self.catalog=json.loads(Path(config['catalog']).read_text(encoding='utf-8'))
        self.secret=config['proof_secret'].encode()
        if digest(self.catalog)!=config['catalog_sha256'] or len(self.secret)<32: raise FixtureError('InvalidFixtureSeal')
        portable=self.catalog['version']==PORTABLE_CATALOG
        if (self.catalog['database']!=('@local-database' if portable else str(self.database)) or self.media.parent!=self.database.parent): raise FixtureError('UnsafeFixtureStorage')
        if self.catalog['version'] not in ('phase2nd-main-catalog-1.0.0',PORTABLE_CATALOG) or self.catalog['origin']!=ORIGIN or len(self.catalog['garments'])!=30: raise FixtureError('InvalidFixtureCatalog')
        self.accepted_catalogs={config['catalog_sha256']}
        for historical in config.get('historical_catalogues',[]):
            # Only path/version transport differs. Never substitute attributes,
            # identities, timestamps, source declarations, media or preferences.
            if not portable or historical.get('version')!='phase2nd-main-catalog-1.0.0' or {**historical,'database':'@local-database','version':PORTABLE_CATALOG}!=self.catalog:raise FixtureError('InvalidPortableHistoricalAuthority')
            self.accepted_catalogs.add(digest(historical))
        if len({x['row']['id'] for x in self.catalog['garments']})!=30: raise FixtureError('DuplicateFixtureSource')
        from app.application.wardrobe.description_policy import DescriptionPolicy
        from app.application.wardrobe.description_normalizer import classify
        p=DescriptionPolicy.load()
        for e in self.catalog['garments']:
            if set(e['attributes'])!={'category','primary_colour','pattern','material','silhouette','style','sleeve_length'}: raise FixtureError('UnknownFixtureField')
            for k,v in e['attributes'].items():
                if classify(k,v,p)[0]!=('Absent' if v is None else 'Known'): raise FixtureError('InvalidFixtureDeclaration')
            if e['row']['processing_item_id'] is not None or e['row']['user_id']!=self.catalog['owner_id']: raise FixtureError('InvalidFixtureOwnership')
        with self.connection() as c:
            row=c.execute('select * from phase2nd_instance').fetchall()
            if len(row)!=1 or row[0]['id']!=self.catalog['instance_id'] or row[0]['catalog_sha256']!=config['catalog_sha256']: raise FixtureError('UnboundFixtureDatabase')

    @contextmanager
    def connection(self):
        if not self.database.is_file(): raise FixtureError('MissingFixtureDatabase')
        c=sqlite3.connect(self.database,timeout=30);c.row_factory=sqlite3.Row;c.execute('pragma foreign_keys=ON')
        try: yield c;c.commit()
        except BaseException: c.rollback();raise
        finally: c.close()

    def sign(self,value): return hmac.new(self.secret,b'phase2n-proof-v1\0'+encoded(value),hashlib.sha256).hexdigest()

    def require_owner(self,c,owner,wearer=None):
        if owner!=self.catalog['owner_id']: raise FixtureError('FixtureAccountRequired',403)
        u=c.execute('select account_status from users where id=?',(owner,)).fetchone()
        if not u or u[0]!='active': raise FixtureError('InactiveFixtureAccount',403)
        if wearer is not None:
            if wearer not in self.catalog['profiles']: raise FixtureError('ForeignWearer',404)
            p=c.execute('select * from wardrobe_profiles where id=? and user_id=? and status=\'active\'',(wearer,owner)).fetchone()
            details=c.execute('select * from wardrobe_profile_details_v1 where profile_id=?',(wearer,)).fetchone()
            expected=self.catalog['profiles'][wearer]
            if not p or dict(p)!=expected['row'] or not details or dict(details)!=expected['details']: raise FixtureError('ChangedFixtureWearer')
            if [dict(r) for r in c.execute('select * from user_preferences where user_id=? and profile_id=? and is_active=1 order by id',(owner,wearer))]!=expected.get('preferences',[]): raise FixtureError('ChangedFixturePreferences')

    def image(self,entry,c):
        m=entry['media'];row=c.execute('select * from media_assets where id=?',(m['id'],)).fetchone()
        if not row or dict(row)!=m or row['user_id']!=self.catalog['owner_id'] or row['status']!='available': raise FixtureError('ChangedFixtureMedia')
        path=(self.media/m['storage_key']).resolve()
        if path.parent!=self.media or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['image_sha256']: raise FixtureError('ChangedFixtureImage')
        return path

    def capture(self,c,owner,wearer):
        self.require_owner(c,owner,wearer)
        ids=[e['row']['id'] for e in self.catalog['garments']]
        actual=[dict(r) for r in c.execute('select * from garments where user_id=? and id in ('+','.join('?' for _ in ids)+') order by id',(owner,*ids))]
        expected=sorted((x['row'] for x in self.catalog['garments']),key=lambda r:r['id'])
        if actual!=expected: raise FixtureError('ChangedFixtureSource')
        for entry in self.catalog['garments']: self.image(entry,c)
        return json.loads(encoded(self.catalog))

    def profile_on(self):
        if self.config.get('profile')!=PROFILE: raise FixtureError('FixtureProfileDisabled',503)

    def verify_record(self,c,row,owner,depth=0):
        if depth>=10 or row['owner_id']!=owner: raise FixtureError('InvalidFixtureHistory',404)
        text=row['proof_json']
        if len(text.encode())>MAX_PROOF: raise FixtureError('OversizedFixtureProof')
        proof=json.loads(text)
        if digest(proof)!=row['proof_sha256'] or not hmac.compare_digest(self.sign(proof),row['signature']): raise FixtureError('ChangedFixtureProof')
        if set(proof)!={'version','catalog','grammar_sha256','raw','wearer_id','engine','seen','floor','decision','parent_id','ordinal','receipt','fingerprint','record_id'}: raise FixtureError('UnknownFixtureProofField')
        if proof['version']!=VERSION or digest(proof['catalog']) not in self.accepted_catalogs or proof['grammar_sha256']!=GRAMMAR_SHA: raise FixtureError('UnregisteredFixtureProof')
        for k in ('wearer_id','parent_id','ordinal','receipt','fingerprint'):
            if proof[k]!=row[k]: raise FixtureError('ChangedFixtureRecord')
        if proof['record_id']!=row['id'] or proof['catalog']['owner_id']!=owner: raise FixtureError('ForeignFixtureProof')
        expected_seen=[];floor='0';ordinal=0
        if row['parent_id']:
            parent=c.execute('select * from phase2nd_proofs where id=? and owner_id=?',(row['parent_id'],owner)).fetchone()
            if not parent: raise FixtureError('MissingFixtureParent')
            pp=self.verify_record(c,parent,owner,depth+1)
            if pp['wearer_id']!=proof['wearer_id'] or pp['raw']!=proof['raw'] or pp['decision']['intent']['optional']: raise FixtureError('ChangedFixtureLineage')
            expected_seen=pp['seen']+[self.base(pp['decision'])];floor=pp['floor'] if pp['ordinal'] else self.r_value(pp['decision']);ordinal=pp['ordinal']+1
        if proof['seen']!=expected_seen or proof['floor']!=floor or proof['ordinal']!=ordinal or ordinal>9: raise FixtureError('InvalidFixtureChain')
        decision=select(proof['catalog'],proof['raw'],proof['wearer_id'],independent=True,seen=self.seen(proof['seen']),floor=proof['floor'])
        if decision!=proof['decision'] or decision['status']!='Selected': raise FixtureError('IndependentFixtureHistoryMismatch')
        return proof

    @staticmethod
    def base(decision): return [x for x in decision['selected']['key'] if x[0]!='outerwear']
    @staticmethod
    def seen(values): return tuple(tuple(tuple(x) for x in key) for key in values)
    @staticmethod
    def r_value(d):
        from app.application.recommendation.decision_score_codec import score_from_json
        return str(score_from_json(json.dumps(d['selected']['score'])).request_match.contribution)

    def action(self,record_id,proof):
        if proof['ordinal']>=9 or proof['decision']['intent']['optional']: return None
        return {'parent_id':record_id,'action_key':self.sign({'parent_id':record_id,'proof_sha256':digest(proof)}),'label':'Suggest another outfit'}

    def view(self,row,proof,replayed=False):
        return {'id':row['id'],'request_text':proof['raw'],'wearer_id':proof['wearer_id'],'ordinal':proof['ordinal'],
                'source':ORIGIN,'synthetic':True,'proof_version':VERSION,'decision':proof['decision'],
                'created_at':row['created_at'],'replayed':replayed,'continuation':self.action(row['id'],proof)}

    def history(self,owner,record_id=None):
        with self.connection() as c:
            self.require_owner(c,owner)
            if record_id:
                r=c.execute('select * from phase2nd_proofs where id=? and owner_id=?',(record_id,owner)).fetchone()
                if not r: raise FixtureError('RecommendationNotFound',404)
                return self.view(r,self.verify_record(c,r,owner))
            rows=c.execute('select * from phase2nd_proofs where owner_id=? order by created_at desc,id desc limit 100',(owner,)).fetchall()
            # Full verification is performed on opening/replaying a record; list
            # contains only IDs/text, never unverified winners or score claims.
            return [{'id':r['id'],'created_at':r['created_at']} for r in rows]

    def recommend(self,owner,wearer,raw,receipt,engine='reference',parent_id=None,action_key=None,*,before_lock=None,after_insert=None):
        self.profile_on()
        if not isinstance(raw,str) or not 1<=len(raw)<=500 or not isinstance(receipt,str) or not 1<=len(receipt)<=200: raise FixtureError('InvalidFixtureRequest',422)
        if engine not in ('reference','compact_exhaustive'): raise FixtureError('UnsupportedFixtureEngine',422)
        fingerprint=digest({'owner':owner,'wearer':wearer,'raw':raw,'engine':engine,'parent_id':parent_id,'action_key':action_key})
        with self.connection() as c:
            self.require_owner(c,owner,wearer)
            existing=c.execute('select * from phase2nd_proofs where owner_id=? and receipt=?',(owner,receipt)).fetchone()
            if existing:
                if existing['fingerprint']!=fingerprint: raise FixtureError('IdempotencyConflict')
                return self.view(existing,self.verify_record(c,existing,owner),True)
            catalog=self.capture(c,owner,wearer);seen=[];floor='0';ordinal=0
            if parent_id:
                p=c.execute('select * from phase2nd_proofs where id=? and owner_id=?',(parent_id,owner)).fetchone()
                if not p: raise FixtureError('RecommendationNotFound',404)
                pp=self.verify_record(c,p,owner);action=self.action(parent_id,pp)
                if not action: raise FixtureError('RefinementUnavailable',422)
                if action_key!=action['action_key'] or raw!=pp['raw'] or wearer!=pp['wearer_id']: raise FixtureError('InvalidContinuationBinding')
                seen=pp['seen']+[self.base(pp['decision'])];floor=pp['floor'] if pp['ordinal'] else self.r_value(pp['decision']);ordinal=pp['ordinal']+1
            elif action_key: raise FixtureError('MissingFixtureParent',422)
        decision=select(catalog,raw,wearer,engine,seen=self.seen(seen),floor=floor)
        if decision['status']!='Selected': return {'synthetic':True,'decision':decision,'persisted':False}
        if before_lock: before_lock()
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('select * from phase2nd_proofs where owner_id=? and receipt=?',(owner,receipt)).fetchone()
            if existing:
                if existing['fingerprint']!=fingerprint: raise FixtureError('IdempotencyConflict')
                return self.view(existing,self.verify_record(c,existing,owner),True)
            fresh=self.capture(c,owner,wearer)
            if fresh!=catalog: raise FixtureError('ChangedFixtureSource')
            if parent_id:
                parent=c.execute('select * from phase2nd_proofs where id=? and owner_id=?',(parent_id,owner)).fetchone()
                if not parent or self.verify_record(c,parent,owner)!=pp: raise FixtureError('ChangedFixtureParent')
            independent=select(fresh,raw,wearer,independent=True,seen=self.seen(seen),floor=floor)
            if independent!=decision: raise FixtureError('IndependentFixtureWriteMismatch')
            proof={'version':VERSION,'catalog':fresh,'grammar_sha256':GRAMMAR_SHA,'raw':raw,'wearer_id':wearer,'engine':engine,
                'seen':seen,'floor':floor,'decision':independent,'parent_id':parent_id,'ordinal':ordinal,'receipt':receipt,
                'fingerprint':fingerprint,'record_id':str(uuid.uuid4())}
            wire=encoded(proof)
            if len(wire)>MAX_PROOF: raise FixtureError('OversizedFixtureProof')
            c.execute('insert into phase2nd_proofs values (?,?,?,?,?,?,?,?,?,?,?)',
                (proof['record_id'],owner,wearer,receipt,fingerprint,parent_id,ordinal,wire.decode(),digest(proof),self.sign(proof),datetime.now(timezone.utc).isoformat()))
            if after_insert: after_insert(c)
            row=c.execute('select * from phase2nd_proofs where id=?',(proof['record_id'],)).fetchone()
            return self.view(row,proof)
