"""Explicit experimental configuration; no discovery or live registration."""
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path

CONFIG = Path(__file__).with_name("config")
RULES = CONFIG / "rule_based_compatibility.v1.json"
PROFILES = CONFIG / "scoring_policy.rule_based.v1.json"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate policy key.")
        result[key] = value
    return result


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),object_pairs_hook=_unique)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class RuleBasedCompatibilityPolicy:
    version: str
    hash: str
    achromatic: frozenset[str] = frozenset(("black","white","grey"))

    def __post_init__(self):
        if self.version != "rule-based-compatibility-1.0.0" or not isinstance(self.hash,str) or len(self.hash)!=64:
            raise ValueError("Invalid rule policy metadata.")
        if frozenset(self.achromatic) != frozenset(("black","white","grey")):
            raise ValueError("Unapproved achromatic colours.")
        object.__setattr__(self,"achromatic",frozenset(self.achromatic))

    @classmethod
    def load(cls,path=RULES):
        raw=load_json(path)
        expected={"version":"rule-based-compatibility-1.0.0","default_activation":False,
                  "colour_rule":"identical_or_achromatic","achromatic":["black","white","grey"],
                  "style_rule":"sorensen_dice","internal_weights":["1/2","1/2"],
                  "pattern_enabled":False,"approximate_hex_enabled":False}
        # Exact schema and types: bool/int equivalence must not authorize activation.
        if json.dumps(raw,sort_keys=True)!=json.dumps(expected,sort_keys=True):
            raise ValueError("Unapproved or invalid experimental compatibility policy.")
        return cls(raw["version"],digest(raw))


@dataclass(frozen=True)
class RuleBasedScoringProfile:
    name: str
    version: str
    weights: tuple[Fraction,...]
    hash: str

    def __post_init__(self):
        approved={"rule_based_request_led":(Fraction(3,5),Fraction(1,5),Fraction(1,5)),
                  "rule_based_balanced":(Fraction(1,2),Fraction(3,10),Fraction(1,5))}
        if (self.version!="rule-based-scoring-1.0.0" or self.name not in approved
                or not isinstance(self.weights,(list,tuple)) or any(type(x) is not Fraction for x in self.weights)
                or tuple(self.weights)!=approved[self.name] or not isinstance(self.hash,str) or len(self.hash)!=64):
            raise ValueError("Invalid experimental scoring profile.")
        object.__setattr__(self,"weights",tuple(self.weights))

    @classmethod
    def load(cls,name,path=PROFILES):
        raw=load_json(path)
        expected={"version":"rule-based-scoring-1.0.0","default_activation":False,
                  "profiles":{"rule_based_request_led":["0.60","0.20","0.20"],
                              "rule_based_balanced":["0.50","0.30","0.20"]}}
        if json.dumps(raw,sort_keys=True)!=json.dumps(expected,sort_keys=True) or name not in expected["profiles"]:
            raise ValueError("Unapproved experimental scoring profile.")
        return cls(name,raw["version"],tuple(Fraction(x) for x in raw["profiles"][name]),digest(raw))
