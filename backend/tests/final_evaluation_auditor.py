"""Independent J-15 oracle: standard-library only; never imports application scorers/gates."""
from fractions import Fraction as F
from itertools import product, combinations
import hashlib
import json
from pathlib import Path

BACKEND=Path(__file__).resolve().parents[1]
CONFIG=BACKEND/'app/application/recommendation/config'
GROUPS={'top':('short_sleeve_top','long_sleeve_top','vest','sling'), 'bottom':('shorts','trousers','skirt'),
        'dress':('short_sleeve_dress','long_sleeve_dress','vest_dress','sling_dress'),
        'outerwear':('short_sleeve_outwear','long_sleeve_outwear')}
ROLES={c:{'top':'upper','bottom':'lower','dress':'one_piece','outerwear':'outerwear'}[g] for g,cs in GROUPS.items() for c in cs}
SHAPES={('upper','lower'):'top_bottom',('upper','lower','outerwear'):'top_bottom_outerwear',
        ('one_piece',):'dress',('one_piece','outerwear'):'dress_outerwear'}
VOCAB=json.loads((BACKEND/'app/application/nlp/config/vocabulary.v1.json').read_text())
ALIASES={f:{a:v['value'] for v in VOCAB['fields'][f] for a in [v['value'],*v['aliases']]} for f in ['colours','style']}
ANCHORS=json.loads((CONFIG/'request_policy.v1.json').read_text())['exact_hex_anchors']
OCCASIONS={'campus','work','casual_outing','shopping','dinner','party','date','travel'}

def encoded(value):
    if isinstance(value,F):return {'numerator':value.numerator,'denominator':value.denominator}
    raise TypeError(type(value).__name__)
def fraction(value):
    return F(value['numerator'],value['denominator']) if value is not None else None
def normalized(fields):
    if fields is None:return None
    result={name:fields.get(name) for name in ('occasion','style','colours','garment_categories','formality')}
    if result['colours'] is not None:result['colours']=sorted(set(result['colours']))
    if result['garment_categories'] is not None:
        result['garment_categories']=sorted((v.split(':',1) if isinstance(v,str) else [v['kind'],v['value']]) for v in result['garment_categories'])
    return result
def colour(row):
    value=row['primary_colour']
    if not isinstance(value,str):return None
    value=' '.join(value.lower().split())
    if len(value)==4 and value.startswith('#'):value='#'+''.join(c*2 for c in value[1:])
    return ALIASES['colours'].get(value,ANCHORS.get(value))
def styles(row):
    raw=json.loads(row['style_tags']) if row.get('style_tags') is not None else json.loads(row['attributes_json']).get('style')
    if raw is None:return None
    if isinstance(raw,str):raw=[raw]
    canonical=[ALIASES['style'].get(' '.join(v.lower().split())) for v in raw]
    return None if any(v is None for v in canonical) else set(canonical)
def declaration(row,field,value):
    raw=json.loads(row['custom_tags']) if row.get('custom_tags') is not None else json.loads(row['attributes_json']).get('custom_tags')
    decisions=set()
    for tag in raw or []:
        if not tag.lower().startswith('rec:'):continue
        parts=tag.split(':');affected=parts[2] if len(parts)>2 else None
        valid=(len(parts)==5 and parts[:2]==['rec','v1'] and affected in ('occasion','formality') and
               parts[3] in (OCCASIONS if affected=='occasion' else {'casual','smart_casual'}) and parts[4] in ('allow','deny'))
        if not valid and (affected==field or affected not in ('occasion','formality')):return 'Unknown'
        if valid and affected==field and parts[3]==value:decisions.add(parts[4])
    return 'Pass' if decisions=={'allow'} else 'Fail' if decisions=={'deny'} else 'Unknown'
def strict(rows,owner):
    return [g for g in rows if g['user_id']==owner and g['status']=='available' and
            g['evidence_item_id'] is not None and g['evidence_review_status']=='confirmed' and g['evidence_job_owner']==owner]
def conditions(members,fields):
    states=[]
    for spec in fields.get('garment_categories') or []:
        kind,value=(spec.split(':',1) if isinstance(spec,str) else (spec['kind'],spec['value']))
        states.append('Pass' if any(g['category'] in (GROUPS[value] if kind=='group' else (value,)) for g in members) else 'Fail')
    for requested in fields.get('colours') or []:
        observed=[colour(g) for g in members]
        states.append('Pass' if requested in observed else 'Unknown' if None in observed else 'Fail')
    if fields.get('style'):
        observed=[styles(g) for g in members if ROLES[g['category']]!='outerwear']
        states.append('Pass' if any(fields['style'] in (s or set()) for s in observed) else 'Unknown' if None in observed else 'Fail')
    for field in ['occasion','formality']:
        if fields.get(field):states.extend(declaration(g,field,fields[field]) for g in members)
    return 'Fail' if 'Fail' in states else 'Unknown' if 'Unknown' in states else 'Pass'
