"""Independent Fraction oracle over fixed descriptors, plus actual confirmed HTTP writes."""
from fractions import Fraction as F
from itertools import combinations,product
from pathlib import Path
import json,os,uuid
import pytest
from app.application.ports.assistant_runtime import assistant_service
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.scoring_eligibility_gate import ScoringEligibilityGate
from app.application.recommendation.request_match_scorer import RequestMatchScorer
from app.application.recommendation.preference_scorer import PreferenceScorer
from app.application.recommendation.preference_normalizer import PreferenceNormalizer
from app.application.recommendation.rule_based_compatibility_scorer import RuleBasedCompatibilityScorer
from app.application.recommendation.compatibility_decision_policy import CompatibilityDecisionPolicy
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence import postgresql_repository as db
from app.application.nlp.nlp_interpreter import NLPInterpreter
from tests.test_suitability_assistant_e2e import integrated,make,submit,tag
from tests.test_forward_style_semantics import lifecycle

DATA=json.loads((Path(__file__).parent/'fixtures/scoring_acceptance.v1.json').read_text())
D='compatibility_deferred';E='experimental_compatibility_decision_v1'
ROLES={'vest':'upper','trousers':'lower','vest_dress':'one_piece','long_sleeve_outwear':'outerwear'}
KNOWN={'black','white','grey','blue','red'}

def independent(case,ids):
    rows={g[0]:g for g in case['garments']};slots={r:[g[0] for g in case['garments'] if ROLES[g[1]]==r] for r in ROLES.values()}
    bases=list(product(slots['upper'],slots['lower']))+[(x,) for x in slots['one_piece']]
    result=[]
    for base in bases:
        for outer in [None]+slots['outerwear']:
            if case.get('outerwear') and outer is None:continue
            members=base+((outer,) if outer else ())
            if case.get('style') and not any(case['style'] in (rows[x][3] or []) for x in base):continue
            r=F(sum(case['style'] in (rows[x][3] or []) for x in base),len(base)) if case.get('style') else F(0)
            if case.get('outerwear'):r=(r+1)/2 if case.get('style') else F(1)
            atoms=[]
            for a,b in combinations(members,2):
                ca,cb=rows[a][2],rows[b][2];sa,sb=rows[a][3],rows[b][3]
                atoms.append(F(int(ca==cb or ca in {'black','white','grey'} or cb in {'black','white','grey'})) if ca in KNOWN and cb in KNOWN else None)
                atoms.append(F(2*len(set(sa)&set(sb)),len(set(sa))+len(set(sb))) if sa and sb else None)
            known=[x for x in atoms if x is not None]
            c=F(1,2) if not atoms else (sum(known,F())/len(atoms)+(sum(known,F())+len(atoms)-len(known))/len(atoms))/2
            basis='NoPairReference' if not atoms else 'Computed' if len(known)==len(atoms) else 'FullyConventional' if not known else 'PartiallyConventional'
            ps=[]
            for preference in case.get('preferences',[]):
                if preference['type']=='colours':ps.append(F(int(any(rows[x][2] in preference['values'] for x in members))))
                elif preference['type']=='styles':ps.append(F(sum(bool(set(rows[x][3] or [])&set(preference['values'])) for x in base),len(base)))
                else:ps.append(F(int(any(ROLES[rows[x][1]]=='upper' for x in members))))
            p=sum(ps,F())/len(ps) if ps else F()
            key=tuple((ROLES[rows[x][1]],ids[x]) for x in members)
            result.append({'members':members,'key':key,'r':r,'c':c,'p':p,'basis':basis,'deferred':F(7,10)*r+F(3,10)*p,'experimental':F(3,5)*r+F(1,5)*c+F(1,5)*p})
    return result

def expected_winner(rows,profile):
    return min(rows,key=lambda x:(-x['experimental' if profile==E else 'deferred'],-x['r'],-(x['c'] if profile==E else 0),-x['p'],x['key']))

