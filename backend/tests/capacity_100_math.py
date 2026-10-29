"""Independent integer capacity calculation; imports no application algorithm."""
from math import comb


def structural_maximum(total=100):
    # Four mutually exclusive role counts. Four permitted structures produce
    # TB, TBO, D and DO distinct combinations respectively.
    best=-1; winners=[]; examined=0
    for tops in range(total+1):
        for bottoms in range(total-tops+1):
            for dresses in range(total-tops-bottoms+1):
                outerwear=total-tops-bottoms-dresses
                count=tops*bottoms+tops*bottoms*outerwear+dresses+dresses*outerwear
                examined+=1
                if count>best: best=count;winners=[]
                if count==best:winners.append({'tops':tops,'bottoms':bottoms,'dresses':dresses,'outerwear':outerwear})
    assert examined==comb(total+3,3)
    return {'total':total,'maximum':best,'maximizers':winners,'integer_role_allocations_checked':examined,
            'formula':'T*B + T*B*O + D + D*O = (T*B+D)*(O+1)',
            'assumptions':'Disjoint upper/lower/one_piece/outerwear roles; four current structures; distinct owned eligible garments. Mandatory constraints can only remove candidates.',
            'at_most_total':'The expression is nondecreasing in every count; any smaller population can be padded to total. Thus this also bounds wardrobes of at most total garments.'}
