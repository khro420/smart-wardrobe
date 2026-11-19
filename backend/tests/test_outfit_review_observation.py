"""Pure observation/correction contracts; no GPU, live DB, or wardrobe registration."""
from io import BytesIO
import json
from hashlib import sha256

from PIL import Image
import pytest
from pydantic import ValidationError

from app.application.outfit_review.contract import (
    Box, ModelRun, Observation, Prediction, digest, issues, parse_prediction,
)
from app.application.outfit_review.confirmation import (
    Authority, Confirmation, Correction, Review, begin, confirm, current, provenance, revise, verify,
)
from app.application.outfit_review.images import prepare_image
from app.application.outfit_review.model import observe, preview


def fact(value=None, state="observed"):
    return {"state": state if value else "unknown", "values": [value] if value else []}


def item(id="dress", **changes):
    value = dict(id=id, person_id="p1", region={"xyxy": [100, 100, 800, 800]}, category="dress",
                 category_alternatives=[], role="one_piece", visibility="visible", unit="single",
                 colours=fact("multicoloured"), pattern=fact(), sleeve_length=fact(), sleeve_state=fact())
    value.update(changes)
    return value


def prediction(**changes):
    value = dict(version="outfit-review-observation-1.0.0", scene="single_person",
                 people=[dict(id="p1", region={"xyxy": [0, 0, 1000, 1000]})], target_person_id="p1",
                 footwear_visibility="not_visible", items=[item()], layering=[], identity_questions=[])
    value.update(changes)
    return value


def parse(value):
    return parse_prediction(json.dumps(value))


def image_bytes():
    out = BytesIO()
    Image.new("RGB", (128, 192), "blue").save(out, "PNG")
    return out.getvalue()


def observation(value=None):
    identity, _ = prepare_image(image_bytes())
    run = ModelRun(model="Qwen3-VL-4B-Instruct-Q4_K_M", revision="pinned-revision", weights_sha256="a"*64,
                   projector_sha256="b"*64, runtime="llama.cpp", runtime_build="b12359",
                   runtime_executable_sha256="c"*64, settings_sha256="d"*64, prompt_sha256="e"*64,
                   run_id="test-only-not-real-inference", generated_at="2026-11-20T00:00:00Z")
    return observe(identity, run, json.dumps(value or prediction()))


def authority(obs=None, user="owner"):
    obs = obs or observation()
    return Authority(authenticated_user_id=user, image_owner_id=user, image_sha256=obs.image.original_sha256)


def changed(review, value, changes):
    return revise(review, authority(review.original), digest(review), parse(value),
                  tuple(Correction(operation=op, subject=subject, reason="Reviewed visible image") for op, subject in changes))


def test_raw_observation_and_confirmation_round_trip():
    obs = observation()
    assert Observation.model_validate_json(obs.model_dump_json()) == obs
    review = begin(obs, authority(obs))
    confirmation = confirm(review, authority(obs), digest(review), inventory_reviewed=True)
    assert Confirmation.model_validate_json(confirmation.model_dump_json()) == confirmation
    assert preview(obs)["evidence"][0]["raw_response_path"] == "/items/0"
    assert set(provenance(review).values()) == {"ai_prediction_user_reviewed"}


@pytest.mark.parametrize("bad", [(-1, 0, 50, 50), (0, 0, 1001, 20), (0, 0, 0, 1), (10, 20, 1, 2), (False, 0, 10, 10), (0.5, 0, 20, 20)])
def test_region_bounds_and_strict_types(bad):
    with pytest.raises(ValidationError):
        Box(xyxy=bad)


@pytest.mark.parametrize("field,value", [("material", "cotton"), ("brand", "guessed"), ("confidence", 0.99)])
def test_no_unsupported_composition_or_invented_confidence(field, value):
    with pytest.raises(ValidationError):
        parse(prediction(items=[item(**{field: value})]))


@pytest.mark.parametrize("changes,code", [
    ({"category": "dress", "role": "upper"}, "category_role_conflict"),
    ({"category": "jacket", "role": "upper"}, "category_role_conflict"),
    ({"category": "coat", "role": "upper"}, "category_role_conflict"),
    ({"visibility": "not_visible"}, "not_an_observed_item"),
    ({"person_id": "foreign-person"}, "wrong_person"),
    ({"unit": "unresolved"}, "unresolved_identity"),
    ({"unit": "footwear_pair"}, "invalid_pair"),
])
def test_exposed_architectural_conflicts_remain_visible(changes, code):
    p = parse(prediction(items=[item(**changes)]))
    assert any(code in e for e in issues(p))
    obs = observation(prediction(items=[item(**changes)]))
    assert preview(obs)["prediction"]["items"]  # Nothing silently dropped.
    review = begin(obs, authority(obs))
    with pytest.raises(ValueError, match="Resolve"):
        confirm(review, authority(obs), digest(review), inventory_reviewed=True)


