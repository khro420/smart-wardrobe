"""Explicit P1 inheritance and P2 overrides; no new preference NLP."""
from dataclasses import dataclass
from fractions import Fraction
from app.domain.value_objects.attribute_preferences import AXES, encode, decode, weight
from app.domain.value_objects.preference_snapshot import NormalizedPreferenceSet
from app.application.recommendation.preference_normalizer import PreferenceNormalizer

LEGACY={'colour':'colours','styles':'styles','garment_categories':'garment_categories','formality':'formality'}


@dataclass(frozen=True)
class ComposedPreferences:
    snapshot: object
    legacy: NormalizedPreferenceSet
    payload: bytes

    def families(self):return decode(self.payload,131072)


def compose(snapshot, normalizer=None):
    value=snapshot.to_dict()
    if normalizer is None and value.get('archive') is not None:
        from app.application.recommendation.attribute_preference_codec import normalized_from_archive
        legacy=normalized_from_archive(snapshot)
    else:legacy=(normalizer or PreferenceNormalizer()).normalize(value['account_id'],snapshot.legacy_rows())
    old={p.preference_type:p for p in legacy.preferences}
    doc=value['document'];settings={} if doc is None else doc['families'];result={}
    for family in AXES:
        setting=settings.get(family,{'mode':'inherit_p1' if family in LEGACY else 'disabled'})
        if setting['mode']=='inherit_p1':
            p=old.get(LEGACY.get(family))
            if p is not None:result[family]={'mode':'inherit_p1','importance':str(p.importance),'legacy_type':p.preference_type,'preference_id':p.preference_id}
        elif setting['mode']=='override' and weight(setting['importance'])>0:
            axes={axis:a for axis,a in setting['axes'].items() if weight(a['importance'])>0 and (a['liked'] or a['avoided'])}
            if axes: result[family]={'mode':'override','importance':setting['importance'],'axes':axes}
    return ComposedPreferences(snapshot,legacy,encode(result))
