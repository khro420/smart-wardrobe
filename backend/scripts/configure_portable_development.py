"""Generate only local configuration; existing files are backed up and merged."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,secrets,shutil,json
ROOT=Path(__file__).resolve().parents[2]

def parse(path):
    result={}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1);result[k.strip()]=v.strip()
    return result

def write(path,updates):
    lines=path.read_text(encoding='utf-8-sig').splitlines() if path.is_file() else []
    old=parse(path);values={**old,**updates};written=set();output=[]
    for line in lines:
        k=line.split('=',1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else None
        if k in values:
            if k not in written:output.append(k+'='+values[k]);written.add(k)
        else:output.append(line)
    output.extend(k+'='+v for k,v in values.items() if k not in written)
    wire=('\n'.join(output)+'\n').encode()
    if path.is_file() and path.read_bytes()==wire:return
    if path.is_file():
        backup=ROOT/'storage/config-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')/path.parent.name
        backup.mkdir(parents=True);shutil.copy2(path,backup/path.name)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(wire)

def configure(storage,mode,port):
    storage=Path(storage).resolve();backend=ROOT/'backend/.env';old=parse(backend)
    values=parse(ROOT/'backend/.env.example')
    token=old.get('SMART_WARDROBE_TOKEN_SECRET','')
    if len(token)<32 or token.startswith(('GENERATE','change-','replace-')):token=secrets.token_hex(32)
    values.update(SMART_WARDROBE_TOKEN_SECRET=token,SMART_WARDROBE_DATA_DIR=str(storage),SMART_WARDROBE_DATABASE=str(storage/'smart_wardrobe.db'),SMART_WARDROBE_MAIN_FIXTURE_CONFIG=str(storage/'phase2nd/runtime.private.json'))
    if mode=='GPU':
        values.update(SMART_WARDROBE_AI_MODE='production',SMART_WARDROBE_VTOFF_ENABLED='auto',SMART_WARDROBE_VTON_ENABLED='auto',SMART_WARDROBE_EMBEDDING_ENABLED='auto',SMART_WARDROBE_FASHIONPEDIA_ATTRIBUTES_ENABLED='auto')
    write(backend,values)
    front=parse(ROOT/'frontend/.env.example');front['SMART_WARDROBE_BACKEND_URL']='http://127.0.0.1:'+str(port);write(ROOT/'frontend/.env.local',front)
    print(json.dumps({'configuration':'local files generated; keys not printed','mode':mode,'storage':str(storage),'backend_port':port,'previous_settings':'backed up; unrelated keys preserved; requested development selectors updated'}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--storage',type=Path,required=True);ap.add_argument('--mode',choices=('CPU','GPU'),default='CPU');ap.add_argument('--backend-port',type=int,default=8000);a=ap.parse_args();configure(a.storage,a.mode,a.backend_port)
