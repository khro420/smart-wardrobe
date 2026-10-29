"""Isolated synthetic exact-validator oracle, including supported subclasses."""
import argparse,dataclasses,hashlib,json,random,sys,tempfile,zipfile,timeit,statistics,tracemalloc
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal
BACKEND=Path(__file__).resolve().parents[1]

def run():
    from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
    calls=[]
    class Numeric(F):
        def __mul__(self,other):calls.append('numeric.mul');return super().__mul__(other)
        def __rmul__(self,other):calls.append('numeric.rmul');return super().__rmul__(other)
        def __add__(self,other):calls.append('numeric.add');return super().__add__(other)
        def __radd__(self,other):calls.append('numeric.radd');return super().__radd__(other)
        def __ne__(self,other):calls.append('numeric.ne');return super().__ne__(other)
    class Weights(list):
        def __iter__(self):calls.append('weights.iter');return super().__iter__()
    class ContainerMeta(type):
        def __eq__(self,other):calls.append('container_meta.eq');return False
    class MetaWeights(list,metaclass=ContainerMeta):
        pass
    class Evidence(ScoreEvidence):
        def __getattribute__(self,name):
            if name=='value':calls.append('evidence.value')
            return super().__getattribute__(name)
    class Component(ComponentScore):
        @property
        def contribution(self):calls.append('component.contribution');return super().contribution
    class Alternative(ComponentScore):
        @property
        def contribution(self):calls.append('alternative.contribution');return alternate[0]
    alternate=[F(0)]
    def canonical(v):
        if isinstance(v,F):return {'fraction':[str(v.numerator),str(v.denominator)]}
        if dataclasses.is_dataclass(v):return {f.name:canonical(getattr(v,f.name)) for f in dataclasses.fields(v)}
        if isinstance(v,(tuple,list)):return [canonical(x) for x in v]
        return v
    records=[]
    def case(name,values=(F(1,2),None,F(1,3)),weights=(F(7,10),F(0),F(3,10)),total='calculate',kind=None,invalid=None,profile='synthetic',version='synthetic-v1',state=None):
        evidence=[ScoreEvidence(n,v,state or ('Available' if v is not None else ('Unavailable' if i==1 else 'NoPreferences')),1 if v is not None else 0,1,('synthetic:known' if v is not None else 'synthetic:missing',)) for i,(n,v) in enumerate(zip(('request','compatibility','preference'),values))]
        components=[ComponentScore(e,(e,)) for e in evidence]
        if total=='calculate':total=sum(w*c.contribution for w,c in zip(weights,components))
        if kind=='total-subclass':total=Numeric(total)
        if kind=='weight-subclass':weights=(Numeric(weights[0]),*weights[1:])
        if kind=='value-subclass':components[0]=ComponentScore(dataclasses.replace(evidence[0],value=Numeric(evidence[0].value)))
        if kind=='weights-list':weights=list(weights)
        if kind=='weights-subclass':weights=Weights(weights)
        if kind=='weights-metaclass':weights=MetaWeights(weights)
        if kind=='component-subclass':components[0]=Component(evidence[0])
        if kind=='evidence-subclass':components[0]=ComponentScore(Evidence(**dataclasses.asdict(evidence[0])))
        if kind and kind.startswith('alternative-'):
            alternate[0]={'alternative-int':1,'alternative-bool':True,'alternative-float':0.5,'alternative-decimal':Decimal('0.5'),'alternative-bad':object()}[kind]
            components[1]=Alternative(evidence[1])
        if invalid:
            for key,value in invalid.items():
                if key=='component':components[0]=value
                elif key=='weights':weights=value
                elif key=='total':total=value
        calls.clear()
        try:
            score=RecommendationScore(*components,total,profile,version,weights)
        except BaseException as exc:
            records.append({'name':name,'error':[type(exc).__name__,str(exc)],'cause':str(exc.__cause__) if exc.__cause__ else None,'calls':list(calls)})
        else:
            trace=list(calls)
            records.append({'name':name,'score':canonical(score),'calls':trace})
    profiles=[('compatibility_deferred',(F(7,10),F(0),F(3,10))),('three_component_experimental',(F(1,2),F(3,10),F(1,5))),('holistic_experimental',(F(1,2),F(3,10),F(1,5))),('only-request',(F(1),F(0),F(0))),('only-compatibility',(F(0),F(1),F(0))),('only-preference',(F(0),F(0),F(1)))]
    for name,weights in profiles:
        for values in ((F(0),F(0),F(0)),(F(1),F(1),F(1)),(F(1,3),F(2,7),F(4,11)),(F(1,2),None,None),(None,None,None)):
            total=sum(w*(v or F(0)) for w,v in zip(weights,values))
            case(name+str(values),values,weights,total,profile=name)
            case(name+'-mismatch'+str(values),values,weights,F(1,2) if total!=F(1,2) else F(1,3),profile=name)
    for kind in ('total-subclass','weight-subclass','value-subclass','weights-list','weights-subclass','weights-metaclass','component-subclass','evidence-subclass','alternative-int','alternative-bool','alternative-float','alternative-decimal','alternative-bad'):
        case(kind,kind=kind)
    # A zero weight does not excuse evaluating an unsupported contribution.
    for kind in ('alternative-int','alternative-bool','alternative-float','alternative-decimal','alternative-bad'):
        case('zero-weight-'+kind,kind=kind)
    for kind,total in (('alternative-int',F(1)),('alternative-bool',F(1)),('alternative-float',F(1,2))):
        case('accepted-'+kind,weights=(F(0),F(1),F(0)),kind=kind,total=total)
    for state in ('Available','Partial','Unknown','NotApplicable','Unavailable','NoPreferences','NoSupportedPreferences'):
        value=F(1,3) if state in ('Available','Partial') else None
        case('availability-'+state,values=(value,)*3,state=state)
    invalids=[{'total':x} for x in (None,0,False,0.5,'0.5',F(-1),F(2))]
    invalids += [{'weights':x} for x in (None,(),(F(1),),[F(1),F(0),F(0),F(0)],(1,F(0),F(0)),(True,F(0),F(0)),(0.7,F(0),F(3,10)),(F(-1),F(1),F(1)),(F(0),F(0),F(0)),(F(1),F(1),F(0)))]
    invalids += [{'component':x} for x in (None,0,False,'invalid')]
    invalids += [{'component':None,'weights':None,'total':None},{'weights':None,'total':F(0)},{'weights':(F(0),F(0),F(0)),'total':F(1)}]
    for i,invalid in enumerate(invalids):case('invalid-'+str(i),invalid=invalid,profile='',version='')
    for profile,version in (('', 'v'),('p',''),(None,'v'),('p',None),(0,'v')):
        case('provenance-'+str((profile,version)),profile=profile,version=version)
        case('mismatch-before-provenance-'+str((profile,version)),profile=profile,version=version,total=F(0))
    rng=random.Random(521)
    for i in range(400):
        ws=[rng.randrange(0,10**8) for _ in range(3)];den=sum(ws);weights=tuple(F(x,den) for x in ws)
        values=tuple(F(rng.randrange(d+1),d) for d in (rng.randrange(1,10**8),rng.randrange(1,10**8),rng.randrange(1,10**8)))
        expected=sum(w*v for w,v in zip(weights,values))
        case('random-match-'+str(i),values,weights,expected)
        case('random-mismatch-'+str(i),values,weights,F(0) if expected else F(1))
    for bits in (64,256,2048,8192):
        d=(1<<bits)-1; values=(F(d-1,d),F(d-3,d-2),F(1,d)); weights=(F(1,3),)*3
        case('large-coprime-'+str(bits),(values[0],values[1],F(2,d-4)),weights)
        case('large-shared-'+str(bits),(F(d-1,d),)*3,weights)
    from app.application.recommendation import exact_score_reuse as producer
    producer.exact_weighted=lambda *_:F(9,10)
    assert producer.ExactScoreReuse().weighted((F(7,10),F(0),F(3,10)),(F(1,2),F(0),F(1,3)))==F(9,10)
    case('forged-producer-total',total=F(9,10))
    case('independently-correct-total',total=F(9,20))
    return records

