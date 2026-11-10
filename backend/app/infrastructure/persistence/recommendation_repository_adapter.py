"""Independent Phase 5A SQLite writer/read model; not wired to live routes."""
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import sqlite3
import uuid
from app.infrastructure.config import DATABASE_PATH
from app.infrastructure.persistence.postgresql_repository import utcnow
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.domain.value_objects.recommendation_persistence import RecommendationWrite, PersistenceConflict, WardrobeChanged
from app.application.wardrobe.profile_service import current_profile_id


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=lambda x: {"numerator": x.numerator, "denominator": x.denominator} if isinstance(x, Fraction) else asdict(x))


def request_fingerprint(operation, request_json, request_text, refinement_action=None,wearer_profile_id=None,*,attribute_conditions=None,attribute_mode=False,preference_profile=None,compatibility_profile=None):
    if compatibility_profile is not None:
        from app.domain.value_objects.palette_compatibility import PROFILE
        from app.domain.value_objects.attribute_conditions import AttributeConditions
        from app.application.recommendation.palette_compatibility_policy import digest
        if operation!='assistant' or wearer_profile_id is None or compatibility_profile!=PROFILE or preference_profile not in (None,'attribute_preference_decision_v2'):raise ValueError('Explicit captured C2 request required.')
        typed=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
        return digest({'version':6,'operation':operation,'wearer_profile_id':wearer_profile_id,'request_text':request_text,'typed_input':typed,'refinement_action':refinement_action.to_dict() if refinement_action else None,'preference_profile':preference_profile,'compatibility_profile':PROFILE})
    if preference_profile is not None:
        from app.domain.value_objects.attribute_preferences import PROFILE,encode as preference_encode
        from app.domain.value_objects.attribute_conditions import AttributeConditions
        if preference_profile!=PROFILE or operation!='assistant' or wearer_profile_id is None:raise ValueError('Explicit captured P2 request required.')
        typed=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
        return hashlib.sha256(preference_encode({'version':5,'operation':operation,'wearer_profile_id':wearer_profile_id,
            'request_text':request_text,'typed_input':typed,'refinement_action':refinement_action.to_dict() if refinement_action else None,'preference_profile':PROFILE})).hexdigest()
    if attribute_mode:
        from app.domain.value_objects.attribute_conditions import AttributeConditions,encode as attribute_encode
        if operation!='assistant' or wearer_profile_id is None:raise ValueError('Attribute intent requires an owned Assistant wearer.')
        typed=AttributeConditions.from_dict(attribute_conditions).to_dict() if attribute_conditions is not None else None
        return hashlib.sha256(attribute_encode({'version':4,'operation':operation,'wearer_profile_id':wearer_profile_id,
            'request_text':request_text,'typed_input':typed,'refinement_action':refinement_action.to_dict() if refinement_action else None})).hexdigest()
    if wearer_profile_id is not None:
        return hashlib.sha256(encode({'version':3,'operation':operation,'wearer_profile_id':wearer_profile_id,
            'request_text':request_text,'interpreted_request':json.loads(request_json),
            'refinement_intent':refinement_action.to_dict() if refinement_action is not None else None}).encode()).hexdigest()
    if refinement_action is not None:
        if operation!='assistant':raise ValueError('Refinement intent is Assistant-only.')
        return hashlib.sha256(encode({'version':2,'operation':operation,'request_text':request_text,
            'interpreted_request':json.loads(request_json),'refinement_intent':refinement_action.to_dict()}).encode()).hexdigest()
    return hashlib.sha256(encode({"version": 1, "operation": operation,
        "request": json.loads(request_json), "request_text": request_text}).encode()).hexdigest()