def scores(members,fields,preferences):
    base=[g for g in members if ROLES[g['category']]!='outerwear']
    supplied=[f for f in ('occasion','style','colours','garment_categories','formality') if fields.get(f) is not None]
    r=sum((F(sum(fields['style'] in (styles(g) or set()) for g in base),len(base)) if f=='style' else F(1) for f in supplied),F())/len(supplied) if supplied else F()
    atoms=[]
    for a,b in combinations(members,2):
        ca,cb=colour(a),colour(b);sa,sb=styles(a),styles(b)
        atoms.extend([F(int(ca==cb or ca in {'black','white','grey'} or cb in {'black','white','grey'})) if ca is not None and cb is not None else None,
                      F(2*len(sa&sb),len(sa)+len(sb)) if sa and sb else None])
    known=[v for v in atoms if v is not None];total=sum(known,F());missing=len(atoms)-len(known)
    lower=total/len(atoms) if atoms else None;upper=(total+missing)/len(atoms) if atoms else None
    c=(lower+upper)/2 if atoms else F(1,2)
    basis='NoPairReference' if not atoms else 'Computed' if not missing else 'FullyConventional' if not known else 'PartiallyConventional'
    raw=total/len(atoms) if atoms and not missing else None
    p=F();den=F()
    for pref in preferences:
        w=F(pref['weight']);den+=w;values=pref['values']
        if pref['type']=='colours':value=F(int(any(colour(g) in values for g in members)))
        elif pref['type']=='styles':value=F(sum(bool((styles(g) or set()) & set(values)) for g in base),len(base))
        else:value=F(int(any(g['category'] in (GROUPS[v['value']] if v['kind']=='group' else (v['value'],)) for v in values for g in members)))
        p+=w*value
    p=p/den if den else F()
    key=tuple((ROLES[g['category']],g['id']) for g in members)
    return {'key':key,'R':r,'C':c,'P':p,'S':F(3,5)*r+F(1,5)*c+F(1,5)*p,'raw_C':raw,
            'basis':basis,'lower':lower,'upper':upper,'atoms':len(atoms),'known':len(known),'structure':SHAPES[tuple(role for role,_ in key)]}
def oracle(rows,owner,fields,preferences):
    eligible=[g for g in strict(rows,owner) if g['preferred_media_id'].strip() and g['category'] in ROLES]
    slots={role:[g for g in eligible if ROLES[g['category']]==role] for role in ['upper','lower','one_piece','outerwear']}
    bases=[*product(slots['upper'],slots['lower']),*((g,) for g in slots['one_piece'])]
    valid=[];unknown=0;failed=0
    for base in bases:
        for outer in [None,*slots['outerwear']]:
            members=base+((outer,) if outer else ())
            state=conditions(members,fields)
            if state=='Pass':valid.append(scores(members,fields,preferences))
            elif state=='Unknown':unknown+=1
            else:failed+=1
    valid.sort(key=lambda s:(-s['S'],-s['R'],-s['C'],-s['P'],s['key']))
    outcome='Selected' if valid else 'NoEligibleGarments' if not eligible else 'InsufficientStructure' if not bases else 'InsufficientEvidence' if unknown else 'NoMatchingCandidates'
    return {'outcome':outcome,'valid':valid,'failed':failed,'unknown':unknown,'strict_ids':sorted(g['id'] for g in strict(rows,owner))}

