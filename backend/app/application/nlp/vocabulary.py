"""Validate and freeze the approved, versioned vocabulary configuration."""
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType

DEFAULT_VOCABULARY = Path(__file__).with_name("config") / "vocabulary.v1.json"


@dataclass(frozen=True)
class Vocabulary:
    version: str
    entries: tuple[tuple[str, str, str, str | None], ...]
    values: object
    groups: object

    @classmethod
    def load(cls, path: Path = DEFAULT_VOCABULARY):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("version") != "1.0.0" or set(raw.get("fields", {})) != {"occasion", "style", "colours", "garment_categories", "formality"}:
            raise ValueError("Unsupported vocabulary version or fields.")
        entries, values = [], {}
        for field, definitions in raw["fields"].items():
            seen = set()
            values[field] = set()
            for item in definitions:
                canonical = item["value"]
                kind = item.get("kind")
                if not isinstance(canonical, str) or not canonical or (field == "garment_categories" and kind not in ("group", "category")):
                    raise ValueError("Invalid vocabulary value.")
                values[field].add((kind, canonical) if kind else canonical)
                for phrase in item["aliases"]:
                    if not isinstance(phrase, str) or not phrase or phrase != phrase.lower() or phrase in seen:
                        raise ValueError("Invalid or duplicate alias.")
                    seen.add(phrase)
                    entries.append((field, canonical, phrase, kind))
        groups = raw["category_groups"]
        categories = {value for kind, value in values["garment_categories"] if kind == "category"}
        if set(groups) != {value for kind, value in values["garment_categories"] if kind == "group"} or any(not members or not set(members) <= categories for members in groups.values()):
            raise ValueError("Invalid category group membership.")
        return cls(raw["version"], tuple(entries), MappingProxyType({key: frozenset(value) for key, value in values.items()}), MappingProxyType({key: tuple(value) for key, value in groups.items()}))
