"""Stored P2 mechanics reconstruct without active preference or description loaders."""
from dataclasses import replace
import json
import pytest
from tests.test_p2_preference_selection import engine_fixture,kernel_rank
from app.application.recommendation.attribute_preference_codec import build_archive_snapshot,legacy_digest
from app.application.recommendation.attribute_preference_policy import AttributePreferencePolicy
from app.application.recommendation.attribute_preference_preparation import PreparedAttributePreferences
from app.application.recommendation.attribute_preference_verifier import build,validate
from app.application.recommendation.refinement_verifier import snapshot_digest,request_digest,preference_digest
from app.domain.value_objects.attribute_selection_evidence import description_digest
from app.domain.value_objects.attribute_preferences import digest,PreferenceError


@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('relative',[True,False])
def test_archived_exact_score_and_P2_ledger_with_current_loaders_unavailable(monkeypatch,compact,relative):
    garments,old,request,*_=engine_fixture(['blue'])
    if not relative:
        from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
        request=StructuredOutfitRequest()
    text="I'm going shopping." if relative else 'Recommend an outfit.'
    captured=build_archive_snapshot(old.snapshot,AttributePreferencePolicy.load())
    assert legacy_digest(captured)==preference_digest('owner-A',captured.legacy_rows())
    prepared=PreparedAttributePreferences(captured,old.collection,request=request,original_text=text)
    result=kernel_rank(garments,prepared,request,compact,relative)
    assert result.status=='Selected',result
    draft=build(prepared,result.winner.verified,result.winner.score,'a'*64,snapshot_digest(garments),description_digest(old.collection),request_digest(text,request,()))
    from app.application.recommendation.decision_score_codec import score_to_json,score_from_json
    encoded=score_to_json(result.winner.score)
    assert score_from_json(encoded)==result.winner.score
    def unavailable(*args,**kwargs):raise AssertionError('Active loader called during historical read')
    from app.application.recommendation.preference_normalizer import PreferenceNormalizer
    from app.application.wardrobe.description_policy import DescriptionPolicy
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    monkeypatch.setattr(AttributePreferencePolicy,'load',unavailable)
    monkeypatch.setattr(PreferenceNormalizer,'normalize',unavailable)
    monkeypatch.setattr(DescriptionPolicy,'load',unavailable)
    monkeypatch.setattr(AttributeEvidencePolicy,'load',unavailable)
    assert validate(draft.evidence.to_dict(),score_from_json(encoded),'owner-A',captured.to_dict()['wearer_id']).payload==draft.evidence.payload
    if relative:
        from app.application.recommendation.context_relevance_verifier import validate_evidence
        validate_evidence(json.loads(result.ranking_evidence),result.winner.score,result.winner.verified.candidate,request)


def test_archived_bridge_preserves_original_nonempty_P1_interpretation():
    from tests.test_p2_preference_selection import snapshot
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    rows=tuple(PreferenceSnapshot(kind,'owner-A',kind,json.dumps({'values':values}),'0.123456789012','owner',True) for kind,values in (
        ('colours',['blue']),('styles',['casual']),('garment_categories',[{'kind':'category','value':'trousers'}]),('formality',['casual'])))
    captured=build_archive_snapshot(snapshot({},rows),AttributePreferencePolicy.load())
    assert legacy_digest(captured)==preference_digest('owner-A',rows)