class SqliteRecommendationRepository:
    def __init__(self, database_path=DATABASE_PATH, checkpoint=None,*,description_policy=None,preference_policy=None,attribute_preference_query=None,compatibility_policy=None):
        self.database_path = database_path
        self.checkpoint = checkpoint or (lambda stage, conn: None)
        self.description_policy=description_policy
        self.preference_policy,self.attribute_preference_query=preference_policy,attribute_preference_query
        self.compatibility_policy=compatibility_policy

    def _connect(self):
        conn = sqlite3.connect(self.database_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def persist(self, command: RecommendationWrite):
        return self._persist(command)[0]

    def persist_homepage(self, command: RecommendationWrite):
        """Additive Homepage result/replay pair, resolved under the write lock."""
        if not isinstance(command, RecommendationWrite) or command.operation != "homepage":
            raise ValueError("Expected Homepage persistence command.")
        return self._persist(command)

    def _persist(self, command: RecommendationWrite):
        if not isinstance(command, RecommendationWrite):
            raise ValueError("Expected immutable persistence command.")
        provenance=json.loads(command.provenance_json)
        draft=command.refinement
        from app.domain.value_objects.garment_only_refinement import GarmentRefinementDraft
        garment_draft=type(draft) is GarmentRefinementDraft
        if 'garment_refinement' in provenance:raise ValueError('Only writer may finalize garment proof.')
        attribute=command.attribute
        preference=command.preference
        palette=command.compatibility
        compatibility_profile='recorded_palette_compatibility_v1' if palette is not None else None
        if 'palette_compatibility' in provenance:raise ValueError('Only the writer may attach C2 evidence.')
        if palette is not None:
            from app.application.recommendation.palette_compatibility_policy import decode
            from app.application.recommendation.palette_compatibility_verifier import validate_archive
            provenance['palette_compatibility']=decode(palette.payload)
            validate_archive(provenance['palette_compatibility'],command.score,command.user_id,command.wearer.profile_id,request_text=command.request_text,request=json.loads(command.request_json))
        preference_profile='attribute_preference_decision_v2' if preference is not None else None
        if 'attribute_preference' in provenance:raise ValueError('Only the writer may attach preference evidence.')
        if preference is not None:
            from app.application.recommendation.attribute_preference_verifier import validate as validate_preference
            from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
            provenance['attribute_preference']=preference.evidence.to_dict()
            conditions=AttributeIntent.from_dict(attribute.evidence.to_dict()['intent']).conditions if attribute is not None else None
            validate_preference(provenance['attribute_preference'],command.score,command.user_id,command.wearer.profile_id,
                conditions=conditions,request_text=command.request_text,exclusions=draft.plan.exclusions if draft else ())
        typed_input=None
        if 'attribute_selection' in provenance or 'attribute_base_scope_sha256' in provenance:raise ValueError('Only the writer may attach attribute evidence.')
        if attribute is not None:
            from app.application.recommendation.attribute_selection_verifier import validate_selection
            provenance['attribute_selection']=attribute.evidence.to_dict()
            provenance['attribute_base_scope_sha256']=attribute.compatibility_scope_sha256
            typed_input=provenance['attribute_selection']['intent']['typed_input']
            validate_selection(provenance['attribute_selection'],command.user_id,command.wearer.profile_id,attribute.compatibility_scope_sha256)
        if 'refinement' in provenance:raise ValueError('Only the writer may finalize refinement proof.')
        if 'context_relevance' in provenance:
            from app.application.recommendation.refinement_verifier import bounded_provenance
            bounded_provenance(provenance,draft=draft is not None)
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            validate_evidence(provenance['context_relevance'],command.score,command.candidate)
            payload=json.loads(command.request_json)
            if provenance['context_relevance'].get('version') in ('context-relevance-evidence-1.1.0','context-relevance-evidence-1.2.0','context-relevance-evidence-1.3.0','context-relevance-evidence-3.0.0') and provenance['context_relevance']['context_plan']['request']!=payload:
                raise ValueError('Stored context/facet proof does not match the request.')
            relative=provenance['context_relevance']
            if preference is not None:
                from app.domain.value_objects.attribute_preferences import digest as p2_digest
                if relative.get('preference_snapshot_sha256')!=provenance['attribute_preference']['snapshot']['revision'] or relative.get('preference_ledger_sha256')!=p2_digest(provenance['attribute_preference']['ledger']):raise ValueError('P2 ranking proof and captured ledger disagree.')
            scoped=('selection_scope_sha256' in relative and relative['selection_mode']=='best_evidenced_with_coverage_v1') if relative['version'] in ('context-relevance-evidence-2.0.0','context-relevance-evidence-3.0.0') else relative['version']=='context-relevance-evidence-1.2.0' or relative['version']=='context-relevance-evidence-1.3.0' and relative['selection_mode']=='best_evidenced_with_coverage_v1'
            if scoped!=(draft is not None):
                raise ValueError('Scoped proof requires a typed refinement draft.')
            if ('attribute_scope_sha256' in relative)!=(attribute is not None):raise ValueError('Attribute ranking proof requires typed attribute write evidence.')
            if attribute is not None and (relative['attribute_selection_sha256']!=attribute.evidence.sha256 or relative['attribute_scope_sha256']!=provenance['attribute_selection']['attribute_scope_sha256']):
                raise ValueError('Attribute ranking/evidence digest mismatch.')
            objective=provenance['context_relevance']['objective']
            if objective is not None:
                if (objective['situation']!=payload['context']['situation']['values'][0]
                    or objective['authority']=='explicit_user_style' and objective['target']!=payload['style']
                    or objective['authority']=='prototype_convention' and (payload['style'] is not None or payload['formality'] is not None)):
                    raise ValueError('Stored objective does not match the request.')
        # Fingerprint request identity, not nondeterministic selected result.
        fingerprint = request_fingerprint(command.operation, command.request_json, command.request_text,draft.action if draft else None,command.wearer.profile_id if command.wearer else None,
            attribute_conditions=typed_input,attribute_mode=attribute is not None,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
        profile_id = command.wearer.profile_id if command.wearer else current_profile_id()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'", (command.user_id,)).fetchone():
                raise ValueError("Active authenticated owner required.")
            prior = self._completed(conn,command.user_id,command.operation,command.submission_key,
                command.request_text,draft.action if draft else None,profile_id,attribute_conditions=typed_input,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
            if prior is not None:
                saved_fingerprint=conn.execute('SELECT fingerprint FROM recommendation_submissions WHERE user_id=? AND operation=? AND submission_key=?',(command.user_id,command.operation,command.submission_key)).fetchone()[0]
                if saved_fingerprint!=fingerprint:raise PersistenceConflict('Trusted command payload conflict.')
                conn.commit()
                return prior, True
            if command.wearer is not None:
                from app.application.wardrobe.profile_service import require_active_profile
                require_active_profile(conn,command.user_id,profile_id)
                if 'intended_wearer' in provenance:raise ValueError('Only the writer may create wearer evidence.')
                provenance['intended_wearer']=command.wearer.evidence()
            from app.application.wardrobe import wearer_category_service as categories
            eligibility_capture=categories.revalidate(conn,command.user_id,profile_id,command.eligibility)
            if command.eligibility is not None:
                from app.domain.value_objects.wearer_category_eligibility import KEY as ELIGIBILITY_KEY,validate_evidence
                if ELIGIBILITY_KEY in provenance:raise ValueError('Only the writer may attach eligibility evidence.')
                saved_eligibility=command.eligibility.to_dict()
                validate_evidence(saved_eligibility,command.user_id,profile_id,command.candidate.members)
                provenance[ELIGIBILITY_KEY]=saved_eligibility
            strict_query=eligibility_capture or SqliteConfirmedGarmentQuery(conn)
            if attribute is not None or preference is not None or palette is not None:
                from app.domain.value_objects.attribute_selection_evidence import description_digest
                if self.description_policy is None:raise ValueError('Prepared description policy required for a new attribute write.')
                try:collection=strict_query.get_confirmed_garment_descriptions(command.user_id,self.description_policy)
                except ValueError as exc:raise WardrobeChanged('Captured attribute collection is unavailable or over capacity.') from exc
                current={item.snapshot.garment_id:item.snapshot for item in collection}
                from app.application.recommendation.refinement_verifier import snapshot_digest
            else:
                current = {g.garment_id: g for g in strict_query.get_confirmed_available_garments(command.user_id)}
            if palette is not None:
                if self.compatibility_policy is None:raise ValueError('C2 write policy is disabled.')
                saved_palette=provenance['palette_compatibility']
                if saved_palette['collection_sha256']!=description_digest(collection) or saved_palette['strict_snapshot_sha256']!=snapshot_digest(current.values()):
                    if draft is not None:
                        from app.domain.value_objects.recommendation_refinement import RefinementError
                        raise RefinementError('RefinementScopeChanged','palette_sources_changed')
                    raise WardrobeChanged('Captured palette descriptions changed.')
                self.checkpoint('palette_revalidated',conn)
            if attribute is not None:
                if attribute.evidence.to_dict()['strict_snapshot_sha256']!=snapshot_digest(current.values()):
                    raise WardrobeChanged('Captured strict attribute snapshot changed.')
                if description_digest(collection)!=attribute.evidence.to_dict()['description_collection_sha256']:
                    if draft is not None:
                        from app.domain.value_objects.recommendation_refinement import RefinementError
                        raise RefinementError('RefinementScopeChanged','attribute_sources_changed')
                    raise WardrobeChanged('Captured garment descriptions changed.')
                from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
                from app.application.recommendation.attribute_selection_verifier import IndependentAttributeVerifier
                from app.domain.value_objects.attribute_conditions import encode as attribute_encode
                from app.domain.value_objects.attribute_selection_evidence import AttributeIntent
                saved=attribute.evidence.to_dict()
                policy=AttributeEvidencePolicy(attribute_encode(saved['policy_snapshot']))
                IndependentAttributeVerifier.prepare(AttributeIntent.from_dict(saved['intent']).conditions,collection,policy,subtype_sources=eligibility_capture.account_subtypes if eligibility_capture else ()).verify(command.candidate)
                if saved.get('subtype_collection_sha256') is not None:
                    from app.domain.value_objects.attribute_selection_evidence import subtype_digest
                    if eligibility_capture is None or saved['subtype_collection_sha256']!=subtype_digest(eligibility_capture.account_subtypes):raise WardrobeChanged('Captured subtype sources changed.')
                self.checkpoint('attribute_revalidated',conn)
            captured_preferences=None
            if preference is not None:
                from app.domain.value_objects.attribute_preferences import digest as preference_digest_full,PreferenceError
                from app.domain.value_objects.attribute_selection_evidence import description_digest
                from app.application.recommendation.attribute_preference_codec import legacy_digest
                if self.preference_policy is None or self.attribute_preference_query is None:raise PreferenceError('PreferenceUnavailable','P2 write policy is unavailable.')
                now_preferences=self.attribute_preference_query.capture_locked(conn,command.user_id,command.wearer)
                saved=preference.evidence.to_dict();scope=saved['scope']
                if preference_digest_full(now_preferences.to_dict())!=preference_digest_full(saved['snapshot']) or snapshot_digest(current.values())!=scope['garment_snapshot_sha256'] or description_digest(collection)!=scope['description_collection_sha256']:
                    from app.domain.value_objects.recommendation_refinement import RefinementError
                    raise RefinementError('RefinementScopeChanged','saved_preferences_or_descriptions_changed_start_fresh')
                if scope['request_sha256']!=__import__('app.application.recommendation.refinement_verifier',fromlist=['request_digest']).request_digest(command.request_text,json.loads(command.request_json),draft.plan.exclusions if draft else ()):
                    raise ValueError('Captured preference request mismatch.')
                captured_preferences=now_preferences.legacy_rows()
                self.checkpoint('preference_revalidated',conn)
            if command.wearer is not None and command.captured_garment_sha256 is not None:
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest
                from app.infrastructure.persistence.active_preference_query_adapter import read_active_preference_rows
                if captured_preferences is None:captured_preferences=read_active_preference_rows(conn,command.user_id,command.wearer)
                if snapshot_digest(current.values())!=command.captured_garment_sha256 or preference_digest(command.user_id,captured_preferences)!=command.captured_preference_sha256:
                    if draft is not None:
                        from app.domain.value_objects.recommendation_refinement import RefinementError
                        raise RefinementError('RefinementScopeChanged','ranking_scope_changed')
                    raise WardrobeChanged('Captured ranking facts changed.')
            if draft is not None:
                from app.domain.value_objects.recommendation_refinement import RefinementError
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest
                from app.infrastructure.persistence.active_preference_query_adapter import read_active_preference_rows
                if snapshot_digest(current.values())!=draft.garment_snapshot_sha256 or preference_digest(command.user_id,captured_preferences if captured_preferences is not None else read_active_preference_rows(conn,command.user_id,command.wearer))!=draft.preference_snapshot_sha256:
                    raise RefinementError('RefinementScopeChanged','ranking_scope_changed')
                if request_digest(command.request_text,json.loads(command.request_json),draft.plan.exclusions)!=draft.request_sha256:
                    raise ValueError('Draft request scope mismatch.')
                if draft.plan.ordinal:
                    from app.infrastructure.persistence.refinement_lineage_query import read_chain
                    from app.application.recommendation.refinement_lineage_service import continuation
                    if palette is not None:
                        from app.application.recommendation.palette_compatibility_verifier import read_chain,continuation
                    if garment_draft:
                        from app.infrastructure.persistence.garment_only_refinement_lineage_query import read_chain
                        from app.application.recommendation.garment_only_refinement_lineage_service import continuation
                    parent,records=read_chain(conn,command.user_id,draft.plan.parent_id)
                    actual,_=continuation(command.user_id,parent,records,command.request_text,command.submission_key,command.wearer,attribute_conditions=typed_input,**({'preference_profile':preference_profile} if preference_profile else {}),**({'compatibility_profile':compatibility_profile} if compatibility_profile else {}))
                    if actual!=draft.plan:raise RefinementError('RefinementScopeChanged','lineage_scope_changed')
                elif command.submission_key.startswith('refine:v1:'):
                    raise ValueError('Reserved step key cannot start a lineage.')
            for member in command.candidate.members:
                if current.get(member.garment.garment_id) != member.garment:
                    raise WardrobeChanged("Selected garment eligibility or snapshot changed.")
            self.checkpoint("revalidated", conn)
            identifier, now = str(uuid.uuid4()), utcnow()
            if garment_draft:
                from app.application.recommendation.garment_only_refinement_verifier import finalize
                from app.application.recommendation.refinement_selector import base_signature
                if base_signature(command.candidate) in draft.plan.seen:raise ValueError('Repeated garment base.')
                provenance['garment_refinement']=finalize(draft,identifier,command.score,command.candidate,provenance,command.user_id,profile_id)
                from app.application.recommendation.refinement_verifier import bounded_provenance
                provenance_text=bounded_provenance(provenance)
            elif draft is not None:
                from app.application.recommendation.refinement_verifier import finalize_supplement,validate_refinement,bounded_provenance
                from app.application.recommendation.refinement_selector import base_signature
                if base_signature(command.candidate) in draft.plan.seen:raise ValueError('Repeated base in trusted write command.')
                relative=provenance['context_relevance']
                if relative['selection_scope_sha256']!=draft.plan.selection_scope_sha256:raise ValueError('Ranking draft scope mismatch.')
                proof=finalize_supplement(draft.plan,identifier,draft.action,command.score,relative,
                    draft.garment_snapshot_sha256,draft.preference_snapshot_sha256,draft.request_sha256,command.wearer)
                validate_refinement(proof,relative,command.score,identifier,command.request_text,json.loads(command.request_json),command.candidate,user_id=command.user_id,wearer_profile_id=profile_id)
                provenance['refinement']=proof
                if command.wearer is not None and draft.plan.ordinal:
                    root_proof=json.loads(records[0]['provenance_json'])['refinement']
                    provenance['lineage_wearer_authority']='legacy_row_bridge' if root_proof['version']=='recommendation-refinement-evidence-1.0.0' else 'explicit_wearer_chain' 
                provenance_text=bounded_provenance(provenance)
            elif palette is not None:
                from app.application.recommendation.palette_compatibility_codec import bounded_provenance as bounded_c2
                provenance_text=bounded_c2(provenance)
            elif preference is not None:
                from app.application.recommendation.attribute_preference_codec import bounded_provenance as bounded_p2
                provenance_text=bounded_p2(provenance)
            elif attribute is not None:
                from app.domain.value_objects.attribute_selection_evidence import bounded_provenance as bounded_attribute
                provenance_text=bounded_attribute(provenance)
            else:provenance_text=encode(provenance)
            chat = str(uuid.uuid4()) if command.operation == "assistant" else None
            if chat:
                conn.execute("INSERT INTO nlp_chats (id,user_id,profile_id,request_text,interpreted_intent,extracted_entities_json,status,created_at,completed_at) VALUES (?,?,?,?,?,?,'completed',?,?)", (chat, command.user_id, profile_id, command.request_text, "outfit_recommendation", command.request_json, now, now))
                self.checkpoint("chat", conn)
            score = command.score
            values = [float(c.summary.value) if c.summary.value is not None else None for c in (score.request_match, score.compatibility, score.preference)] + [float(score.total)] if score else [None]*4
            conn.execute("INSERT INTO recommendations (id,user_id,profile_id,chat_id,recommendation_type,status,created_at,expires_at,request_match_score,compatibility_score,preference_score,total_score) VALUES (?,?,?,?,?, ?,?,NULL,?,?,?,?)", (identifier, command.user_id, profile_id, chat, command.operation, "available", now, *values))
            self.checkpoint("recommendation", conn)
            for member in command.candidate.members:
                g = member.garment
                conn.execute("INSERT INTO recommendation_items VALUES (?,?,?,?,?)", (identifier, g.garment_id, member.role, member.item_order, now))
                self.checkpoint("item", conn)
                conn.execute("INSERT INTO recommendation_item_snapshots VALUES (?,?,?)", (identifier, g.garment_id, encode({"name": g.name, "category": g.category, "preferred_media_id": g.preferred_media_id})))
                self.checkpoint("snapshot", conn)
            exact_score=encode(score) if score else None
            if score is not None and (palette is not None or score.profile_name in ('context_relevance_decision_v1','attribute_preference_decision_v2')):
                from app.application.recommendation.decision_score_codec import score_to_json
                exact_score=score_to_json(score)
            conn.execute("INSERT INTO recommendation_metadata VALUES (?,?,?)", (identifier, provenance_text, exact_score))
            self.checkpoint("metadata", conn)
            conn.execute("INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)", (command.user_id, command.operation, command.submission_key, fingerprint, identifier))
            self.checkpoint("submission", conn)
            result = self._read(conn, command.user_id, identifier,eligible=set(current) if draft is not None or attribute is not None else None)
            self.checkpoint("before_commit", conn)
            conn.commit()
            return result, False
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def persist_assistant(self, command: RecommendationWrite):
        if not isinstance(command,RecommendationWrite) or command.operation != "assistant":
            raise ValueError("Expected Assistant command.")
        return self._persist(command)

    def _completed(self,conn,user_id,operation,key,text=None,action=None,wearer_profile_id=None,header_profile_id=None,*,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
        if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
            raise ValueError('Active authenticated owner required.')
        row=conn.execute("SELECT s.fingerprint,r.id,r.profile_id,c.extracted_entities_json,m.provenance_json,m.score_json FROM recommendation_submissions s JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id LEFT JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=r.user_id LEFT JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE s.user_id=? AND s.operation=? AND s.submission_key=?",(user_id,operation,key)).fetchone()
        if row is None:return None
        for assertion in (wearer_profile_id,header_profile_id):
            if assertion is not None and assertion!=row['profile_id']:
                raise PersistenceConflict('Submission wearer conflict.')
        provenance=json.loads(row['provenance_json']) if row['provenance_json'] else {}
        stored_palette=provenance.get('palette_compatibility')
        from app.domain.value_objects.palette_compatibility import PROFILES
        stored_score=json.loads(row['score_json']) if row['score_json'] else {}
        if (stored_score.get('profile_name') in PROFILES.values())!=(stored_palette is not None):raise ValueError('Corrupt C2 score/archive identity.')
        if (stored_palette is not None)!=(compatibility_profile is not None):raise PersistenceConflict('Submission compatibility profile conflict.')
        stored_preference=provenance.get('attribute_preference')
        if (stored_preference is not None)!=(preference_profile is not None):raise PersistenceConflict('Submission preference profile conflict.')
        captured=provenance.get('intended_wearer')
        if captured is not None:
            from app.domain.value_objects.intended_wearer import validate_wearer_evidence
            validate_wearer_evidence(captured,user_id,row['profile_id'])
        stored_request=row['extracted_entities_json'] if operation=='assistant' else '{}'
        attribute=provenance.get('attribute_selection')
        if attribute is None and attribute_conditions is not None:raise PersistenceConflict('New attributes cannot reuse a legacy submission key.')
        expected=request_fingerprint(operation,stored_request,text,action,row['profile_id'] if captured else None,
            attribute_conditions=attribute_conditions,attribute_mode=attribute is not None,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
        if row['fingerprint']!=expected:
            raise PersistenceConflict('Submission payload conflict.')
        return self._read(conn,user_id,row['id'],account_history=True)

    def find_assistant_submission(self,user_id,submission_key,request_text,refinement_action=None,*,wearer_profile_id=None,header_profile_id=None,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
        conn=self._connect()
        try:
            conn.execute('BEGIN')
            asserted=wearer_profile_id if wearer_profile_id is not None else current_profile_id()
            return self._completed(conn,user_id,'assistant',submission_key,request_text,refinement_action,asserted,header_profile_id,attribute_conditions=attribute_conditions,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
        finally:
            conn.rollback();conn.close()

    def get(self, user_id, recommendation_id,*,profile_id=None,view='active'):
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            if view=='historical':
                from app.application.wardrobe.profile_service import historical_profile
                historical_profile(conn,user_id,profile_id)
            elif view not in ('active','legacy_unrecorded'):raise ValueError('Unsupported recommendation view.')
            record=self._read(conn,user_id,recommendation_id,account_history=view!='active')
            if view=='historical' and record['profile_id']!=profile_id or view=='legacy_unrecorded' and record['profile_id'] is not None:
                raise LookupError('Recommendation not found.')
            return record
        finally:
            conn.rollback()
            conn.close()

    def find_homepage_submission(self,user_id,submission_key,*,wearer_profile_id=None,header_profile_id=None):
        conn=self._connect()
        try:
            conn.execute('BEGIN')
            asserted=wearer_profile_id if wearer_profile_id is not None else current_profile_id()
            return self._completed(conn,user_id,'homepage',submission_key,wearer_profile_id=asserted,header_profile_id=header_profile_id)
        finally:
            conn.rollback();conn.close()

    def require_owned_parent(self,user_id,parent_id):
        conn=self._connect()
        try:
            row=conn.execute("SELECT 1 FROM recommendations WHERE id=? AND user_id=? AND recommendation_type='assistant'",(parent_id,user_id)).fetchone()
            if row is None:raise LookupError('Recommendation not found.')
        finally:conn.close()

    def refinement_continuation(self,user_id,parent_id,request_text,submission_key,wearer=None,*,attribute_conditions=None,preference_profile=None,compatibility_profile=None):
        from app.infrastructure.persistence.refinement_lineage_query import read_chain
        from app.application.recommendation.refinement_lineage_service import continuation
        conn=self._connect()
        try:
            conn.execute('BEGIN')
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
                raise LookupError('Recommendation not found.')
            peek=conn.execute('SELECT m.provenance_json FROM recommendations r JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE r.id=? AND r.user_id=?',(parent_id,user_id)).fetchone()
            if peek is not None and 'garment_refinement' in json.loads(peek[0]):
                from app.infrastructure.persistence.garment_only_refinement_lineage_query import read_chain
                from app.application.recommendation.garment_only_refinement_lineage_service import continuation
                parent,records=read_chain(conn,user_id,parent_id)
                return continuation(user_id,parent,records,request_text,submission_key,wearer,attribute_conditions=attribute_conditions,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
            if peek is not None and 'refinement' not in json.loads(peek[0]):
                from app.domain.value_objects.recommendation_refinement import RefinementError
                raise RefinementError('RefinementUnavailable','stored_root_has_no_continuation_contract')
            is_palette=peek is not None and 'palette_compatibility' in json.loads(peek[0])
            if is_palette or compatibility_profile is not None:
                from app.domain.value_objects.recommendation_refinement import RefinementError
                if not is_palette or compatibility_profile!='recorded_palette_compatibility_v1':raise RefinementError('IdempotencyConflict','compatibility_profile_mismatch_start_fresh')
                from app.application.recommendation.palette_compatibility_verifier import read_chain,continuation
                parent,records=read_chain(conn,user_id,parent_id)
                return continuation(user_id,parent,records,request_text,submission_key,wearer,attribute_conditions=attribute_conditions,preference_profile=preference_profile,compatibility_profile=compatibility_profile)
            parent,records=read_chain(conn,user_id,parent_id)
            return continuation(user_id,parent,records,request_text,submission_key,wearer,attribute_conditions=attribute_conditions,preference_profile=preference_profile)
        finally:
            conn.rollback();conn.close()

    def _read(self, conn, user_id, identifier,eligible=None,*,account_history=False):
        profile_id=current_profile_id()
        sql="SELECT r.*,c.request_text FROM recommendations r LEFT JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=r.user_id WHERE r.id=? AND r.user_id=?"
        params=[identifier,user_id]
        if profile_id and not account_history: sql+=" AND r.profile_id=?";params.append(profile_id)
        row = conn.execute(sql,params).fetchone()
        if not row:
            raise LookupError("Recommendation not found.")
        result = dict(row)
        profile=conn.execute('SELECT name,status FROM wardrobe_profiles WHERE id=? AND user_id=?',(result.get('profile_id'),user_id)).fetchone()
        result['wearer_archived']=bool(profile and profile['status']!='active')
        result['wearer_association']={'profile_id':result.get('profile_id'),'name':profile['name'] if profile else None,'authority':'stored_association_only'}
        result['wearer_intent_state']='legacy_not_recorded' 
        if eligible is None:eligible = {g.garment_id for g in SqliteConfirmedGarmentQuery(conn).get_confirmed_available_garments(user_id)}
        items = []; captured_identity_items=[]
        for item in conn.execute("SELECT i.*,s.display_json FROM recommendation_items i LEFT JOIN recommendation_item_snapshots s USING(recommendation_id,garment_id) WHERE i.recommendation_id=? ORDER BY i.item_order", (identifier,)):
            value = {k: item[k] for k in ("garment_id", "garment_role", "item_order")}
            value.update(json.loads(item["display_json"]) if item["display_json"] else {"name": None, "category": None, "preferred_media_id": None})
            value.update(snapshot_available=item["display_json"] is not None, currently_eligible=item["garment_id"] in eligible)
            captured_identity_items.append(dict(value))
            # Do not expose media for unavailable/inaccessible references.
            if not value["currently_eligible"]:
                value["preferred_media_id"] = None
            items.append(value)
        metadata = conn.execute("SELECT * FROM recommendation_metadata WHERE recommendation_id=?", (identifier,)).fetchone()
        result.update(items=items, provenance=json.loads(metadata["provenance_json"]) if metadata else None,
                      score_metadata=json.loads(metadata["score_json"]) if metadata and metadata["score_json"] else None)
        from app.domain.value_objects.wearer_category_eligibility import KEY as ELIGIBILITY_KEY,validate_evidence
        if isinstance(result['provenance'],dict) and ELIGIBILITY_KEY in result['provenance']:
            validate_evidence(result['provenance'][ELIGIBILITY_KEY],user_id,result['profile_id'],captured_identity_items)
        from app.domain.value_objects.palette_compatibility import PROFILES
        palette=result.get('provenance',{}).get('palette_compatibility') if isinstance(result.get('provenance'),dict) else None
        is_c2=isinstance(result.get('score_metadata'),dict) and result['score_metadata'].get('profile_name') in PROFILES.values()
        if is_c2!=(palette is not None):raise ValueError('C2 historical score/archive mismatch.')
        if palette is not None:
            from app.application.recommendation.decision_score_codec import score_from_json
            from app.application.recommendation.palette_compatibility_verifier import validate_archive
            saved_score=score_from_json(metadata['score_json'])
            validate_archive(palette,saved_score,user_id,result['profile_id'],items=items,request_text=result['request_text'])
            p2=saved_score.profile_name in (PROFILES[True,False],PROFILES[True,True])
            if p2!=('attribute_preference' in result['provenance']):raise ValueError('C2 historical preference mode mismatch.')
        if isinstance(result.get('provenance'),dict) and 'intended_wearer' in result['provenance']:
            from app.domain.value_objects.intended_wearer import validate_wearer_evidence
            validate_wearer_evidence(result['provenance']['intended_wearer'],user_id,result['profile_id'])
            result['intended_wearer']=result['provenance']['intended_wearer']
            result['wearer_intent_state']='captured'
        if isinstance(result.get('provenance'),dict) and 'attribute_selection' in result['provenance']:
            from app.application.recommendation.attribute_selection_verifier import validate_selection
            from app.domain.value_objects.attribute_selection_evidence import bounded_provenance as bounded_attribute,require_hash
            provenance=result['provenance'];base=provenance.get('attribute_base_scope_sha256')
            require_hash(base)
            from app.application.recommendation.refinement_verifier import bounded_provenance
            bounded_provenance(provenance)
            evidence=validate_selection(provenance['attribute_selection'],user_id,result['profile_id'],base,items)
            if provenance.get('context_relevance') is not None:
                relative=provenance['context_relevance']
                if relative.get('version') not in ('context-relevance-evidence-1.3.0','context-relevance-evidence-2.0.0','context-relevance-evidence-3.0.0') or relative.get('attribute_selection_sha256')!=evidence.sha256 or relative.get('attribute_scope_sha256')!=evidence.to_dict()['attribute_scope_sha256']:
                    raise ValueError('Stored ranking/attribute evidence mismatch.')
            elif 'refinement' in provenance:raise ValueError('Attribute refinement requires ranking evidence.')
        if isinstance(result.get('provenance'),dict) and 'attribute_preference' in result['provenance']:
            from app.application.recommendation.attribute_preference_verifier import validate as validate_preference,conditions_from
            from app.application.recommendation.decision_score_codec import score_from_json
            saved=result['provenance'];exclusions=saved.get('garment_refinement',saved.get('refinement',{})).get('excluded_categories',())
            validate_preference(saved['attribute_preference'],score_from_json(metadata['score_json']),user_id,result['profile_id'],
                conditions=conditions_from(saved),items=items,request_text=result['request_text'],exclusions=exclusions)
        elif result.get('score_metadata',{} ) and result['score_metadata'].get('profile_name')=='attribute_preference_decision_v2':raise ValueError('Missing P2 preference archive.')
        if isinstance(result.get('provenance'),dict) and result['provenance'].get('context_relevance') is not None:
            from app.application.recommendation.decision_score_codec import score_from_json
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            validate_evidence(result['provenance']['context_relevance'],score_from_json(metadata['score_json']))
            from app.application.recommendation.refinement_verifier import bounded_provenance
            bounded_provenance(result['provenance'])
            relative=result['provenance']['context_relevance']
            scoped=('selection_scope_sha256' in relative and relative['selection_mode']=='best_evidenced_with_coverage_v1') if relative['version'] in ('context-relevance-evidence-2.0.0','context-relevance-evidence-3.0.0') else relative['version']=='context-relevance-evidence-1.2.0' or relative['version']=='context-relevance-evidence-1.3.0' and relative['selection_mode']=='best_evidenced_with_coverage_v1'
            if relative['version']=='context-relevance-evidence-1.3.0' and 'attribute_selection' not in result['provenance']:
                raise ValueError('Missing archived attribute selection evidence.')
            if scoped!=('refinement' in result['provenance']):raise ValueError('Missing archived refinement supplement.')
            if scoped:
                from app.infrastructure.persistence.refinement_lineage_query import read_chain
                from app.application.recommendation.refinement_lineage_service import validate_chain
                if palette is not None:
                    from app.application.recommendation.palette_compatibility_verifier import read_chain,validate_chain
                _,chain=read_chain(conn,user_id,identifier)
                validate_chain(user_id,chain)
        if isinstance(result.get('provenance'),dict) and 'garment_refinement' in result['provenance']:
            from app.infrastructure.persistence.garment_only_refinement_lineage_query import read_chain
            from app.application.recommendation.garment_only_refinement_lineage_service import validate_chain
            _,chain=read_chain(conn,user_id,identifier);validate_chain(user_id,chain)
        return result
