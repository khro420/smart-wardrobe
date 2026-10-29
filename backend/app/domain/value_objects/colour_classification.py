"""Diagnostics for experimental colour naming, never mandatory evidence."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ColourClassification:
    status: str
    colour: str | None
    method: str
    configuration_version: str
    configuration_hash: str
    distances: tuple[tuple[str, float], ...] = ()
    reason: str | None = None

    def __post_init__(self):
        if self.status not in ("Recognised", "Ambiguous", "Unknown", "Missing", "Malformed"):
            raise ValueError("Invalid classification status.")
        if (self.status == "Recognised") != (isinstance(self.colour, str) and bool(self.colour)) or (self.status != "Recognised" and self.colour is not None):
            raise ValueError("Only recognised classifications carry a colour.")
        for value in (self.method, self.configuration_version, self.configuration_hash):
            if not isinstance(value, str) or not value:
                raise ValueError("Missing classification provenance.")
        if not isinstance(self.distances, (tuple, list)):
            raise ValueError("Invalid distances.")
        entries = []
        for entry in self.distances:
            if not isinstance(entry, (tuple, list)) or len(entry) != 2:
                raise ValueError("Invalid class distance.")
            name, distance = entry
            if not isinstance(name, str) or not name or isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(distance) or distance < 0:
                raise ValueError("Invalid class distance.")
            entries.append((name, float(distance)))
        if len({name for name,_ in entries}) != len(entries):
            raise ValueError("Distances must represent distinct classes.")
        object.__setattr__(self, "distances", tuple(entries))
        if self.reason is not None and not isinstance(self.reason, str):
            raise ValueError("Invalid reason.")

    @property
    def closest(self):
        return self.distances[0] if self.distances else None

    @property
    def second_closest(self):
        return self.distances[1] if len(self.distances) > 1 else None
