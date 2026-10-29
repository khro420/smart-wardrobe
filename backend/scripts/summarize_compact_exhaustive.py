"""Retain failures, separate transport/service/instrumented populations."""
import argparse
import json
from pathlib import Path
from statistics import median


def stats(values):
    values=list(values)
    return {'count':len(values),'median':median(values) if values else None,'maximum':max(values) if values else None}


def summarize(data):
    transport='records' in data
    rows=data['records'] if transport else data['runs']
    groups={}
    for row in rows:groups.setdefault((row['name'],row['profile'],row.get('layer','service'),row['arm']),[]).append(row)
    result=[]
    for (name,profile,layer,arm),members in groups.items():
        jobs=[r.get('job',r) for r in members]
        entry={'name':name,'profile':profile,'layer':layer,'arm':arm,'trials':len(members),
            'errors':sum(r.get('error') is not None if transport else r['status']!='Selected' for r in members),
            'elapsed_all':stats(r['seconds'] for r in members),
            'elapsed_successful_only':stats(r['seconds'] for r in members if r.get('error') is None and (transport or r['status']=='Selected')),
            'service':stats(j['service_seconds'] if transport else r['seconds'] for j,r in zip(jobs,members) if not transport or 'service_seconds' in j),
            'cpu':stats(j['cpu_seconds'] for j in jobs if 'cpu_seconds' in j),
            'fingerprints':sorted({r['fingerprint'] for r in members if 'fingerprint' in r}),
            'candidate_counts':sorted({r.get('candidate_count',r.get('job',{}).get('candidate_count')) for r in members}-{None}),
            'statuses':[r.get('http_status',r.get('status')) for r in members]}
        if transport:
            entry['unsettled_jobs']=sum(not j.get('done',False) for j in jobs)
            entry['response_arrival']=stats(r['http_seconds'] for r in members if 'http_seconds' in r)
            entry['proxy_network_browser_residual']=stats(r['http_seconds']-r['backend_seconds'] for r in members if r.get('http_seconds') is not None and r.get('backend_seconds') is not None)
        memory=[j.get('memory',{}) for j in jobs]
        entry['working_set']=stats(m['working_set_bytes'] for m in memory if m.get('available'))
        entry['process_lifetime_peak']=stats(m['process_lifetime_peak_bytes'] for m in memory if m.get('available'))
        stages=[j.get('kernel_stages',r.get('kernel_stages',{})) for j,r in zip(jobs,members)]
        entry['kernel_stages']={key:stats(s[key] for s in stages if key in s) for key in sorted({k for s in stages for k in s})}
        result.append(entry)
    for name,profile in dict.fromkeys((r['name'],r['profile']) for r in rows):
        hashes={r['fingerprint'] for r in rows if (r['name'],r['profile'])==(name,profile) and 'fingerprint' in r}
        if len(hashes)>1:raise ValueError('Semantic result mismatch')
    return {'method':'Medians and observed maxima; all failures retained. Failure elapsed time is not successful recommendation latency. Windows peak is process-lifetime, not request-attributable. Instrumented populations remain separate.',
        'instrumented':data.get('instrumented',False),'trials':len(rows),'errors':sum(g['errors'] for g in result),
        'metadata':data.get('metadata'),'groups':result}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    result=summarize(json.loads(args.input.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'trials':result['trials'],'errors':result['errors']}))
