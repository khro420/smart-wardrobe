"""Explicit offline snapshot versions; no runtime acquisition or archive repair."""
from dataclasses import asdict,fields
import hashlib,json
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
from app.domain.value_objects.general_context_evidence import AppearanceEvidence
from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence

LEGACY='1.0.0'
CURRENT='2.0.0'
EVIDENCE={'contextual_suitability':ContextualGarmentEvidence,'appearance_evidence':AppearanceEvidence,'saved_attribute_evidence':SavedAttributeEvidence}
LEGACY_FIELDS=frozenset({'garment_id','user_id','status','category','name','preferred_media_id','updated_at','is_favourite','structural_role','layering_index','primary_colour','style_tags','pattern','invalid_attributes','secondary_colour','colour_temperature','fit','material','is_dominant','custom_tags','colour_palette'})
REQUIRED=frozenset({'garment_id','user_id','status','category','name','preferred_media_id','updated_at','is_favourite','structural_role','layering_index'})


def _encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def _digest(value):return hashlib.sha256(_encode(value)).hexdigest()


def decode_snapshot(raw,version):
    if version not in (LEGACY,CURRENT):raise ValueError('Unknown offline snapshot version.')
    allowed=LEGACY_FIELDS if version==LEGACY else LEGACY_FIELDS|set(EVIDENCE)
    required=REQUIRED if version==LEGACY else REQUIRED|set(EVIDENCE)
    if type(raw) is not dict or not required<=set(raw)<=allowed:
        raise ValueError('Snapshot fields do not match its explicit offline version.')
    _encode(raw)  # Reject nonfinite/non-JSON input before immutable reconstruction.
    value=dict(raw)
    if version==CURRENT:
        for name,kind in EVIDENCE.items():
            entry=value[name]
            if type(entry) is not dict or set(entry)!={f.name for f in fields(kind)}:
                raise ValueError('Unexpected immutable evidence fields.')
            entry=dict(entry)
            if name=='contextual_suitability':
                for key in ('reviewed_styles','wedding_decisions'):
                    if type(entry[key]) is not list:raise ValueError('Evidence collections must be JSON arrays.')
                    entry[key]=tuple(entry[key])
            elif name=='appearance_evidence':
                if type(entry['features']) is not list or any(type(pair) is not list for pair in entry['features']):
                    raise ValueError('Appearance features must be JSON arrays.')
                entry['features']=tuple(tuple(pair) for pair in entry['features'])
            value[name]=kind(**entry)
    return ConfirmedGarmentSnapshot(**value)


def encode_snapshot(snapshot,version=CURRENT):
    if type(snapshot) is not ConfirmedGarmentSnapshot:raise ValueError('Immutable snapshot required.')
    if version==LEGACY:return legacy_projection(snapshot)['snapshot']
    if version!=CURRENT:raise ValueError('Unknown offline snapshot version.')
    raw=json.loads(_encode(asdict(snapshot)))
    if decode_snapshot(raw,CURRENT)!=snapshot:raise ValueError('Offline snapshot round-trip mismatch.')
    return raw


def legacy_projection(snapshot):
    """Opt-in downgrade only for exact absent defaults, retaining both views."""
    if type(snapshot) is not ConfirmedGarmentSnapshot:raise ValueError('Immutable snapshot required.')
    if any(getattr(snapshot,name)!=kind() for name,kind in EVIDENCE.items()):
        raise ValueError('Legacy projection would discard meaningful evidence.')
    source=encode_snapshot(snapshot,CURRENT)
    projected={k:v for k,v in source.items() if k in LEGACY_FIELDS}
    decode_snapshot(projected,LEGACY)
    return {'contract':'offline-snapshot-legacy-projection-1.0.0','source_version':CURRENT,'target_version':LEGACY,
            'source_sha256':_digest(source),'projection_sha256':_digest(projected),'source':source,'snapshot':projected}
