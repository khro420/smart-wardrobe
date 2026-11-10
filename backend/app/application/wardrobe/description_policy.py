"""Prepare immutable, pinned description resources once, outside enumeration."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from app.domain.value_objects.garment_description_evidence import RESOURCE_HASHES, FIELDS, STATES, ORIGINS

ENVIRONMENT_KEY = 'SMART_WARDROBE_DESCRIPTION_PROFILE'
PROFILE = 'description_evidence_v1'


@dataclass(frozen=True)
class DescriptionPolicy:
    enums: tuple[tuple[str, tuple[str, ...]], ...]
    aliases: tuple[tuple[str, str, str], ...]
    anchors: tuple[tuple[str, str], ...]

    def __post_init__(self):
        object.__setattr__(self, 'enums', tuple((name, tuple(values)) for name, values in self.enums))
        object.__setattr__(self, 'aliases', tuple(tuple(entry) for entry in self.aliases))
        object.__setattr__(self, 'anchors', tuple(tuple(entry) for entry in self.anchors))

    def values(self, field):
        return next((values for name, values in self.enums if name == field), ())

    def legacy_alias(self, field, raw):
        return next((v for f, k, v in self.aliases if f == field and k == raw), raw)

    def colour_family(self, raw):
        return dict(self.anchors).get(raw, raw if raw in self.values('primary_colour') else None)

    @classmethod
    def load(cls, directory=None):
        directory = Path(directory) if directory is not None else Path(__file__).with_name('config')
        documents = {}
        for name, expected in RESOURCE_HASHES.items():
            try:
                with (directory/name).open('rb') as stream:
                    raw = stream.read(65537)
            except OSError as exc:
                raise ValueError('Description policy resource is unavailable.') from exc
            if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Unregistered description policy resource.')
            documents[name] = json.loads(raw)
        vocab = documents['garment_description_vocabulary.v1.json']
        registry = documents['model_vocabulary_registry.v1.json']
        policy = documents['description_evidence_policy.v1.json']
        if registry['enabled'] or registry['membership_verified'] is not False:
            raise ValueError('No model-head vocabulary has been independently registered.')
        if tuple(policy['fields']) != FIELDS or set(policy['states']) != STATES or set(policy['origins']) != ORIGINS:
            raise ValueError('Invalid description policy definition.')
        return cls(tuple((key, tuple(values)) for key, values in vocab['enums'].items()),
                   tuple((a['field'], a['raw'], a['canonical']) for a in vocab['legacy_aliases']),
                   tuple(vocab['exact_hex_anchors'].items()))


def select_policy(value='disabled'):
    if value == 'disabled':
        return None
    if value != PROFILE:
        raise ValueError('Invalid description profile.')
    return DescriptionPolicy.load()
