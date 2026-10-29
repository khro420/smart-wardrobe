"""Paired ABBA completed-2B versus live stream progress benchmark.

Latency is uninstrumented. Progress validation counts, RSS and profiles are
separate runs after all timing cells. Synthetic confirmed SQLite fixtures only.
"""
import argparse,hashlib,importlib.metadata,json,platform,pstats,statistics,subprocess,sys
from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from tests.test_assistant_performance_equivalence import garment,preferences

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--sizes',nargs='+',type=int,default=[20,50,100,200])
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--warmups',type=int,default=2)
    p.add_argument('--measure-only',action='store_true')
    p.add_argument('--diagnostics-only',action='store_true')
    p.add_argument('--reference',type=Path,default=BACKEND/'tests/fixtures/performance_reference_2b')
    p.add_argument('--candidate-reference',type=Path,help='Independently archived experimental arm instead of live app')
    args=p.parse_args()
    if args.repeats<2 or args.warmups<1:p.error('Repeated measured trials and excluded warmups required')
    args.output.mkdir(parents=True,exist_ok=True)
    reference=args.reference
    worker=BACKEND/'tests/performance_worker.py'
    metadata={'python':sys.version,'platform':platform.platform(),'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
      'reference_sha256':hashlib.sha256((reference/'app.zip').read_bytes()).hexdigest(),
      'source_hashes':{n:hashlib.sha256((BACKEND/'app/application/recommendation'/n).read_bytes()).hexdigest() for n in ('recommendation_engine.py','request_candidate_session.py')},
      'method':'ABBA fresh worker blocks, two excluded warmups and three trials per block by default; six measured samples per arm. No tracing/profiling during timings. Full Assistant service, not HTTP/browser.', 'blocks':[],'summary':[],'diagnostics':[],'profiles':[]}
    metadata['source_hashes']['recommendation_score.py']=hashlib.sha256((BACKEND/'app/domain/value_objects/recommendation_score.py').read_bytes()).hexdigest()
    metadata['reference_directory']=str(reference.resolve())
    destination=args.output/'results.json'
    if args.diagnostics_only:metadata=json.loads(destination.read_text())
    if args.candidate_reference:
        candidate_digest=hashlib.sha256((args.candidate_reference/'app.zip').read_bytes()).hexdigest()
        if candidate_digest==metadata['reference_sha256']:raise ValueError('Reference and trial archives must differ')
        metadata['candidate_reference_sha256']=candidate_digest
        metadata['candidate_reference_directory']=str(args.candidate_reference.resolve())
        trial_manifest=json.loads((args.candidate_reference/'manifest.json').read_text())
        for name in metadata['source_hashes']:
            folder='app/domain/value_objects/' if name=='recommendation_score.py' else 'app/application/recommendation/'
            metadata['source_hashes'][name]=trial_manifest[folder+name]
    def save():destination.write_text(json.dumps(metadata,indent=2)+'\n')
    def arm(variant):
        return (args.candidate_reference,'original') if variant=='combined' and args.candidate_reference else (reference,variant)
    def run(fixture,label,variant,extra):
        out=args.output/(label+'.json')
        arm_reference,arm_variant=arm(variant)
        subprocess.run([sys.executable,'-B',str(worker),'--reference',str(arm_reference),'--variant',arm_variant,'--fixtures',str(fixture),'--output',str(out),*extra],check=True)
        return json.loads(out.read_text())[0]
    jobs=[]
    for size in args.sizes:
        counts=[int(size*.4),int(size*.4),int(size*.1)];counts.append(size-sum(counts))
        rows=[]
        for role,category,count in zip(('top','bottom','dress','outerwear'),('vest','trousers','vest_dress','long_sleeve_outwear'),counts):
            rows.extend(garment(f'{role}-{i:06d}',category,primary_colour='blue',style_tags=['vintage']) for i in range(count))
        expected=(counts[0]*counts[1]+counts[2])*(1+counts[3])
        for populated in (False,True):
            label=f'size-{size}-prefs-{int(populated)}';fixture=args.output/(label+'-input.json')
            if not args.diagnostics_only:fixture.write_text(json.dumps([dict(name=label,garments=rows,preferences=preferences() if populated else [],service=True)]))
            jobs.append((label,fixture,expected))
            if args.diagnostics_only:continue
            baseline=None;collected={'original':[],'combined':[]}
            for block,variant in enumerate(('original','combined','combined','original')):
                print(f'Timing {label} block {block}: {variant}',flush=True)
                value=run(fixture,label+f'-block-{block}',variant,['--repeats',str(args.repeats),'--warmups',str(args.warmups)])
                fingerprint=(value['winner'],value['score_metadata'])
                if baseline is None:baseline=fingerprint
                if fingerprint!=baseline or value['scored_count']!=expected:raise RuntimeError('Full outcome changed')
                collected[variant].extend(value['timings'])
                metadata['blocks'].append(dict(label=label,variant=variant,block=block,candidates=expected,timings=value['timings']))
                save()
            record=dict(size=size,populated=populated,candidates=expected,fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
            for variant,samples in collected.items():
                walls=[s['wall'] for s in samples]
                record[variant]=dict(median=statistics.median(walls),minimum=min(walls),maximum=max(walls),cpu_median=statistics.median(s['cpu'] for s in samples),trials=len(samples))
            record['speedup_percent']=100*(1-record['combined']['median']/record['original']['median'])
            metadata['summary'].append(record);save();print(json.dumps(record),flush=True)
    if args.measure_only:return
    # Separate instrumentation, never mixed with latency measurements.
    for label,fixture,expected in jobs:
        progress_reference = None
        for variant in ('original','combined'):
            print(f'Diagnostics {label} {variant}',flush=True)
            value=run(fixture,label+'-'+variant+'-diagnostics',variant,['--diagnostics','--progress-digest'])
            if value['scored_count']!=expected:raise RuntimeError('Incomplete diagnostic stream')
            comparable=(value['progress'],value['winner'],value['score_metadata'])
            if progress_reference is None:progress_reference=comparable
            elif comparable!=progress_reference:raise RuntimeError('Progress or complete outcome changed')
            metadata['diagnostics'].append(dict(label=label,variant=variant,progress=value['progress'],memory=value['cache_diagnostics']))
            save()
    for label,fixture,expected in jobs:
        if not label.startswith(f'size-{max(args.sizes)}-'):continue
        for variant in ('original','combined'):
            print(f'Separate profile {label} {variant}',flush=True)
            prof=args.output/(label+'-'+variant+'.prof');out=args.output/(label+'-'+variant+'-profile.json')
            arm_reference,arm_variant=arm(variant)
            subprocess.run([sys.executable,'-B','-m','cProfile','-o',str(prof),str(worker),'--reference',str(arm_reference),'--variant',arm_variant,'--fixtures',str(fixture),'--output',str(out)],check=True)
            if json.loads(out.read_text())[0]['scored_count']!=expected:raise RuntimeError('Incomplete profile')
            stats=pstats.Stats(str(prof))
            metadata['profiles'].append(dict(label=label,variant=variant,self_seconds=stats.total_tt,functions=[dict(file=k[0],line=k[1],function=k[2],calls=v[1],self=v[2],cumulative=v[3]) for k,v in stats.stats.items()]))
            save()
if __name__=='__main__':main()
