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


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=lambda x: {"numerator": x.numerator, "denominator": x.denominator} if isinstance(x, Fraction) else asdict(x))


def request_fingerprint(operation, request_json, request_text, refinement_action=None):
    if refinement_action is not None:
        if operation!='assistant':raise ValueError('Refinement intent is Assistant-only.')
        return hashlib.sha256(encode({'version':2,'operation':operation,'request_text':request_text,
            'interpreted_request':json.loads(request_json),'refinement_intent':refinement_action.to_dict()}).encode()).hexdigest()
    return hashlib.sha256(encode({"version": 1, "operation": operation,
        "request": json.loads(request_json), "request_text": request_text}).encode()).hexdigest()


class SqliteRecommendationRepository:
    def __init__(self, database_path=DATABASE_PATH, checkpoint=None):
        self.database_path = database_path
        self.checkpoint = checkpoint or (lambda stage, conn: None)

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
        if 'refinement' in provenance:raise ValueError('Only the writer may finalize refinement proof.')
        if 'context_relevance' in provenance:
            from app.application.recommendation.refinement_verifier import bounded_provenance
            bounded_provenance(provenance,draft=draft is not None)
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            validate_evidence(provenance['context_relevance'],command.score,command.candidate)
            payload=json.loads(command.request_json)
            if provenance['context_relevance'].get('version') in ('context-relevance-evidence-1.1.0','context-relevance-evidence-1.2.0') and provenance['context_relevance']['context_plan']['request']!=payload:
                raise ValueError('Stored context/facet proof does not match the request.')
            if (provenance['context_relevance']['version']=='context-relevance-evidence-1.2.0')!=(draft is not None):
                raise ValueError('Scoped proof requires a typed refinement draft.')
            objective=provenance['context_relevance']['objective']
            if objective is not None:
                if (objective['situation']!=payload['context']['situation']['values'][0]
                    or objective['authority']=='explicit_user_style' and objective['target']!=payload['style']
                    or objective['authority']=='prototype_convention' and (payload['style'] is not None or payload['formality'] is not None)):
                    raise ValueError('Stored objective does not match the request.')
        # Fingerprint request identity, not nondeterministic selected result.
        fingerprint = request_fingerprint(command.operation, command.request_json, command.request_text,draft.action if draft else None)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'", (command.user_id,)).fetchone():
                raise ValueError("Active authenticated owner required.")
            prior = conn.execute("SELECT fingerprint,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation=? AND submission_key=?",
                                 (command.user_id, command.operation, command.submission_key)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise PersistenceConflict("Submission key payload conflict.")
                result = self._read(conn, command.user_id, prior["recommendation_id"])
                conn.commit()
                return result, True
            current = {g.garment_id: g for g in SqliteConfirmedGarmentQuery(conn).get_confirmed_available_garments(command.user_id)}
            if draft is not None:
                from app.domain.value_objects.recommendation_refinement import RefinementError
                from app.application.recommendation.refinement_verifier import snapshot_digest,preference_digest,request_digest
                from app.infrastructure.persistence.active_preference_query_adapter import read_active_preference_rows
                if snapshot_digest(current.values())!=draft.garment_snapshot_sha256 or preference_digest(command.user_id,read_active_preference_rows(conn,command.user_id))!=draft.preference_snapshot_sha256:
                    raise RefinementError('RefinementScopeChanged','ranking_scope_changed')
                if request_digest(command.request_text,json.loads(command.request_json),draft.plan.exclusions)!=draft.request_sha256:
                    raise ValueError('Draft request scope mismatch.')
                if draft.plan.ordinal:
                    from app.infrastructure.persistence.refinement_lineage_query import read_chain
                    from app.application.recommendation.refinement_lineage_service import continuation
                    parent,records=read_chain(conn,command.user_id,draft.plan.parent_id)
                    actual,_=continuation(command.user_id,parent,records,command.request_text,command.submission_key)
                    if actual!=draft.plan:raise RefinementError('RefinementScopeChanged','lineage_scope_changed')
                elif command.submission_key.startswith('refine:v1:'):
                    raise ValueError('Reserved step key cannot start a lineage.')
            for member in command.candidate.members:
                if current.get(member.garment.garment_id) != member.garment:
                    raise WardrobeChanged("Selected garment eligibility or snapshot changed.")
            self.checkpoint("revalidated", conn)
            identifier, now = str(uuid.uuid4()), utcnow()
            if draft is not None:
                from app.application.recommendation.refinement_verifier import finalize_supplement,validate_refinement,bounded_provenance
                from app.application.recommendation.refinement_selector import base_signature
                if base_signature(command.candidate) in draft.plan.seen:raise ValueError('Repeated base in trusted write command.')
                relative=provenance['context_relevance']
                if relative['selection_scope_sha256']!=draft.plan.selection_scope_sha256:raise ValueError('Ranking draft scope mismatch.')
                proof=finalize_supplement(draft.plan,identifier,draft.action,command.score,relative,
                    draft.garment_snapshot_sha256,draft.preference_snapshot_sha256,draft.request_sha256)
                validate_refinement(proof,relative,command.score,identifier,command.request_text,json.loads(command.request_json),command.candidate)
                provenance['refinement']=proof
                provenance_text=bounded_provenance(provenance)
            else:provenance_text=command.provenance_json
            chat = str(uuid.uuid4()) if command.operation == "assistant" else None
            if chat:
                conn.execute("INSERT INTO nlp_chats VALUES (?,?,?,?,?,'completed',?,?)", (chat, command.user_id, command.request_text, "outfit_recommendation", command.request_json, now, now))
                self.checkpoint("chat", conn)
            score = command.score
            values = [float(c.summary.value) if c.summary.value is not None else None for c in (score.request_match, score.compatibility, score.preference)] + [float(score.total)] if score else [None]*4
            conn.execute("INSERT INTO recommendations VALUES (?,?,?,?,? ,?,NULL,?,?,?,?)", (identifier, command.user_id, chat, command.operation, "available", now, *values))
            self.checkpoint("recommendation", conn)
            for member in command.candidate.members:
                g = member.garment
                conn.execute("INSERT INTO recommendation_items VALUES (?,?,?,?,?)", (identifier, g.garment_id, member.role, member.item_order, now))
                self.checkpoint("item", conn)
                conn.execute("INSERT INTO recommendation_item_snapshots VALUES (?,?,?)", (identifier, g.garment_id, encode({"name": g.name, "category": g.category, "preferred_media_id": g.preferred_media_id})))
                self.checkpoint("snapshot", conn)
            exact_score=encode(score) if score else None
            if score is not None and score.profile_name=='context_relevance_decision_v1':
                from app.application.recommendation.decision_score_codec import score_to_json
                exact_score=score_to_json(score)
            conn.execute("INSERT INTO recommendation_metadata VALUES (?,?,?)", (identifier, provenance_text, exact_score))
            self.checkpoint("metadata", conn)
            conn.execute("INSERT INTO recommendation_submissions VALUES (?,?,?,?,?)", (command.user_id, command.operation, command.submission_key, fingerprint, identifier))
            self.checkpoint("submission", conn)
            result = self._read(conn, command.user_id, identifier,eligible=set(current) if draft is not None else None)
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

    def find_assistant_submission(self,user_id,submission_key,request_text,refinement_action=None):
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
                raise ValueError("Active authenticated owner required.")
            row = conn.execute("SELECT s.fingerprint,s.recommendation_id,c.extracted_entities_json FROM recommendation_submissions s JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=s.user_id WHERE s.user_id=? AND s.operation='assistant' AND s.submission_key=?",(user_id,submission_key)).fetchone()
            if row is None:
                return None
            if row["fingerprint"] != request_fingerprint("assistant",row["extracted_entities_json"],request_text,refinement_action):
                raise PersistenceConflict("Assistant submission payload conflict.")
            return self._read(conn,user_id,row["recommendation_id"])
        finally:
            conn.rollback()
            conn.close()

    def get(self, user_id, recommendation_id):
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            return self._read(conn, user_id, recommendation_id)
        finally:
            conn.rollback()
            conn.close()

    def find_homepage_submission(self, user_id, submission_key):
        """Read-only retry recovery before generation, including stale results."""
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'", (user_id,)).fetchone():
                raise ValueError("Active authenticated owner required.")
            prior = conn.execute("SELECT fingerprint,recommendation_id FROM recommendation_submissions WHERE user_id=? AND operation='homepage' AND submission_key=?", (user_id, submission_key)).fetchone()
            if prior is None:
                return None
            if prior["fingerprint"] != request_fingerprint("homepage", "{}", None):
                raise PersistenceConflict("Homepage submission payload conflict.")
            return self._read(conn, user_id, prior["recommendation_id"])
        finally:
            conn.rollback()
            conn.close()

    def refinement_continuation(self,user_id,parent_id,request_text,submission_key):
        from app.infrastructure.persistence.refinement_lineage_query import read_chain
        from app.application.recommendation.refinement_lineage_service import continuation
        conn=self._connect()
        try:
            conn.execute('BEGIN')
            if not conn.execute("SELECT 1 FROM users WHERE id=? AND account_status='active'",(user_id,)).fetchone():
                raise LookupError('Recommendation not found.')
            parent,records=read_chain(conn,user_id,parent_id)
            return continuation(user_id,parent,records,request_text,submission_key)
        finally:
            conn.rollback();conn.close()

    def _read(self, conn, user_id, identifier,eligible=None):
        row = conn.execute("SELECT r.*,c.request_text FROM recommendations r LEFT JOIN nlp_chats c ON c.id=r.chat_id AND c.user_id=r.user_id WHERE r.id=? AND r.user_id=?", (identifier, user_id)).fetchone()
        if not row:
            raise LookupError("Recommendation not found.")
        result = dict(row)
        if eligible is None:eligible = {g.garment_id for g in SqliteConfirmedGarmentQuery(conn).get_confirmed_available_garments(user_id)}
        items = []
        for item in conn.execute("SELECT i.*,s.display_json FROM recommendation_items i LEFT JOIN recommendation_item_snapshots s USING(recommendation_id,garment_id) WHERE i.recommendation_id=? ORDER BY i.item_order", (identifier,)):
            value = {k: item[k] for k in ("garment_id", "garment_role", "item_order")}
            value.update(json.loads(item["display_json"]) if item["display_json"] else {"name": None, "category": None, "preferred_media_id": None})
            value.update(snapshot_available=item["display_json"] is not None, currently_eligible=item["garment_id"] in eligible)
            # Do not expose media for unavailable/inaccessible references.
            if not value["currently_eligible"]:
                value["preferred_media_id"] = None
            items.append(value)
        metadata = conn.execute("SELECT * FROM recommendation_metadata WHERE recommendation_id=?", (identifier,)).fetchone()
        result.update(items=items, provenance=json.loads(metadata["provenance_json"]) if metadata else None,
                      score_metadata=json.loads(metadata["score_json"]) if metadata and metadata["score_json"] else None)
        if isinstance(result.get('provenance'),dict) and result['provenance'].get('context_relevance') is not None:
            from app.application.recommendation.decision_score_codec import score_from_json
            from app.application.recommendation.context_relevance_verifier import validate_evidence
            validate_evidence(result['provenance']['context_relevance'],score_from_json(metadata['score_json']))
            from app.application.recommendation.refinement_verifier import bounded_provenance
            bounded_provenance(result['provenance'])
            scoped=result['provenance']['context_relevance']['version']=='context-relevance-evidence-1.2.0'
            if scoped!=('refinement' in result['provenance']):raise ValueError('Missing archived refinement supplement.')
            if scoped:
                from app.infrastructure.persistence.refinement_lineage_query import read_chain
                from app.application.recommendation.refinement_lineage_service import validate_chain
                _,chain=read_chain(conn,user_id,identifier)
                validate_chain(user_id,chain)
        return result
