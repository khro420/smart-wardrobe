"""Immutable server-captured intent; a profile is not an authentication principal."""
from dataclasses import dataclass,asdict
import json
from app.domain.value_objects.recommendation_refinement import canonical_uuid

VERSION='intended-wearer-evidence-1.0.0'


@dataclass(frozen=True)
class IntendedWearer:
    account_id: str
    profile_id: str
    name_at_request: str
    selection_origin: str
    captured_at: str

    def __post_init__(self):
        canonical_uuid(self.profile_id)
        if not self.account_id or not isinstance(self.name_at_request,str) or not 1<=len(self.name_at_request)<=60:
            raise ValueError('Invalid intended wearer.')
        if self.selection_origin not in ('explicit','single_active_auto') or not isinstance(self.captured_at,str) or not self.captured_at:
            raise ValueError('Invalid wearer capture.')

    def evidence(self):
        data={'version':VERSION,**asdict(self),'request_fingerprint_version':3}
        validate_wearer_evidence(data,self.account_id,self.profile_id)
        return data


def validate_wearer_evidence(data,account_id,profile_id):
    if type(data) is not dict or set(data)!={'version','account_id','profile_id','name_at_request','selection_origin','captured_at','request_fingerprint_version'}:
        raise ValueError('Invalid wearer evidence fields.')
    if data['version']!=VERSION or type(data['request_fingerprint_version']) is not int or data['request_fingerprint_version']!=3:
        raise ValueError('Unsupported wearer evidence.')
    if len(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode())>4096:
        raise ValueError('Oversized wearer evidence.')
    captured=IntendedWearer(*(data[key] for key in ('account_id','profile_id','name_at_request','selection_origin','captured_at')))
    if captured.account_id!=account_id or captured.profile_id!=profile_id:
        raise ValueError('Stored wearer does not match recommendation ownership.')
    return captured
