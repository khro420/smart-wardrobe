"""Phase 3A structure-only checks; no request or aesthetic compatibility rules."""
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.application.recommendation.structural_policy import StructuralPolicy


class MandatoryRuleEvaluator:
    def __init__(self, policy=None):
        self.policy = policy or StructuralPolicy.load()

    def is_structurally_valid(self, garments) -> bool:
        if not garments or any(not isinstance(item, ConfirmedGarmentSnapshot) for item in garments):
            return False
        if len({item.garment_id for item in garments}) != len(garments) or len({item.user_id for item in garments}) != 1:
            return False
        roles = []
        for item in garments:
            expected = GARMENT_STRUCTURE.get(item.category)
            if item.status != "available" or expected is None or expected != (item.structural_role, item.layering_index):
                return False
            roles.append(self.policy.role_map[item.structural_role])
        return tuple(roles) in self.policy.compositions
