"""Isolated experiment: no AttributeEvidence adapter or recommendation activation.

Thresholds are supplied experiments, never inferred defaults or release approval.
Named aliases/exact anchors remain exclusively owned by ColourClassifier.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.oklab import normalize_hex, hex_to_oklab, oklab_distance
from app.domain.value_objects.colour_classification import ColourClassification

DEFAULT_PROTOTYPES = Path(__file__).with_name("config") / "colour_prototypes.v1.json"


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ColourPrototype:
    identifier: str
    colour: str
    hex_value: str
    provenance: str
    review_status: str = "initial_unreviewed_candidate"

    def __post_init__(self):
        if any(not isinstance(x,str) or not x.strip() for x in (self.identifier,self.colour,self.provenance)):
            raise ValueError("Invalid prototype metadata.")
        if self.colour not in Vocabulary.load().values["colours"] or self.review_status != "initial_unreviewed_candidate":
            raise ValueError("Unsupported prototype colour or review status.")
        object.__setattr__(self,"hex_value",normalize_hex(self.hex_value))


class PrototypeColourClassifier:
    def __init__(self, path=DEFAULT_PROTOTYPES, thresholds=None):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw,dict) or raw.get("schema_version") != "1.0.0" or not isinstance(raw.get("version"),str) or not raw["version"] or raw.get("status") != "initial_unreviewed_candidates" or raw.get("mandatory_evidence_enabled") is not False or not isinstance(raw.get("prototypes"),list) or any(not isinstance(item,dict) for item in raw["prototypes"]):
            raise ValueError("Invalid prototype configuration.")
        try:
            self.prototypes = tuple(ColourPrototype(**item) for item in raw["prototypes"])
        except TypeError as exc:
            raise ValueError("Invalid prototype fields.") from exc
        colours = Vocabulary.load().values["colours"]
        if not self.prototypes or {p.colour for p in self.prototypes} != colours or len({p.identifier for p in self.prototypes}) != len(self.prototypes) or len({(p.colour,p.hex_value) for p in self.prototypes}) != len(self.prototypes):
            raise ValueError("All approved colours need unique candidate prototypes.")
        # No cross-class duplicate swatches: these would encode a permanent tie.
        if len({p.hex_value for p in self.prototypes}) != len(self.prototypes):
            raise ValueError("Conflicting prototype hex values.")
        self.version = raw["version"]
        raw = dict(raw,prototypes=sorted(raw["prototypes"],key=lambda item:item["identifier"]))
        self.prototype_hash = content_hash(raw)
        self.thresholds = None
        if thresholds is not None:
            if not isinstance(thresholds,dict) or thresholds.get("schema_version") != "1.0.0" or thresholds.get("status") != "experimental_unapproved" or thresholds.get("mandatory_evidence_enabled") is not False or thresholds.get("prototype_hash") != self.prototype_hash or not isinstance(thresholds.get("version"),str) or not thresholds["version"]:
                raise ValueError("Invalid experimental threshold configuration.")
            distance, margin = thresholds.get("max_distance"), thresholds.get("min_margin")
            if any(isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x < 0 for x in (distance,margin)):
                raise ValueError("Thresholds must be explicit finite nonnegative distances.")
            self.thresholds = (float(distance),float(margin))
        self.configuration_hash = content_hash({"prototypes":raw,"thresholds":thresholds})
        self.configuration_version = self.version + "/" + (thresholds["version"] if thresholds else "uncalibrated")
        self._points = tuple((p.colour,hex_to_oklab(p.hex_value)) for p in self.prototypes)

    def classify(self, value):
        def result(status,colour=None,distances=(),reason=None):
            return ColourClassification(status,colour,"experimental_oklab_prototypes",self.configuration_version,self.configuration_hash,distances,reason)
        if value is None or (isinstance(value,str) and not value.strip()):
            return result("Missing",reason="missing_primary")
        try:
            point = hex_to_oklab(value)
        except ValueError:
            return result("Malformed",reason="invalid_hex")
        distances = {}
        for name,prototype in self._points:
            distance = oklab_distance(point,prototype)
            distances[name] = min(distance,distances.get(name,float("inf")))
        ordered = tuple(sorted(distances.items(),key=lambda item:(item[1],item[0])))
        if self.thresholds is None:
            return result("Unknown",distances=ordered,reason="missing_calibration")
        maximum, margin = self.thresholds
        if ordered[0][1] > maximum:
            return result("Unknown",distances=ordered,reason="outside_acceptance_distance")
        gap = ordered[1][1]-ordered[0][1]
        if gap == 0 or gap < margin:
            return result("Ambiguous",distances=ordered,reason="insufficient_class_separation")
        return result("Recognised",ordered[0][0],ordered,reason="experimental_thresholds_only")
