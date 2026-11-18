"""Idempotent additive main fixture materialization and conservative retirement."""
from pathlib import Path
import json,sqlite3,secrets,uuid,hashlib,os,argparse
if __name__=='__main__':
    from app.infrastructure.environment import load_local_environment
    load_local_environment()
from .core import digest,ORIGIN
from .store import Store,SCHEMA,PROFILE

def write(path,v):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.new');temp.write_text(json.dumps(v,indent=2),encoding='utf-8');temp.replace(path)

def seed(source_catalog,*,owner_email='khorhs2004@gmail.com'):
    from app.infrastructure.persistence.postgresql_repository import connection,utcnow,DATABASE_PATH
    from app.infrastructure.media.protected_media_store import store_media_bytes,MEDIA_DIR
    root=DATABASE_PATH.resolve().parent/'phase2nd';root.mkdir(exist_ok=True)
    cfgpath=root/'runtime.private.json'
    if cfgpath.exists():
        s=Store(json.loads(cfgpath.read_text()))
        with s.connection() as c:
            for wearer in s.catalog['profiles']:s.capture(c,s.catalog['owner_id'],wearer)
        return {'added':0,'reconciled':30,'config':str(cfgpath)}
    source_path=Path(source_catalog);source=json.loads(source_path.read_text());source_images=source_path.parent/'media'
    assert len(source['garments'])==30
    with connection() as c:
        u=c.execute('select id,account_status from users where lower(email)=?',(owner_email.lower(),)).fetchone()
        if not u or u['account_status']!='active':raise ValueError('Active existing account required.')
        owner=u['id'];profiles={}
        for row in c.execute("select * from wardrobe_profiles where user_id=? and status='active'",(owner,)):
            details=c.execute('select * from wardrobe_profile_details_v1 where profile_id=?',(row['id'],)).fetchone()
            if details and (details['gender_identity'] or '').strip().lower() in ('male','female'):
                profiles[row['id']]={'row':dict(row),'details':dict(details),'gender':details['gender_identity'].strip().lower(),
                    'preferences':[dict(p) for p in c.execute('select * from user_preferences where user_id=? and profile_id=? and is_active=1 order by id',(owner,row['id']))]}
        if not profiles:raise ValueError('Existing wearer needs an explicit supported category policy; no profile is inferred or edited.')
        used=c.execute("select count(*) from garments where user_id=? and status='available'",(owner,)).fetchone()[0]
        if used+30>100:raise ValueError('Existing 100-garment quota would be exceeded.')
    progress_path=root/'creation-progress.json'
    if progress_path.exists():progress=json.loads(progress_path.read_text())
    else:progress={'version':'phase2nd-creation-ledger-1.0.0','database':str(DATABASE_PATH.resolve()),'owner_id':owner,'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'media':{}}
    if progress['database']!=str(DATABASE_PATH.resolve()) or progress['owner_id']!=owner or progress['source_sha256']!=hashlib.sha256(source_path.read_bytes()).hexdigest():raise ValueError('Conflicting creation ledger.')
    for e in source['garments']:
        fixture=e['fixture_id'];payload=(source_images/e['media']['storage_key']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=e['image_sha256']:raise ValueError('Changed source drawing.')
        if fixture not in progress['media']:
            mid=store_media_bytes(payload,owner,'synthetic_development_garment','image/png',fixture+'.png');progress['media'][fixture]=mid;write(progress_path,progress)
    catalog={'version':'phase2nd-main-catalog-1.0.0','origin':ORIGIN,'instance_id':str(uuid.uuid4()),'database':str(DATABASE_PATH.resolve()),
        'owner_id':owner,'profiles':profiles,'garments':[],'scope':'fixture_only_explicit_v1','normal_garments_included':False,
        'renderer':source['renderer'],'license':source['license'],'source_catalog_sha256':progress['source_sha256'],'limitations':source['limitations']}
    now=utcnow()
    with connection() as c:
        c.executescript(SCHEMA);c.execute('BEGIN IMMEDIATE')
        # Check quota and owner again under the materialization lock.
        if c.execute("select count(*) from garments where user_id=? and status='available'",(owner,)).fetchone()[0]+30>100:raise ValueError('Changed quota.')
        for i,e in enumerate(source['garments'],1):
            gid=f'2e2d0000-0000-4000-8000-{i:012d}';mid=progress['media'][e['fixture_id']];a=e['attributes']
            if c.execute('select 1 from garments where id=?',(gid,)).fetchone():raise ValueError('Unregistered existing fixture ID; refuse duplicate/replacement.')
            from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
            role,layer=GARMENT_STRUCTURE[a['category']]
            attrs={'phase2nd_synthetic':{'origin':ORIGIN,'instance_id':catalog['instance_id'],'fixture_id':e['fixture_id'],'declaration':a},
                'garment_type':role,'layering_index':layer,'style':a['style'],'material':a['material'],'fit':a['silhouette'],
                'pattern':a['pattern'],'primary_colour':a['primary_colour'],'custom_tags':['SYNTHETIC DEVELOPMENT TEST','Authored fixture attributes; not extraction or owner review']}
            media=c.execute('select * from media_assets where id=? and user_id=?',(mid,owner)).fetchone()
            path=MEDIA_DIR.resolve()/media['storage_key'] if media else None
            if not media or media['status']!='available' or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=e['image_sha256']:raise ValueError('Changed staged media.')
            name=e['row']['name'].replace('TEST-2N-','TEST-2ND-')+' SYNTHETIC'
            wire=json.dumps(attrs,sort_keys=True)
            c.execute("insert into garments (id,user_id,profile_id,processing_item_id,preferred_media_id,name,category,primary_colour,pattern,attributes_json,status,is_favourite,created_at,updated_at,style_tags,custom_tags,structural_scores,additional_attributes,embedding) values (?,?,NULL,NULL,?,?,?,?,?,?,'available',0,?,?,?,?,?,?,?)",
                (gid,owner,mid,name,a['category'],a['primary_colour'],a['pattern'],wire,now,now,json.dumps(a['style']),json.dumps(attrs['custom_tags']),json.dumps({'garment_role':role,'layering_index':layer}),wire,'null'))
            catalog['garments'].append({'fixture_id':e['fixture_id'],'attributes':a,'row':dict(c.execute('select * from garments where id=?',(gid,)).fetchone()),'media':dict(media),'image_sha256':e['image_sha256']})
        cfg={'database':str(DATABASE_PATH.resolve()),'media':str(MEDIA_DIR.resolve()),'catalog':str(root/'catalog.json'),'catalog_sha256':digest(catalog),'profile':PROFILE,'proof_secret':secrets.token_hex(32)}
        c.execute('insert into phase2nd_instance values (?,?)',(catalog['instance_id'],cfg['catalog_sha256']))
        write(root/'catalog.json',catalog);write(cfgpath,cfg)
    # Complete rows are admitted only after a full independent source check.
    s=Store(cfg)
    with s.connection() as c:
        for wearer in profiles:s.capture(c,owner,wearer)
    return {'added':30,'images':30,'config':str(cfgpath),'owner_id':owner}

def retire(*,apply=False):
    from .gateway import open_store
    s=open_store();report=[]
    with s.connection() as c:
        if apply:c.execute('BEGIN IMMEDIATE')
        # All source members are captured by every fixture history proof.
        history=c.execute('select count(*) from phase2nd_proofs').fetchone()[0]
        for e in s.catalog['garments']:
            gid=e['row']['id'];r=c.execute('select * from garments where id=?',(gid,)).fetchone()
            if not r:report.append({'id':gid,'action':'already_absent'});continue
            current=dict(r)
            if current!=e['row']:
                cfg_retired=s.config.get('retired',False)
                if cfg_retired and current['status']=='archived' and {**current,'status':e['row']['status']}==e['row']:
                    report.append({'id':gid,'action':'already_retired'});continue
                report.append({'id':gid,'action':'skip_later_edit'});continue
            referenced=history>0
            for table,col in [('outfit_items','garment_id'),('recommendation_items','garment_id'),('recommendation_item_snapshots','garment_id'),('visualisation_items','garment_id')]:
                referenced=referenced or c.execute('select 1 from '+table+' where '+col+'=? limit 1',(gid,)).fetchone() is not None
            if referenced:
                if apply:c.execute("update garments set status='archived' where id=?",(gid,))
                report.append({'id':gid,'action':'archive_retain_history_and_media'})
            else:
                if apply:c.execute('delete from garments where id=?',(gid,))
                # Media is deliberately retained, even for an unused fixture:
                # later assets may reference it outside ordinary garment FKs.
                report.append({'id':gid,'action':'remove_unchanged_unreferenced_row_retain_media'})
    if apply:
        cfgpath=Path(os.getenv('SMART_WARDROBE_MAIN_FIXTURE_CONFIG',s.database.parent/'phase2nd/runtime.private.json'));cfg=json.loads(cfgpath.read_text());cfg['retired']=True;write(cfgpath,cfg)
    return {'dry_run':not apply,'items':report,'media_deleted':0,'account_or_history_deleted':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['seed','retire']);parser.add_argument('--source-catalog');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(seed(args.source_catalog) if args.command=='seed' else retire(apply=args.apply),indent=2))
