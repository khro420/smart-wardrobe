"""Request-only filtering and deterministic selection support."""
from dataclasses import dataclass
from app.domain.value_objects.recommendation_refinement import canonical_categories, RefinementError


@dataclass(frozen=True)
class FilteredSnapshot:
    garments: tuple
    excluded_garments: int
    structural_bound_before: int
    structural_bound_after: int


def structural_bound(garments):
    # Match the existing declared structural roles, never infer context from category.
    counts = {role: sum(g.structural_role == role for g in garments)
              for role in ('top', 'bottom', 'dress', 'outerwear')}
    return (counts['top'] * counts['bottom'] + counts['dress']) * (1 + counts['outerwear'])


def filter_snapshot(garments, exclusions):
    exclusions = canonical_categories(list(exclusions))
    original = tuple(garments)
    remaining = tuple(g for g in original if g.category not in exclusions)
    return FilteredSnapshot(remaining, len(original) - len(remaining),
                            structural_bound(original), structural_bound(remaining))


def check_category_conflicts(request, exclusions, vocabulary):
    excluded = set(exclusions)
    for constraint in request.garment_categories or ():
        members = (vocabulary.groups[constraint.value] if constraint.kind == 'group'
                   else (constraint.value,))
        if set(members) <= excluded:
            raise RefinementError('RefinementConflict', 'required_category_excluded')


def check_selected_exclusions(candidate, exclusions):
    if any(member.garment.category in exclusions for member in candidate.members):
        raise ValueError('Selected outfit violates request category exclusions.')


def base_signature(candidate):
    members = tuple((m.role, m.garment.garment_id) for m in candidate.members if m.role != 'outerwear')
    if tuple(role for role, _ in members) not in (('one_piece',), ('upper', 'lower')):
        raise ValueError('Invalid base structure.')
    return members


def classify_remaining(plan, garment_key, bounds):
    signature=tuple(pair for pair in garment_key if pair[0]!='outerwear')
    if signature in plan.seen:
        return 'already_seen'
    low,high,_,_=bounds
    floor=plan.root_R
    if low==high:
        return 'below_floor_points' if floor is not None and low<floor else 'point_candidates'
    return 'unresolved_below_floor' if floor is not None and high<floor else 'unresolved_candidates'


def outcome_summary(plan,filtered,tracker,failed,unknown,status):
    import json
    return json.dumps(dict(reason=status,
        cause='request_category_exclusion' if filtered.excluded_garments and status in ('InsufficientStructure','NoEligibleGarments','NoStructuralCandidates') else 'mandatory_or_remaining_pool',
        excluded_categories=list(plan.exclusions),excluded_garments=filtered.excluded_garments,
        structural_bound_before=filtered.structural_bound_before,structural_bound_after=filtered.structural_bound_after,
        mandatory_failed=failed,mandatory_unknown=unknown,
        coverage=dict(hard_passed=tracker.passed,point_candidates=tracker.points,unresolved_candidates=tracker.unresolved,
            objective_unavailable_candidates=tracker.passed if tracker.facts.objective is None else 0,**tracker.skipped)),sort_keys=True)
