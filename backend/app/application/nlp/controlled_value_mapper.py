"""Map only approved extraction values; no inference from wardrobe records."""
from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint
from app.application.nlp.vocabulary import Vocabulary


class ControlledValueMapper:
    def __init__(self, vocabulary: Vocabulary):
        self.vocabulary = vocabulary

    def map_values(self, matches):
        fields = {field: [] for field in self.vocabulary.values}
        for match in matches:
            value = (match.kind, match.canonical_value) if match.field == "garment_categories" else match.canonical_value
            if value not in self.vocabulary.values[match.field]:
                raise ValueError("Extractor supplied a value outside the controlled vocabulary.")
            if match.field == "garment_categories":
                value = GarmentCategoryConstraint(*value)
            if value not in fields[match.field]:
                fields[match.field].append(value)
        return {field: tuple(values) for field, values in fields.items()}
