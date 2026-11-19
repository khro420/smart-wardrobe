"""Additive mixed proof namespace; complete locked original and synthetic reconstruction."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
from dataclasses import asdict
import json,hashlib,hmac,sqlite3,uuid
from app.development.main_fixture.store import Store as BaseStore,FixtureError,MAX_PROOF
from .core import VERSION,ORIGIN,encoded,digest,select,GRAMMAR_SHA
PROFILE='phase2nd_mixed_v1'
SCHEMA="""CREATE TABLE IF NOT EXISTS phase2nd_mixed_proofs (
 id TEXT PRIMARY KEY,owner_id TEXT NOT NULL REFERENCES users(id),wearer_id TEXT NOT NULL REFERENCES wardrobe_profiles(id),
 receipt TEXT NOT NULL,fingerprint TEXT NOT NULL,parent_id TEXT REFERENCES phase2nd_mixed_proofs(id),ordinal INTEGER NOT NULL,
 proof_json TEXT NOT NULL,proof_sha256 TEXT NOT NULL,signature TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(owner_id,receipt))"""

class Store(BaseStore):
    def require_owner(self,c,owner,wearer=None):
        from .personalization import PROFILE as PERSONAL
        if self.config.get('personalization_profile')!=PERSONAL:return super().require_owner(c,owner,wearer)
        super().require_owner(c,owner)
        if wearer is not None:
            expected=self.catalog['profiles'].get(wearer)
            p=c.execute("select * from wardrobe_profiles where id=? and user_id=? and status='active'",(wearer,owner)).fetchone()
            d=c.execute('select * from wardrobe_profile_details_v1 where profile_id=?',(wearer,)).fetchone()
            if not expected or not p or dict(p)!=expected['row'] or not d or dict(d)!=expected['details']:raise FixtureError('ChangedFixtureWearer')
            # Identity stays pinned; current preferences are captured and
            # revalidated in the source scope instead of treated as identity.

    def selection_version(self,raw):
        version=self.interpretation_version(raw)
        from .fashion_contract import PROFILE as FASHION,versions
        chosen=versions()[version] if self.config.get('fashion_profile')==FASHION else version
        from .personalization import PROFILE as PERSONAL,versions as personal_versions
        return personal_versions()[chosen] if self.config.get('personalization_profile')==PERSONAL and chosen in personal_versions() else chosen

    def interpretation_version(self,raw):
        if self.config.get('semantic_error'):raise FixtureError(self.config['semantic_error'],422)
        from .context_contract import PROFILE as CONTEXT_PROFILE,VERSION as CONTEXT_VERSION
        if self.config.get('context_profile')==CONTEXT_PROFILE:
            from .semantic_frame_contract import PROFILE as FRAME_PROFILE,VERSION as FRAME_VERSION
            from .semantic_reliability_contract import PROFILE as SCOPED_PROFILE
            from .semantic_structured_contract import PROFILE as TYPED_PROFILE,VERSION as TYPED_VERSION
            typed=self.config.get('semantic_frame_profile')==TYPED_PROFILE
            scoped=self.config.get('semantic_frame_profile')==SCOPED_PROFILE
            if self.config.get('semantic_frame_profile') in (FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE):
                try:
                    if typed:
                        from .semantic_structured import identity as frame_identity
                    elif scoped:
                        from .semantic_reliability import identity as frame_identity
                    else:
                        from .semantic_constraints import identity as frame_identity
                    frame_identity()
                except (ImportError,OSError,ValueError) as error:
                    raise FixtureError('SemanticInterpreterUnavailable',503) from error
                from .semantic_reliability_contract import VERSION as SCOPED_VERSION
                from .semantic_constraint_contract import VERSION as NOUN_VERSION
                return TYPED_VERSION if typed else SCOPED_VERSION if scoped else NOUN_VERSION
            from .interview_default_contract import PROFILE as DEFAULT_PROFILE,VERSION as DEFAULT_VERSION
            if self.config.get('interview_default_profile')==DEFAULT_PROFILE:
                from .interview_default import contextual as interview_contextual
                if interview_contextual(raw):return DEFAULT_VERSION
            from .context_language_contract import PROFILE as LANGUAGE_PROFILE,VERSION as LANGUAGE_VERSION
            if self.config.get('language_profile')==LANGUAGE_PROFILE:
                from .context_language import contextual as language_contextual
                if language_contextual(raw):return LANGUAGE_VERSION
            from .context_intent import contextual
            if contextual(raw):return CONTEXT_VERSION
        return VERSION

    @staticmethod
    def select_version(version,*args,**kwargs):
        from .personalization import base_version as personal_base
        original=personal_base(version)
        if original is not None:
            if kwargs.get('_personalization') is None:raise FixtureError('MissingPersonalizationSnapshot')
            return Store.select_version(original,*args,**kwargs)
        from .fashion_contract import base_version
        original=base_version(version)
        if original is not None:
            from .fashion import FashionFacts
            return Store.select_version(original,*args,**kwargs,_fashion=FashionFacts)
        if version==VERSION:return select(*args,**kwargs)
        from .semantic_frame_contract import VERSION as FRAME_VERSION
        from .semantic_constraint_contract import VERSION as NOUN_VERSION
        from .semantic_reliability_contract import VERSION as SCOPED_VERSION
        from .semantic_structured_contract import VERSION as TYPED_VERSION
        if version in (FRAME_VERSION,NOUN_VERSION,SCOPED_VERSION,TYPED_VERSION):
            if version==FRAME_VERSION:
                from .semantic_frames import document as frame_document
            elif version==NOUN_VERSION:
                from .semantic_constraints import document as frame_document
            elif version==SCOPED_VERSION:
                from .semantic_reliability import document as frame_document
            else:
                from .semantic_structured import document as frame_document
            from .context_selection import select as contextual_select
            proposal=kwargs.pop('_semantic_proposal',None)
            if proposal is None:raise FixtureError('MissingSemanticProposal')
            interpret=lambda raw:frame_document(raw,proposal)
            return (select if proposal['slots']['context']=='none' else contextual_select)(*args,**kwargs,_interpret=interpret)
        from .interview_default_contract import VERSION as DEFAULT_VERSION
        if version==DEFAULT_VERSION:
            from .interview_default import document as default_document
            from .context_selection import select as contextual_select
            return contextual_select(*args,**kwargs,_interpret=default_document)
        from .context_language_contract import VERSION as LANGUAGE_VERSION
        if version==LANGUAGE_VERSION:
            from .context_language import document as language_document
            from .context_selection import select as contextual_select
            return contextual_select(*args,**kwargs,_interpret=language_document)
        from .context_contract import VERSION as CONTEXT_VERSION
        if version!=CONTEXT_VERSION:raise FixtureError('UnregisteredFixtureProof')
        from .context_selection import select as contextual_select
        return contextual_select(*args,**kwargs)

    @staticmethod
    def grammar_for(version):
        from .personalization import base_version as personal_base
        original=personal_base(version)
        if original is not None:return Store.grammar_for(original)
        from .fashion_contract import base_version
        original=base_version(version)
        if original is not None:return Store.grammar_for(original)
        if version==VERSION:return GRAMMAR_SHA
        from .semantic_frame_contract import VERSION as FRAME_VERSION
        if version==FRAME_VERSION:
            from .semantic_frames import identity as frame_identity
            return frame_identity()
        from .semantic_constraint_contract import VERSION as NOUN_VERSION
        if version==NOUN_VERSION:
            from .semantic_constraints import identity as noun_identity
            return noun_identity()
        from .semantic_reliability_contract import VERSION as SCOPED_VERSION
        if version==SCOPED_VERSION:
            from .semantic_reliability import identity as scoped_identity
            return scoped_identity()
        from .semantic_structured_contract import VERSION as TYPED_VERSION
        if version==TYPED_VERSION:
            from .semantic_structured import identity as typed_identity
            return typed_identity()
        from .interview_default_contract import VERSION as DEFAULT_VERSION
        if version==DEFAULT_VERSION:
            from .interview_default import identity as default_identity
            return default_identity()
        from .context_language_contract import VERSION as LANGUAGE_VERSION
        if version==LANGUAGE_VERSION:
            from .context_language import identity as language_identity
            return language_identity()
        from .context_contract import VERSION as CONTEXT_VERSION
        if version!=CONTEXT_VERSION:raise FixtureError('UnregisteredFixtureProof')
        from .context_intent import identity
        return identity()

    def lookup(self,c,owner,receipt):
        if not c.execute("select 1 from sqlite_master where name='phase2nd_mixed_proofs' and type='table'").fetchone():return None
        return c.execute('select * from phase2nd_mixed_proofs where owner_id=? and receipt=?',(owner,receipt)).fetchone()

    def capture(self,c,owner,wearer):
        fixture=super().capture(c,owner,wearer)
        authority=c.execute('select id,catalog_sha256 from phase2nd_instance').fetchall()
        if len(authority)!=1 or authority[0]['id']!=self.catalog['instance_id'] or authority[0]['catalog_sha256']!=self.config['catalog_sha256']:raise FixtureError('ChangedFixtureAuthority')
        from app.application.wardrobe.wearer_category_service import capture
        from app.application.recommendation.request_local_soft_workflow import InternalLocalPreferenceWorkflow,resource_identities
        from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
        from app.domain.value_objects.intended_wearer import IntendedWearer
        from app.domain.value_objects.request_local_source_codec import pack_sources,VERSION as CODEC
        profile=fixture['profiles'][wearer]['row']
        bound=IntendedWearer(owner,wearer,profile['name'],'explicit',profile['created_at'])
        scope=capture(owner,wearer,c)
        if scope is None:raise FixtureError('ExplicitWearerPolicyRequired',422)
        sources=[]
        from app.infrastructure.persistence.active_preference_query_adapter import read_active_preference_rows
        prefs=[asdict(p) for p in read_active_preference_rows(c,owner,bound)]
        if scope.account_descriptions:
            scope,sources,preferences=InternalLocalPreferenceWorkflow(source_codec=CODEC).capture(c,owner,bound,source_codec=CODEC,media_root=self.media)
            prefs=[asdict(p) for p in preferences]
        available=[r[0] for r in c.execute("select id from garments where user_id=? and status='available' order by id",(owner,))]
        if len(available)>100:raise FixtureError('WardrobeCapacityExceeded',422)
        original={'owner_id':owner,'wearer':{'profile_id':wearer},'source_table':pack_sources(sources) if sources else None,'eligibility':scope.eligibility.to_dict(),'preferences':prefs}
        return json.loads(encoded({'version':'mixed-wardrobe-scope-1.0.0','fixture':fixture,'original':original,'available_ids':available,'attribute_policy':AttributeEvidencePolicy.load().snapshot(),'resources':resource_identities()}))

    def profile_on(self):
        if self.config.get('profile')!=PROFILE: raise FixtureError('FixtureProfileDisabled',503)

    def verify_record(self,c,row,owner,depth=0):
        if depth>=10 or row['owner_id']!=owner: raise FixtureError('InvalidFixtureHistory',404)
        text=row['proof_json']
        if len(text.encode())>MAX_PROOF: raise FixtureError('OversizedFixtureProof')
        proof=json.loads(text)
        if digest(proof)!=row['proof_sha256'] or not hmac.compare_digest(self.sign(proof),row['signature']): raise FixtureError('ChangedFixtureProof')
        from .personalization import base_version as personal_base
        personal=personal_base(proof.get('version')) is not None
        from .semantic_structured_contract import owns as semantic_version
        semantic=semantic_version(proof.get('version'))
        if set(proof)!=({'version','catalog','grammar_sha256','raw','wearer_id','engine','seen','floor','decision','parent_id','ordinal','receipt','fingerprint','record_id'}|({'personalization'} if personal else set())|({'semantic_proposal'} if semantic else set())): raise FixtureError('UnknownFixtureProofField')
        if digest(proof['catalog']['fixture']) not in self.accepted_catalogs or proof['grammar_sha256']!=self.grammar_for(proof['version']): raise FixtureError('UnregisteredFixtureProof')
        for k in ('wearer_id','parent_id','ordinal','receipt','fingerprint'):
            if proof[k]!=row[k]: raise FixtureError('ChangedFixtureRecord')
        if proof['record_id']!=row['id'] or proof['catalog']['fixture']['owner_id']!=owner: raise FixtureError('ForeignFixtureProof')
        expected_seen=[];floor='0';ordinal=0
        if row['parent_id']:
            parent=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(row['parent_id'],owner)).fetchone()
            if not parent: raise FixtureError('MissingFixtureParent')
            pp=self.verify_record(c,parent,owner,depth+1)
            if pp['wearer_id']!=proof['wearer_id'] or pp['raw']!=proof['raw'] or pp['decision']['intent']['optional']: raise FixtureError('ChangedFixtureLineage')
            if proof['version']!=VERSION and (pp['version']!=proof['version'] or pp['catalog']!=proof['catalog']):raise FixtureError('ChangedFixtureLineage')
            if personal and proof['personalization']!=pp.get('personalization'):raise FixtureError('ChangedFixtureLineage')
            expected_seen=pp['seen']+[self.base(pp['decision'])];floor=pp['floor'] if pp['ordinal'] else self.r_value(pp['decision']);ordinal=pp['ordinal']+1
        if proof['seen']!=expected_seen or proof['floor']!=floor or proof['ordinal']!=ordinal or ordinal>9: raise FixtureError('InvalidFixtureChain')
        decision=self.select_version(proof['version'],proof['catalog'],proof['raw'],proof['wearer_id'],independent=True,seen=self.seen(proof['seen']),floor=proof['floor'],**({'_personalization':proof['personalization']} if personal else {}),**({'_semantic_proposal':proof['semantic_proposal']} if semantic else {}))
        if decision!=proof['decision'] or decision['status']!='Selected': raise FixtureError('IndependentFixtureHistoryMismatch')
        return proof

    @staticmethod
    def base(decision): return [x for x in decision['selected']['key'] if x[0]!='outerwear']
    @staticmethod
    def seen(values): return tuple(tuple(tuple(x) for x in key) for key in values)
    @staticmethod
    def r_value(d):
        from app.application.recommendation.decision_score_codec import score_from_json
        return str(score_from_json(json.dumps(d['selected']['score'])).request_match.contribution)

    def action(self,record_id,proof):
        if proof['ordinal']>=9 or proof['decision']['intent']['optional']: return None
        from .fashion_contract import base_version,PROFILE as FASHION
        from .personalization import base_version as personal_base,PROFILE as PERSONAL
        personal=personal_base(proof['version'])
        if personal is not None and self.config.get('personalization_profile')!=PERSONAL:return None
        original=base_version(personal or proof['version'])
        if original is not None and self.config.get('fashion_profile')!=FASHION:return None
        version=original or proof['version']
        from .semantic_frame_contract import VERSION as FRAME_VERSION,PROFILE as FRAME_PROFILE
        from .semantic_constraint_contract import VERSION as NOUN_VERSION
        from .semantic_reliability_contract import VERSION as SCOPED_VERSION,PROFILE as SCOPED_PROFILE
        from .semantic_structured_contract import VERSION as TYPED_VERSION,PROFILE as TYPED_PROFILE
        if version==TYPED_VERSION and (self.config.get('semantic_frame_profile')!=TYPED_PROFILE or self.config.get('semantic_error')):return None
        if version in (FRAME_VERSION,NOUN_VERSION,SCOPED_VERSION) and (self.config.get('semantic_frame_profile') not in (FRAME_PROFILE,SCOPED_PROFILE,TYPED_PROFILE) or self.config.get('semantic_error')):return None
        if version==SCOPED_VERSION and self.config.get('semantic_frame_profile') not in (SCOPED_PROFILE,TYPED_PROFILE):return None
        if version!=VERSION and not (version in (FRAME_VERSION,NOUN_VERSION,SCOPED_VERSION,TYPED_VERSION) and 'context' not in proof['decision']):
            from .context_contract import PROFILE as CONTEXT_PROFILE
            if self.config.get('context_profile')!=CONTEXT_PROFILE or proof['decision']['context']['selection_mode']!='best_evidenced_with_coverage_v1':return None
            from .context_language_contract import VERSION as LANGUAGE_VERSION,PROFILE as LANGUAGE_PROFILE
            if version==LANGUAGE_VERSION and self.config.get('language_profile')!=LANGUAGE_PROFILE:return None
        return {'parent_id':record_id,'action_key':self.sign({'parent_id':record_id,'proof_sha256':digest(proof)}),'label':'Suggest another outfit'}

    def view(self,row,proof,replayed=False):
        return {'id':row['id'],'request_text':proof['raw'],'wearer_id':proof['wearer_id'],'ordinal':proof['ordinal'],
                'source':'mixed_original_and_synthetic_v1','synthetic':any(i['source']==ORIGIN for i in proof['decision']['items']),'proof_version':proof['version'],'decision':proof['decision'],
                'created_at':row['created_at'],'replayed':replayed,'continuation':self.action(row['id'],proof)}

    def history(self,owner,record_id=None):
        with self.connection() as c:
            self.require_owner(c,owner)
            if record_id:
                r=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(record_id,owner)).fetchone()
                if not r: raise FixtureError('RecommendationNotFound',404)
                return self.view(r,self.verify_record(c,r,owner))
            rows=c.execute('select * from phase2nd_mixed_proofs where owner_id=? order by created_at desc,id desc limit 100',(owner,)).fetchall()
            # Full verification is performed on opening/replaying a record; list
            # contains only IDs/text, never unverified winners or score claims.
            return [{'id':r['id'],'created_at':r['created_at']} for r in rows]

    def recommend(self,owner,wearer,raw,receipt,engine='reference',parent_id=None,action_key=None,*,before_lock=None,after_insert=None):
        self.profile_on()
        if not isinstance(raw,str) or not 1<=len(raw)<=500 or not isinstance(receipt,str) or not 1<=len(receipt)<=200: raise FixtureError('InvalidFixtureRequest',422)
        if engine not in ('reference','compact_exhaustive'): raise FixtureError('UnsupportedFixtureEngine',422)
        fingerprint=digest({'owner':owner,'wearer':wearer,'raw':raw,'engine':engine,'parent_id':parent_id,'action_key':action_key})
        with self.connection() as c:
            c.execute('BEGIN')
            self.require_owner(c,owner,wearer)
            existing=self.lookup(c,owner,receipt)
            if existing:
                if existing['fingerprint']!=fingerprint: raise FixtureError('IdempotencyConflict')
                return self.view(existing,self.verify_record(c,existing,owner),True)
            catalog=self.capture(c,owner,wearer);seen=[];floor='0';ordinal=0
            if parent_id:
                p=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(parent_id,owner)).fetchone()
                if not p: raise FixtureError('RecommendationNotFound',404)
                pp=self.verify_record(c,p,owner);action=self.action(parent_id,pp)
                # A saved parent's original interpretation revision owns its
                # continuation even after a newer language profile is enabled.
                version=pp['version']
                if catalog!=pp['catalog']:raise FixtureError('RefinementScopeChanged')
                if not action: raise FixtureError('RefinementUnavailable',422)
                if action_key!=action['action_key'] or raw!=pp['raw'] or wearer!=pp['wearer_id']: raise FixtureError('InvalidContinuationBinding')
                seen=pp['seen']+[self.base(pp['decision'])];floor=pp['floor'] if pp['ordinal'] else self.r_value(pp['decision']);ordinal=pp['ordinal']+1
            elif action_key: raise FixtureError('MissingFixtureParent',422)
            else:version=self.selection_version(raw)
            from .personalization import base_version as personal_base,capture as capture_personal
            personal=pp.get('personalization') if parent_id else capture_personal(self,c,owner,wearer) if personal_base(version) else None
        options={'_personalization':personal} if personal is not None else {}
        from .semantic_structured_contract import owns as semantic_version,base as semantic_base
        from .semantic_reliability_contract import VERSION as SCOPED_VERSION
        if semantic_version(version):
            from .semantic_model import propose,ModelUnavailable
            if semantic_base(version)==SCOPED_VERSION:
                from .semantic_reliability import propose
            from .semantic_structured_contract import VERSION as TYPED_VERSION
            if semantic_base(version)==TYPED_VERSION:
                from .semantic_structured import propose
            try:proposal=pp['semantic_proposal'] if parent_id else propose(raw)
            except ModelUnavailable as error:raise FixtureError('SemanticInterpreterUnavailable',503) from error
            options['_semantic_proposal']=proposal
        decision=self.select_version(version,catalog,raw,wearer,engine,seen=self.seen(seen),floor=floor,**options)
        if decision['status']!='Selected': return {'synthetic':True,'decision':decision,'persisted':False}
        if before_lock: before_lock()
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=self.lookup(c,owner,receipt)
            if existing:
                if existing['fingerprint']!=fingerprint: raise FixtureError('IdempotencyConflict')
                return self.view(existing,self.verify_record(c,existing,owner),True)
            fresh=self.capture(c,owner,wearer)
            if fresh!=catalog: raise FixtureError('ChangedFixtureSource')
            if personal is not None and not parent_id and capture_personal(self,c,owner,wearer)!=personal:raise FixtureError('ChangedPersonalizationSources')
            if parent_id:
                parent=c.execute('select * from phase2nd_mixed_proofs where id=? and owner_id=?',(parent_id,owner)).fetchone()
                if not parent or self.verify_record(c,parent,owner)!=pp: raise FixtureError('ChangedFixtureParent')
            elif semantic_version(version):
                # Re-run extraction independently under the write lock. History
                # later reconstructs the signed frozen interpretation, not a
                # potentially different model result on another machine.
                try:reconstructed=propose(raw)
                except ModelUnavailable as error:raise FixtureError('SemanticInterpreterUnavailable',503) from error
                if reconstructed!=proposal:raise FixtureError('SemanticInterpretationChanged')
            independent=self.select_version(version,fresh,raw,wearer,independent=True,seen=self.seen(seen),floor=floor,**options)
            if independent!=decision: raise FixtureError('IndependentFixtureWriteMismatch')
            proof={'version':version,'catalog':fresh,'grammar_sha256':self.grammar_for(version),'raw':raw,'wearer_id':wearer,'engine':engine,
                'seen':seen,'floor':floor,'decision':independent,'parent_id':parent_id,'ordinal':ordinal,'receipt':receipt,
                'fingerprint':fingerprint,'record_id':str(uuid.uuid4())}
            if semantic_version(version):proof['semantic_proposal']=proposal
            if personal is not None:proof['personalization']=personal
            wire=encoded(proof)
            if len(wire)>MAX_PROOF: raise FixtureError('OversizedFixtureProof')
            c.execute(SCHEMA)
            c.execute('insert into phase2nd_mixed_proofs values (?,?,?,?,?,?,?,?,?,?,?)',
                (proof['record_id'],owner,wearer,receipt,fingerprint,parent_id,ordinal,wire.decode(),digest(proof),self.sign(proof),datetime.now(timezone.utc).isoformat()))
            if after_insert: after_insert(c,wire)
            row=c.execute('select * from phase2nd_mixed_proofs where id=?',(proof['record_id'],)).fetchone()
            return self.view(row,proof)
