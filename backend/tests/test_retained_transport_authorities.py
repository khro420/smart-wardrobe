"""Finite path relocation preserves genuine original authorities and all values."""
import json
from pathlib import Path
import pytest
from tests.retained_evidence import assert_relocated_authority
from tests import retained_evidence as transport
import copy
import hashlib

SPEC=json.loads((Path(__file__).parent/'fixtures/retained_transport_authorities.v1.json').read_text())
ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('relative',list(SPEC['files']))
@pytest.mark.parametrize('mutation',['current_bytes','wrong_original','unknown_path'])
def test_exact_transport_proof_and_targeted_tamper_refusal(tmp_path,relative,mutation):
    expected=SPEC['files'][relative]['original_sha256']
    copy=tmp_path/relative;copy.parent.mkdir(parents=True);copy.write_bytes((ROOT/relative).read_bytes())
    assert_relocated_authority(relative,tmp_path,expected)
    if mutation=='current_bytes':
        copy.write_bytes(copy.read_bytes()+b' ')
        match='Unregistered relocated authority bytes'
    elif mutation=='wrong_original':
        expected='0'*64;match='Wrong original authority identity'
    else:
        relative='backend/tests/fixtures/unknown_authority.json';match='Unknown relocated authority'
    with pytest.raises(AssertionError,match=match):
        assert_relocated_authority(relative,tmp_path,expected)


@pytest.mark.parametrize('relative',list(SPEC['files']))
@pytest.mark.parametrize('mutation',['manifest','original_bytes'])
def test_original_source_evidence_cannot_be_replaced(tmp_path,monkeypatch,relative,mutation):
    expected=SPEC['files'][relative]['original_sha256']
    assert_relocated_authority(relative,ROOT,expected)
    source=transport.review_path(SPEC['source_review'])
    for name in ('delivery-final-verified/SOURCE_MANIFEST.json','source/'+relative):
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((source/name).read_bytes())
    monkeypatch.setattr(transport,'review_path',lambda _:tmp_path)
    assert_relocated_authority(relative,ROOT,expected)
    name='delivery-final-verified/SOURCE_MANIFEST.json' if mutation=='manifest' else 'source/'+relative
    target=tmp_path/name;target.write_bytes(target.read_bytes()+b' ')
    with pytest.raises(AssertionError,match='Original source manifest changed' if mutation=='manifest' else 'Original authority bytes changed'):
        assert_relocated_authority(relative,ROOT,expected)


@pytest.mark.parametrize('relative',list(SPEC['files']))
def test_a_changed_approval_digest_does_not_allow_nontransport_edits(tmp_path,monkeypatch,relative):
    expected=SPEC['files'][relative]['original_sha256']
    assert_relocated_authority(relative,ROOT,expected)
    current=json.loads((ROOT/relative).read_bytes());current['unauthorized_numeric_or_policy_change']=1
    target=tmp_path/relative;target.parent.mkdir(parents=True);target.write_text(json.dumps(current))
    changed=copy.deepcopy(SPEC);changed['files'][relative]['relocated_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    loads=json.loads
    def altered_approval(value,*args,**kwargs):
        parsed=loads(value,*args,**kwargs)
        if isinstance(parsed,dict) and parsed.get('version')==SPEC['version']:
            return changed
        return parsed
    monkeypatch.setattr(transport.json,'loads',altered_approval)
    with pytest.raises(AssertionError,match='Non-transport authority change'):
        assert_relocated_authority(relative,tmp_path,expected)
