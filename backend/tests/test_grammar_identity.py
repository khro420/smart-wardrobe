"""Exact LF/CRLF equivalence without redefining archived raw-byte hashes."""
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest

from app.shared_contracts.grammar_identity import (
    RESOURCE_CONTRACT, FINGERPRINT_CONTRACT, ResourceIdentity,
    canonical_bytes, semantic_fingerprint,
)
from app.application.nlp.general_context_interpreter import GRAMMAR, GeneralContextInterpreter
from app.application.recommendation.general_context_evaluator import EvaluatorSpecification
from app.application.recommendation.context_relevance_policy import ContextRelevancePolicy


def test_versioned_resource_identity_keeps_raw_and_semantic_hashes_separate():
    lf=b'{\n  "word": "cotton",\n  "literal": "\\r\\n"\n}\n'
    crlf=lf.replace(b'\n',b'\r\n')
    a,b=ResourceIdentity.capture(lf),ResourceIdentity.capture(crlf)
    assert a.contract==b.contract==RESOURCE_CONTRACT=='crlf-to-lf-sha256-1.0.0'
    assert a.raw_sha256==a.semantic_sha256==sha256(lf).hexdigest()
    assert b.raw_sha256==sha256(crlf).hexdigest()!=a.raw_sha256
    assert b.semantic_sha256==a.semantic_sha256
    assert canonical_bytes(crlf)==lf
    # No JSON reserialization, stripping, Unicode folding or lone-CR rewrite.
    for changed in (lf+b' ',lf.replace(b'cotton',b'linen'),b'\xef\xbb\xbf'+lf,lf.replace(b'\n',b'\r')):
        assert ResourceIdentity.capture(changed).semantic_sha256!=a.semantic_sha256
    with pytest.raises(TypeError):canonical_bytes('text')


@pytest.mark.parametrize('text',[
    "I'm going shopping.","I'm going to class.","I'm meeting friends for dinner.",
])
def test_legacy_parser_evaluator_and_relative_policy_agree_for_lf_and_crlf(monkeypatch,text):
    original_open=Path.open
    lf=GRAMMAR.read_bytes().replace(b'\r\n',b'\n')
    captured=[]
    for payload in (lf,lf.replace(b'\n',b'\r\n')):
        def fixture_open(path,mode='r',*args,**kwargs):
            if path==GRAMMAR:
                assert mode=='rb'
                return BytesIO(payload)
            return original_open(path,mode,*args,**kwargs)
        with monkeypatch.context() as local:
            local.setattr(Path,'open',fixture_open)
            parser=GeneralContextInterpreter()
            result=parser.interpret(text)
            assert result.status=='Supported'
            request=result.structured_request
            specification=EvaluatorSpecification.current()
            policy=ContextRelevancePolicy.load()
            assert parser.grammar_hash==specification.grammar_sha256==policy.grammar_sha256
            assert request.context.grammar_sha256==parser.grammar_identity.semantic_sha256
            assert parser.grammar_identity.raw_sha256==sha256(payload).hexdigest()
            assert specification.construct().supports(request)
            resolution=policy.resolve(request)
            assert resolution.objective is not None
            captured.append((request.to_dict(),asdict(resolution)))
    assert captured[0]==captured[1]


@pytest.mark.parametrize('subtypes',[False,True])
def test_current_composite_grammar_is_cross_platform_and_versioned(monkeypatch,subtypes):
    from app.application.nlp.conversational_context_interpreter import fingerprint
    from app.domain.value_objects.verified_garment_subtype import ENVIRONMENT_KEY,PROFILE
    monkeypatch.setenv(ENVIRONMENT_KEY,PROFILE if subtypes else 'disabled')
    original=Path.read_bytes
    results=[]
    for newline in (b'\n',b'\r\n'):
        with monkeypatch.context() as local:
            local.setattr(Path,'read_bytes',lambda path:original(path).replace(b'\r\n',b'\n').replace(b'\n',newline))
            results.append(fingerprint())
    expected=('8555bb6c367aa276d5a21685c8d2a008155dc7282d37ecf325bba31c0903b1e2' if subtypes else
              '14b41df8fe4f815e655b7b593afc66326c70896f58d699e6174b977b8cf51a14')
    assert FINGERPRINT_CONTRACT=='conversational-grammar-fingerprint-2.0.0'
    assert results==[expected,expected]
    assert semantic_fingerprint([b'a\r\nb',b'c'])==semantic_fingerprint([b'a\nb',b'c'])
    old_raw=sha256(sha256(b'a\nb').digest()+sha256(b'c').digest()).hexdigest()
    assert semantic_fingerprint([b'a\nb',b'c'])!=old_raw


def test_conversational_resource_accepts_only_the_pinned_newline_equivalence(tmp_path):
    from app.application.nlp.conversational_context_interpreter import RESOURCE,load_language
    lf=RESOURCE.read_bytes().replace(b'\r\n',b'\n')
    path=tmp_path/'language.json'
    path.write_bytes(lf);a=load_language(path)
    path.write_bytes(lf.replace(b'\n',b'\r\n'));assert load_language(path)==a
    path.write_bytes(lf+b' ')
    with pytest.raises(ValueError,match='Unregistered'):load_language(path)


def test_archived_raw_frame_hash_is_preserved_without_reinterpretation(monkeypatch):
    """Synthetic archive schema control; no actual historical record is edited."""
    from app.application.recommendation.refinement_verifier import rebuild_request
    payload=GeneralContextInterpreter().interpret("I'm going shopping.").structured_request.to_dict()
    raw=GRAMMAR.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    historical_raw=sha256(raw).hexdigest()
    payload['context']['grammar_sha256']=historical_raw
    monkeypatch.setattr(GeneralContextInterpreter,'interpret',lambda *a:pytest.fail('Archive was reinterpreted'))
    restored=rebuild_request(payload)
    assert restored.to_dict()==payload
    assert restored.context.grammar_sha256==historical_raw
    assert historical_raw!=ResourceIdentity.capture(raw).semantic_sha256
