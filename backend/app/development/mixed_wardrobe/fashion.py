"""Bounded per-pass facts; every locked/history pass reconstructs independently."""
from dataclasses import replace,asdict
from fractions import Fraction as F
from itertools import combinations,product
import json
from . import core
from .fashion_policy import policy,pair_value,POLICY_SHA256
from .fashion_contract import PROFILE,POLICY_VERSION
from app.domain.value_objects.recommendation_score import ScoreEvidence,ComponentScore,RecommendationScore

FIELDS={'colour':'primary_colour','style':'style','pattern':'pattern','layering':'sleeve_length','silhouette':'silhouette'}

class FashionFacts:
    def __init__(self,rows,request,scope,independent,evaluator=None):
        self.rules=policy();self.independent=independent;self.rows={r.snapshot.garment_id:r for r in rows}
        if len(self.rows)!=len(rows) or len(rows)>100:raise ValueError('Invalid fashion source scope.')
        # This cache belongs only to this qualified source pass, never a user,
        # next request, write verification, or history reconstruction.
        self.facts={gid:{kind:core.fact(row,field,scope) for kind,field in FIELDS.items()} for gid,row in self.rows.items()}
        self.context={'situation':None,'targets':[],'channel':'none','double_counted':False}
        if evaluator is not None:
            from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy
            resolution=ContextRelevancePolicy.load(bundle_id='context_18_v1').resolve(request)
            self.context['situation']=request.context.situation.value
            if resolution.objective is not None or request.formality is not None or request.style is not None:
                target=resolution.objective.target if resolution.objective is not None else request.style or request.formality.replace('_',' ')
                self.context.update(targets=[target],channel='existing_request_R')
            else:
                targets=[]
                p=evaluator.plan(request).predicate
                if p.operator in ('saved_style_in','reviewed_style_in','reviewed_style_equals'):
                    targets=list(p.value) if isinstance(p.value,(list,tuple)) else [p.value]
                if targets:self.context.update(targets=targets,channel='compatibility_style')

    def _known(self,f):
        return f.state=='Known' and f.complete and f.applicability=='applicable' and bool(f.values)

    def _pair(self,kind,a,b):
        x,y=self.facts[a][kind],self.facts[b][kind]
        if not self._known(x) or not self._known(y):return None
        # Multivalued colours/patterns cannot pretend to be singleton facts.
        if kind!='style' and (len(x.values)!=1 or len(y.values)!=1):return None
        values=[pair_value(kind,u,v) for u,v in product(x.values,y.values)]
        return None if any(v is None for v in values) else sum(values,F())/len(values)

    def _factor(self,kind,key):
        pairs=list(combinations([gid for _,gid in key],2))
        roles=dict(key)
        if kind=='layering':pairs=[(roles['upper'] if 'upper' in roles else roles['one_piece'],roles['outerwear'])] if 'outerwear' in roles else []
        if kind=='silhouette':pairs=[(roles['upper'],roles['lower'])] if 'upper' in roles and 'lower' in roles else []
        values=[self._pair(kind,a,b) for a,b in pairs]
        if kind=='style' and self.context['channel']=='compatibility_style':
            alignment=[]
            for _,gid in key:
                f=self.facts[gid]['style']
                alignment.append(F(len(set(f.values)&set(self.context['targets'])),len(set(f.values))) if self._known(f) else None)
            # Cross-garment consistency and context style share one bounded
            # factor; neither obtains an extra global weight.
            values=[self._mean(values)] if values else []
            values.append(self._mean(alignment))
        observed=sum(v is not None for v in values);possible=len(values)
        state='NotApplicable' if not possible else 'Unknown' if not observed else 'Available' if observed==possible else 'Partial'
        value=None if not observed else sum((v for v in values if v is not None),F())/possible
        return ScoreEvidence(kind,value,state,observed,possible,('qualified_attribute_rules',))

    @staticmethod
    def _mean(values):
        # A partial inner aggregate must not be relabelled fully observed.
        return None if not values or any(v is None for v in values) else sum(values,F())/len(values)

    def component(self,key):
        if any(gid not in self.rows for _,gid in key):raise ValueError('Foreign fashion member.')
        details=tuple(self._factor(kind,key) for kind in FIELDS)
        active=[d for d in details if d.state!='NotApplicable']
        denominator=sum((F(self.rules['weights'][d.name]) for d in active),F())
        observed=sum(d.observed for d in active);possible=sum(d.possible for d in active)
        if not denominator:summary=ScoreEvidence('fashion_compatibility_v2',None,'NotApplicable')
        elif not observed:summary=ScoreEvidence('fashion_compatibility_v2',None,'Unknown',0,possible,(POLICY_SHA256,))
        else:
            if self.independent:
                # Rebuild each weighted exact term; no first-pass totals/cache.
                numerator=F()
                for d in active:
                    if d.value is not None:numerator+=d.value*F(self.rules['weights'][d.name])
            else:numerator=sum((F(self.rules['weights'][d.name])*(d.value if d.value is not None else F()) for d in active),F())
            summary=ScoreEvidence('fashion_compatibility_v2',numerator/denominator,'Available' if observed==possible else 'Partial',observed,possible,(POLICY_SHA256,))
        return ComponentScore(summary,details)

    def apply(self,key,score):
        c=self.component(key)
        return RecommendationScore(score.request_match,c,score.preference,
            F(3,5)*score.request_match.contribution+F(1,5)*c.contribution+F(1,5)*score.preference.contribution,
            PROFILE,POLICY_VERSION,(F(3,5),F(1,5),F(1,5)))

    @staticmethod
    def retag(score):return replace(score,profile_name=PROFILE,policy_version=POLICY_VERSION)

    def describe(self,key):
        c=self.component(key);active=[d for d in c.details if d.state!='NotApplicable'];den=sum((F(self.rules['weights'][d.name]) for d in active),F())
        def ratio(v):return None if v is None else str(v)
        result={'profile':PROFILE,'policy_version':POLICY_VERSION,'policy_sha256':POLICY_SHA256,
          'context':self.context,'human_fashion_quality':'NOT_EVALUATED','unknown_rule':self.rules['unknown_rule'],
          'compatibility':{'state':c.summary.state,'value':ratio(c.summary.value),'observed':c.summary.observed,'possible':c.summary.possible},
          'factors':[{'name':d.name,'state':d.state,'value':ratio(d.value),'nominal_weight':self.rules['weights'][d.name],
             'effective_weight':ratio(F(self.rules['weights'][d.name])/den) if d.state!='NotApplicable' and den else '0',
             'total_contribution':ratio(F(1,5)*F(self.rules['weights'][d.name])/den*(d.value or F())) if d.state!='NotApplicable' and den else '0',
             'observed':d.observed,'possible':d.possible} for d in c.details],
          'sources':[{'garment_id':gid,'source':'normal_B0_B1' if isinstance(self.rows[gid],core.OriginalRow) else core.ORIGIN,
              'facts':{kind:asdict(f) for kind,f in self.facts[gid].items()}} for _,gid in key]}
        return json.loads(core.encoded(result))
