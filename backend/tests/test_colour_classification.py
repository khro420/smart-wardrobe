"""Synthetic infrastructure tests, not reviewed garment validation evidence."""
from dataclasses import FrozenInstanceError, replace
import json
import math
import pytest
from app.application.recommendation.oklab import normalize_hex,hex_to_oklab,oklab_distance
from app.application.recommendation.prototype_colour_classifier import PrototypeColourClassifier,DEFAULT_PROTOTYPES
from app.application.recommendation.colour_classifier import ColourClassifier
from app.application.recommendation.colour_dataset import validate_dataset,evaluate_dataset,load_dataset
from app.domain.value_objects.colour_classification import ColourClassification
from scripts.evaluate_colour_classifier import main


def thresholds(**updates):
    raw = {"schema_version":"1.0.0","version":"synthetic-test-only","status":"experimental_unapproved","mandatory_evidence_enabled":False,
           "prototype_hash":PrototypeColourClassifier().prototype_hash,"max_distance":0.0,"min_margin":0.0}
    return dict(raw,**updates)


@pytest.mark.parametrize("hex_value,expected",[("#000000",(0,0,0)),("#ffffff",(1,0,0)),("#ff0000",(.6279553606,.2248630611,.1258462985)),("#00ff00",(.8664396115,-.2338875742,.1794984799)),("#0000ff",(.4520137184,-.0324569842,-.3115281477))])
def test_ottosson_reference_coordinates(hex_value,expected):
    assert hex_to_oklab(hex_value) == pytest.approx(expected,abs=1e-7)
    assert oklab_distance(expected,expected) == 0


@pytest.mark.parametrize("value",[None,123,"blue","123456","#ab","#abcd","#12345g","#ffffffff"])
def test_invalid_hex(value):
    with pytest.raises(ValueError): normalize_hex(value)


def test_short_hex_and_symmetric_distance():
    assert normalize_hex(" #AbC ") == "#aabbcc"
    assert hex_to_oklab("#abc") == hex_to_oklab("#aabbcc")
    a,b = hex_to_oklab("#123456"),hex_to_oklab("#abcdef")
    assert oklab_distance(a,b) == oklab_distance(b,a) > 0
    with pytest.raises(ValueError): oklab_distance((math.nan,0,0),b)


def test_missing_calibration_never_recognises_even_candidate():
    result = PrototypeColourClassifier().classify("#182a46")
    assert result.status == "Unknown" and result.colour is None
    assert result.reason == "missing_calibration" and result.closest[0] == "navy"
    assert len(result.distances) == 14
    assert PrototypeColourClassifier().classify(None).status == "Missing"
    assert PrototypeColourClassifier().classify("#xyz").status == "Malformed"


def test_order_independence_and_distinct_classes(tmp_path):
    raw = json.loads(DEFAULT_PROTOTYPES.read_text())
    raw["prototypes"].reverse()
    path = tmp_path / "reverse.json"
    path.write_text(json.dumps(raw))
    first = PrototypeColourClassifier(thresholds=thresholds())
    second = PrototypeColourClassifier(path,thresholds())
    assert first.classify("#182a46") == second.classify("#182a46")
    result = first.classify("#182a46")
    assert result.status == "Recognised" and result.colour == "navy"
    assert result.closest[0] != result.second_closest[0]


def test_distance_and_margin_boundaries():
    probe = PrototypeColourClassifier().classify("#182a47")
    distance = probe.closest[1]
    gap = probe.second_closest[1]-distance
    assert distance > 0 and gap > 0
    assert PrototypeColourClassifier(thresholds=thresholds(max_distance=distance,min_margin=gap)).classify("#182a47").status == "Recognised"
    assert PrototypeColourClassifier(thresholds=thresholds(max_distance=math.nextafter(distance,0))).classify("#182a47").status == "Unknown"
    assert PrototypeColourClassifier(thresholds=thresholds(max_distance=distance,min_margin=math.nextafter(gap,math.inf))).classify("#182a47").status == "Ambiguous"


def test_exact_tie_abstains_even_zero_margin():
    classifier = PrototypeColourClassifier(thresholds=thresholds(max_distance=2))
    p = hex_to_oklab("#123456")
    # Synthetic symmetric geometry tests tie handling; not real reviewed prototypes.
    classifier._points = (("blue",(p[0],p[1]+1,p[2])),("navy",(p[0],p[1]-1,p[2])))
    result = classifier.classify("#123456")
    assert result.status == "Ambiguous" and result.colour is None


