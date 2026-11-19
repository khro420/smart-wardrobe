"""Install pinned, hash-verified offline NLP assets. Never reads a wardrobe DB."""
from pathlib import Path
import hashlib,json,os,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def setup():
 from app.development.mixed_wardrobe.semantic_model import MANIFEST,ASSETS,load
 manifest=json.loads(MANIFEST.read_text());ASSETS.mkdir(parents=True,exist_ok=True)
 for name,item in manifest['files'].items():
  if Path(name).name!=name:raise ValueError('Invalid model manifest path.')
  target=ASSETS/name
  if target.exists():
   if target.stat().st_size!=item['bytes'] or sha(target)!=item['sha256']:raise ValueError('Unexpected model bytes; no existing file was replaced: '+name)
   continue
  part=ASSETS/(name+'.part');count=0;digest=hashlib.sha256()
  url='https://huggingface.co/'+manifest['model']+'/resolve/'+manifest['revision']+'/'+name
  with urllib.request.urlopen(url,timeout=90) as response,part.open('wb') as output:
   while block:=response.read(1024*1024):
    count+=len(block)
    if count>item['bytes']:raise ValueError('Oversized model download.')
    output.write(block);digest.update(block)
  if count!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise ValueError('Model integrity failure: '+name)
  os.replace(part,target)
 load()  # Includes syntax package version and every trained pipeline hash.
 print('Offline NLI and dependency models verified. No database or API request used.')

if __name__=='__main__':setup()
