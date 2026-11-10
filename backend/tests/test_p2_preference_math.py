"""Frozen literal Fraction expectations, never generated from P2 output."""
from fractions import Fraction as F
import pytest
from tests.test_p2_preference_contracts import LABELS
from app.application.recommendation.attribute_preference_scorer import Utility,utility,weighted,mean


@pytest.mark.parametrize('case',LABELS['acceptance']['arithmetic'],ids=lambda c:c['id'])
def test_frozen_exact_arithmetic(case):
    result=weighted(tuple((F(w),Utility(F(v),F(v),'Available',1,1)) for w,v in zip(case['axis_weights'],case['axis_utilities'])))
    assert result.lower==F(case['P'])
    assert F(3,5)+F(1,5)+F(1,5)*result.lower==F(case['T'])


@pytest.mark.parametrize('case',LABELS['acceptance']['truth_table'])
def test_all_frozen_three_valued_utility_completions(case):
    states={'T':'Pass','F':'Fail','U':'Unknown'}
    result=utility((states[case['like_OR']],),(states[case['avoid_OR']],))
    assert (result.lower,result.upper)==(F(case['lower']),F(case['upper']))


def test_partial_known_like_cannot_hide_unresolved_avoid():
    assert utility(('Pass',),('Unknown',)).lower==0
    assert utility(('Pass',),('Unknown',)).upper==1
    assert utility(('Pass','Unknown'),()).lower==1
    assert utility((),('Fail',)).lower==1
    assert utility(('Fail',),('Unknown',)).upper==0


def test_unknown_member_and_not_applicable_keep_active_denominators():
    a=utility(('Pass',),());b=utility(('Unknown',),())
    result=mean((a,b));assert (result.lower,result.upper)==(F(1,2),F(1))
    result=weighted(((F(1),a),(F(1),Utility(F(),F(),'NotApplicable'))))
    assert result.lower==F(1,2)


def test_raw_optimistic_preference_never_becomes_earned_utility():
    unknown=utility(('Unknown',),())
    assert F(3,5)+F(1,5)+F(1,5)*unknown.lower==F(4,5)
    assert unknown.upper==1
