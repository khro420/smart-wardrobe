"""Grounded model-selected judgments and an independent experimental rubric.

The model chooses qualitative anchors, never a final number. Published mappings
are subjective assessment anchors, not validated universal fashion standards.
Concrete clothing statements are rendered only from the confirmed fact catalog.
"""
from fractions import Fraction
from copy import deepcopy
import json
from typing import Literal
from pydantic import Field
from .contract import Frozen,Short
from .confirmation_v11 import parse_confirmation,current,provenance

DIMENSIONS=('occasion_suitability','colour_coordination','style_consistency','pattern_layering')
WEIGHTS=(40,25,20,15)
ANCHORS={'strong':90,'coherent':75,'mixed':50,'needs_attention':25,'not_assessable':None}
REASONS={
 'occasion_suitability':('activity_alignment','dress_code_alignment','occasion_uncertain'),
 'colour_coordination':('repeated_colour','palette_unity','palette_contrast','competing_colours','colour_uncertain'),
 'style_consistency':('style_alignment','style_mixture','style_uncertain'),
 'pattern_layering':('pattern_balance','pattern_competition','layering_balance','pattern_uncertain'),
}


class Judgment(Frozen):
    dimension: Literal['occasion_suitability','colour_coordination','style_consistency','pattern_layering']
    anchor: Literal['strong','coherent','mixed','needs_attention','not_assessable']
    reason: Literal['activity_alignment','dress_code_alignment','occasion_uncertain','repeated_colour','palette_unity','palette_contrast','competing_colours','colour_uncertain','style_alignment','style_mixture','style_uncertain','pattern_balance','pattern_competition','layering_balance','pattern_uncertain']
    evidence_refs: tuple[Short,...]=Field(max_length=96)


class Suggestion(Frozen):
    action: Literal['repeat_recorded_colour','simplify_pattern_mix','align_recorded_styles','review_visible_layers','check_dress_code','clarify_footwear','resolve_unknown_details']
    item_refs: tuple[Short,...]=Field(max_length=24)


class Judgments(Frozen):
    version: Literal['outfit-review-judgments-1.0.0']
    dimensions: tuple[Judgment,...]=Field(min_length=4,max_length=4)
    suggestions: tuple[Suggestion,...]=Field(min_length=1,max_length=5)


def catalog(confirmation):
    p=current(confirmation.review);facts={};aliases={}
    for n,item in enumerate(p.items,1):
        alias=f'item{n}';aliases[alias]=item.id
        for field in ('category','role'):
            value=getattr(item,field)
            if value!='unknown':facts[f'{alias}.{field}']=[value]
        for field in ('colours','pattern','sleeve_length','sleeve_state','style'):
            value=getattr(item,field,None)
            if value is not None and value.state=='observed':facts[f'{alias}.{field}']=list(value.values)
    for n,layer in enumerate(p.layering,1):
        if layer.state=='observed':facts[f'layer{n}']=[layer.over,layer.under]
    return p,facts,aliases


def evidence_requirements(p,occasion):
    """Eligibility for a dimension score, not a fashion-classification algorithm."""
    category=all(i.category!='unknown' and i.role!='unknown' for i in p.items)
    colours=all(i.colours.state=='observed' and i.colours.values and 'multicoloured' not in i.colours.values for i in p.items)
    styles=all(getattr(i,'style',None) is not None and i.style.state=='observed' for i in p.items)
    patterns=all(i.pattern.state=='observed' for i in p.items) and all(l.state=='observed' for l in p.layering)
    feet=getattr(p,'feet_observation','uncertain') in ('shoes_visible','bare_feet_visible')
    roles={i.role for i in p.items}
    clothing_coverage='one_piece' in roles or {'upper','lower'}<=roles
    # This v1 rubric cannot independently certify arbitrary additional garment
    # requirements (e.g. composition). Retain them, withhold occasion score.
    occasion_ok=category and styles and feet and clothing_coverage and not occasion.requirements
    return {
      'occasion_suitability':(occasion_ok,'Occasion scoring needs a reviewed one-piece or upper/lower outfit, known categories/appearance styles, a resolved visible-foot view and no unassessed additional requirements.'),
      'colour_coordination':(colours,'Record the visible named colours of every garment; uncertain or unspecified multicolour palettes cannot support this score.'),
      'style_consistency':(category and styles,'Record known garment categories and explicitly reviewed visual styles; category alone does not establish style.'),
      'pattern_layering':(patterns,'Review patterns for every garment and resolve uncertain layering before scoring this dimension.'),
    }


