"""Dated owner observations; no inferred professional or present-condition claim."""
from dataclasses import dataclass
from datetime import datetime

KEY = 'appearance_evidence_v1'
FEATURES = ('collared_neckline', 'tailored_cut', 'structured_shape')


@dataclass(frozen=True)
class AppearanceEvidence:
    state: str = 'Missing'
    category: str | None = None
    media_id: str | None = None
    features: tuple[tuple[str, bool | None], ...] = ()
    condition: str | None = None
    reviewed_at: str | None = None

    def __post_init__(self):
        if self.state not in ('Missing', 'Known', 'Malformed') or type(self.features) is not tuple:
            raise ValueError('Invalid appearance evidence.')
        if any(type(pair) is not tuple or len(pair) != 2 or pair[0] not in FEATURES or pair[1] is not None and type(pair[1]) is not bool for pair in self.features):
            raise ValueError('Invalid immutable appearance facts.')
        if len({pair[0] for pair in self.features}) != len(self.features):
            raise ValueError('Duplicate appearance fact.')
        if self.state == 'Known':
            if (set(k for k,v in self.features) != set(FEATURES) or any(type(v) is not str or not v for v in (self.category,self.media_id,self.reviewed_at))
                    or self.condition not in ('clean_intact','needs_attention','unknown')
                    or datetime.fromisoformat(self.reviewed_at.replace('Z','+00:00')).tzinfo is None):
                raise ValueError('Incomplete known appearance observation.')

    def current(self, garment):
        return self.state == 'Known' and self.category == garment.category and self.media_id == garment.preferred_media_id


def project_appearance_evidence(raw, present=False):
    if not present:
        return AppearanceEvidence()
    try:
        if (type(raw) is not dict or set(raw) != {'schema_version', 'source', 'category', 'media_id', 'construction_features', 'condition_observation', 'reviewed_at'}
                or raw['schema_version'] != '1.0.0' or raw['source'] != 'owner_review'
                or any(type(raw[k]) is not str or not raw[k] for k in ('category', 'media_id', 'reviewed_at'))
                or type(raw['construction_features']) is not dict or set(raw['construction_features']) != set(FEATURES)
                or any(v is not None and type(v) is not bool for v in raw['construction_features'].values())
                or raw['condition_observation'] not in ('clean_intact', 'needs_attention', 'unknown')
                or datetime.fromisoformat(raw['reviewed_at'].replace('Z', '+00:00')).tzinfo is None):
            raise ValueError('Invalid owner observation.')
        return AppearanceEvidence('Known', raw['category'], raw['media_id'], tuple((k, raw['construction_features'][k]) for k in FEATURES), raw['condition_observation'], raw['reviewed_at'])
    except (ValueError, TypeError, KeyError, AttributeError):
        return AppearanceEvidence(state='Malformed')
