"""Train lightweight visible-attribute heads on Fashionpedia training crops."""
from __future__ import annotations
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import json, random
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from transformers import AutoProcessor, SiglipModel

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

class Crops(Dataset):
    def __init__(self, rows, image_root, field_labels, processor): self.rows,self.image_root,self.field_labels,self.processor=rows,image_root,field_labels,processor
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        r=self.rows[i]; x,y,w,h=r['bbox']
        with Image.open(self.image_root/r['file_name']) as im:
            im=im.convert('RGB'); crop=im.crop((max(0,int(x)),max(0,int(y)),min(im.width,int(x+w)),min(im.height,int(y+h))))
        return self.processor(images=crop, return_tensors='pt')['pixel_values'][0], r['field'], self.field_labels[r['field']][r['label_id']]

def batch(items):
    return torch.stack([x[0] for x in items]), [x[1] for x in items], torch.tensor([x[2] for x in items])

def main():
    ap=ArgumentParser(); ap.add_argument('--steps',type=int,default=2000); ap.add_argument('--batch-size',type=int,default=8); ap.add_argument('--lr',type=float,default=1e-3); ap.add_argument('--seed',type=int,default=20261010); ap.add_argument('--manifest',type=Path,default=ROOT/'storage'/'verification'/'fashionpedia_attributes'/'fashionpedia_training_manifest.json'); ap.add_argument('--run-dir',type=Path,default=BACKEND/'runs'/'fashionpedia_attribute_heads'); args=ap.parse_args()
    torch.manual_seed(args.seed); random.seed(args.seed)
    evidence=ROOT/'storage'/'verification'/'fashionpedia_attributes'; manifest=json.loads(args.manifest.read_text())
    vocab={f:{x['id']:i for i,x in enumerate(v)} for f,v in manifest['label_vocabulary'].items()}
    processor=AutoProcessor.from_pretrained(BACKEND/'models'/'vtoff'/'siglip-base-patch16-512',local_files_only=True)
    data=Crops(manifest['rows'],Path(manifest['dataset_root'])/'train',vocab,processor)
    field_counts={field:sum(row['field']==field for row in manifest['rows']) for field in vocab}
    # Give each visible field equal opportunity to update, despite Fashionpedia's
    # naturally much more frequent pattern labels.
    sampler=WeightedRandomSampler([1/field_counts[row['field']] for row in manifest['rows']], num_samples=args.steps*args.batch_size, replacement=True)
    loader=DataLoader(data,batch_size=args.batch_size,sampler=sampler,num_workers=2,pin_memory=True,collate_fn=batch,drop_last=True)
    device='cuda' if torch.cuda.is_available() else 'cpu'; base=SiglipModel.from_pretrained(BACKEND/'models'/'vtoff'/'siglip-base-patch16-512',local_files_only=True).to(device).eval()
    for p in base.parameters(): p.requires_grad=False
    heads=nn.ModuleDict({f:nn.Sequential(nn.LayerNorm(768),nn.Linear(768,len(v))) for f,v in manifest['label_vocabulary'].items()}).to(device)
    opt=torch.optim.AdamW(heads.parameters(),lr=args.lr,weight_decay=1e-4); losses=[]; iterator=iter(loader)
    for step in range(1,args.steps+1):
        try: pixels,fields,labels=next(iterator)
        except StopIteration: iterator=iter(loader); pixels,fields,labels=next(iterator)
        with torch.no_grad(), torch.autocast('cuda',dtype=torch.bfloat16,enabled=device=='cuda'): features=base.get_image_features(pixel_values=pixels.to(device))
        loss=0.; count=0
        for field in set(fields):
            ix=[j for j,name in enumerate(fields) if name==field]; idx=torch.tensor(ix,device=device)
            loss=loss+nn.functional.cross_entropy(heads[field](features.index_select(0,idx).float()),labels.index_select(0,idx.cpu()).to(device)); count+=1
        loss=loss/count; opt.zero_grad(); loss.backward(); opt.step(); losses.append(float(loss.detach().cpu()))
        if step%100==0: print(json.dumps({'step':step,'loss':sum(losses[-100:])/100}),flush=True)
    run=args.run_dir; run.mkdir(parents=True,exist_ok=True)
    out=run / f"step{args.steps}.pt"; torch.save({'heads':heads.state_dict(),'vocabulary':manifest['label_vocabulary'],'steps':args.steps,'seed':args.seed,'loss':sum(losses[-100:])/min(100,len(losses))},out)
    (run/'training_results.json').write_text(json.dumps({'status':'complete','created_at':datetime.now(timezone.utc).isoformat(),'checkpoint':str(out),'steps':args.steps,'loss_mean_last_100':sum(losses[-100:])/min(100,len(losses)),'validation_used_for_training':False,'base':'local SigLIP frozen visual encoder'},indent=2))
    print(json.dumps({'status':'complete','checkpoint':str(out),'loss':sum(losses[-100:])/min(100,len(losses))}))
if __name__=='__main__': main()