def audit(record):
    """Return every mismatch; application status is never accepted as proof."""
    errors=[];case=record['case'];result=record['result'];owner=record['owner'];fields=case['fields']
    if record['actual_intent']!=case['intent']:errors.append('intent')
    expected_fields=None if case['intent']!='Supported' else normalized(fields)
    if normalized(record['actual_fields'])!=expected_fields:errors.append('structured_fields')
    if record['outcome']!=case['expected_outcome']:errors.append('downstream_outcome')
    computed=oracle(record['wardrobe_before'],owner,fields,case['preferences'])
    if case['intent']=='Supported' and not case.get('fault') and fields.get('occasion')!='exercise' and fields.get('formality')!='formal':
        if computed['outcome']!=record['outcome']:errors.append('independent_outcome')
    if record['outcome']!='Selected':
        if record['counts_after']!=record['counts_before']:errors.append('terminal_wrote_generation_rows')
        if result.get('id') or result.get('chat_id'):errors.append('terminal_has_recommendation')
        return {'pass':not errors,'errors':errors,'generated':False,'oracle':computed}
    items=result['items'];actual=tuple((i['garment_role'],i['garment_id']) for i in items)
    if not computed['valid']:errors.append('no_independent_valid_candidate');return {'pass':False,'errors':errors,'generated':True,'oracle':computed}
    winner=computed['valid'][0]
    if actual!=winner['key']:errors.append('winner_or_tie_break')
    if tuple(role for role,_ in actual) not in SHAPES:errors.append('structure')
    if len({gid for _,gid in actual})!=len(actual):errors.append('duplicate_member')
    if [i['item_order'] for i in items]!=list(range(1,len(items)+1)):errors.append('member_order')
    strict_ids=set(computed['strict_ids'])
    if not all(gid in strict_ids for _,gid in actual):errors.append('owner_confirmation_availability')
    if not all(any(g['id']==gid for g in record['wardrobe_before']) for _,gid in actual):
        return {'pass':False,'errors':errors+['missing_garment'],'generated':True,'oracle':computed}
    if not record['query_observations'] or not all(gid in {g['garment_id'] for g in record['query_observations'][0]} for _,gid in actual):errors.append('strict_query_origin')
    for observation in record['query_observations']:
        if {g['garment_id'] for g in observation}!=strict_ids:errors.append('strict_query_vs_raw_proof')
    selected=[next(g for g in record['wardrobe_before'] if g['id']==gid) for _,gid in actual]
    if conditions(selected,fields)!='Pass':errors.append('mandatory_condition')
    metadata=result['score_metadata'];decision=metadata['compatibility']['decision']
    components={'R':fraction(metadata['request_match']['summary']['value']) or F(),
                'C':fraction(decision['value']),'P':fraction(metadata['preference']['summary']['value']) or F(),
                'S':fraction(metadata['total'])}
    if any(components[k]!=winner[k] for k in components):errors.append('exact_components_or_total')
    if [fraction(v) for v in metadata['weights']]!=[F(3,5),F(1,5),F(1,5)]:errors.append('weights')
    if result['total_score']!=float(winner['S']):errors.append('public_total')
    if result['request_match_score']!=(float(winner['R']) if any(v is not None for v in normalized(fields).values()) else None):errors.append('public_request_score')
    if result['preference_score']!=(float(winner['P']) if case['preferences'] else None):errors.append('public_preference_score')
    if result['compatibility_score']!=(float(winner['raw_C']) if winner['raw_C'] is not None else None):errors.append('public_raw_compatibility')
    if fraction(metadata['compatibility']['summary']['value'])!=winner['raw_C']:errors.append('raw_compatibility')
    if decision['basis']!=winner['basis']:errors.append('conventional_basis')
    if decision['atomic_count']!=winner['atoms'] or decision['known_count']!=winner['known']:errors.append('atomic_evidence_count')
    if decision['structure']!=winner['structure']:errors.append('decision_structure')
    for field,key in [('lower','lower'),('upper','upper')]:
        if fraction(decision[field])!=winner[key]:errors.append('decision_'+field)
    provenance=result['provenance']
    if provenance['scored_count']!=len(computed['valid']):errors.append('incomplete_scoring')
    if provenance['scoring_profile']!='experimental_compatibility_decision_v1' or provenance['request_evaluator']!='SuitabilityRequestEvaluator':errors.append('profile_or_evaluator')
    if provenance['assistant_execution_selection']['engine']!='compact_exhaustive':errors.append('engine')
    policy=json.loads((CONFIG/'compatibility_decision.v1.json').read_text())
    digest=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if provenance['compatibility_decision_hash']!=digest or provenance['suitability_policy']!='owner-declarations-1.0.0':errors.append('policy_provenance')
    persisted=record['persisted']
    if persisted['metadata']['provenance_json']!=json.dumps(provenance) and json.loads(persisted['metadata']['provenance_json'])!=provenance:errors.append('persisted_provenance')
    if json.loads(persisted['metadata']['score_json'])!=metadata:errors.append('persisted_score')
    if json.loads(persisted['chat']['extracted_entities_json'])!=record['actual_fields'] or persisted['chat']['request_text']!=case['text']:errors.append('persisted_request')
    if persisted['recommendation']['user_id']!=owner or persisted['chat']['user_id']!=owner:errors.append('persisted_owner')
    if [(i['garment_role'],i['garment_id']) for i in persisted['items']]!=list(actual):errors.append('persisted_members')
    for snapshot,item,source in zip(persisted['snapshots'],items,selected):
        if snapshot['garment_id']!=item['garment_id']:errors.append('snapshot_id')
        display=json.loads(snapshot['display_json'])
        if display!={k:source[k] for k in ['name','category','preferred_media_id']}:errors.append('display_snapshot')
        if any(item[k]!=display[k] for k in display):errors.append('display_result')
    if len(persisted['snapshots'])!=len(items):errors.append('snapshot_count')
    if persisted['receipt']['recommendation_id']!=result['id']:errors.append('receipt')
    if record['counts_after']['recommendations']-record['counts_before']['recommendations']!=1:errors.append('not_exactly_one_result')
    if record['quota_before']!=record['quota_after']:errors.append('recommendation_consumed_quota')
    return {'pass':not errors,'errors':errors,'generated':True,'winner':winner,'oracle':computed}
