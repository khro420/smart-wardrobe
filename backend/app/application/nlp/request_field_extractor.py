"""Longest nonoverlapping approved phrase extraction and meaning safeguards."""
import re
from app.domain.value_objects.nlp_result import ExtractionMatch
from app.application.nlp.vocabulary import Vocabulary


class UnsupportedMeaning(ValueError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class RequestFieldExtractor:
    # Grammar/function words only. These never become garment attributes.
    GLUE = frozenset("please can could would you i me my an a the outfit outfits clothes clothing something suitable suggest recommend give show help choose pick what should wear for to on at with and include including using use from confirmed wardrobe in of look style colour colours color colors want need that is dressed".split())

    def __init__(self, vocabulary: Vocabulary):
        self.vocabulary = vocabulary

    def extract(self, text: str) -> tuple[ExtractionMatch, ...]:
        if re.search(r"\b(?:no|not|without|avoid|excluding|except|don't|do not|never)\b", text):
            raise UnsupportedMeaning("negation")
        if re.search(r"\b(?:or|either|instead)\b", text):
            raise UnsupportedMeaning("alternatives")
        if re.search(r"\b(?:two|three|multiple|several|another)\b", text):
            raise UnsupportedMeaning("multiple_requests")
        if len(re.findall(r"\b(?:suggest|recommend|give me|show me|what (?:should|can) i wear)\b", text)) > 1:
            raise UnsupportedMeaning("multiple_requests")
        candidates = []
        for field, value, phrase, kind in self.vocabulary.entries:
            for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
                candidates.append(ExtractionMatch(field, value, phrase, match.start(), match.end(), kind))
        selected = []
        for match in sorted(candidates, key=lambda item: (-(item.end-item.start), item.start, item.field)):
            if not any(match.start < item.end and match.end > item.start for item in selected):
                selected.append(match)
        selected.sort(key=lambda item: item.start)
        for field in ("occasion", "style", "formality"):
            if len({item.canonical_value for item in selected if item.field == field}) > 1:
                raise UnsupportedMeaning("conflicting_" + field)
        colours = [item for item in selected if item.field == "colours"]
        categories = [item for item in selected if item.field == "garment_categories"]
        if colours and categories:
            # The schema has global colours, not per-garment colour bindings.
            # Only an explicitly global colour clause is representable, and
            # no local binding may coexist with it.
            for colour in colours:
                for category in categories:
                    first, second = sorted((colour, category), key=lambda item: item.start)
                    between = re.findall(r"[a-z']+", text[first.end:second.start])
                    if len(between) <= 4 and all(word in {"a", "the", "in", "of", "for", "that", "is", "coloured", "colored"} for word in between):
                        raise UnsupportedMeaning("garment_colour_binding")
            global_clause = re.search(r"\busing\s+(.+?)\s+(?:colours|colors)\s+with\b", text)
            if not global_clause or any(not (global_clause.start(1) <= item.start and item.end <= global_clause.end(1)) for item in colours) or any(item.start < global_clause.end() for item in categories):
                raise UnsupportedMeaning("garment_colour_binding")
        remainder = list(text)
        for match in selected:
            remainder[match.start:match.end] = " " * (match.end-match.start)
        unknown = set(re.findall(r"[\w']+", "".join(remainder))) - self.GLUE
        if unknown:
            raise UnsupportedMeaning("unrecognized_condition")
        # A bare overlapping style/formality word has no justified field.
        if not selected and re.search(r"\b(?:casual|formal)\b", text):
            raise UnsupportedMeaning("ambiguous_field")
        return tuple(selected)
