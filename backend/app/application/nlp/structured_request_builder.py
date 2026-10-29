"""Build the five-field request with absent optional information as None."""
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest


class StructuredRequestBuilder:
    def build(self, fields):
        for field in ("occasion", "style", "formality"):
            if len(fields[field]) > 1:
                raise ValueError("Conflicting singular field.")
        return StructuredOutfitRequest(
            occasion=next(iter(fields["occasion"]), None),
            style=next(iter(fields["style"]), None),
            colours=fields["colours"] or None,
            garment_categories=fields["garment_categories"] or None,
            formality=next(iter(fields["formality"]), None),
        )
