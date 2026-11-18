"""Server-owned opt-in bridge; no caller-selected policies, winners or proofs."""
import json,re
from app.domain.value_objects.recommendation_persistence import PersistenceConflict,WardrobeChanged
from app.domain.value_objects.request_local_preference import RequestLocalPreferenceIntent,IsolatedPreferenceError
from app.domain.value_objects.attribute_conditions import encode,AttributeRequestError
from app.application.nlp.conversational_context_interpreter import matching,outside_literals

ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_LOCAL_PREFERENCE_PROFILE'
PROFILE='request_local_bounded_preference_v1'


def has_soft_language(text):
    return bool(re.search(r'\b(?:prefer|preferably)\b|\bwould\s+be\s+nice\b',outside_literals(matching(text))))


def capability(service):
    local=getattr(service,'local_preferences',None)
    return {'version':'request-local-preference-capabilities-1.0.0','enabled':local is not None,
        'profile':PROFILE,'grammar_version':'conversational-attribute-grammar-1.7.0' if local else None,
        'grammar_sha256':local.grammar if local else None,'preference':'P1','compatibility':'C1',
        'contextual':False,'roles':['upper','lower'],'attributes':['category','primary_colour'],
        'continuation':False,'typed_supplement':False}


def completed_receipt(repository,owner,body,header_profile):
    """Read-only v7 replay, including when activation/parser is now disabled.

    Never derive a new intent from text or reuse a key across request modes.
    The existing fingerprint and complete historical reader remain authoritative.
    """
    if body.submission_key is None:return None
    conn=repository._connect()
    try:
        conn.execute('BEGIN')
        row=conn.execute("SELECT r.profile_id,m.provenance_json FROM recommendation_submissions s JOIN recommendations r ON r.id=s.recommendation_id AND r.user_id=s.user_id JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE s.user_id=? AND s.operation='assistant' AND s.submission_key=?",(owner,body.submission_key)).fetchone()
        if row is None:return None
        provenance=json.loads(row['provenance_json']) if row['provenance_json'] else {}
        saved=provenance.get('request_local_preference')
        if saved is None:return None
        if body.refinement is not None or body.attribute_conditions is not None or body.preference_profile is not None or body.compatibility_profile is not None:raise PersistenceConflict('Local receipt mode conflict.')
        intent=RequestLocalPreferenceIntent(encode(saved['intent']))
        if intent.to_dict()['original_text']!=body.request_text or any(p is not None and p!=row['profile_id'] for p in (body.wearer_profile_id,header_profile)):raise PersistenceConflict('Local receipt text/wearer conflict.')
        return repository._completed(conn,owner,'assistant',body.submission_key,wearer_profile_id=row['profile_id'],header_profile_id=header_profile,local_request=intent)
    finally:conn.rollback();conn.close()


def is_local_parent(repository,owner,parent):
    conn=repository._connect()
    try:
        row=conn.execute('SELECT m.provenance_json FROM recommendations r JOIN recommendation_metadata m ON m.recommendation_id=r.id WHERE r.id=? AND r.user_id=?',(parent,owner)).fetchone()
        return row is not None and 'request_local_preference' in (json.loads(row[0]) if row[0] else {})
    finally:conn.close()


class LocalPreferenceAssistant:
    def __init__(self,repository,workflow,engine):
        from app.application.nlp.request_local_soft_parser import IsolatedSoftPreferenceParser,isolated_fingerprint,GRAMMAR_VERSION,REGISTRY
        self.parser=IsolatedSoftPreferenceParser();self.grammar=isolated_fingerprint()
        if self.grammar not in REGISTRY[GRAMMAR_VERSION]:raise ValueError('Unregistered soft parser source.')
        self.repository,self.workflow,self.engine=repository,workflow,engine

    def recommend(self,owner,body,wearer):
        from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
        from app.application.recommendation.request_local_selection_engine import LocalSelectionUnavailable
        if body.refinement is not None:return {'status':'SoftContinuationUnavailable','complete':False}
        if body.attribute_conditions is not None:return {'status':'SoftProfileUnavailable','complete':False,'reason':'Use the approved textual hard requirement and one wish; typed supplements cannot be dropped.'}
        if body.submission_key is None:return {'status':'InvalidInput','complete':False}
        try:
            parsed=self.parser.interpret(body.request_text,preference_profile=body.preference_profile,compatibility_profile=body.compatibility_profile)
            if parsed.local_intent is None:return {'status':'UnsupportedSoftPreference','complete':False}
            saved,replayed=self.workflow.submit(self.repository,owner,wearer.profile_id,parsed.local_intent,body.submission_key,engine=self.engine)
            return OutfitAssistantService._success(saved,replayed,{})
        except IsolatedPreferenceError as error:
            result={'status':error.code,'complete':False,'reason':error.reason}
            # Guidance only: never rewrite text or issue a different intent.
            if error.code=='UnsupportedSoftPreference' and re.match(r'^\s*id\s+prefer\b',matching(body.request_text)):
                result['context_reason']='soft_preference_apostrophe_required'
            return result
        except LocalSelectionUnavailable as error:
            resolution=parsed.local_intent.to_dict()['optional']['resolution']['state']
            result={'status':error.status,'complete':True,'mandatory':error.completion.__dict__,
                'optional_resolution':resolution}
            if error.status=='InsufficientEvidence':
                result['context_reason']='hard_evidence_unknown_conflicting_preference' if resolution=='ContradictedByHard' else 'required_garment_description_unknown'
            return result
        except AttributeRequestError as error:return {'status':error.status,'complete':False,'reason':error.reason}
        except PersistenceConflict:return {'status':'IdempotencyConflict','complete':False}
        except WardrobeChanged:return {'status':'WardrobeChanged','complete':False}
        except __import__('fastapi').HTTPException:raise
        except Exception as error:
            if isinstance(error,ValueError) and any(x in str(error).lower() for x in ('byte budget','encoding budget','encoding_budget','unbounded local source','proof exceeds','oversized')):
                return {'status':'EncodingLimitExceeded','complete':False}
            from app.application.recommendation.failure_diagnostics import log_failure
            log_failure('assistant','local_preference','PersistenceFailure',error)
            return {'status':'PersistenceFailure','complete':False}
