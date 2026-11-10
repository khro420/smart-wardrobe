"""Conservative whole-axis entailment; selected-item coincidence is never proof."""
from fractions import Fraction
from app.domain.value_objects.attribute_conditions import ROLES,ANCHORS

SCALAR=frozenset(('primary_colour','secondary_colour','category','pattern','silhouette','neckline','sleeve_length','colour_temperature','colour_dominance'))


def _equal(a,b):return type(a) is type(b) and a==b


def _has(values,value):return any(_equal(v,value) for v in values)


def _like_implied(axis,condition,liked):
    op,values=condition['operator'],condition['values']
    if axis=='palette_coverage':
        return op=='coverage_ge' and any(v['colour']==values[0]['colour'] and Fraction(values[0]['minimum'])>=Fraction(v['minimum']) for v in liked)
    if op=='contains_all':return any(_has(liked,v) for v in values)
    return op in ('in','exact_hex','exact_text','contains_any','bool_eq') and all(_has(liked,v) for v in values)


def _avoids_absent(axis,condition,avoided):
    def overlaps(left,right):
        if _equal(left,right):return True
        if axis in ('primary_colour','secondary_colour') and type(left) is str and type(right) is str:
            return ANCHORS.get(left)==right or ANCHORS.get(right)==left
        return False
    return axis in SCALAR and condition['operator'] in ('in','exact_hex','bool_eq') and all(not any(overlaps(v,a) for a in avoided) for v in condition['values'])


def _none_implies_absence(condition,avoided):
    op,values=condition['operator'],condition['values']
    if op=='contains_all' and len(values)!=1:return False
    if op=='coverage_ge':
        return all(v['colour']==values[0]['colour'] and Fraction(v['minimum'])>=Fraction(values[0]['minimum']) for v in avoided)
    return op in ('in','exact_hex','exact_text','contains_any','contains_all','bool_eq') and all(_has(values,v) for v in avoided)


def hard_mask(axis,settings,conditions,aggregation):
    """A proof conditional on nonempty applicable preference domain; no input edits."""
    if conditions is None:return None
    groups=conditions.to_dict()['groups'] if hasattr(conditions,'to_dict') else conditions['groups']
    roles=set(ROLES[settings['scope']]);liked,avoided=settings['liked'],settings['avoided']
    like_proof=[] if not liked else None
    avoid_proof=[] if not avoided else None
    for group in groups:
        domain=set(ROLES[group['role']]);q=group['quantifier']
        for condition in group['conditions']:
            if condition['attribute']!=axis:continue
            marker=(group['id'],condition['id'])
            if q=='all_present' and roles<=domain:
                if liked and _like_implied(axis,condition,liked):like_proof=[marker]
                if avoided and _avoids_absent(axis,condition,avoided):avoid_proof=[marker]
            if q=='exists' and aggregation=='any' and domain<=roles and liked and _like_implied(axis,condition,liked):like_proof=[marker]
            # Excluding a conjunction cannot prove any one conjunct absent.
            if q=='none' and len(group['conditions'])==1 and roles<=domain and avoided and _none_implies_absence(condition,avoided):avoid_proof=[marker]
    if like_proof is None or avoid_proof is None:return None
    return {'rule':'hard_implied_utility_one_v1','scope':settings['scope'],'conditions':[list(v) for v in sorted(set(like_proof+avoid_proof))]}


def style_r_mask(axis,settings,objective):
    return (axis=='style' and objective is not None and settings['scope']=='base'
            and not settings['avoided'] and settings['liked']==[objective.target])


def legacy_request_mask(axis,settings,request,groups=None):
    """Only existing hard predicates with the same source/aggregation semantics."""
    if request is None or settings['avoided']:return None
    scope=settings['scope'];liked=settings['liked'];marker=None
    if axis=='primary_colour' and scope=='all_selected' and any(_has(liked,v) for v in request.colours or ()):
        marker=('colours',next(v for v in request.colours if _has(liked,v)))
    elif axis=='category' and scope=='all_selected':
        for constraint in request.garment_categories or ():
            allowed=(groups or {}).get(constraint.value,()) if constraint.kind=='group' else (constraint.value,)
            if allowed and all(_has(liked,v) for v in allowed):marker=('garment_categories',constraint.kind+':'+constraint.value);break
    elif axis=='formality' and scope=='all_selected' and request.formality in liked:
        from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
        # Expanded context gates may admit by other evidence. Only the legacy
        # generic contract guarantees the same raw all-member declarations.
        if type(request) is StructuredOutfitRequest:marker=('formality',request.formality)
    return None if marker is None else {'rule':'legacy_required_'+marker[0]+'_v1','scope':scope,'conditions':[['legacy_request',marker[0]+':'+marker[1]]]}