def request_payload(confirmation,occasion):
    confirmation=parse_confirmation(confirmation.model_dump_json())
    p,facts,aliases=catalog(confirmation)
    return {'version':'outfit-review-assessment-input-1.0.0','facts':facts,'items':list(aliases),
            'occasion':{'context':occasion.context,'role':occasion.role,'explicit_dress_code':occasion.dress_code,'explicit_formality':occasion.formality},
            'additional_requirements':list(occasion.requirements),
            'feet_observation':getattr(p,'feet_observation','uncertain'),
            'score_eligibility':{k:v[0] for k,v in evidence_requirements(p,occasion).items()}}


def decoding_schema(confirmation,occasion):
    """Bind generated references to this confirmed catalog before inference.

    This narrows decoding to existing verification requirements. It never adds
    citations to a completed model response or turns partial evidence into a score.
    Historical judgment readers and the independent assessor remain unchanged.
    """
    confirmation=parse_confirmation(confirmation.model_dump_json())
    p,facts,aliases=catalog(confirmation)
    eligibility=evidence_requirements(p,occasion)
    schema=deepcopy(Judgments.model_json_schema())
    base=schema['$defs']['Judgment']
    dimensions=[]
    fields=(('category','style'),('colours',),('category','style'),('pattern',))
    for name,group in zip(DIMENSIONS,fields):
        missing=deepcopy(base)
        missing['properties'].update(dimension={'type':'string','const':name},anchor={'type':'string','const':'not_assessable'},
            reason={'type':'string','const':REASONS[name][-1]},evidence_refs={'type':'array','const':[]})
        choices=[missing]
        if eligibility[name][0]:
            required=sorted({f'{alias}.{field}' for alias in aliases for field in group}|
                ({ref for ref in facts if ref.startswith('layer')} if name=='pattern_layering' else set()))
            assert set(required)<=set(facts)
            assessed=deepcopy(base)
            reasons=[r for r in REASONS[name] if not r.endswith('_uncertain')]
            if name=='occasion_suitability' and (occasion.dress_code or occasion.formality):reasons=['dress_code_alignment']
            assessed['properties'].update(dimension={'type':'string','const':name},
                anchor={'type':'string','enum':[a for a in ANCHORS if a!='not_assessable']},
                reason={'type':'string','enum':reasons},evidence_refs={'type':'array','const':required})
            choices.insert(0,assessed)
        dimensions.append({'anyOf':choices})
    # Pinned llama.cpp chooses "items" ahead of "prefixItems" and does not
    # parse a boolean item schema. Four prefix slots + exact bounds suffice.
    schema['properties']['dimensions']={'type':'array','prefixItems':dimensions,'minItems':4,'maxItems':4}
    # No decorated references or invented IDs in suggestions either.
    schema['$defs']['Suggestion']['properties']['item_refs']['items']={'type':'string','enum':list(aliases)}
    return schema


