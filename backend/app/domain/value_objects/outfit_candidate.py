"""Immutable structural candidates, not request/compatibility-valid outfits."""
from dataclasses import dataclass
import hashlib
import json
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE

ROLE_ORDER = ("upper", "lower", "one_piece", "outerwear")


@dataclass(frozen=True)
class CandidateMember:
    garment: ConfirmedGarmentSnapshot
    role: str
    item_order: int

    def __post_init__(self):
        if not isinstance(self.garment, ConfirmedGarmentSnapshot) or self.role not in ROLE_ORDER:
            raise ValueError("Invalid candidate member.")
        if isinstance(self.item_order, bool) or not isinstance(self.item_order, int) or self.item_order < 1:
            raise ValueError("Invalid candidate item order.")


@dataclass(frozen=True)
class OutfitCandidate:
    members: tuple[CandidateMember, ...]

    def __post_init__(self):
        if not isinstance(self.members, (list, tuple)) or not self.members or any(not isinstance(item, CandidateMember) for item in self.members):
            raise ValueError("Invalid candidate members.")
        members = tuple(self.members)
        roles = tuple(item.role for item in members)
        if roles not in (("upper", "lower"), ("upper", "lower", "outerwear"), ("one_piece",), ("one_piece", "outerwear")):
            raise ValueError("Candidate is not a complete supported structure.")
        if len({item.garment.garment_id for item in members}) != len(members) or len({item.garment.user_id for item in members}) != 1:
            raise ValueError("Candidate has duplicate IDs or mixed ownership.")
        if tuple(item.item_order for item in members) != tuple(range(1, len(members)+1)):
            raise ValueError("Candidate order must be stable and contiguous.")
        mapping = {"top":"upper", "bottom":"lower", "dress":"one_piece", "outerwear":"outerwear"}
        for item in members:
            expected = GARMENT_STRUCTURE.get(item.garment.category)
            if not item.garment.garment_id.strip() or item.garment.status != "available" or expected is None or expected != (item.garment.structural_role, item.garment.layering_index) or mapping[expected[0]] != item.role:
                raise ValueError("Candidate garment does not match its structural slot.")
        object.__setattr__(self, "members", members)

    @property
    def validity(self) -> str:
        return "STRUCTURALLY_VALID"

    @property
    def key(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.role, item.garment.garment_id) for item in self.members)

    @property
    def candidate_id(self) -> str:
        return hashlib.sha256(json.dumps(self.key, separators=(",", ":")).encode()).hexdigest()
