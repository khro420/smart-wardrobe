"""Actual-service four-way measurements; retain failures and resource variation."""
import argparse,json
from pathlib import Path
from statistics import median
from summarize_compact_exhaustive import summarize,stats


def envelope(values):
    values=[v for v in values if isinstance(v,(int,float))]
    return {'count':len(values),'minimum':min(values) if values else None,
        'median':median(values) if values else None,'maximum':max(values) if values else None}


def report(data):
    result=summarize(data)
    result['tail_method']='Observed maximum only; two/three pairs cannot establish a reliable percentile SLA.'
    result['engine_mapping']={'reference':'reference','compact':'compact_exhaustive'}
    for group in result['groups']:
        rows=[r for r in data['records'] if (r['name'],r['profile'],r['layer'],r['arm'])==(group['name'],group['profile'],group['layer'],group['arm'])]
        samples=[r[k] for r in rows for k in ('resources_before','resources_after') if k in r]
        group['resources']={'observations':len(samples),'unavailable':sum(not r.get('available',False) for r in samples),
            'free_physical_kib':envelope(r.get('system',{}).get('free_physical_kib') for r in samples),
            'cpu_load_percent':envelope(r.get('system',{}).get('cpu_load_percent') for r in samples)}
        stages=[r.get('job',{}).get('stages') or {} for r in rows]
        group['service_stages']={k:stats(s[k] for s in stages if k in s) for k in sorted({k for s in stages for k in s})}
    result['acceptance']='Exploratory measured configurations only. Formal baseline requires approval; failures and contended samples are not discarded.'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    if args.output.exists():p.error('Refusing to overwrite retained summary')
    result=report(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'trials':result['trials'],'errors':result['errors']}))