def test_second_closest_is_not_second_prototype():
    classifier = PrototypeColourClassifier(thresholds=thresholds(max_distance=1))
    p = hex_to_oklab("#123456")
    classifier._points = (("navy",p),("navy",(p[0]+.01,p[1],p[2])),("blue",(p[0]+.2,p[1],p[2])))
    result = classifier.classify("#123456")
    assert result.closest == ("navy",0)
    assert result.second_closest[0] == "blue"
    assert result.second_closest[1] == pytest.approx(.2)


@pytest.mark.parametrize("update",[{"max_distance":-1},{"min_margin":math.nan},{"max_distance":True},{"mandatory_evidence_enabled":True},{"status":"approved"},{"prototype_hash":"wrong"}])
def test_invalid_threshold_configuration(update):
    with pytest.raises(ValueError): PrototypeColourClassifier(thresholds=thresholds(**update))


@pytest.mark.parametrize("kind",["missing_colour","duplicate_id","duplicate_hex","invalid_review","enabled"])
def test_invalid_prototype_configuration(tmp_path,kind):
    raw = json.loads(DEFAULT_PROTOTYPES.read_text())
    if kind == "missing_colour": raw["prototypes"] = [x for x in raw["prototypes"] if x["colour"] != "cream"]
    if kind == "duplicate_id": raw["prototypes"].append(raw["prototypes"][0])
    if kind == "duplicate_hex": raw["prototypes"][2]["hex_value"] = raw["prototypes"][0]["hex_value"]
    if kind == "invalid_review": raw["prototypes"][0]["review_status"] = "reviewed"
    if kind == "enabled": raw["mandatory_evidence_enabled"] = True
    path = tmp_path / "bad.json"; path.write_text(json.dumps(raw))
    with pytest.raises(ValueError): PrototypeColourClassifier(path)


def test_result_freezes_nested_mutable_inputs():
    distances = [["blue",0.1],["navy",0.2]]
    result = ColourClassification("Unknown",None,"test","test","hash",distances)
    distances[0][0] = "red"
    assert result.closest == ("blue",0.1)
    with pytest.raises(FrozenInstanceError): result.status = "Recognised"
    with pytest.raises(TypeError): result.distances[0][0] = "red"
    with pytest.raises(ValueError): replace(result,status="Recognised")


def test_existing_evidence_boundary_unchanged():
    existing = ColourClassifier()
    assert existing.classify("gray").values == ("grey",)
    assert existing.classify("NAVY BLUE").values == ("navy",)
    for anchor,name in existing.anchors.items():
        assert existing.classify(anchor.upper()).values == (name,)
    prototype = PrototypeColourClassifier(thresholds=thresholds())
    assert prototype.classify("#182a46").status == "Recognised"
    assert existing.classify("#182a46").state == "Unrecognized"
    assert not existing.classify("#182a46").values


def sample(identifier="a",partition="calibration",hex_value="#182a46",**updates):
    row = dict(sample_id=identifier,source_group=identifier,hex=hex_value,partition=partition,reference_kind="canonical",label="navy",provenance="synthetic unit fixture, not garment evidence",reviewer_ids=[],independently_reviewed=False)
    return dict(row,**updates)


def dataset(*rows):
    return {"schema_version":"1.0.0","version":"synthetic-test-only","validation_locked":True,"samples":list(rows)}


@pytest.mark.parametrize("row",[sample("a"),sample("b",partition="validation"),sample("b",partition="validation",hex_value="#123456",source_group="a")])
def test_duplicate_identity_hex_and_source_overlap(row):
    with pytest.raises(ValueError): validate_dataset(dataset(sample(),row))


@pytest.mark.parametrize("updates",[{"label":"teal"},{"hex":"#ggg"},{"partition":"test"},{"independently_reviewed":True},{"reviewer_ids":["r","r"]},{"reference_kind":"unknown","label":"navy"}])
def test_invalid_samples(updates):
    with pytest.raises(ValueError): validate_dataset(dataset(sample(**updates)))


