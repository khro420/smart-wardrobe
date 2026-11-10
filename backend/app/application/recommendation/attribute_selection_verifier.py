"""Independent operator/quantifier checks over captured sources, not admission cache."""
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from app.domain.value_objects.attribute_conditions import ROLES,ANCHORS


def _possibility(fact,field,op,wanted):
    """Set of possible truth values; singleton certifies a primitive verdict."""
    if fact.applicability!='applicable' or fact.state not in ('Known','KnownEmpty'):return frozenset((True,False))
    if field not in ('palette_colour','palette_coverage'):
        witnesses=[value in fact.values for value in wanted]
        proved=all(witnesses) if op=='contains_all' else any(witnesses)
        return frozenset((True,)) if proved else frozenset((False,)) if fact.complete else frozenset((True,False))
    def equal(raw,target):return raw==target if target[:1]=='#' else ANCHORS.get(raw)==target
    if op=='coverage_ge':
        target=wanted[0]['colour'];threshold=Fraction(wanted[0]['minimum'])
        positive=Fraction(0);negative=Fraction(0)
        for raw,mass in fact.values:
            if mass is None:continue
            if equal(raw,target):positive+=Fraction(mass)
            elif target.startswith('#') or raw in ANCHORS:negative+=Fraction(mass)
        maximum=1-negative
        if fact.complete and all(target.startswith('#') or raw in ANCHORS for raw,_ in fact.values):maximum=positive
        possible=set()
        if maximum>=threshold:possible.add(True)
        if positive<threshold:possible.add(False)
        return frozenset(possible)
    present=[any(equal(raw,value) for raw,_ in fact.values) for value in wanted]
    if (all(present) if op=='contains_all' else any(present)):return frozenset((True,))
    if fact.complete and (op=='exact_hex' or all(raw in ANCHORS for raw,_ in fact.values)):return frozenset((False,))
    return frozenset((True,False))


def _state(possible):
    return 'Pass' if possible==frozenset((True,)) else 'Fail' if possible==frozenset((False,)) else 'Unknown'


@dataclass(frozen=True)
class IndependentAttributeVerifier:
    groups: tuple
    rows: object
    possibilities: object
    applicable: object

    @classmethod
    def prepare(cls,conditions,collection,policy,subtype_sources=()):
        classifier=policy.primary_classifier();rows={};possibilities={};applicable={}
        subtype_map={s.garment_id:s for s in subtype_sources}
        groups=conditions.to_dict()['groups']
        for item in collection:
            snapshot=item.snapshot;gid=snapshot.garment_id
            if gid in rows:raise ValueError('Duplicate independent attribute source.')
            rows[gid]=snapshot;description=item.description.to_dict()
            for group in groups:
                for c in group['conditions']:
                    fact=policy.subtype_fact(snapshot,subtype_map.get(gid)) if c['attribute']=='verified_subtype' else policy.fact(snapshot,description,c['attribute'],c['operator'],classifier)
                    possibilities[gid,c['id']]=_possibility(fact,c['attribute'],c['operator'],c['values'])
                    applicable[gid,c['id']]=fact.applicability!='inapplicable'
        frozen=tuple((ROLES[g['role']],g['quantifier'],tuple(c['id'] for c in g['conditions'])) for g in groups)
        return cls(frozen,MappingProxyType(rows),MappingProxyType(possibilities),MappingProxyType(applicable))

    def decision(self,members):
        group_states=[]
        for scope,quantifier,ids in self.groups:
            member_bounds=[]
            for role,gid in members:
                if gid not in self.rows:raise ValueError('Uncaptured independent member.')
                if role not in scope or not all(self.applicable[gid,c] for c in ids):continue
                bounds=[self.possibilities[gid,c] for c in ids]
                # Conjunction is definitely true iff all are; definitely false
                # iff one is. This does not assume uncertain fields independent.
                member_bounds.append((all(b=={True} for b in bounds),all(True in b for b in bounds)))
            if quantifier=='exists':
                lower=any(v[0] for v in member_bounds);upper=any(v[1] for v in member_bounds)
            elif quantifier=='none':
                lower=not any(v[1] for v in member_bounds);upper=not any(v[0] for v in member_bounds)
            else:
                lower=bool(member_bounds) and all(v[0] for v in member_bounds)
                upper=bool(member_bounds) and all(v[1] for v in member_bounds)
            group_states.append((lower,upper))
        lower=all(v[0] for v in group_states);upper=all(v[1] for v in group_states)
        return 'Pass' if lower else 'Fail' if not upper else 'Unknown'

    def verify_members(self,members):
        if self.decision(members)!='Pass':raise ValueError('Independent hard attribute admission failed.')

    def verify(self,candidate):
        if any(self.rows[m.garment.garment_id]!=m.garment for m in candidate.members):raise ValueError('Independent captured snapshot mismatch.')
        self.verify_members(tuple((m.role,m.garment.garment_id) for m in candidate.members))


