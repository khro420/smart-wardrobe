"""Closed prototype conventions, not independently validated fashion quality.

Only named, qualified attribute families enter these rules. No image/name,
material, body-fit, cleanliness or dress-code inference is performed.
"""
from fractions import Fraction as F
from .fashion_contract import PROFILE,POLICY_VERSION
from .core import digest

RULES = {
 'version':POLICY_VERSION,'profile':PROFILE,
 'weights':{'colour':'7/20','style':'1/4','pattern':'1/5','layering':'3/20','silhouette':'1/20'},
 'neutral_colours':['black','white','grey','navy','brown','beige','cream'],
 'hue_ring':['red','orange','yellow','green','blue','purple'],
 'adjacent_styles':[['casual','smart casual'],['classic','smart casual'],['classic','formal'],
                    ['minimal','classic'],['minimal','smart casual'],['casual','streetwear'],['casual','sporty']],
 'fitted':['tight','regular','straight','pencil'],'relaxed':['loose','oversized','baggy','wide leg'],
 'colour_rule':'same-or-neutral=1; adjacent-or-opposite-hue=3/4; other=1/4',
 'style_rule':'mean cross-label equality=1, approved adjacency=3/4, other=1/4',
 'pattern_rule':'one-plain=1; both-plain=3/4; identical-pattern=1/2; different-patterns=1/4',
 'layer_rule':'qualified sleeves: outer>=inner=1; outer shorter=1/2',
 'silhouette_rule':'fitted+relaxed=1; both-fitted=3/4; both-relaxed=1/2',
 'unknown_rule':'active unknown weight retained; no fabricated numerical observation; lower contribution zero',
 'na_rule':'structurally absent comparisons excluded from weight denominator',
 'context_rule':'approved context objective or explicit style/formality or inferred formality stays in R, never repeated in C; otherwise existing reviewed-style predicate in half of style factor',
 'human_quality_validation':'NOT_EVALUATED',
}
# Pinned below after authoring: edits must be registered as a new policy.
POLICY_SHA256 = 'eb3dc5f7c6e55bebbb736d4ef87427d5b8bebab241fd246f864afcbc1cdd59fb'

def policy():
    if digest(RULES)!=POLICY_SHA256:raise ValueError('Unregistered fashion policy.')
    return RULES

def pair_value(kind,a,b):
    r=policy()
    if kind=='colour':
        if a==b or a in r['neutral_colours'] or b in r['neutral_colours']:return F(1)
        ring=r['hue_ring']
        if a not in ring or b not in ring:return None
        distance=min((ring.index(a)-ring.index(b))%6,(ring.index(b)-ring.index(a))%6)
        return F(3,4) if distance in (1,3) else F(1,4)
    if kind=='style':
        return F(1) if a==b else F(3,4) if [a,b] in r['adjacent_styles'] or [b,a] in r['adjacent_styles'] else F(1,4)
    if kind=='pattern':
        return F(3,4) if a==b=='plain' else F(1) if 'plain' in (a,b) else F(1,2) if a==b else F(1,4)
    if kind=='layering':
        sleeves=['sleeveless','short','elbow-length','wrist-length']
        if a not in sleeves or b not in sleeves:return None
        return F(1) if sleeves.index(b)>=sleeves.index(a) else F(1,2)
    if kind=='silhouette':
        groups=[r['fitted'],r['relaxed']]
        x=next((i for i,g in enumerate(groups) if a in g),None);y=next((i for i,g in enumerate(groups) if b in g),None)
        if x is None or y is None:return None
        return F(1) if x!=y else F(3,4) if x==0 else F(1,2)
    raise ValueError('Unknown fashion factor.')
