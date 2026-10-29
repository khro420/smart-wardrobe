"""Validate reference provenance and exact ratings; never manufacture reviews."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from app.application.nlp.vocabulary import Vocabulary
from app.domain.value_objects.compatibility_signature import CompatibilityDescriptor,CompatibilitySignature

DEFAULT_REFERENCES = Path(__file__).with_name("config") / "compatibility_references.v1.json"
EXISTING_REVIEW_PATTERNS = frozenset(("plain","abstract","cartoon","letters, numbers","camouflage","check","dot","fair isle","floral","geometric","paisley","stripe","houndstooth","herringbone","chevron","argyle","leopard","snakeskin","cheetah","peacock","zebra","giraffe","toile de jouy","plant"))


def artifact_hash(raw):
    return hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ReviewedCompatibilityReference:
    reference_id: str
    signature: CompatibilitySignature
    ratings: tuple[tuple[str,int], ...]
    adjudication: tuple[tuple[str,str], ...]
    source_ids: tuple[str, ...]
    approval_status: str
    independently_reviewed: bool
    value: Fraction

    def __post_init__(self):
        if not isinstance(self.reference_id,str) or not self.reference_id or not isinstance(self.signature,CompatibilitySignature) or self.approval_status not in ("draft","approved","rejected") or not isinstance(self.independently_reviewed,bool):
            raise ValueError("Invalid reference metadata.")
        if not isinstance(self.ratings,(tuple,list)) or any(not isinstance(x,(tuple,list)) or len(x) != 2 or not isinstance(x[0],str) or not x[0] or isinstance(x[1],bool) or not isinstance(x[1],int) or not 0 <= x[1] <= 4 for x in self.ratings):
            raise ValueError("Invalid individual review ratings.")
        if len({x[0] for x in self.ratings}) != len(self.ratings) or len(self.ratings) < 2:
            raise ValueError("At least two distinct reviewer declarations are required.")
        if not isinstance(self.adjudication,(tuple,list)) or any(not isinstance(x,(tuple,list)) or len(x) != 2 or any(not isinstance(y,str) or not y for y in x) for x in self.adjudication):
            raise ValueError("Invalid adjudication provenance.")
        adjudication = dict(self.adjudication)
        if len(adjudication) != len(self.adjudication) or set(adjudication) != {"reviewer_id","decision","note"} or adjudication["decision"] not in ("accepted","pending","rejected"):
            raise ValueError("Incomplete adjudication record.")
        if self.approval_status == "approved" and adjudication["decision"] != "accepted":
            raise ValueError("Approved references require accepted adjudication.")
        if not isinstance(self.source_ids,(list,tuple)) or not self.source_ids or any(not isinstance(x,str) or not x for x in self.source_ids):
            raise ValueError("Source reference identifiers required.")
        expected = Fraction(sum(x[1] for x in self.ratings),4*len(self.ratings))
        if not isinstance(self.value,Fraction) or self.value != expected:
            raise ValueError("Normalized value must equal the recorded ratings.")
        object.__setattr__(self,"ratings",tuple(sorted(tuple(x) for x in self.ratings)))
        object.__setattr__(self,"adjudication",tuple(sorted(tuple(x) for x in self.adjudication)))
        object.__setattr__(self,"source_ids",tuple(sorted(set(self.source_ids))))


@dataclass(frozen=True,init=False)
class CompatibilityReferencePolicy:
    synthetic: bool
    patterns: frozenset[str]
    vocabulary: Vocabulary
    version: str
    available: bool
    hash: str
    references: tuple[ReviewedCompatibilityReference, ...]
    approved: object

    def __init__(self,raw,allow_synthetic=False):
        if not isinstance(raw,dict) or raw.get("schema_version") != "1.0.0" or not isinstance(raw.get("version"),str) or not raw["version"] or raw.get("activation_approved") is not False or not isinstance(raw.get("available"),bool):
            raise ValueError("Invalid experimental reference policy.")
        object.__setattr__(self,"synthetic",raw.get("kind") == "synthetic_fixture")
        if raw.get("kind") not in ("reviewed_reference_policy","synthetic_fixture") or (self.synthetic and not allow_synthetic):
            raise ValueError("Synthetic references are permitted only by explicit test-fixture opt-in.")
        if raw.get("rubric") != {"minimum":0,"maximum":4,"normalization":"mean_individual_ratings_divided_by_4"}:
            raise ValueError("Unsupported review rubric.")
        patterns = raw.get("patterns")
        if not isinstance(patterns,list) or not patterns or any(not isinstance(x,str) or not x or x != x.strip().casefold() for x in patterns) or len(set(patterns)) != len(patterns):
            raise ValueError("Invalid exact pattern evidence configuration.")
        if not set(patterns) <= EXISTING_REVIEW_PATTERNS:
            raise ValueError("Patterns must use existing reviewed options, without invented aliases.")
        object.__setattr__(self,"patterns",frozenset(patterns))
        object.__setattr__(self,"vocabulary",Vocabulary.load())
        object.__setattr__(self,"version",raw["version"])
        object.__setattr__(self,"available",raw["available"])
        object.__setattr__(self,"hash",artifact_hash(raw))
        records = raw.get("references")
        if not isinstance(records,list):
            raise ValueError("References must be an explicit list.")
        references,ids,keys = [],set(),set()
        for item in records:
            try:
                signature = self.parse_signature(item["signature"])
                ratings = tuple((x["reviewer_id"],x["rating"]) for x in item["ratings"])
                value = item["normalized_value"]
                if set(value) != {"numerator","denominator"} or any(isinstance(value[x],bool) or not isinstance(value[x],int) for x in value) or value["denominator"] <= 0:
                    raise ValueError("Normalized value requires an exact rational.")
                reference = ReviewedCompatibilityReference(item["reference_id"],signature,ratings,tuple(item["adjudication"].items()),item["source_ids"],item["approval_status"],item["independently_reviewed"],Fraction(value["numerator"],value["denominator"]))
            except (KeyError,TypeError,AttributeError,ZeroDivisionError) as exc:
                raise ValueError("Malformed compatibility reference.") from exc
            if reference.reference_id in ids or signature.key in keys:
                raise ValueError("Duplicate reference ID or conflicting signature.")
            if reference.approval_status == "approved" and not self.synthetic and not reference.independently_reviewed:
                raise ValueError("Approved real references require independent review declarations.")
            if self.synthetic and reference.independently_reviewed:
                raise ValueError("Synthetic fixtures cannot claim independent human review.")
            ids.add(reference.reference_id); keys.add(signature.key); references.append(reference)
        object.__setattr__(self,"references",tuple(sorted(references,key=lambda x:x.reference_id)))
        object.__setattr__(self,"approved",MappingProxyType({x.signature.key:x for x in self.references if x.approval_status == "approved"}))

    def parse_signature(self,raw):
        try:
            if set(raw) != {"structure","members"} or not isinstance(raw["members"],list):
                raise ValueError("Invalid signature fields.")
            members = []
            for item in raw["members"]:
                if set(item) != {"role","styles","colour","pattern"}:
                    raise ValueError("Invalid signature descriptor fields.")
                descriptor = CompatibilityDescriptor(item["styles"],item["colour"],item["pattern"])
                if not set(descriptor.styles) <= self.vocabulary.values["style"] or descriptor.colour not in self.vocabulary.values["colours"] or descriptor.pattern not in self.patterns:
                    raise ValueError("Unapproved descriptor value.")
                members.append((item["role"],descriptor))
            return CompatibilitySignature(raw["structure"],tuple(members))
        except (KeyError,TypeError) as exc:
            raise ValueError("Malformed structure-aware signature.") from exc

    @classmethod
    def load(cls,path=DEFAULT_REFERENCES,allow_synthetic=False):
        return cls(json.loads(Path(path).read_text(encoding="utf-8")),allow_synthetic)