SYSTEM_PROMPT="""You are an experimental outfit-review rater, not an observer of new garments.
Use only the supplied user-reviewed clothing facts and structured occasion. You
have no permission to infer new garments, materials, brands, body shape, hidden
footwear, or dress codes. Do not evaluate attractiveness, weight, or body shape.
Choose one qualitative assessment for each of the four dimensions. Never output
an overall number. These are subjective judgments, not certified venue rules.
Anchors: strong = clear, well-supported coherence for this dimension;
coherent = generally aligned with minor reservations; mixed = meaningful tension;
needs_attention = substantial supported mismatch; not_assessable = insufficient facts.
Give only existing evidence_refs, using category/style facts for style, colours
for colour, pattern/layer records for pattern, and known clothing facts for occasion.
Use not_assessable when score_eligibility is false. Missing facts must not become
invented observations. There is no default formal dress code for weddings or interviews.
Choose reason codes belonging to the corresponding dimension. repeated_colour
requires a shared named colour in at least two cited items; pattern suggestions
require visible patterns and style suggestions require recorded styles.
For an assessable dimension, cite the relevant facts for EVERY selected item,
not just a convenient subset. Occasion/style require category and style refs;
colour requires colours refs; pattern requires pattern refs and recorded layers.
palette_unity describes a single recorded named-colour palette. Contrast/competing
colours require multiple recorded colours. style_mixture needs different recorded
styles; pattern_competition needs multiple non-plain patterns. Do not invent tension.
When an explicit dress code/formality is provided, use dress_code_alignment for
an assessed occasion judgment; do not rate only the general activity instead.
Select specific practical suggestions grounded in the recorded items. Suggestions
are optional changes, never claims that additional clothing is already present.
Output the requested structured JSON only. No free-text claims or final scores."""