def test_skirt_shorts_uncertainty_is_one_unresolved_item_not_two_garments():
    value = prediction(items=[item(category="unknown", role="lower", category_alternatives=["skirt", "shorts"])])
    p = parse(value)
    assert len(p.items) == 1 and "dress:unresolved_identity" in issues(p)
    review = begin(observation(value), authority())
    # The user may explicitly leave type unknown rather than guessing skirt/shorts.
    value["items"][0]["category_alternatives"] = []
    review = changed(review, value, [("replace_item", "dress")])
    confirm(review, authority(), digest(review), inventory_reviewed=True)


def test_long_sleeve_and_rolled_state_are_independent():
    p = parse(prediction(items=[item(sleeve_length=fact("long"), sleeve_state=fact("rolled"))]))
    assert not issues(p)
    assert p.items[0].sleeve_length.values == ("long",)
    p = parse(prediction(items=[item(sleeve_length=fact(), sleeve_state=fact("rolled"))]))
    assert not issues(p)  # Rolling does not imply original sleeve extent.


def test_footwear_visibility_not_existence_and_unknown_placeholder_blocked():
    p = parse(prediction(items=[item(category="footwear", role="footwear", visibility="not_visible")]))
    assert "dress:footwear_visibility_conflict" in issues(p)
    assert "dress:not_an_observed_item" in issues(p)
    assert not issues(parse(prediction()))  # A cropped body needs no shoe item.


def test_two_shoes_require_explicit_pair_resolution_not_auto_merge():
    first = item("left", category="footwear", role="footwear", region={"xyxy": [10, 800, 200, 950]})
    second = item("right", category="footwear", role="footwear", region={"xyxy": [210, 800, 400, 950]})
    value = prediction(footwear_visibility="visible", items=[first, second])
    obs = observation(value)
    assert "footwear_pair_grouping_required" in issues(obs.prediction)
    assert len(obs.prediction.items) == 2
    review = begin(obs, authority(obs))
    first.update(unit="footwear_pair", region={"xyxy": [10, 800, 400, 950]})
    value["items"] = [first]
    review = changed(review, value, [("replace_item", "left"), ("remove_item", "right")])
    confirm(review, authority(obs), digest(review), inventory_reviewed=True)
    assert len(review.original.prediction.items) == 2


def test_layers_overlap_without_iou_merging_and_cyclic_layers_refuse():
    top = item("top", category="top", role="upper", region={"xyxy": [120, 120, 700, 750]})
    coat = item("coat", category="coat", role="outerwear")
    value = prediction(items=[top, coat], layering=[dict(over="coat", under="top", state="observed")])
    assert not issues(parse(value))
    value["layering"].append(dict(over="top", under="coat", state="observed"))
    assert "cyclic_layers" in issues(parse(value))


@pytest.mark.parametrize("kind", ["same_region", "same_id", "question", "dangling_layer"])
def test_duplicate_or_ambiguous_identity_never_silently_accepted(kind):
    value = prediction(items=[item("a"), item("b")])
    code = "same_region_identity_review"
    if kind == "same_id":
        value["items"][1]["id"] = "a"
        code = "duplicate_id"
    elif kind == "question":
        value["identity_questions"] = [dict(items=["a", "missing"], relation="possibly_same_garment")]
        code = "invalid_identity_reference"
    elif kind == "dangling_layer":
        value["layering"] = [dict(over="a", under="missing", state="observed")]
        code = "invalid_layer_reference"
    assert any(code in e for e in issues(parse(value)))


