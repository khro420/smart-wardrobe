"""Immutable prepared annotations, not independently verified fashion evidence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PreparedCompatibilityEvidence:
    garment_id: str
    colour: str | None
    colour_state: str
    styles: frozenset[str]
    style_state: str
    reasons: tuple[str,...] = ()

    def __post_init__(self):
        states=("Known","Missing","Malformed","Unrecognized","Empty")
        if not isinstance(self.garment_id,str) or self.colour_state not in states or self.style_state not in states:
            raise ValueError("Invalid prepared compatibility evidence.")
        if self.colour is not None and (not isinstance(self.colour,str) or not self.colour):
            raise ValueError("Invalid primary colour value.")
        if (self.colour_state=="Known") != (isinstance(self.colour,str) and bool(self.colour)):
            raise ValueError("Only recognized primary colours carry a value.")
        if not isinstance(self.styles,(list,tuple,set,frozenset)) or any(not isinstance(x,str) or not x for x in self.styles):
            raise ValueError("Invalid style evidence.")
        if self.style_state=="Known" and not self.styles:
            raise ValueError("Complete styles must be nonempty.")
        if not isinstance(self.reasons,(list,tuple)) or any(not isinstance(x,str) for x in self.reasons):
            raise ValueError("Invalid evidence diagnostics.")
        object.__setattr__(self,"styles",frozenset(self.styles))
        object.__setattr__(self,"reasons",tuple(self.reasons))