def _member_results(prepared,members):
    records=[]
    for member in members:
        gid=member.garment.garment_id
        for group in prepared.conditions.to_dict()['groups']:
            for c in group['conditions']:
                cid=c['id'];verdict=prepared.verdicts[gid,cid];fact=prepared.facts[gid,cid]
                records.append({'garment_id':gid,'condition_id':cid,'state':verdict.state,'reason':verdict.reason,
                    'source_kind':fact.source,'source_revision':fact.revision})
    return records


def build_selection(intent,collection,prepared,independent,candidate,coverage,base_scope,wearer,subtype_sources=()):
    from dataclasses import asdict
    from app.domain.value_objects.attribute_selection_evidence import (
        AttributeSelectionEvidence,EVIDENCE_VERSION,description_digest,scope_digest,digest,subtype_digest)
    from app.application.recommendation.refinement_verifier import snapshot_digest
    independent.verify(candidate)
    collection_hash=description_digest(collection)
    documents={item.snapshot.garment_id:item.description for item in collection}
    selected=[];identities=[]
    for member in candidate.members:
        g=member.garment
        selected.append({'role':member.role,'garment_id':g.garment_id,'description':documents[g.garment_id].to_dict(),
            'appearance_evidence':asdict(g.appearance_evidence)})
        identities.append({'garment_id':g.garment_id,'name':g.name,'category':g.category,'primary_colour':g.primary_colour,
            'preferred_media_id':g.preferred_media_id,'updated_at':g.updated_at})
    value={'version':EVIDENCE_VERSION,'intent':intent.to_dict(),'wearer_profile_id':wearer.profile_id,
        'strict_snapshot_sha256':snapshot_digest(tuple(item.snapshot for item in collection)),
        'description_collection_sha256':collection_hash,
        'attribute_scope_sha256':scope_digest(wearer.account_id,wearer.profile_id,base_scope,intent,collection_hash,subtype_digest(subtype_sources) if intent.to_dict()['version']=='assistant-attribute-intent-2.0.0' else None),
        'policy_snapshot':prepared.policy.snapshot(),'selected_evidence':selected,
        'decisions':{'identities':identities,'member_results':_member_results(prepared,candidate.members)},
        'coverage':coverage,'revision':''}
    if intent.to_dict()['version']=='assistant-attribute-intent-2.0.0':
        from app.domain.value_objects.attribute_selection_evidence import subtype_digest
        from app.domain.value_objects.verified_garment_subtype import registry
        sources={s.garment_id:s.to_dict() for s in subtype_sources}
        value.update(version='attribute-selection-evidence-2.0.0',subtype_collection_sha256=subtype_digest(subtype_sources),subtype_registry=registry(),selected_subtypes=[sources[m.garment.garment_id] for m in candidate.members])
        value['attribute_scope_sha256']=scope_digest(wearer.account_id,wearer.profile_id,base_scope,intent,collection_hash,value['subtype_collection_sha256'])
    value['revision']=digest(value)
    return AttributeSelectionEvidence.from_dict(value)