def test_explicit_user_target_is_required_for_crowd_and_foreign_items_refuse():
    value = prediction(scene="multiple_people", target_person_id=None,
                       people=[dict(id="p1", region={"xyxy": [0, 0, 800, 1000]}), dict(id="p2", region={"xyxy": [500, 0, 1000, 1000]})], items=[])
    review = begin(observation(value), authority())
    with pytest.raises(ValueError):
        confirm(review, authority(), digest(review), inventory_reviewed=True)
    value.update(target_person_id="p1", items=[item()])
    review = changed(review, value, [("select_target", "scene"), ("add_item", "dress")])
    confirm(review, authority(), digest(review), inventory_reviewed=True)
    value["items"][0]["person_id"] = "p2"
    review = changed(review, value, [("replace_item", "dress")])
    with pytest.raises(ValueError, match="wrong_person"):
        confirm(review, authority(), digest(review), inventory_reviewed=True)


def test_correct_remove_add_unknown_and_field_provenance_preserve_original():
    obs = observation()
    review = begin(obs, authority(obs))
    original_hash = digest(obs)
    value = prediction()
    value["items"][0].update(colours=fact("blue"), pattern=fact())
    value["items"].append(item("top", category="top", role="upper", region={"xyxy": [200, 120, 600, 550]}))
    review = changed(review, value, [("replace_item", "dress"), ("add_item", "top")])
    sources = provenance(review)
    assert sources["dress.colours"] == "user_correction_not_model_verified"
    assert sources["dress.category"] == "ai_prediction_user_reviewed"
    assert sources["top.category"] == "user_correction_not_model_verified"
    value["items"].pop(0)
    review = changed(review, value, [("remove_item", "dress")])
    assert not any(k.startswith("dress.") for k in provenance(review))
    assert digest(review.original) == original_hash
    assert len(review.revisions) == 2
    assert current(review).items[0].id == "top"
    verify(Review.model_validate_json(review.model_dump_json()))


@pytest.mark.parametrize("kind", ["stale", "wrong_image", "foreign", "unrecorded", "no_consent"])
def test_confirmation_and_correction_security_boundaries(kind):
    obs = observation()
    review = begin(obs, authority(obs))
    with pytest.raises(ValueError):
        if kind == "stale":
            confirm(review, authority(obs), "0"*64, inventory_reviewed=True)
        elif kind == "wrong_image":
            begin(obs, Authority(authenticated_user_id="owner", image_owner_id="owner", image_sha256="0"*64))
        elif kind == "foreign":
            confirm(review, authority(obs, "other"), digest(review), inventory_reviewed=True)
        elif kind == "unrecorded":
            revise(review, authority(obs), digest(review), parse(prediction(items=[])), ())
        else:
            confirm(review, authority(obs), digest(review), inventory_reviewed=False)
    with pytest.raises(ValidationError):
        Authority(authenticated_user_id="other", image_owner_id="owner", image_sha256="a"*64)


@pytest.mark.parametrize("field", ["actor_id", "previous_revision_sha256", "original_observation_sha256", "prediction", "changes"])
def test_altered_correction_records_fail_independent_link_verification(field):
    review = begin(observation(), authority())
    review = changed(review, prediction(items=[item(colours=fact("blue"))]), [("replace_item", "dress")])
    raw = review.model_dump(mode="json")
    revision = raw["revisions"][0]
    if field == "actor_id":
        revision[field] = "foreign"
    elif field == "prediction":
        revision[field]["items"] = []
    elif field == "changes":
        revision[field][0]["subject"] = "wrong"
    else:
        revision[field] = "0"*64
    with pytest.raises(ValueError):
        verify(Review.model_validate_json(json.dumps(raw)))


def test_raw_prediction_substitution_duplicate_json_fields_and_confirmation_tamper_reject():
    obs = observation()
    raw = obs.model_dump(mode="json")
    raw["prediction"]["items"][0]["category"] = "shirt"
    with pytest.raises(ValueError):
        Observation.model_validate_json(json.dumps(raw))
    with pytest.raises(ValueError, match="Duplicate"):
        parse_prediction(obs.raw_response[:-1] + ',"scene":"no_person"}')
    review = begin(obs, authority(obs))
    out = confirm(review, authority(obs), digest(review), inventory_reviewed=True).model_dump(mode="json")
    out["confirmed_by"] = "other"
    with pytest.raises(ValueError):
        Confirmation.model_validate_json(json.dumps(out))


@pytest.mark.parametrize("bad", ["material", "bad_colour", "too_many", "bad_fact"])
def test_wire_contract_refuses_unsupported_or_unbounded_outputs(bad):
    value = prediction()
    if bad == "material":
        value["items"][0]["material"] = "denim"
    elif bad == "bad_colour":
        value["items"][0]["colours"] = fact("leather")
    elif bad == "too_many":
        value["items"] = [item(str(i)) for i in range(25)]
    else:
        value["items"][0]["pattern"] = dict(state="unknown", values=["striped"])
    with pytest.raises(ValueError):
        parse(value)


