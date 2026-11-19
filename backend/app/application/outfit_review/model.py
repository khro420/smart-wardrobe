"""Pure adapter for bounded local VLM output; no model loading or app activation."""
from .contract import ImageIdentity, ModelRun, Observation, digest, issues, parse_prediction

DEFAULT_CANDIDATE = "Qwen3-VL-4B-Instruct-Q4_K_M"
PROMPT_VERSION = "outfit-review-grounding-prompt-1.0.0"
SYSTEM_PROMPT = """Observe pixels, not a plausible completed outfit. Output only the provided JSON schema.
Identify visible people and their full visible regions before the inventory. With several people,
leave target_person_id null and items empty: a user must choose the subject. With one person,
include every visible worn garment, including genuine layers, and only visible footwear.
All boxes use 0..1000 on the supplied oriented image. Each physical garment appears once;
use one footwear_pair item for a visible pair. If two records may be the same garment, report
an identity_question instead of guessing. Never merge actual overlapping layers by box overlap.
category names describe physical clothing; role describes upper/lower/outerwear/one_piece/footwear.
A dress is one_piece; jacket/coat are outerwear. If skirt versus shorts is unclear, category is
unknown with both alternatives. An unknown detail is not an extra garment. Footwear_visibility
is not evidence that shoes must exist: not_visible means no footwear inventory item.
Use supported visible colour labels, or unknown; never infer fabric composition, brand, comfort,
body measurements or hidden details. Pattern may be unknown. Sleeve length and rolled state
are separate; rolled sleeves do not prove the original sleeve length. Unknown facts have empty
values; uncertain facts name alternatives. Do not turn uncertainty into observed certainty.
Record visible layering only. Do not list bags, chairs, phones or other background objects as
clothing. These are visual proposals awaiting user review, not verified garment evidence."""
USER_PROMPT = "Identify the visibly worn clothing for review, following the schema. Do not complete cropped bodies or guess hidden properties."


def observe(image: ImageIdentity, run: ModelRun, raw_response: str) -> Observation:
    if len(raw_response) > 65536:
        raise ValueError("Model response exceeds observation bound")
    return Observation(image=image, run=run, raw_response=raw_response, prediction=parse_prediction(raw_response))


def preview(observation: Observation) -> dict:
    """Fixture/dev preview data; preserve all proposals and show blocking issues."""
    return {
        "observation_sha256": digest(observation),
        "image": observation.image.model_dump(mode="json"),
        "prediction": observation.prediction.model_dump(mode="json"),
        "issues": list(issues(observation.prediction)),
        "evidence": [{"id": i.id, "source": "vlm_prediction_not_visual_verification",
                      "raw_response_path": f"/items/{n}", "region": i.region.model_dump(mode="json"),
                      "image_sha256": observation.image.original_sha256,
                      "run_id": observation.run.run_id} for n, i in enumerate(observation.prediction.items)],
        "unknown_properties": ["material_composition", "brand", "comfort", "body_measurements"],
        "confirmation_required": True,
    }