def micro():
    from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore
    records=[]
    for name,values in [('no-preferences',(F(1),None,None)),('four-preferences',(F(1),None,F(4,5))),('mixed-denominators',(F(9,17),F(3,11),F(13,19)))]:
        weights=(F(7,10),F(0),F(3,10))
        components=tuple(ComponentScore(ScoreEvidence(str(i),v,'Available' if v is not None else 'Unavailable')) for i,v in enumerate(values))
        total=sum(w*c.contribution for w,c in zip(weights,components))
        construct=lambda:RecommendationScore(*components,total,'synthetic','synthetic-v1',weights)
        timeit.timeit(construct,number=5000)
        samples=timeit.repeat(construct,number=20000,repeat=5)
        tracemalloc.start();before=tracemalloc.get_traced_memory()[0];tracemalloc.reset_peak()
        for _ in range(10000):construct()
        retained,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        records.append(dict(name=name,iterations=20000,samples=samples,median_us=statistics.median(samples)*1e6/20000,traced_retained_delta=retained-before,traced_peak_delta=peak-before))
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--micro',action='store_true');args=p.parse_args()
    sys.set_int_max_str_digits(0)  # Trusted synthetic large-integer fixtures only.
    with tempfile.TemporaryDirectory(prefix='score-validator-oracle-') as folder:
        if args.reference:
            manifest=json.loads((args.reference/'manifest.json').read_text())
            with zipfile.ZipFile(args.reference/'app.zip') as z:
                assert set(z.namelist())==set(manifest)
                for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
                z.extractall(folder)
            sys.path.insert(0,folder)
        else:sys.path.insert(0,str(BACKEND))
        args.output.write_text(json.dumps(micro() if args.micro else run(),sort_keys=True,indent=2)+'\n')
