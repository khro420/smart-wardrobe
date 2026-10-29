"""Immutable projection of owner-reviewed attributes and optional overrides."""
from dataclasses import dataclass
from datetime import datetime

KEY = 'contextual_suitability_v1'


@dataclass(frozen=True)
class ContextualGarmentEvidence:
    state: str = 'Missing'
    review_state: str = 'Missing'
    reviewed_styles: tuple[str, ...] = ()
    reviewed_category: str | None = None
    reviewed_at: str | None = None
    wedding_decisions: tuple[str, ...] = ()

    def __post_init__(self):
        if (self.state not in ('Missing', 'Known', 'Malformed')
                or self.review_state not in ('Missing', 'Known', 'Malformed')
                or not isinstance(self.reviewed_styles, tuple)
                or any(not isinstance(v, str) for v in self.reviewed_styles)
                or not isinstance(self.wedding_decisions, tuple)
                or any(v not in ('allow', 'deny') for v in self.wedding_decisions)
                or self.reviewed_category is not None and not isinstance(self.reviewed_category, str)
                or self.reviewed_at is not None and not isinstance(self.reviewed_at, str)):
            raise ValueError('Invalid immutable contextual evidence.')


def project_contextual_evidence(raw, present=False):
    if not present:
        return ContextualGarmentEvidence()
    if not isinstance(raw, dict):
        return ContextualGarmentEvidence(state='Malformed')
    overrides = raw.get('occasion_overrides')
    decisions = overrides.get('wedding') if isinstance(overrides, dict) else None
    # Retain identifiable Deny even alongside malformed metadata/other entries.
    valid = tuple(dict.fromkeys(v for v in decisions if isinstance(v, str) and v in ('allow', 'deny'))) if isinstance(decisions, list) else ()
    clean = (set(raw) == {'schema_version', 'style_review', 'occasion_overrides'}
             and raw.get('schema_version') == '1.0.0' and isinstance(overrides, dict)
             and set(overrides) <= {'wedding'}
             and ('wedding' not in overrides or isinstance(decisions, list)
                  and bool(decisions) and all(isinstance(v, str) and v in ('allow', 'deny') for v in decisions)))
    review = raw.get('style_review')
    if review is None:
        return ContextualGarmentEvidence(state='Known' if clean else 'Malformed', wedding_decisions=valid)
    try:
        styles = review['styles']
        reviewed_at = review['reviewed_at']
        timestamp = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
        review_ok = (set(review) == {'source', 'styles', 'category', 'reviewed_at'}
                     and review['source'] == 'owner_review' and isinstance(styles, list)
                     and len(styles) == 1 and all(isinstance(v, str) and v for v in styles)
                     and isinstance(review['category'], str) and bool(review['category'])
                     and timestamp.tzinfo is not None)
        if not review_ok:
            raise ValueError('Malformed review.')
        return ContextualGarmentEvidence('Known' if clean else 'Malformed', 'Known',
                                          tuple(styles), review['category'], reviewed_at, valid)
    except (ValueError, TypeError, KeyError, AttributeError):
        return ContextualGarmentEvidence('Known' if clean else 'Malformed', 'Malformed', wedding_decisions=valid)

