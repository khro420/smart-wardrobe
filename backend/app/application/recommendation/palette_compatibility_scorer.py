"""Independent public and compact exact C2 aggregation, with original style rule."""
from fractions import Fraction as F
from itertools import combinations
from app.domain.value_objects.palette_compatibility import Interval,PaletteDecision,PaletteCompatibilityComponent,CompactPaletteDecision,STRUCTURES
from app.domain.value_objects.recommendation_score import ComponentScore,ScoreEvidence
from app.domain.value_objects.compact_recommendation import Measure

def public_atoms(facts,ids,policy):
    achromatic=frozenset(policy.snapshot()['achromatic']);colours=[];styles=[]
    for a,b in combinations(ids,2):
        x,y=facts[a],facts[b];mass_x=sum((c for _,c in x.palette),F());mass_y=sum((c for _,c in y.palette),F())
        q=sum((cx*cy*int(lx==ly or lx in achromatic or ly in achromatic) for lx,cx in x.palette for ly,cy in y.palette),F())
        key=a+':'+b;colours.append(('colour:'+key,Interval(q,q+1-mass_x*mass_y)))
        if x.style_known and y.style_known:
            s=F(2*len(x.styles&y.styles),len(x.styles)+len(y.styles));bound=Interval(s,s)
        else:bound=Interval(F(),F(1))
        styles.append(('style:'+key,bound))
    return tuple(colours+styles)

def public_component(facts,members,policy):
    structure,pairs=STRUCTURES[tuple(role for role,_ in members)]
    atoms=public_atoms(facts,tuple(gid for _,gid in members),policy)
    def summary(name,axis):
        known=sum(b.point for _,b in axis);n=len(axis)
        value=sum((b.lower for _,b in axis),F())/n if n and known==n else None
        return ScoreEvidence(name,value,'NotApplicable' if not n else 'Available' if known==n else 'Unknown',known,n)
    details=(summary('colour_coordination',atoms[:pairs]),summary('style_consistency',atoms[pairs:]),
             *(ScoreEvidence(name,b.lower if b.point else None,'Available' if b.point else 'Unknown',int(b.point),1) for name,b in atoms))
    raw=ComponentScore(ScoreEvidence('compatibility',summary('',atoms).value,summary('',atoms).state,summary('',atoms).observed,len(atoms),
        ('recorded_palette_convention','policy_version:'+policy.snapshot()['version'],'policy_hash:'+policy.hash)),details)
    decision=PaletteDecision(raw,structure,atoms,policy.hash)
    return PaletteCompatibilityComponent(raw.summary,raw.details,decision=decision)

def compact_pair(x,y,achromatic):
    # Independent loop/order from the public selected-object reconstruction.
    lower=F();mx=F();my=sum((c for _,c in y.palette),F())
    for label,c in x.palette:
        mx+=c
        for other,d in y.palette:
            if label==other or label in achromatic or other in achromatic:lower+=c*d
    colour=Interval(lower,lower+F(1)-mx*my)
    style=Interval(F(),F(1))
    if x.style_known and y.style_known:
        value=F(2*len(x.styles.intersection(y.styles)),len(x.styles)+len(y.styles));style=Interval(value,value)
    return colour,style

def compact_decision(intervals,policy_hash):
    n=len(intervals)//2
    def measured(axis):
        known=sum(b.lower==b.upper for b in axis);count=len(axis)
        value=sum((b.lower for b in axis),F())/count if count and known==count else None
        return Measure(value,'NotApplicable' if not count else 'Available' if known==count else 'Unknown',known,count)
    return CompactPaletteDecision(measured(intervals),measured(intervals[:n]),measured(intervals[n:]),intervals,policy_hash)
