"""Approved aliases and W3C exact anchors only; no approximate classifier."""
import json
from pathlib import Path
import re
from types import MappingProxyType
from app.application.nlp.vocabulary import Vocabulary
from app.domain.value_objects.request_candidate_evaluation import AttributeEvidence


class ColourClassifier:
    def __init__(self, vocabulary=None):
        vocabulary = vocabulary or Vocabulary.load()
        self.aliases = MappingProxyType({alias: value for field,value,alias,_ in vocabulary.entries if field == "colours"})
        raw = json.loads((Path(__file__).with_name("config") / "request_policy.v1.json").read_text(encoding="utf-8"))
        anchors = raw["exact_hex_anchors"]
        if raw["version"] != "1.0.0" or any(not re.fullmatch(r"#[0-9a-f]{6}", key) or value not in vocabulary.values["colours"] for key,value in anchors.items()):
            raise ValueError("Invalid exact colour anchors.")
        self.anchors = MappingProxyType(dict(anchors))

    def classify(self, primary_colour):
        if primary_colour is None or (isinstance(primary_colour, str) and not primary_colour.strip()):
            return AttributeEvidence((), "Missing", "primary")
        if not isinstance(primary_colour, str):
            return AttributeEvidence((), "Malformed", "primary")
        value = re.sub(r"\s+", " ", primary_colour.strip().casefold())
        if value in self.aliases:
            return AttributeEvidence((self.aliases[value],), "Known", "named_primary")
        if value.startswith("#"):
            if re.fullmatch(r"#[0-9a-f]{3}", value):
                value = "#" + "".join(char*2 for char in value[1:])
            if not re.fullmatch(r"#[0-9a-f]{6}", value):
                return AttributeEvidence((), "Malformed", "hex_primary")
            if value in self.anchors:
                return AttributeEvidence((self.anchors[value],), "Known", "exact_hex_primary")
            return AttributeEvidence((), "Unrecognized", "uncalibrated_hex_primary")
        return AttributeEvidence((), "Unrecognized", "named_primary")
