"""Restricted internal workflow. Never installed by the normal composition root."""
from dataclasses import asdict
import hashlib,json
from app.domain.value_objects.attribute_conditions import encode,digest
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent
from app.domain.value_objects.request_local_selection import LocalSelectionProof,LocalPreferenceWriteDraft,VERSION,KEY,SETTINGS,POLICY
from app.domain.value_objects.intended_wearer import IntendedWearer
from app.domain.value_objects.recommendation_persistence import RecommendationWrite,WardrobeChanged
from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
from app.application.recommendation.request_local_selection_engine import first_selection,decision_document

def resource_identities():
    from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
    from app.application.recommendation.rule_based_compatibility_policy import RuleBasedCompatibilityPolicy
    from app.application.recommendation.structural_policy import StructuralPolicy
    from app.application.wardrobe.description_policy import DescriptionPolicy
    return {'C1':asdict(CompatibilityDecisionPolicy.load()),'raw_C1':{'version':RuleBasedCompatibilityPolicy.load().version,'sha256':RuleBasedCompatibilityPolicy.load().hash},
        'structure':StructuralPolicy.load().version,'B0':digest(asdict(DescriptionPolicy.load())),'ranking':'request_local_bounded_preference_v1'}

class InternalLocalPreferenceWorkflow:
    """Only trusted internal callers supply already interpreted, typed requests.

    Authenticated owner/profile and full source scope are recaptured from SQLite;
    no caller-selected query, winner, scoring policy or verification bypass.
    """
    def __init__(self,*,source_codec=None):
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        if source_codec not in (None,codec):raise ValueError('Unsupported internal source codec.')
        self.source_codec=source_codec

    def source_revisions(self,conn,owner,wearer):
        profile=conn.execute('SELECT * FROM wardrobe_profiles WHERE id=? AND user_id=?',(wearer.profile_id,owner)).fetchone()
        details=conn.execute('SELECT * FROM wardrobe_profile_details_v1 WHERE profile_id=?',(wearer.profile_id,)).fetchone()
        preferences=conn.execute('SELECT * FROM user_preferences WHERE user_id=? AND profile_id=? AND is_active=1 ORDER BY preference_type,id',(owner,wearer.profile_id)).fetchall()
        return {'profile':dict(profile) if profile else None,'details':dict(details) if details else None,'preferences':[dict(p) for p in preferences]}

    def capture(self,conn,owner,wearer,*,source_codec=None,media_root=None):
        from app.application.wardrobe.profile_service import require_active_profile
        from app.application.wardrobe import wearer_category_service as categories
        from app.application.ports.workflow_runtime import runtime
        from app.infrastructure.persistence.active_preference_query_adapter import read_active_preference_rows
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(owner,)).fetchone():raise ValueError('Active authenticated owner required.')
        profile=require_active_profile(conn,owner,wearer.profile_id)
        if wearer.account_id!=owner or wearer.name_at_request!=profile['name']:raise ValueError('Changed captured wearer.')
        scope=categories.capture(owner,wearer.profile_id,conn)
        if scope is None or runtime().description_policy is None:raise ValueError('Explicit wearer and description qualification required for internal soft workflow.')
        from app.domain.value_objects.request_local_source_codec import VERSION as codec,pack_sources
        if source_codec not in (None,codec):raise ValueError('Unsupported capture source codec.')
        if not scope.account_descriptions:
            from app.application.recommendation.request_local_selection_engine import LocalSelectionUnavailable
            from app.application.recommendation.request_local_bounded_ranking import CompletedLedger
            raise LocalSelectionUnavailable(CompletedLedger(0,0,0,0,True),no_eligible=True)
        if len(scope.account_descriptions)>100:raise ValueError('Unbounded local source scope.')
        sources=[];source_bytes=0
        for item in sorted(scope.account_descriptions,key=lambda r:r.snapshot.garment_id):
            g=item.snapshot
            raw=conn.execute('SELECT * FROM garments WHERE id=? AND user_id=?',(g.garment_id,owner)).fetchone()
            links=conn.execute('SELECT p.id processing_item_id,p.job_id,p.review_status,p.crop_media_id,p.preferred_media_id,p.created_at item_created_at,j.user_id owner_id,j.status job_status,j.source_media_id,j.updated_at job_updated_at,j.completed_at job_completed_at FROM processing_items p JOIN processing_jobs j ON j.id=p.job_id WHERE p.id=?',(raw['processing_item_id'],)).fetchone()
            media=conn.execute("SELECT id,user_id,media_type,storage_key,content_type,size_bytes,status,created_at FROM media_assets WHERE id=? AND user_id=? AND status='available'",(g.preferred_media_id,owner)).fetchone()
            if links is None or media is None or links['owner_id']!=owner:raise WardrobeChanged('Missing owned confirmed source/media.')
            if media_root is None:
                path,_=runtime().media.path_for_owner(g.preferred_media_id,owner)
            else:
                # Trusted bound stores may resolve the owned available media row
                # already selected above on this transaction. Opening another
                # SQLite reader can self-block after a large writer cache spill.
                from pathlib import Path
                root=Path(media_root).resolve()
                path=(root/media['storage_key']).resolve()
                if not path.is_relative_to(root):raise WardrobeChanged('Captured source media escapes its bound root.')
            if not path.is_file():raise WardrobeChanged('Captured source media is unavailable.')
            media_hash=hashlib.sha256(path.read_bytes()).hexdigest()
            sources.append({'snapshot':asdict(g),'description':item.description.to_dict(),'category_source':{k:raw[k] for k in ('id','category','attributes_json','additional_attributes','preferred_media_id','updated_at')},'links':dict(links),'media':dict(media),'media_sha256':media_hash})
            size=len(encode(sources[-1]));source_bytes+=size
            if size>262144 or source_codec is None and source_bytes>3145728:raise ValueError('Captured local source proof exceeds its byte budget.')
        if len(sources)!=len(scope.account_rows):raise ValueError('Complete account descriptions required.')
        if source_codec is not None:pack_sources(sources)
        preferences=tuple(read_active_preference_rows(conn,owner,wearer))
        return scope,sources,preferences

    def prepare(self,repository,owner,profile_id,intent,key,*,engine='reference'):
        if type(intent) is not RequestLocalPreferenceIntent:raise ValueError('Typed isolated intent required.')
        conn=repository._connect()
        try:
            conn.execute('BEGIN')
            from app.application.wardrobe.profile_service import require_active_profile
            from app.infrastructure.persistence.postgresql_repository import utcnow
            profile=require_active_profile(conn,owner,profile_id)
            wearer=IntendedWearer(owner,profile_id,profile['name'],'explicit',utcnow())
            scope,sources,preferences=self.capture(conn,owner,wearer,source_codec=self.source_codec)
            policy=AttributeEvidencePolicy.load()
            revisions=self.source_revisions(conn,owner,wearer)
            resources=resource_identities()
        finally:conn.rollback();conn.close()
        # All SQL-derived facts/revisions above belong to the same read snapshot.
        # Ranking and proof verification consume private/frozen captured values;
        # the writer still recaptures and verifies the full current scope locked.
        decision,candidate,score=first_selection(owner,wearer,intent,scope.usable_descriptions,preferences,policy,engine)
        value={'version':VERSION,'intent':intent.to_dict(),'owner_id':owner,'wearer':asdict(wearer),'settings':dict(SETTINGS),'policy':dict(POLICY),
            'attribute_policy':policy.snapshot(),'sources':sources,'preferences':[asdict(p) for p in preferences],'source_revisions':revisions,'eligibility':scope.eligibility.to_dict(),
            'resources':resources,'decision':decision_document(decision),'revision':''}
        value['revision']=digest(value)
        proof=LocalSelectionProof.with_source_codec(value) if self.source_codec is not None else LocalSelectionProof(encode(value))
        from app.application.recommendation.request_local_selection_verifier import verify
        verify(proof,owner,profile_id,candidate=candidate,score=score,text=intent.to_dict()['original_text'])
        from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest
        return RecommendationWrite(owner,'assistant',key,json.dumps(intent.to_dict()['mandatory_request']),candidate,
            json.dumps({'scoring_profile':score.profile_name,'internal_local_workflow':'1.0.0'}),intent.to_dict()['original_text'],score,
            wearer=wearer,captured_garment_sha256=snapshot_digest(scope.usable_rows),captured_preference_sha256=preference_digest(owner,preferences),
            eligibility=scope.eligibility,local_preference=LocalPreferenceWriteDraft(proof))

    def revalidate(self,conn,command):
        from app.domain.value_objects.request_local_selection import CODEC_VERSION
        from app.domain.value_objects.request_local_source_codec import VERSION as codec
        proof=command.local_preference.proof
        saved=proof.expanded_dict()
        scope,sources,preferences=self.capture(conn,command.user_id,command.wearer,source_codec=codec if proof.to_dict()['version']==CODEC_VERSION else None)
        if encode(sources)!=encode(saved['sources']) or encode([asdict(p) for p in preferences])!=encode(saved['preferences']) or scope.eligibility.to_dict()!=saved['eligibility'] or saved['resources']!=resource_identities() or saved['source_revisions']!=self.source_revisions(conn,command.user_id,command.wearer) or encode(saved['attribute_policy'])!=encode(AttributeEvidencePolicy.load().snapshot()):raise WardrobeChanged('Captured complete local ranking source/settings scope changed.')
        from app.application.recommendation.request_local_selection_verifier import _verify_locked
        return _verify_locked(conn,command)

    def submit(self,repository,owner,profile_id,intent,key,*,engine='reference'):
        prior=repository.find_local_submission(owner,profile_id,intent,key)
        if prior is not None:return prior,True
        return repository.persist_assistant(self.prepare(repository,owner,profile_id,intent,key,engine=engine))