def test_metrics_count_abstentions_and_uncertain_false_positives():
    raw = validate_dataset(dataset(sample(),sample("b",hex_value="#ffffff",label="white"),sample("c",hex_value="#123456",label="blue"),sample("d",hex_value="#182a46",reference_kind="ambiguous",label=None)))
    report = evaluate_dataset(raw,PrototypeColourClassifier(thresholds=thresholds()),"calibration")
    assert report["precision"] == pytest.approx(2/3)
    assert report["recall"] == pytest.approx(2/3)
    assert report["coverage"] == .75 and report["abstention_rate"] == .25
    assert report["false_recognitions_on_uncertain_references"] == 1
    assert report["per_class"]["navy"]["precision"] == .5
    assert report["per_class"]["cream"]["precision"] is None
    assert report["release_validation_complete"] is False
    empty = evaluate_dataset(raw,PrototypeColourClassifier(),"validation")
    assert empty["sample_count"] == 0 and empty["coverage"] is None


def test_tool_import_and_locked_validation_guard(tmp_path):
    path = tmp_path / "data.json"; path.write_text(json.dumps(dataset(sample())))
    output = tmp_path / "imported.json"
    main(["import","--dataset",str(path),"--output",str(output)])
    assert load_dataset(output) == load_dataset(path)
    with pytest.raises(SystemExit): main(["evaluate","--dataset",str(path),"--partition","validation","--output",str(output)])
    with pytest.raises(SystemExit): main(["calibrate","--dataset",str(path),"--partition","validation","--output",str(output)])
    with pytest.raises(SystemExit): main(["import","--dataset",str(path),"--output",str(path)])
    main(["evaluate","--dataset",str(path),"--partition","validation","--confirm-locked-validation","--output",str(output)])
    report = json.loads(output.read_text())
    assert report["sample_count"] == 0 and report["precision"] is None


def test_tool_calibration_experiment_and_hashes(tmp_path):
    path = tmp_path / "data.json"; path.write_text(json.dumps(dataset(sample())))
    config = tmp_path / "thresholds.json"; config.write_text(json.dumps(thresholds()))
    output = tmp_path / "report.json"
    main(["calibrate","--dataset",str(path),"--thresholds",str(config),"--partition","calibration","--output",str(output)])
    first = json.loads(output.read_text())
    main(["calibrate","--dataset",str(path),"--thresholds",str(config),"--partition","calibration","--output",str(output)])
    assert json.loads(output.read_text()) == first
    assert first["precision"] == 1 and first["independently_reviewed_count"] == 0
    assert first["missing_reviewed_colours"] and not first["release_validation_complete"]
    assert first["dataset_hash"] and first["partition_hash"] and first["configuration_hash"]
    with pytest.raises(SystemExit): main(["calibrate","--dataset",str(path),"--partition","calibration","--output",str(output)])


def test_ambiguity_metrics_and_sample_order_independence():
    raw = validate_dataset(dataset(sample(),sample("b",hex_value="#123456",label="blue")))
    classifier = PrototypeColourClassifier(thresholds=thresholds(max_distance=1,min_margin=2))
    first = evaluate_dataset(raw,classifier,"calibration")
    second = evaluate_dataset(validate_dataset(dataset(*reversed(raw["samples"]))),classifier,"calibration")
    assert first == second and first["ambiguity_rate"] == 1
    assert first["coverage"] == 0 and first["precision"] is None


def test_partition_changes_and_missing_fields_rejected():
    with pytest.raises(ValueError): validate_dataset(dict(dataset(),validation_locked=False))
    with pytest.raises(ValueError): validate_dataset(dataset({"sample_id":"a"}))


def test_candidate_primary_precedence_and_unvalidated_nonpromotion():
    from tests.test_request_candidates import dressed,run
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest
    from app.shared_contracts.confirmed_garment_snapshot import GarmentPaletteEntry
    rows = [dressed("d","vest_dress","#182a46",secondary_colour="navy",colour_palette=(GarmentPaletteEntry("#000080",1),))]
    candidates,session = run(rows,StructuredOutfitRequest(colours=("navy",)))
    assert not candidates and session.result.status == "InsufficientEvidence"
    rows = [replace(rows[0],primary_colour="red")]
    candidates,session = run(rows,StructuredOutfitRequest(colours=("navy",)))
    assert not candidates and session.result.status == "NoMatchingCandidates"
