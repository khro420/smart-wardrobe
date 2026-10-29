"""Immutable structure-aware evidence; a dress is exactly one one_piece member."""
from dataclasses import dataclass

STRUCTURES = {
    "top_bottom": ("upper","lower"),
    "top_bottom_outerwear": ("upper","lower","outerwear"),
    "dress": ("one_piece",),
    "dress_outerwear": ("one_piece","outerwear"),
}


@dataclass(frozen=True)
class CompatibilityDescriptor:
    styles: tuple[str, ...]
    colour: str
    pattern: str

    def __post_init__(self):
        if not isinstance(self.styles,(list,tuple)) or not self.styles or any(not isinstance(x,str) or not x for x in self.styles) or any(not isinstance(x,str) or not x for x in (self.colour,self.pattern)):
            raise ValueError("Incomplete compatibility descriptor.")
        object.__setattr__(self,"styles",tuple(sorted(set(self.styles))))


@dataclass(frozen=True)
class CompatibilitySignature:
    structure: str
    members: tuple[tuple[str,CompatibilityDescriptor], ...]

    def __post_init__(self):
        if self.structure not in STRUCTURES or not isinstance(self.members,(list,tuple)):
            raise ValueError("Invalid compatibility structure.")
        if any(not isinstance(x,(list,tuple)) or len(x) != 2 or not isinstance(x[0],str) or not isinstance(x[1],CompatibilityDescriptor) for x in self.members):
            raise ValueError("Invalid signature member.")
        by_role = dict(self.members)
        expected = STRUCTURES[self.structure]
        if len(by_role) != len(self.members) or set(by_role) != set(expected):
            raise ValueError("Signature does not match its actual structure.")
        object.__setattr__(self,"members",tuple((role,by_role[role]) for role in expected))

    @property
    def key(self):
        return (self.structure,tuple((role,d.styles,d.colour,d.pattern) for role,d in self.members))

    def to_dict(self):
        return {"structure":self.structure,"members":[{"role":role,"styles":list(d.styles),"colour":d.colour,"pattern":d.pattern} for role,d in self.members]}


@dataclass(frozen=True)
class GarmentCompatibilityEvidence:
    descriptor: CompatibilityDescriptor | None
    observed: int
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if (self.descriptor is not None and not isinstance(self.descriptor,CompatibilityDescriptor)) or isinstance(self.observed,bool) or not isinstance(self.observed,int) or not 0 <= self.observed <= 3 or (self.descriptor is not None and self.observed != 3):
            raise ValueError("Invalid garment compatibility evidence.")
        if not isinstance(self.reasons,(list,tuple)) or any(not isinstance(x,str) for x in self.reasons):
            raise ValueError("Invalid compatibility diagnostics.")
        object.__setattr__(self,"reasons",tuple(self.reasons))