def validate_selection(value,user_id,wearer_profile_id,base_scope,items=None):
    """Restore recorded facts only. Never load current grammar, config or wardrobe."""
    from app.domain.value_objects.attribute_selection_evidence import AttributeSelectionEvidence,AttributeIntent,scope_digest
    from app.domain.value_objects.attribute_conditions import encode,exact
    from app.domain.value_objects.garment_description_evidence import GarmentDescriptionEvidence
    from app.domain.value_objects.general_context_evidence import AppearanceEvidence
    from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.shared_contracts.confirmed_garment_description import ConfirmedGarmentDescription
    from app.domain.value_objects.outfit_candidate import OutfitCandidate,CandidateMember
    from app.application.recommendation.attribute_evidence_policy import AttributeEvidencePolicy
    from app.application.recommendation.attribute_condition_evaluator import PreparedAttributeConditions
    from app.application.nlp.attribute_request_interpreter import GRAMMAR_SHA256
    evidence=AttributeSelectionEvidence.from_dict(value);data=evidence.to_dict()
    intent=AttributeIntent.from_dict(data['intent'])
    policy=AttributeEvidencePolicy(encode(data['policy_snapshot']))
    # Explicit archived language descendant; never load active companion code here.
    registered_grammars=(GRAMMAR_SHA256,'1e2bfbccbaa0dc2e83284b4bb18cacd970b601b254b229b613af6a71b03ebb53','701080a9b339b9e785b958d56621f3524a303de3f2734e9744152f9f8989659a','9236cec2dbf017be05a69fa753aa42f57d924a8a7c42f56d85aa220b7b83f144','5745bf5b3fed2d5c3c758bf4fa7bf1bd39ffd6b4f7564f9119296af5599c3de4','14dcf620aa3ec7cc5f7568aa4b627409a55ab490c1239132f0473fe6222a1a13','adad8be0efa2de5b258fb498f70eaa08b169c03e6d4d40d404c851a151f56189','2e167f42a16407e5341f736562257aa2a5cfb77a2f2d9702bce5e202cdf33670','232e17d866a7f93128ff7dca8cabd08c30a9f5dce779a0434501406e13dd0763','2cc305e8f17a045dfd418ce6bde6caae028b3e03e694c3571074f0610676a974','d37a98f21a6f1286ffc7fb65adf8a821b68a1cccaf2b929c5f8fe0581ba6e50c','f0bd9fd429400e18f67258fa7e0484475ec83ce58ba9b4f53376255340c5dd33','4fdf75bd573dfc920579bfb2bd88378e4f32068db75df17448400c975b542f26','8afc724b747a82e6dc1f8f598b0c856a6032412f1f3b945deb4200de8944acff','3b66c3bd83bf918e41a1353af6aa64d4c894bd30da3de6d1875b05b75e522ccf','4255c59e23969055e1570e37a5e08467a7a36fba5f095faa2843b2c8364067ee','4e0ea721015a4b28d6434f49ddf13655f0c030d1f4e9a79f5ce53ffab190ef97','03b41d02401e3e28c028cf907da6141f63d368e98d65d4cfbe963b5b8fe0c110','50d4fc4e43c314b942c2a1b8c743b0e4c19cf6905d1eee7d57e8d2857fcd0cc6','1c58c4890365c5643550818359a4b0a8339e2dd124965446b08e19857c451cab')
    if intent.to_dict()['grammar_sha256'] not in registered_grammars or intent.to_dict()['policy_sha256']!=policy.sha256:
        raise ValueError('Unregistered archived attribute contract identity.')
    if data['wearer_profile_id']!=wearer_profile_id or data['attribute_scope_sha256']!=scope_digest(user_id,wearer_profile_id,base_scope,intent,data['description_collection_sha256'],data.get('subtype_collection_sha256')):
        raise ValueError('Archived attribute wearer/scope mismatch.')
    identities=data['decisions']['identities']
    by_id={}
    for identity in identities:
        exact(identity,('garment_id','name','category','primary_colour','preferred_media_id','updated_at'))
        if identity['garment_id'] in by_id:raise ValueError('Duplicate archived attribute identity.')
        by_id[identity['garment_id']]=identity
    collection=[];members=[]
    for position,selected in enumerate(data['selected_evidence'],1):
        gid=selected['garment_id'];identity=by_id.get(gid)
        if identity is None:raise ValueError('Missing selected attribute identity.')
        description=GarmentDescriptionEvidence.from_dict(selected['description'])
        if description.to_dict()['subject']['account_id']!=user_id:raise ValueError('Foreign archived description.')
        raw=selected['appearance_evidence']
        exact(raw,('state','category','media_id','features','condition','reviewed_at'))
        raw={**raw,'features':tuple(tuple(pair) for pair in raw['features'])}
        appearance=AppearanceEvidence(**raw)
        role,layer=GARMENT_STRUCTURE[identity['category']]
        g=ConfirmedGarmentSnapshot(gid,user_id,'available',identity['category'],identity['name'],identity['preferred_media_id'],False,
            identity['updated_at'],role,layer,primary_colour=identity['primary_colour'],appearance_evidence=appearance)
        collection.append(ConfirmedGarmentDescription(g,description))
        members.append(CandidateMember(g,selected['role'],position))
    candidate=OutfitCandidate(tuple(members))
    from app.shared_contracts.confirmed_garment_subtype import ConfirmedGarmentSubtype
    subtype_sources=tuple(ConfirmedGarmentSubtype(s['subject_id'],__import__('json').dumps(s)) for s in data.get('selected_subtypes',()))
    if subtype_sources and [s.garment_id for s in subtype_sources]!=[m.garment.garment_id for m in candidate.members]:raise ValueError('Wrong selected subtype ordering.')
    independent=IndependentAttributeVerifier.prepare(intent.conditions,collection,policy,subtype_sources=subtype_sources)
    independent.verify(candidate)
    prepared=PreparedAttributeConditions.prepare(intent.conditions,collection,policy,subtype_sources=subtype_sources)
    if data['decisions']['member_results']!=_member_results(prepared,candidate.members):raise ValueError('Archived attribute verdict facts disagree.')
    if items is not None:
        stored={item['garment_id']:item for item in items}
        if set(stored)!=set(by_id):raise ValueError('Stored item/attribute identities disagree.')
        if any(stored[gid].get('name')!=identity['name'] or stored[gid].get('category')!=identity['category'] for gid,identity in by_id.items()):
            raise ValueError('Stored historical item label disagreement.')
    return evidence
