"""Lazy optional facts after real mandatory admission. No runtime registration or IO."""
from dataclasses import dataclass
from fractions import Fraction as F
from types import MappingProxyType
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
from app.domain.value_objects.scored_candidate import VerifiedScoringInput
from app.domain.value_objects.attribute_conditions import encode,digest
from app.application.recommendation.attribute_condition_evaluator import predicate,conjunction
from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
from app.application.recommendation.attribute_selection_verifier import _possibility
from app.application.recommendation.refinement_verifier import snapshot_digest
from app.domain.value_objects.attribute_selection_evidence import description_digest

@dataclass(frozen=True)
class OptionalEvaluation:
    key:tuple
    scope_hash:str
    state:str
    support:int
    lower:F
    upper:F
    ledger:tuple
    def __post_init__(self):
        if self.state not in ('Satisfied','Unsatisfied','Unverifiable') or type(self.support) is not int or self.support!=int(self.state=='Satisfied'):raise ValueError('Invalid qualified optional support.')
        expected=(F(1),F(1)) if self.state=='Satisfied' else (F(),F()) if self.state=='Unsatisfied' else (F(),F(1))
        if (self.lower,self.upper)!=expected:raise ValueError('Invalid optional uncertainty interval.')
    @property
    def value(self):return None if self.state=='Unverifiable' else self.lower

class PreparedLocalPreference:
    def __init__(self,intent,collection,policy,*,account_id,wearer_scope):
        if type(intent) is not RequestLocalPreferenceIntent or policy.sha256!=intent.to_dict()['qualification_policy_sha256'] or not account_id or not wearer_scope:raise ValueError('Unbound isolated optional scope.')
        collection=tuple(collection)
        if len(collection)>100 or len({x.snapshot.garment_id for x in collection})!=len(collection):raise ValueError('Invalid source collection bound.')
        if any(x.snapshot.user_id!=account_id or x.snapshot.status!='available' for x in collection):raise ValueError('Foreign/unavailable optional source.')
        self.intent,self.policy,self.account_id,self.wearer_scope=intent,policy,account_id,wearer_scope
        self.rows=MappingProxyType({x.snapshot.garment_id:x for x in collection});self._cache={};self.fact_resolutions=0
        self.scope_hash=digest({'contract':'isolated-local-source-scope-1.0.0','account':account_id,'wearer_scope':wearer_scope,'intent':intent.revision,
          'snapshots':snapshot_digest(x.snapshot for x in collection),'descriptions':description_digest(collection),'policy':policy.sha256})
        self.hard=IndependentAttributeVerifier.prepare(intent.hard.conditions,collection,policy) if intent.hard else None

    def validate_mandatory(self,verified):
        if type(verified) is not VerifiedScoringInput or verified.user_id!=self.account_id or verified.evaluated.evaluation.state!='Pass' or verified.request.to_dict()!=self.intent.to_dict()['mandatory_request']:raise ValueError('Optional evaluation requires matching mandatory Pass.')
        for member in verified.candidate.members:
            row=self.rows.get(member.garment.garment_id)
            if row is None or row.snapshot!=member.garment:raise ValueError('Changed/uncaptured optional source.')
        if self.hard:self.hard.verify(verified.candidate)

    def evaluate(self,verified):
        self.validate_mandatory(verified)
        optional=self.intent.to_dict()['optional'];states=[];ledger=[]
        for member in verified.candidate.members:
            if member.role!=optional['role']:continue
            row=self.rows[member.garment.garment_id];doc=row.description.to_dict();primitives=[]
            for p in optional['predicates']:
                key=(member.garment.garment_id,p['id'])
                if key not in self._cache:
                    field=p['attribute'];record=doc['fields'][field]
                    fact=self.policy.fact(member.garment,doc,field,'in',self.policy.primary_classifier())
                    verdict=predicate(fact,field,'in',p['values'])
                    # Optional support is conservative about an explicit B0
                    # disagreement. This never alters B1's qualification rules.
                    unresolved=record['state'] in ('Stale','Conflicting','Malformed','Unsure')
                    state='Unknown' if unresolved else verdict.state
                    independent='Unknown' if unresolved else 'Pass' if _possibility(fact,field,'in',p['values'])=={True} else 'Fail' if _possibility(fact,field,'in',p['values'])=={False} else 'Unknown'
                    if state!=independent:raise ValueError('Optional predicate verification mismatch.')
                    detail={'garment_id':member.garment.garment_id,'role':member.role,'predicate':p,'verdict':state,'fact_state':fact.state,'source':fact.source,
                            'fact_values':list(fact.values),'record_state':record['state'],'reason':'unresolved_B0_record' if unresolved else verdict.reason}
                    self._cache[key]=(state,encode(detail));self.fact_resolutions+=1
                state,detail=self._cache[key];primitives.append(state);ledger.append(detail)
            states.append(conjunction(tuple(primitives)))
        value='Pass' if 'Pass' in states else 'Unknown' if 'Unknown' in states else 'Fail'
        state={'Pass':'Satisfied','Unknown':'Unverifiable','Fail':'Unsatisfied'}[value]
        if not states:ledger.append(encode({'reason':'preferred_role_absent','role':optional['role']}))
        return OptionalEvaluation(verified.candidate.key,self.scope_hash,state,int(value=='Pass'),F(int(value=='Pass')),F(int(value!='Fail')),tuple(ledger))
