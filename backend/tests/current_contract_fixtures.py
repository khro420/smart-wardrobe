"""Explicit synthetic test scope; never a runtime default or ownership bypass."""
from tests.retained_evidence import review_path, review_reference
from app.infrastructure.persistence import postgresql_repository as db
from app.application.wardrobe.profile_service import ensure_default_profile
from app.application.recommendation.wearer_identity import resolve_wearer


def wearer_id(owner):
    with db.connection() as conn:
        return ensure_default_profile(conn,owner)['id']


def wearer(owner):
    return resolve_wearer(owner,wearer_id(owner),None)


def history_scope(owner,chat_id):
    with db.connection() as conn:
        row=conn.execute('SELECT profile_id FROM nlp_chats WHERE id=? AND user_id=?',(chat_id,owner)).fetchone()
        if row is None:raise LookupError('Synthetic history scope not found.')
    return {'profile_id':row['profile_id'],'view':'legacy_unrecorded' if row['profile_id'] is None else 'active'}


def original_fields_exact(expected,actual):
    """Every original value/order/type; additions only at their declared sites."""
    defaults={
        'appearance_evidence':{'state':'Missing','category':None,'media_id':None,'features':[],'condition':None,'reviewed_at':None},
        'contextual_suitability':{'state':'Missing','review_state':'Missing','reviewed_styles':[],'reviewed_category':None,'reviewed_at':None,'wedding_decisions':[]},
        'saved_attribute_evidence':{'state':'Absent','origin':'unknown','contributor':None,'recorded_at':None,'value_sha256':None,'category':None,'media_id':None,'owner_id':None}}
    if isinstance(expected,dict):
        assert type(actual) is dict and set(expected)<=set(actual)
        extras=set(actual)-set(expected)
        if 'garment_id' in expected:
            assert extras<=set(defaults)
            for name in extras:assert actual[name]==defaults[name]
        elif {'status','complete','winner','scored_count'}<=set(expected):
            assert extras<={'ranking_evidence','refinement_summary'}
            for name in extras:assert actual[name] is None
        else:assert not extras
        for name,value in expected.items():original_fields_exact(value,actual[name])
    elif isinstance(expected,list):
        assert type(actual) is list and len(expected)==len(actual)
        for a,b in zip(expected,actual):original_fields_exact(a,b)
    else:assert type(expected) is type(actual) and expected==actual


def frozen_archive():
    from pathlib import Path
    import hashlib,json,zipfile
    directory=Path(__file__).parent/'fixtures/performance_reference'
    archive=zipfile.ZipFile(directory/'app.zip')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert set(archive.namelist())==set(manifest)
    assert all(hashlib.sha256(archive.read(p)).hexdigest()==h for p,h in manifest.items())
    return archive


def historical_visualisation_contract(monkeypatch):
    """Use the certified older plan, preserving the older refusal assertion."""
    import sys,types
    from app.application.visualisation import outfit_identifier_validator as boundary
    name='tests._frozen_visualisation_plan'
    module=types.ModuleType(name);sys.modules[name]=module
    with frozen_archive() as archive:
        source=archive.read('app/domain/value_objects/visualisation_plan.py')
    exec(compile(source,'certified-historical-visualisation-plan','exec'),module.__dict__)
    assert 'long_sleeve_outwear' not in module.CATEGORY_MODES
    monkeypatch.setattr(boundary,'VisualisationPlan',module.VisualisationPlan)


def historical_disabled_extra_response():
    """Execute the original pre-A route body; never change the active route."""
    import ast,hashlib,json
    from pathlib import Path
    from types import SimpleNamespace
    from fastapi.responses import JSONResponse
    root=review_path('phase_regression_contract_reconciliation_20261107/historical-contracts')
    provenance=json.loads((root/'provenance.json').read_text())
    authority=review_reference(provenance['authority'])
    assert hashlib.sha256(authority.read_bytes()).hexdigest()==provenance['authority_sha256']
    source=(root/'recommendation_routes.py').read_bytes()
    assert hashlib.sha256(source).hexdigest()==provenance['source_sha256']==json.loads(authority.read_text())['backend/app/api/recommendation_routes.py']
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='create')
    node.decorator_list=[];node.returns=None
    for argument in node.args.args:argument.annotation=None
    node.args.defaults=[ast.Constant(None) for _ in node.args.defaults]
    tree=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    namespace={'JSONResponse':JSONResponse};exec(compile(tree,'certified-pre-A-route','exec'),namespace)
    return namespace['create'](SimpleNamespace(model_extra={'scoring_profile':'client'}),user_id='historical-unit-owner',profile_id=None,service=None,pipeline='integrated')


def historical_structural_counts(rows):
    """Actual original engine in a separate process with its certified sources."""
    import dataclasses,json,os,subprocess,sys,tempfile
    from pathlib import Path
    from collections import Counter
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.domain.value_objects.contextual_garment_evidence import ContextualGarmentEvidence
    from app.domain.value_objects.general_context_evidence import AppearanceEvidence
    from app.domain.value_objects.saved_attribute_evidence import SavedAttributeEvidence
    captured=[]
    for row in rows:
        assert row.contextual_suitability==ContextualGarmentEvidence()
        assert row.appearance_evidence==AppearanceEvidence()
        assert row.saved_attribute_evidence==SavedAttributeEvidence()
        raw=dataclasses.asdict(row)
        for name in ('contextual_suitability','appearance_evidence','saved_attribute_evidence'):raw.pop(name)
        captured.append(raw)
    with tempfile.TemporaryDirectory(prefix='historical-capacity-') as temporary:
        root=Path(temporary)
        with frozen_archive() as archive:archive.extractall(root)
        script="""import json,sys
from collections import Counter
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.application.recommendation.recommendation_engine import RecommendationEngine
rows=tuple(ConfirmedGarmentSnapshot(**v) for v in json.load(sys.stdin))
class Query:
 def get_confirmed_available_garments(self,owner):return rows
session=RecommendationEngine(Query()).generate_homepage_candidates('owner')
counts=Counter(tuple(m.role for m in c.members) for c in session)
assert session.result.complete
print(json.dumps([[list(k),v] for k,v in counts.items()]))
"""
        process=subprocess.run([sys.executable,'-B','-c',script],cwd=root,input=json.dumps(captured),capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(root)},check=True)
        return Counter({tuple(k):v for k,v in json.loads(process.stdout)})
