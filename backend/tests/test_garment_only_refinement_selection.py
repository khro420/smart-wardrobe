"""Fixed independent score/base labels; outerwear is not another base."""
from fractions import Fraction as F
from types import SimpleNamespace as S
from app.application.recommendation.garment_only_refinement_selection import GarmentTracker

def test_independent_four_variant_labels_and_exhaustion():
    # Pure request R=0, neutral P=1/2; independent C labels are frozen.
    from app.domain.value_objects.garment_only_refinement import GarmentRefinementPlan
    from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
    from app.application.nlp.conversational_context_interpreter import ConversationalContextInterpreter
    from app.application.recommendation.conversational_request_pipeline import ConversationalRequestPipeline
    from app.application.wardrobe.description_policy import DescriptionPolicy
    _,intent=ConversationalRequestPipeline(ConversationalContextInterpreter(),DescriptionPolicy.load()).interpret('I want a shirt with black trousers.')
    root='00000000-0000-0000-0000-000000000001'
    plan=GarmentRefinementPlan(wearer_profile_id=root,attribute_intent=intent,description_collection_sha256='0'*64,attribute_scope_sha256='0'*64)
    garments=tuple(S(garment_id=g) for g in ('T01','T02','L01','O01'))
    rows=[(('upper','lower'),(0,2),F(1),F(3,10)),(('upper','lower','outerwear'),(0,2,3),F(1),F(3,10)),(('upper','lower'),(1,2),F(1,2),F(1,5)),(('upper','lower','outerwear'),(1,2,3),F(1),F(3,10))]
    def rank(p):
        tracker=GarmentTracker(garments,p)
        for roles,indexes,c,total in rows:
            assert F(3,5)*0+F(1,5)*c+F(1,5)*F(1,2)==total
            tracker.consider(roles,indexes,(),S(total=total,contributions=(F(0),c,F(1,2))),tuple((r,garments[i].garment_id) for r,i in zip(roles,indexes)))
        return tracker
    first=rank(plan);assert first.selected[2]==(0,2)
    from dataclasses import replace
    child=replace(plan,root_id=root,parent_id=root,ordinal=1,root_R=F(0),root_total=F(3,10),seen=((('upper','T01'),('lower','L01')),))
    assert rank(child).selected[2]==(1,2,3)
    exhausted=replace(child,ordinal=2,seen=(*child.seen,(('upper','T02'),('lower','L01'))))
    assert rank(exhausted).selected is None and rank(exhausted).empty_refinement_status=='RefinementExhausted'  # Public adapter uses the garment-specific outcome.
