"""Deterministic lazy products; uniqueness follows from deduplicated role slots."""
from itertools import product
from app.application.recommendation.structural_policy import StructuralPolicy
from app.domain.value_objects.outfit_candidate import CandidateMember, OutfitCandidate


class CandidateGenerator:
    def __init__(self, policy=None):
        self.policy = policy or StructuralPolicy.load()

    def groups(self, garments):
        groups = {role: [] for role in self.policy.role_map.values()}
        seen = {}
        for garment in garments:
            if garment.garment_id in seen:
                if seen[garment.garment_id] != garment:
                    raise ValueError("Conflicting duplicate garment.")
                continue
            seen[garment.garment_id] = garment
            groups[self.policy.role_map[garment.structural_role]].append(garment)
        return {role: tuple(sorted(items, key=lambda item: item.garment_id)) for role, items in groups.items()}

    def has_base(self, garments):
        groups = self.groups(garments)
        return bool(groups["one_piece"] or (groups["upper"] and groups["lower"]))

    def enumerate(self, garments, evaluator):
        groups = self.groups(garments)
        for composition in self.policy.compositions:
            for members in product(*(groups[role] for role in composition)):
                if evaluator.is_structurally_valid(members):
                    yield OutfitCandidate(tuple(CandidateMember(garment, role, order) for order, (garment, role) in enumerate(zip(members, composition), 1)))
