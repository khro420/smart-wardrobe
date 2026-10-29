"""Streaming every-candidate public evidence audit; never latency acceptance."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--size',default='100');p.add_argument('--diverse',action='store_true');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'storage'):p.error('New output under storage required')
    from tests import assistant_decision_server as fixture
    from tests.test_compact_exhaustive import oracle_records
    from app.application.recommendation.compact_exhaustive_scorer import CompactExhaustiveScorer,DEFERRED,EXPERIMENTAL
    from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
    from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    from tests.test_rule_based_compatibility import Preferences
    owner=fixture.workloads[args.size]['owner']
    if args.diverse:
        with fixture.db.connection() as c:
            rows=c.execute('SELECT id FROM garments WHERE user_id=? ORDER BY id',(owner,)).fetchall()
            for i,row in enumerate(rows):
                colours=('blue','red','white',None,'#182a46'); styles=(['vintage'],['classic'],['sporty'],None,[],['classic','bad'])
                tags=styles[(i//len(colours))%len(styles)];attrs=json.dumps({'style':tags})
                c.execute('UPDATE garments SET primary_colour=?,style_tags=?,attributes_json=?,additional_attributes=? WHERE id=?',(colours[i%len(colours)],json.dumps(tags),attrs,attrs,row['id']))
            for kind,values in (('styles',['vintage']),('garment_categories',[{'kind':'group','value':'top'}])):
                c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(owner+kind,owner,kind,json.dumps({'values':values}),'synthetic','now','now'))
    query=SqliteConfirmedGarmentQuery(); garments=query.get_confirmed_available_garments(owner)
    preferences=SqliteActivePreferenceQuery().get_active_preferences(owner); structured=StructuredOutfitRequest()
    result={'metadata':fixture.metadata(),'diverse':args.diverse,'method':'Two lazily compared every-candidate streams; complete public explanations and exact rational values; no candidate list retained. Audit overhead is not performance evidence.','profiles':[]}
    for profile in (DEFERRED,EXPERIMENTAL):
        expected=iter(oracle_records(garments,structured,preferences,profile,None,owner));digest=hashlib.sha256();counts={'examined':0,'verified':0,'fail':0,'unknown':0};bases={}
        best=None
        def audit(actual):
            nonlocal best
            reference=next(expected)
            if reference!=actual:
                result['mismatch']={'key':actual['key'],'reference':reference,'actual':actual}
                output.write_text(json.dumps(result,indent=2,default=lambda f:{'numerator':f.numerator,'denominator':f.denominator})+'\n')
                raise AssertionError('Candidate mismatch: '+repr(actual['key']))
            data=json.dumps(actual,sort_keys=True,separators=(',',':'),default=lambda f:{'numerator':f.numerator,'denominator':f.denominator} if isinstance(f,Fraction) else None).encode()
            digest.update(len(data).to_bytes(8,'big'));digest.update(data);counts['examined']+=1
            states={x['state'] for x in actual['evaluation']['conditions']}
            state='Fail' if 'Fail' in states else 'Unknown' if 'Unknown' in states else 'Pass'
            if actual['verified']:
                counts['verified']+=1;score=actual['score']
                c=score['compatibility'];decision=c.get('decision')
                if decision:bases[decision['basis']]=bases.get(decision['basis'],0)+1
                values=(score['total'],score['request_match']['summary']['value'] or Fraction(0),decision['value'] if decision else Fraction(0),score['preference']['summary']['value'] or Fraction(0))
                if best is None or values>best[0] or values==best[0] and actual['key']<best[1]:best=(values,actual['key'])
            elif state=='Fail':counts['fail']+=1
            else:counts['unknown']+=1
        start=perf_counter(); kernel=CompactExhaustiveScorer(query,Preferences(preferences),profile,audit=audit)
        outcome=kernel.rank(owner,structured)
        result['last_outcome']={'profile':profile,'status':outcome.status,**counts}
        output.write_text(json.dumps(result,indent=2,default=lambda f:{'numerator':f.numerator,'denominator':f.denominator})+'\n')
        assert next(expected,None) is None,'Reference stream not exhausted'
        assert counts['examined']==fixture.workloads[args.size]['candidate_count']
        assert outcome.complete and outcome.scored_count==counts['verified']
        assert outcome.winner.verified.candidate.key==best[1]
        row={'profile':profile,**counts,'complete':outcome.complete,'status':outcome.status,'sha256':digest.hexdigest(),'decision_basis':bases,'audit_seconds':perf_counter()-start,'winner':best[1]}
        result['profiles'].append(row);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(row),flush=True)
    fixture.temporary.cleanup()


if __name__=='__main__':main()
