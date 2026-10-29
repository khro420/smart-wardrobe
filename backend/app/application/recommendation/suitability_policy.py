"""Explicit owner-declaration policy, never a style-to-suitability inference."""
from dataclasses import dataclass
import json
from pathlib import Path

DEFAULT_POLICY = Path(__file__).with_name("config") / "suitability_policy.v1.json"
OCCASIONS = frozenset(("campus","work","casual_outing","shopping","dinner","party","date","travel"))
FORMALITY = frozenset(("casual","smart_casual"))


@dataclass(frozen=True)
class SuitabilityPolicy:
    version: str
    reserved_prefix: str
    enabled_occasions: tuple[str, ...]
    enabled_formality: tuple[str, ...]

    def __post_init__(self):
        if self.version != "owner-declarations-1.0.0" or self.reserved_prefix != "rec:v1":
            raise ValueError("Unsupported suitability policy.")
        for field,expected in (("enabled_occasions",OCCASIONS),("enabled_formality",FORMALITY)):
            values = getattr(self,field)
            if not isinstance(values,(tuple,list)) or any(not isinstance(x,str) for x in values) or len(values) != len(expected) or set(values) != expected:
                raise ValueError("Only the approved suitability capabilities may be enabled.")
            object.__setattr__(self,field,tuple(sorted(values)))

    def values(self,field):
        if field == "occasion": return self.enabled_occasions
        if field == "formality": return self.enabled_formality
        raise ValueError("Unsupported suitability field.")

    @classmethod
    def load(cls,path=DEFAULT_POLICY):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw,dict) or raw.get("schema_version") != "1.0.0" or raw.get("default_activation") is not False or raw.get("unavailable_occasions") != ["exercise"] or raw.get("unavailable_formality") != ["formal"] or raw.get("decisions") != ["allow","deny"] or raw.get("aggregation") != "all_constituents_fail_then_unknown" or raw.get("annotation_source") != "owner_declared_custom_tags":
            raise ValueError("Invalid suitability policy configuration.")
        try:
            return cls(raw["version"],raw["reserved_prefix"],raw["enabled_occasions"],raw["enabled_formality"])
        except KeyError as exc:
            raise ValueError("Incomplete suitability policy.") from exc
