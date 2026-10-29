"""Separately prepared primary and independent mandatory facts, not Pass flags."""
from app.application.recommendation.general_context_evaluator import GeneralContextEvaluator, construct_evaluator
from dataclasses import replace
from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.application.recommendation.contextual_suitability_evaluator import ContextualSuitabilityEvaluator
from app.application.recommendation.suitability_evidence_mapper import SuitabilityEvidenceParser
from app.application.recommendation.scoring_eligibility_gate import InvalidScoringInput
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.application.recommendation.structural_policy import StructuralPolicy

PASS, FAIL, UNKNOWN = 1,0,-1


class CompactMandatoryFacts:
    def __delattr__(self,name):raise AttributeError('Immutable mandatory preparation.')
    def __setattr__(self,name,value):
        if hasattr(self,name):raise AttributeError('Immutable mandatory preparation.')
        object.__setattr__(self,name,value)
    def __init__(self, garments, request, evaluator_type):
        try:
            evaluator = construct_evaluator(evaluator_type)
        except ValueError as error:
            raise InvalidScoringInput('Unapproved evaluator type or bundle.') from error
        actual_type = type(evaluator)
        if not evaluator.supports(request):
            raise ValueError('Unavailable mandatory policy.')
        minimum = evaluator.minimum if actual_type in (SuitabilityRequestEvaluator,ContextualSuitabilityEvaluator,GeneralContextEvaluator) else evaluator
        parser = SuitabilityEvidenceParser()
        definitions, tables = [],[]
        def add(field,value,mode,states):
            definitions.append((field,value,mode)); tables.append(tuple(states))
        for constraint in request.garment_categories or ():
            allowed = minimum.vocabulary.groups[constraint.value] if constraint.kind=='group' else (constraint.value,)
            add('garment_categories',constraint.kind+':'+constraint.value,'any',(int(g.category in allowed) for g in garments))
        evidence = tuple(minimum.mapper.classify(g) for g in garments) if request.colours or request.style else ()
        for colour in request.colours or ():
            add('colours',colour,'any',(PASS if colour in e.colour.values else FAIL if e.colour.state=='Known' else UNKNOWN for e in evidence))
        if request.style:
            add('style',request.style,'base',(PASS if request.style in e.style.values else FAIL if e.style.state=='Known' else UNKNOWN for e in evidence))
        for field in ('occasion','formality'):
            value = getattr(request,field)
            if value is not None:
                states = (evaluator.member_condition(g,request,field)[0] for g in garments) if actual_type in (ContextualSuitabilityEvaluator,GeneralContextEvaluator) else (parser.parse(g).state_for(field,value) for g in garments)
                add(field,value,'all',({'Pass':PASS,'Fail':FAIL,'Unknown':UNKNOWN}[state] for state in states))
        self.definitions,self.tables = tuple(definitions),tuple(tables)

    def evaluate(self, roles, indexes):
        result = []
        category_failed = False
        for (field,value,mode),table in zip(self.definitions,self.tables):
            # Original optimized minimum evaluator stops after definite category
            # failure; suitability declarations are still evaluated afterwards.
            if category_failed and field in ('colours','style'):
                continue
            selected = tuple((position,table[i]) for position,i in enumerate(indexes) if mode!='base' or roles[position]!='outerwear')
            positive = sum(1<<position for position,state in selected if state==PASS)
            negative = sum(1<<position for position,state in selected if state==FAIL)
            unknown = sum(1<<position for position,state in selected if state==UNKNOWN)
            if mode=='all':
                state = FAIL if negative else UNKNOWN if unknown else PASS
                mask = negative if state==FAIL else unknown if state==UNKNOWN else positive
            else:
                state = PASS if positive else UNKNOWN if unknown else FAIL
                mask = positive
            result.append((field,value,state,mask))
            if field=='garment_categories' and state==FAIL:
                category_failed = True
        return tuple(result)


def state_of(conditions):
    return FAIL if any(x[2]==FAIL for x in conditions) else UNKNOWN if any(x[2]==UNKNOWN for x in conditions) else PASS


class CompactEligibilityVerifier:
    def __delattr__(self,name):raise AttributeError('Immutable independent context.')
    def __setattr__(self,name,value):
        if hasattr(self,name):raise AttributeError('Immutable independent context.')
        object.__setattr__(self,name,value)
    def __init__(self, user_id, garments, request, evaluator_type):
        self.user_id,self.garments,self.request = user_id,tuple(garments),request
        self.facts = CompactMandatoryFacts(self.garments,request,evaluator_type)
        self.roles = StructuralPolicy.load().role_map
        self.compositions = StructuralPolicy.load().compositions
        # Independent snapshot validation, separate from acquisition/filter facts.
        seen = set()
        for g in self.garments:
            expected = GARMENT_STRUCTURE.get(g.category)
            if g.user_id!=user_id or g.status!='available' or not g.garment_id.strip() or g.garment_id in seen or not g.preferred_media_id.strip() or expected!=(g.structural_role,g.layering_index):
                raise InvalidScoringInput('Invalid independent snapshot membership.')
            seen.add(g.garment_id)

    def verify(self, roles, indexes, primary):
        if type(indexes) is not tuple or roles not in self.compositions or len(roles)!=len(indexes) or len(set(indexes))!=len(indexes):
            raise InvalidScoringInput('Invalid compact structure.')
        for role,i in zip(roles,indexes):
            if type(i) is not int or not 0<=i<len(self.garments) or self.roles[self.garments[i].structural_role]!=role:
                raise InvalidScoringInput('Foreign or wrong-slot compact member.')
        # Different reduction implementation from the primary evaluator. Inputs
        # come from independently classified, immutable tables.
        checked=[]; category_failed=False
        for (field,value,mode),table in zip(self.facts.definitions,self.facts.tables):
            if category_failed and field in ('colours','style'):continue
            entries=[(p,table[i]) for p,i in enumerate(indexes) if mode!='base' or roles[p]!='outerwear']
            states=[s for _,s in entries]
            if mode=='all': s=FAIL if FAIL in states else UNKNOWN if UNKNOWN in states else PASS
            else: s=PASS if PASS in states else UNKNOWN if UNKNOWN in states else FAIL
            ids=sum(1<<p for p,v in entries if v==(s if mode=='all' else PASS))
            checked.append((field,value,s,ids))
            category_failed |= field=='garment_categories' and s==FAIL
        if tuple(checked)!=primary or state_of(checked)!=PASS:
            raise InvalidScoringInput('Independent mandatory evidence mismatch.')
        return True
