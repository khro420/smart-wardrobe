"""All approved products, represented by immutable garment-index tuples."""
from itertools import product
from app.application.recommendation.structural_policy import StructuralPolicy
from app.domain.value_objects.outfit_candidate import CandidateMember, OutfitCandidate


def groups(garments):
    policy = StructuralPolicy.load()
    slots = {role: [] for role in policy.role_map.values()}
    for index, garment in enumerate(garments):
        slots[policy.role_map[garment.structural_role]].append(index)
    return {role: tuple(items) for role,items in slots.items()}


def enumerate_indexes(slots):
    for roles in StructuralPolicy.load().compositions:
        for indexes in product(*(slots[role] for role in roles)):
            yield roles,indexes


def key(garments, roles, indexes):
    # Actual identifiers and role strings, never numeric index ordering.
    return tuple((role,garments[i].garment_id) for role,i in zip(roles,indexes))


def materialize(garments, roles, indexes):
    return OutfitCandidate(tuple(CandidateMember(garments[i],role,order) for order,(role,i) in enumerate(zip(roles,indexes),1)))
