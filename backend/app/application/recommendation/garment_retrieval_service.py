"""Only Phase 1 snapshots cross acquisition; no direct wardrobe persistence."""
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.candidate_generation_result import RetrievalResult, GarmentExclusion


class GarmentDataError(ValueError):
    pass


class GarmentRetrievalService:
    def __init__(self, query: ConfirmedGarmentQuery):
        self.query = query

    def retrieve(self, user_id: str) -> RetrievalResult:
        if not isinstance(user_id, str) or not user_id.strip():
            raise GarmentDataError("Invalid user context.")
        rows = self.query.get_confirmed_available_garments(user_id)
        garments, exclusions, seen = [], [], {}
        for row in rows:
            if not isinstance(row, ConfirmedGarmentSnapshot):
                exclusions.append(GarmentExclusion(None, "invalid_snapshot"))
                continue
            if not row.garment_id.strip() or not row.preferred_media_id.strip():
                exclusions.append(GarmentExclusion(row.garment_id, "missing_identity_or_media_reference"))
                continue
            if row.garment_id in seen:
                if seen[row.garment_id] != row:
                    raise GarmentDataError("Conflicting snapshots share a garment ID.")
                continue
            seen[row.garment_id] = row
            if row.user_id != user_id or row.status != "available":
                exclusions.append(GarmentExclusion(row.garment_id, "ownership_or_availability_mismatch"))
                continue
            structure = GARMENT_STRUCTURE.get(row.category)
            if structure is None:
                exclusions.append(GarmentExclusion(row.garment_id, "unsupported_category"))
                continue
            if (row.structural_role, row.layering_index) != structure:
                exclusions.append(GarmentExclusion(row.garment_id, "inconsistent_structure"))
                continue
            # Optional colour/style/fit/material never gate Phase 3A structure.
            garments.append(row)
        return RetrievalResult(tuple(sorted(garments, key=lambda item: item.garment_id)), tuple(exclusions))