def test_image_identity_and_exif_orientation_reuse_without_vton_fit_or_writes(tmp_path):
    image = Image.new("RGB", (128, 256), "red")
    image.paste("blue", (0, 128, 128, 256))
    exif = Image.Exif()
    exif[274] = 6
    encoded = BytesIO()
    image.save(encoded, "JPEG", exif=exif)
    payload = encoded.getvalue()
    identity, png = prepare_image(payload)
    assert (identity.width, identity.height) == (256, 128)
    assert identity.original_sha256 == sha256(payload).hexdigest()
    oriented = Image.open(BytesIO(png))
    assert oriented.getexif().get(274) is None
    assert oriented.size == (256, 128)
    assert list(tmp_path.iterdir()) == []
    assert prepare_image(payload) == (identity, png)


@pytest.mark.parametrize("payload", [b"not an image", b"GIF89a", b"", b"x"*(20*1024*1024+1)], ids=["invalid", "gif", "empty", "oversized"])
def test_bad_or_oversized_images_refuse(payload):
    with pytest.raises(ValueError):
        prepare_image(payload)


def test_small_image_refuses_before_decode_and_models_are_immutable():
    out = BytesIO()
    Image.new("RGB", (16, 16)).save(out, "PNG")
    with pytest.raises(ValueError):
        prepare_image(out.getvalue())
    with pytest.raises(ValidationError):
        observation().prediction.items[0].category = "coat"


def test_no_person_contradiction_and_no_outfit_confirmation():
    value = prediction(scene="no_person", people=[], target_person_id=None, items=[])
    assert not issues(parse(value))
    review = begin(observation(value), authority())
    with pytest.raises(ValueError, match="no_reviewable_outfit"):
        confirm(review, authority(), digest(review), inventory_reviewed=True)
    value["items"] = [item()]
    assert "no_person_inventory_conflict" in issues(parse(value))


def test_offline_preview_binds_image_and_escapes_model_ids():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts/preview_outfit_review.py"
    spec = importlib.util.spec_from_file_location("review_preview", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = prediction(items=[item("<script>unsafe</script>")])
    obs = observation(value)
    page = module.render(obs, image_bytes())
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in page
    assert "<script>unsafe</script>" not in page
    other = BytesIO()
    Image.new("RGB", (128, 192), "red").save(other, "PNG")
    with pytest.raises(ValueError, match="differs"):
        module.render(obs, other.getvalue())


def test_revision_bound_and_unknown_detail_correction():
    review = begin(observation(), authority())
    for n in range(16):
        value = prediction(items=[item(colours=fact("red" if n % 2 else "blue"))])
        review = changed(review, value, [("replace_item", "dress")])
    with pytest.raises(ValueError):
        changed(review, prediction(items=[item(colours=fact())]), [("replace_item", "dress")])
    # A separate review may explicitly mark colour unknown, without a fake AI fact.
    review = begin(observation(), authority())
    review = changed(review, prediction(items=[item(colours=fact())]), [("replace_item", "dress")])
    confirm(review, authority(), digest(review), inventory_reviewed=True)
    assert current(review).items[0].colours.state == "unknown"


def test_real_pilot_redundant_category_proposal_is_retained_but_cannot_confirm():
    # New exposed regression after the frozen pilot. No inference rerun or
    # visual correctness claim: retain the contradiction for explicit review.
    value = prediction(footwear_visibility="visible", items=[item(category="footwear", role="footwear",
                       unit="footwear_pair", category_alternatives=["footwear"])])
    obs = observation(value)
    assert "dress:invalid_category_alternatives" in issues(obs.prediction)
    assert obs.prediction.items[0].category_alternatives == ("footwear",)
    review = begin(obs, authority(obs))
    with pytest.raises(ValueError, match="invalid_category_alternatives"):
        confirm(review, authority(obs), digest(review), inventory_reviewed=True)
    value["items"][0]["category_alternatives"] = []
    review = changed(review, value, [("replace_item", "dress")])
    confirm(review, authority(obs), digest(review), inventory_reviewed=True)
    assert review.original.prediction.items[0].category_alternatives == ("footwear",)
