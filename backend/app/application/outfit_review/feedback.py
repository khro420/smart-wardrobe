"""Conservative, evidence-referenced feedback; no model-invented fashion score.

This prototype has no validated suitability/style measurement. Its rubric is an
explicit proposal and always abstains numerically until all methods are defined.
"""
from .confirmation_v11 import parse_confirmation, current, provenance
from .occasion import Occasion

RUBRIC = "outfit-review-experimental-rubric-1.0.0"
DIMENSIONS = (("occasion_suitability", 40), ("colour_coordination", 25),
              ("style_consistency", 20), ("pattern_layering", 15))


def review_outfit(confirmation, occasion: Occasion) -> dict:
    # Even internal consumers independently validate the full confirmation.
    confirmation = parse_confirmation(confirmation.model_dump_json())
    p = current(confirmation.review)
    modern=confirmation.version.endswith('1.1.0')
    labels={i.id:f"Garment {n}: {i.category.replace('_',' ')}" for n,i in enumerate(p.items,1)}
    refs = [i.id for i in p.items]
    facts = []
    for item in p.items:
        colours = "/".join(item.colours.values) if item.colours.state == "observed" else "colour unknown/uncertain"
        facts.append({"item_id": item.id, "category": item.category, "role": item.role,
                      "text": f"{colours} {item.category.replace('_', ' ')}" if modern else f"{item.id}: {colours} {item.category.replace('_', ' ')}",
                      "basis": "user_reviewed_observation", "region": item.region.model_dump(mode="json")})
    known_colours = sorted({c for i in p.items if i.colours.state == "observed" for c in i.colours.values})
    patterns = [{"item_id": i.id, "values": list(i.pattern.values)} for i in p.items if i.pattern.state == "observed"]
    observed_layers = [l.model_dump() for l in p.layering if l.state == "observed"]
    display=lambda id:labels[id] if modern else id
    unknown = [f"{i.id}.{name}" for i in p.items for name in ("colours", "pattern", "sleeve_length", "sleeve_state")
               if getattr(i, name).state != "observed"]
    label = occasion.context.replace(".", " / ").replace("_", " ")
    dress = f"You explicitly specified {occasion.dress_code or occasion.formality}." if occasion.dress_code or occasion.formality else "No dress code was supplied; none has been assumed."
    sections = [
        {"dimension": "occasion_suitability", "text": f"Occasion interpreted as {label}; role: {occasion.role}. {dress} Garment construction and venue-specific dress rules are not established by these observations, so suitability is not certified.", "item_ids": refs},
        {"dimension": "colour_coordination", "text": (f"Recorded colours: {', '.join(known_colours)}. Consider repeating one of these colours if you want a more connected palette; this is a styling option, not a measured quality rating." if known_colours else "No colours are sufficiently recorded for colour-coordination feedback; mark visible colours or retain Unknown."), "item_ids": [i.id for i in p.items if i.colours.state == "observed"]},
        {"dimension": "style_consistency", "text": "The inventory records clothing type, not a verified aesthetic style. A style-consistency rating cannot be justified from category alone.", "item_ids": refs},
        {"dimension": "pattern_layering", "text": (f"Recorded patterns: {'; '.join(display(x['item_id']) + ': ' + '/'.join(x['values']) for x in patterns)}. " if patterns else "Patterns remain unknown. ") + (f"Recorded layering: {'; '.join(display(x['over']) + ' over ' + display(x['under']) for x in observed_layers)}. Keep these visible layers intentional rather than adding an assumed hidden layer." if observed_layers else "No definite layering relationship was recorded; none is inferred."), "item_ids": [i["item_id"] for i in patterns] + [x[k] for x in observed_layers for k in ("over", "under")]},
    ]
    suggestions = ["Check the venue's stated requirements before relying on this outfit for admission or a formal event."]
    if unknown:
        suggestions.append("Review the listed unknown visual details only when visible; do not guess hidden information.")
    if p.footwear_visibility in ("unknown", "not_visible"):
        suggestions.append("Footwear is not established in this photograph. Include it in a new photo if it is important to the occasion.")
    if occasion.requirements:
        suggestions.append("Your additional conditions and optional wishes are retained, but this basic visual summary does not independently certify them." if modern else "Explicit requirements were retained, but this visual prototype does not certify every requirement: " + "; ".join(occasion.requirements))
    return {"version": "outfit-review-feedback-1.1.0" if confirmation.version.endswith('1.1.0') else "outfit-review-feedback-1.0.0", "feedback_source":"descriptive_cpu_summary", "confirmation_sha256": confirmation.review_sha256,
            "occasion": occasion.model_dump(mode="json"), "overall_assessment": f"Confirmation-based review of {len(p.items)} visible clothing items. Numerical suitability is not established.",
            "facts": facts, "sections": sections,
            "strengths": ["The review uses the specific inventory you confirmed: " + "; ".join(f["text"] for f in facts)],
            "potential_improvements": suggestions, "unknown_details": unknown,
            "limitations": ["AI observations and user assertions are fallible; confirmation is not measured model accuracy.",
                            "Fabric composition, brands, body measurements and hidden garments are not assessed.",
                            "No validated fashion-quality or style-suitability metric is implemented."],
            "provenance": provenance(confirmation.review),
            "rubric": {"version": RUBRIC, "experimental": True, "dimensions": [
                {"name": name, "weight_percent": weight, "score": None, "status": "assessment_method_not_validated"} for name, weight in DIMENSIONS],
                "score": None, "weights_redistributed": False,
                "message": "Not enough information to provide a reliable score"}}
