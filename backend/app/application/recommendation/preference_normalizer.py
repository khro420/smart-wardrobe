"""Explicit approved type/value semantics, never free-text preference inference."""
from decimal import Decimal,InvalidOperation
from fractions import Fraction
import json
import re
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.suitability_policy import SuitabilityPolicy
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot,NormalizedPreference,NormalizedPreferenceSet
from app.domain.value_objects.structured_outfit_request import GarmentCategoryConstraint


class InvalidPreferenceData(ValueError):
    pass


def precise_weight(value):
    if isinstance(value,bool):
        raise ValueError("Boolean is not a numeric weight.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError) as exc:
        raise ValueError("Invalid numeric weight.") from exc
    if not number.is_finite() or not 0 <= number <= 1:
        raise ValueError("Weights must be finite and within 0–1.")
    return Fraction(number)


class PreferenceNormalizer:
    def __init__(self):
        self.vocabulary = Vocabulary.load()
        self.aliases = {}
        for field in ("colours","style","formality"):
            aliases = {x:x for x in self.vocabulary.values[field]}
            aliases.update({phrase:value for f,value,phrase,_ in self.vocabulary.entries if f == field})
            self.aliases[field] = aliases

    def canonical(self,field,value):
        if not isinstance(value,str):
            return None
        return self.aliases[field].get(re.sub(r"\s+"," ",value.strip().casefold()))

    def normalize(self,user_id,rows):
        preferences,diagnostics,seen = [],[],set()
        for row in rows:
            if not isinstance(row,PreferenceSnapshot) or row.user_id != user_id:
                raise InvalidPreferenceData("Preference ownership/contract mismatch.")
            if not row.is_active:
                diagnostics.append((row.preference_id,"inactive")); continue
            kind = row.preference_type
            if kind not in ("colours","styles","garment_categories","formality","style_note"):
                diagnostics.append((row.preference_id,"unsupported_type")); continue
            try:
                importance = Fraction(1) if row.weight is None else precise_weight(row.weight)
            except ValueError as exc:
                raise InvalidPreferenceData("Invalid preference importance.") from exc
            if importance == 0:
                diagnostics.append((row.preference_id,"zero_weight")); continue
            if kind in seen:
                raise InvalidPreferenceData("Duplicate active positive-weight preference type.")
            seen.add(kind)
            try:
                raw = json.loads(row.value_json,parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
                if not isinstance(raw,dict):
                    raise ValueError("Expected a preference object.")
                if kind == "style_note":
                    value = self.canonical("style",raw.get("value")) if set(raw) == {"value"} else None
                    if value is None:
                        diagnostics.append((row.preference_id,"unsupported_style_note")); continue
                    values,normalized_kind = (value,),"styles"
                else:
                    normalized_kind = kind
                    if set(raw) != {"values"} or not isinstance(raw["values"],list) or not raw["values"]:
                        raise ValueError("Expected nonempty values list.")
                    if kind == "garment_categories":
                        values = []
                        for item in raw["values"]:
                            if not isinstance(item,dict) or set(item) != {"kind","value"}:
                                raise ValueError("Invalid category preference.")
                            constraint = GarmentCategoryConstraint(**item)
                            if (constraint.kind,constraint.value) not in self.vocabulary.values["garment_categories"]:
                                raise ValueError("Unsupported category preference.")
                            values.append(constraint)
                    else:
                        field = "style" if kind == "styles" else kind
                        values = [self.canonical(field,item) for item in raw["values"]]
                        if any(value is None for value in values):
                            raise ValueError("Unsupported preference value.")
                        if kind == "formality" and any(value not in SuitabilityPolicy.load().enabled_formality for value in values):
                            diagnostics.append((row.preference_id,"unavailable_formality_capability")); continue
                preferences.append((kind,NormalizedPreference(row.preference_id,normalized_kind,tuple(values),importance)))
            except (ValueError,TypeError,KeyError) as exc:
                raise InvalidPreferenceData("Malformed supported preference data.") from exc
        if any(kind == "styles" for kind,_ in preferences):
            diagnostics.extend((item.preference_id,"structured_styles_precedence") for kind,item in preferences if kind == "style_note")
            preferences = [(kind,item) for kind,item in preferences if kind != "style_note"]
        return NormalizedPreferenceSet(user_id,tuple(sorted((item for _,item in preferences),key=lambda x:x.preference_type)),tuple(sorted(diagnostics)))
