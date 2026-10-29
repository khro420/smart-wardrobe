"""Reproduce local three-layer latency summaries; no timing/quality fabrication."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'storage/verification/phase5f2e3c3b'
PROFILES=('compatibility_deferred','experimental_compatibility_decision_v1')


def summarize():
    lines=['## Actual local integrated measurements','',
        'Seconds; three retained trials per cell. Tail = observed maximum, not p95.',
        'Successful completions only in median/max columns; every failed trial is counted explicitly.',
        'Backend column is middleware processing for the real HTTP trials. Browser',
        'times include submit-to-visible completion; all layers use fresh submission keys.','']
    results={}
    for profile in PROFILES:
        data=json.loads((OUTPUT/('latency-'+profile+'.json')).read_text(encoding='utf-8'))
        assert data['profile']==profile and data['metadata']['profile']==profile
        assert len(data['records'])==45
        lines.extend([f'### {profile}','','| Garments | Candidates | Service median / max | HTTP median / max | Backend median / max | Browser median / max | Errors service/HTTP/browser |','|---|---|---|---|---|---|---|'])
        rows=[]
        for name in ('20','50','100','200','stress'):
            meta=data['metadata']['workloads'][name];groups={}
            for layer in ('service','http','browser'):
                records=[r for r in data['records'] if r['name']==name and r['layer']==layer]
                assert len(records)==3 and {r['trial'] for r in records}=={0,1,2}
                successful=[r for r in records if not r.get('error')]
                assert all(r['outcome']=='Selected' and r['scored_count']==meta['candidate_count'] for r in successful)
                values=[r['seconds'] for r in successful]
                errors=[r for r in records if r.get('error')]
                groups[layer]={'median':statistics.median(values) if values else None,'max':max(values) if values else None,
                    'successful':len(successful),'errors':len(errors),'over_five_seconds':sum(v>5 for v in values),
                    'error_samples':errors}
                for r in errors:
                    if r.get('eventual_backend_completion'):assert r['eventual_backend_completion']['scored_count']==meta['candidate_count']
                if layer=='http':
                    values=[r['backend_seconds'] for r in successful]
                    groups['backend']={'median':statistics.median(values) if values else None,'max':max(values) if values else None}
            fmt=lambda layer:f"{groups[layer]['median']:.3f} / {groups[layer]['max']:.3f}" if groups[layer]['median'] is not None else 'No completed response'
            errors='/'.join(str(groups[x]['errors']) for x in ('service','http','browser'))
            lines.append(f"| {name} | {meta['candidate_count']:,} | {fmt('service')} | {fmt('http')} | {fmt('backend')} | {fmt('browser')} | {errors} |")
            rows.append({'workload':name,**meta,'summary':groups})
        results[profile]=rows
        lines.append('')
    before=json.loads((OUTPUT/'before.json').read_text(encoding='utf-8'))
    original=json.loads((ROOT/'storage/verification/phase5f2e3a/before.json').read_text(encoding='utf-8'))
    digest=lambda name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    changed=[n for n,h in original.items() if digest(n)!=h]
    authorized={'backend/app/application/recommendation/outfit_assistant_service.py',
        'backend/app/infrastructure/workflow_runtime.py','backend/app/application/chat_history/chat_history_service.py'}
    assert len(original)==157 and set(changed)==authorized
    pins=[n for n in before if n.startswith('backend/tests/fixtures/')]
    assert all(digest(n)==before[n] for n in pins)
    errors=sum(bool(r.get('error')) for p in PROFILES for r in json.loads((OUTPUT/('latency-'+p+'.json')).read_text(encoding='utf-8'))['records'])
    lines.extend([f'All 90 scheduled trials are retained: {90-errors} successful completions, {errors} errors.',
        'Every successful result has the expected full candidate count. Errors remain failures,',
        'even where read-only inspection subsequently confirms backend commit after proxy reset.',
        'No no-result substitute, candidate truncation or timing sample exclusion occurred.',
        'NFR-02 remains unmet for representative workloads exceeding five seconds; these',
        'local synthetic measurements do not approve a final deployment baseline or human fashion quality.','',
        f'Integrity: 154/157 original application files byte-identical; exactly three separately',
        f'authorized integration replacements. All {len(pins)} pre-phase fixture/manifests/archive',
        'entries in the phase snapshot remain byte-identical; old reference pins were not rewritten.',''])
    result={'profiles':results,'trials':90,'errors':errors,'successful':90-errors,'original_unchanged':154,'authorized_replacements':changed,
        'prior_fixture_entries_unchanged':len(pins),'measurement_files_sha256':{
            p:digest('storage/verification/phase5f2e3c3b/latency-'+p+'.json') for p in PROFILES}}
    (OUTPUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (OUTPUT/'measurements.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines))


if __name__=='__main__': summarize()