def assess(confirmation,occasion,raw,run):
    confirmation=parse_confirmation(confirmation.model_dump_json())
    if len(raw)>65536:raise ValueError('Assessment exceeds bound')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate judgment field')
            result[key]=value
        return result
    json.loads(raw,object_pairs_hook=unique)
    proposal=Judgments.model_validate_json(raw)
    p,facts,aliases=catalog(confirmation)
    if {j.dimension for j in proposal.dimensions}!=set(DIMENSIONS):raise ValueError('Four unique dimension judgments required')
    eligibility=evidence_requirements(p,occasion)
    item_by_alias={alias:next(i for i in p.items if i.id==id) for alias,id in aliases.items()}
    dimensions=[];sections=[];strengths=[];improvements=[]
    for name,weight in zip(DIMENSIONS,WEIGHTS):
        judgment=next(j for j in proposal.dimensions if j.dimension==name)
        if judgment.reason not in REASONS[name] or len(set(judgment.evidence_refs))!=len(judgment.evidence_refs):raise ValueError('Wrong or duplicate evidence for judgment')
        if judgment.reason.endswith('_uncertain') and judgment.anchor!='not_assessable':raise ValueError('An uncertain judgment cannot supply a score')
        if any(ref not in facts for ref in judgment.evidence_refs):raise ValueError('Unconfirmed model fact reference')
        relevant={'colour_coordination':('colours',),'style_consistency':('style',),'pattern_layering':('pattern',)}.get(name,('category','style','role'))
        if judgment.anchor!='not_assessable' and (not judgment.evidence_refs or not any(ref.startswith('layer') and name=='pattern_layering' or ref.rsplit('.',1)[-1] in relevant for ref in judgment.evidence_refs)):
            raise ValueError('Judgment lacks relevant evidence')
        if judgment.reason=='repeated_colour':
            sets=[set(facts[r]) for r in judgment.evidence_refs if r.endswith('.colours')]
            if len(sets)<2 or not any(a & b for n,a in enumerate(sets) for b in sets[n+1:]):raise ValueError('No cited shared colour')
        named_colours={c for ref in judgment.evidence_refs if ref.endswith('.colours') for c in facts[ref] if c!='multicoloured'}
        if judgment.reason=='palette_unity' and len(named_colours)!=1:raise ValueError('Palette unity lacks a single named palette')
        if judgment.reason in ('palette_contrast','competing_colours') and len(named_colours)<2:raise ValueError('Colour contrast needs different recorded colours')
        if judgment.reason=='style_mixture' and len({v for r in judgment.evidence_refs if r.endswith('.style') for v in facts[r]})<2:raise ValueError('No cited style mixture')
        if judgment.reason=='pattern_competition' and sum(r.endswith('.pattern') and any(v!='plain' for v in facts[r]) for r in judgment.evidence_refs)<2:raise ValueError('No cited competing patterns')
        if judgment.reason=='layering_balance' and not any(r.startswith('layer') for r in judgment.evidence_refs):raise ValueError('No cited visible layers')
        allowed,missing=eligibility[name]
        if name=='occasion_suitability' and (occasion.dress_code or occasion.formality) and judgment.anchor!='not_assessable' and judgment.reason!='dress_code_alignment':
            raise ValueError('Explicit dress requirement was not assessed')
        if allowed and judgment.anchor!='not_assessable':
            fields={'occasion_suitability':('category','style'),'colour_coordination':('colours',),
                    'style_consistency':('category','style'),'pattern_layering':('pattern',)}[name]
            required={f'{alias}.{field}' for alias in aliases for field in fields}
            if name=='pattern_layering':required|={ref for ref in facts if ref.startswith('layer')}
            if not required<=set(judgment.evidence_refs):raise ValueError('Whole-outfit judgment omits confirmed garment evidence')
        value=ANCHORS[judgment.anchor] if allowed else None
        refs=[aliases[r.split('.')[0]] for r in judgment.evidence_refs if r.split('.')[0] in aliases]
        details=[];by_item={}
        for ref in judgment.evidence_refs:
            if ref.startswith('layer'):details.append(' over '.join(next((i.category.replace('_',' ') for i in p.items if i.id==id),'Unknown garment') for id in facts[ref]))
            else:
                alias,field=ref.split('.')
                by_item.setdefault(alias,[])
                if field not in ('category','role','colours'):by_item[alias].append(f"{field.replace('_',' ')} {' / '.join(facts[ref])}")
        for alias,attributes in by_item.items():
            item=item_by_alias[alias]
            title=f"{' / '.join(item.colours.values)+' ' if item.colours.state=='observed' else ''}{item.category.replace('_',' ')}"
            details.append(title+(' ('+', '.join(attributes)+')' if attributes else ''))
        label=judgment.anchor.replace('_',' ')
        intro={
          'occasion_suitability':f"For {occasion.context.replace('.',' / ').replace('_',' ')}, the AI's subjective activity-alignment assessment is {label}. " + (f"Your explicit requirement is {occasion.dress_code or occasion.formality}. " if occasion.dress_code or occasion.formality else 'No dress code was supplied or assumed. '),
          'colour_coordination':f"The AI rates the recorded palette as {label} ({judgment.reason.replace('_',' ')}). ",
          'style_consistency':f"The AI rates the reviewed appearance styles as {label} ({judgment.reason.replace('_',' ')}). ",
          'pattern_layering':f"The AI rates the confirmed patterns/layers as {label} ({judgment.reason.replace('_',' ')}). ",
        }[name]
        if value is None:intro=f"This dimension is not sufficiently assessable. {missing} "
        text=intro+('Supported record: '+'; '.join(details)+'.' if details else 'The missing details remain Unknown.')
        dimensions.append({'name':name,'weight_percent':weight,'score':value,'anchor':judgment.anchor,
                           'status':'assessed' if value is not None else 'not_assessable','explanation':text,'evidence_refs':list(judgment.evidence_refs)})
        sections.append({'dimension':name,'text':text,'item_ids':list(dict.fromkeys(refs))})
        if value is not None:
            summary=f"{name.replace('_',' ').capitalize()}: the AI identified {judgment.reason.replace('_',' ')} in {', '.join(item_by_alias[a].category.replace('_',' ') for a in by_item)} ({label})."
            (strengths if value>=75 else improvements).append(summary)
    suggestions=[]
    for suggestion in proposal.suggestions:
        if len(set(suggestion.item_refs))!=len(suggestion.item_refs):raise ValueError('Duplicate suggestion item')
        if any(ref not in aliases for ref in suggestion.item_refs):raise ValueError('Unknown suggestion item')
        selected=[item_by_alias[a] for a in suggestion.item_refs]
        names=', '.join(i.category.replace('_',' ') for i in selected)
        action=suggestion.action
        if action=='repeat_recorded_colour':
            palette=sorted({c for i in selected if i.colours.state=='observed' for c in i.colours.values if c!='multicoloured'})
            if not palette:raise ValueError('Colour advice has no confirmed palette')
            text=f"For the {names}, consider repeating {' or '.join(palette)} in your styling for continuity. This is an optional change, not an observed extra item."
        elif action=='simplify_pattern_mix':
            if not selected or any(i.pattern.state!='observed' for i in selected):raise ValueError('Pattern advice lacks observations')
            text=f"Consider letting one recorded pattern in the {names} lead and simplifying the others if you want a quieter visual balance."
        elif action=='align_recorded_styles':
            if not selected or any(getattr(i,'style',None) is None or i.style.state!='observed' for i in selected):raise ValueError('Style advice lacks observations')
            text=f"For the {names}, decide whether you want their recorded styles to read consistently or as a deliberate contrast for this occasion."
        elif action=='review_visible_layers':
            if not p.layering:raise ValueError('No recorded layers support this advice')
            text='Review the recorded over/under relationships so the visible layers look intentional; no hidden layer is assumed.'
        elif action=='check_dress_code':text='Check the actual venue or organizer requirements; this review does not impose or certify an unstated dress code.'
        elif action=='clarify_footwear':
            if getattr(p,'feet_observation','uncertain')=='shoes_visible':raise ValueError('Footwear already resolved')
            text='Footwear is not fully established. A photo including the visible shoes can support a more complete occasion assessment; socks do not establish shoes.'
        else:text='Leave genuinely unassessable details Unknown; correct the visible missing details before relying on a complete score.'
        suggestions.append(text)
    complete=all(d['score'] is not None for d in dimensions)
    total=sum((Fraction(d['score']*d['weight_percent'],100) for d in dimensions),Fraction()) if complete else None
    facts_display=[{'item_id':i.id,'category':i.category,'role':i.role,'text':f"{' / '.join(i.colours.values) if i.colours.state=='observed' else 'Colour unknown'} {i.category.replace('_',' ')}"} for i in p.items]
    return {'version':'outfit-review-feedback-1.1.0','feedback_source':'local_model_grounded_anchors','confirmation_sha256':confirmation.review_sha256,
            'occasion':occasion.model_dump(mode='json'),'overall_assessment':('The confirmed outfit has a complete experimental assessment.' if complete else 'The confirmed outfit supports a partial assessment; the overall score is withheld.'),
            'facts':facts_display,'sections':sections,'strengths':strengths or ['No clearly supported strong dimension was identified; see individual assessments.'],
            'potential_improvements':improvements,'suggestions':suggestions,
            'unknown_details':[f'{i.id}.{field}' for i in p.items for field in ('colours','pattern','style','sleeve_length','sleeve_state') if getattr(i,field,None) is None or getattr(i,field).state!='observed'],
            'limitations':['Experimental subjective model judgments, not universal fashion standards or venue certification.','User confirmation is not measured AI recognition accuracy.','No fabric composition, brand, body shape or hidden clothing inference.'],
            'provenance':provenance(confirmation.review),'model_run':run.model_dump(mode='json'),'raw_judgments':raw,
            'rubric':{'version':'outfit-review-experimental-rubric-1.1.0','experimental':True,'dimensions':dimensions,'score':round(float(total),1) if total is not None else None,
                      'exact_score':str(total) if total is not None else None,'weights_redistributed':False,
                      'message':'Experimental outfit assessment' if complete else 'Not enough information to provide a reliable score'}}
