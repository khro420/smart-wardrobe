"""Independent entailment examples and concrete countermodels from frozen contract."""
from types import SimpleNamespace
from app.application.recommendation.attribute_preference_masks import hard_mask,style_r_mask


def settings(liked,avoided=(),scope='all_selected'):
    return {'scope':scope,'importance':'1','liked':list(liked),'avoided':list(avoided)}


def conditions(axis,values,q='all_present',scope='all_selected',op='in',extra=None):
    return {'groups':[{'id':'g01','role':scope,'quantifier':q,'conditions':[{'id':'c01','attribute':axis,'operator':op,'values':values}]+(extra or [])}]}


def test_HM01_universal_plain_masks_identical_mean_but_HM02_existential_does_not():
    s=settings(['plain'])
    assert hard_mask('pattern',s,conditions('pattern',['plain']),'mean')
    assert hard_mask('pattern',s,conditions('pattern',['plain'],q='exists'),'mean') is None


def test_HM03_existential_subset_entails_any_member_like():
    assert hard_mask('primary_colour',settings(['blue']),conditions('primary_colour',['blue'],q='exists',scope='upper'),'any')


def test_HM04_none_floral_masks_identical_avoid_only_and_HM05_conjunction_does_not():
    s=settings([],['floral'])
    assert hard_mask('pattern',s,conditions('pattern',['floral'],q='none'),'mean')
    assert hard_mask('pattern',s,conditions('pattern',['floral'],q='none',extra=[{'id':'c02','attribute':'material','operator':'contains_any','values':['cotton']}]),'mean') is None


def test_HM06_HM11_material_membership_does_not_prove_other_fibre_absence():
    c=conditions('material',['cotton'],op='contains_any')
    assert hard_mask('material',settings([],['wool']),c,'mean') is None
    assert hard_mask('material',settings(['cotton'],['wool']),c,'mean') is None


def test_HM07_primary_does_not_imply_palette_and_HM08_threshold_same_channel_is_monotonic():
    assert hard_mask('palette_colour',settings(['blue']),conditions('primary_colour',['blue']),'mean') is None
    s=settings([{'colour':'blue','minimum':'0.50'}]);c=conditions('palette_coverage',[{'colour':'blue','minimum':'0.75'}],op='coverage_ge')
    assert hard_mask('palette_coverage',s,c,'mean')
    c['groups'][0]['quantifier']='exists'
    assert hard_mask('palette_coverage',s,c,'mean') is None  # HM09


def test_HM10_scalar_pattern_disjointness_proves_avoided_absence():
    assert hard_mask('pattern',settings(['plain'],['floral']),conditions('pattern',['plain']),'mean')


def test_HM12_HM13_original_R_style_duplicate_rule_has_its_own_name_and_scope():
    objective=SimpleNamespace(target='casual')
    assert style_r_mask('style',settings(['casual'],scope='base'),objective)
    assert not style_r_mask('style',settings(['casual'],scope='outerwear'),objective)
    assert not style_r_mask('style',settings(['casual'],['formal'],scope='base'),objective)


def test_named_colour_and_exact_anchor_avoid_are_not_proved_disjoint():
    assert hard_mask('primary_colour',settings(['blue'],['#0000ff']),conditions('primary_colour',['blue']),'any') is None
    assert hard_mask('secondary_colour',settings(['#0000ff'],['blue']),conditions('secondary_colour',['#0000ff'],op='exact_hex'),'mean') is None
