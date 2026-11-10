"""Existence check for unresolved unseen bases, never a ranking or score producer."""
def could_matter(scope,owner,request=None,intent=None,plan=None,evaluator_factory=None,preferences=()):
    if scope is None:return False
    evidence=scope.eligibility.to_dict()
    if evidence['version']!='wearer-category-eligibility-evidence-2.0.0':return False
    decisions=evidence['subtype_decisions'];unknown={g for g,s in decisions.items() if s=='Unknown'}
    if not unknown:return False
    from app.application.recommendation.refinement_selector import filter_snapshot,base_signature
    exclusions=plan.exclusions if plan else ()
    rows=filter_snapshot(tuple(g for g in scope.account_rows if decisions[g.garment_id]!='Deny'),exclusions).garments
    class Query:
        def get_confirmed_available_garments(self,user):
            if user!=owner:raise ValueError('Unresolved source owner mismatch.')
            return rows
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    engine=RecommendationEngine(Query());evaluator=evaluator_factory() if evaluator_factory else None
    if evaluator is not None and not evaluator.supports(request):return False
    independent=None
    if intent is not None:
        from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
        from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
        independent=IndependentAttributeVerifier.prepare(intent.conditions,scope.account_descriptions,AttributeEvidencePolicy.for_conditions(intent.conditions),subtype_sources=scope.account_subtypes)
    relative=None
    if plan is not None and plan.root_R is not None:
        from app.application.recommendation.context_relevance_scorer import applies,PreparedRelativeFacts
        if applies(request):
            from app.application.recommendation.preference_normalizer import PreferenceNormalizer
            relative=PreparedRelativeFacts(rows,request,PreferenceNormalizer().normalize(owner,preferences))
    with engine.generate_homepage_candidates(owner) as session:
        for candidate in session:
            if not any(m.garment.garment_id in unknown for m in candidate.members):continue
            if plan is not None and base_signature(candidate) in plan.seen:continue
            if evaluator is not None and evaluator.evaluate(candidate,request).state=='Fail':continue
            members=tuple((m.role,m.garment.garment_id) for m in candidate.members)
            if independent is not None and independent.decision(members)=='Fail':continue
            if relative is not None:
                bounds=relative.bounds(tuple(m.role for m in candidate.members),tuple(relative.by_id[m.garment.garment_id] for m in candidate.members))
                if bounds is not None and bounds[1]<plan.root_R:continue
            return True  # One witness proves unresolved relevance; no winner is emitted.
        if not session.result.complete:raise ValueError('Unresolved subtype scan did not complete.')
    return False