@pytest.mark.parametrize('case',DATA['cases'],ids=lambda c:c['id'])
def test_fixed_exact_candidates_four_way_http_and_profile_replay(integrated,case):
    client,create=integrated;ids={}
    for name,category,colour,styles in case['garments']:
        gid=make(client,create,category,[tag(),tag('formality','casual')]);ids[name]=gid
        assert client.patch('/api/v1/wardrobe/garments/'+gid,json={'primary_colour':colour,'attributes':{'style':styles}}).status_code==200
    with db.connection() as c:
        for index,pref in enumerate(case.get('preferences',[])):
            c.execute('INSERT INTO user_preferences VALUES(?,?,?,?,1,?,1,?,?)',(str(index),'style-owner',pref['type'],json.dumps({'values':pref['values']}),'synthetic','now','now'))
    oracle=independent(case,ids);request=NLPInterpreter().interpret(case['text']).structured_request
    assert request is not None
    engine=assistant_service().engine
    session=engine.generate_candidates('style-owner',request);gate=ScoringEligibilityGate(session,'style-owner',request)
    preferences=PreferenceNormalizer().normalize('style-owner',SqliteActivePreferenceQuery().get_active_preferences('style-owner'))
    observed=[]
    for evaluated in session:
        verified=gate.verify(evaluated);candidate=verified.candidate
        expected=next(x for x in oracle if x['key']==candidate.key)
        raw=RuleBasedCompatibilityScorer().evaluate(candidate)
        structure='dress' if candidate.members[0].role=='one_piece' else 'top_bottom'
        if candidate.members[-1].role=='outerwear':structure+='_outerwear'
        compatibility=CompatibilityDecisionPolicy.load().apply(raw,structure)
        assert (RequestMatchScorer().score(verified).contribution,compatibility.contribution,PreferenceScorer().score(verified,preferences).contribution)==(expected['r'],expected['c'],expected['p'])
        assert compatibility.decision.basis==expected['basis'];observed.append(expected['key'])
    assert session.result.complete and set(observed)=={x['key'] for x in oracle}
    records=[];saved=None
    for engine_name in ('compact_exhaustive','reference'):
        for profile in (D,E):
            service=assistant_service();service.execution_engine=engine_name;service.scoring_profile=profile
            key=uuid.uuid4().hex;response,result=submit(client,case['text'],key)
            assert response.status_code==201,result
            expected=expected_winner(oracle,profile)
            assert tuple((x['garment_role'],x['garment_id']) for x in result['items'])==expected['key']
            score=result['score_metadata'];frac=lambda x:F(x['numerator'],x['denominator'])
            assert frac(score['total'])==expected['experimental' if profile==E else 'deferred']
            assert result['provenance']['scored_count']==len(oracle)
            if saved is not None:
                _,retry=submit(client,case['text'],saved[0]);assert retry['replayed'] and retry['id']==saved[1]['id']
                assert retry['score_metadata']==saved[1]['score_metadata'] and retry['provenance']==saved[1]['provenance']
            saved=(key,result)
            records.append({'engine':engine_name,'profile':profile,'winner':expected['members'],'record':result})
    output=os.getenv('SMART_WARDROBE_SCORING_EVIDENCE')
    if output:
        with Path(output).open('a') as f:f.write(json.dumps({'case':case['id'],'oracle':oracle,'actual':records},default=str)+'\n')

@pytest.fixture
def experimental(integrated):
    assistant_service().scoring_profile=E
    return integrated

@pytest.mark.parametrize('position',[0,1,2])
@pytest.mark.parametrize('state',['allow','deny','unknown','conflict','malformed','deny_and_unknown'])
def test_experimental_suitability_remains_mandatory(experimental,position,state):
    from tests.test_suitability_assistant_e2e import test_each_member_aggregate_including_outerwear
    test_each_member_aggregate_including_outerwear(experimental,position,state)


def test_competing_missing_empty_and_no_pair_conventions(integrated):
    case=json.loads((Path(__file__).parent/'fixtures/scoring_evidence_competition.v1.json').read_text())['case']
    test_fixed_exact_candidates_four_way_http_and_profile_replay(integrated,case)
