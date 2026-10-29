"""Development/unit examples only; fixed evaluation labels are never rule inputs."""
import ast
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
from unittest.mock import Mock
import pytest

from app.application.nlp.nlp_interpreter import NLPInterpreter
from app.application.nlp.vocabulary import Vocabulary
from app.application.nlp.request_preprocessor import RequestPreprocessor
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest, GarmentCategoryConstraint

FIXTURES = Path(__file__).with_name("fixtures")


@pytest.fixture
def interpreter():
    return NLPInterpreter()


@pytest.mark.parametrize("text", [None, 42, {}, [], "", " \t\n", "a"*501])
def test_invalid_text_stops_before_classification(text):
    classifier = Mock()
    result = NLPInterpreter(classifier=classifier).interpret(text)
    assert result.status == "InvalidInput" and result.structured_request is None
    classifier.classify.assert_not_called()


def test_development_examples(interpreter):
    for text, expected in json.loads((FIXTURES / "nlp_development.v1.json").read_text())["examples"]:
        assert interpreter.interpret(text).status == expected, text


def test_original_text_and_normalization(interpreter):
    original = "  PLEASE Suggest A SMART-CASUAL outfit! \n"
    result = interpreter.interpret(original)
    assert result.status == "Supported" and result.original_text == original
    assert result.structured_request.formality == "smart_casual"
    assert result.structured_request.style is None


@pytest.mark.parametrize("phrase,field,value", [("lectures", "occasion", "campus"), ("vintage style", "style", "vintage"), ("navy blue", "colours", ("navy",)), ("formal outfit", "formality", "formal")])
def test_independent_fields(interpreter, phrase, field, value):
    result = interpreter.interpret("Please recommend an outfit with " + phrase)
    assert result.status == "Supported"
    assert getattr(result.structured_request, field) == value


def test_generic_request_has_no_invented_fields(interpreter):
    result = interpreter.interpret("Suggest an outfit")
    assert result.structured_request.to_dict() == {"intent":"outfit_recommendation", "occasion":None,"style":None,"colours":None,"garment_categories":None,"formality":None}


@pytest.mark.parametrize("phrase,kind,value", [("top", "group", "top"), ("dress", "group", "dress"), ("bottom", "group", "bottom"), ("outerwear", "group", "outerwear"), ("short sleeve dress", "category", "short_sleeve_dress")])
def test_broad_groups_and_specific_precedence(interpreter, phrase, kind, value):
    result = interpreter.interpret("Suggest an outfit including a " + phrase)
    assert result.structured_request.garment_categories == (GarmentCategoryConstraint(kind, value),)


def test_occasion_does_not_infer_style_or_formality(interpreter):
    request = interpreter.interpret("Suggest an outfit for the office").structured_request
    assert request.occasion == "work" and request.style is None and request.formality is None


def test_explicit_style_and_formality_are_separate(interpreter):
    request = interpreter.interpret("Suggest a casual outfit with a vintage look.").structured_request
    assert request.style == "vintage" and request.formality == "casual"


@pytest.mark.parametrize("text", ["Recommend a blue top and black trousers outfit", "Recommend an outfit with a dress in blue", "Suggest an outfit using red colours with a blue top", "Suggest an outfit with black for the trousers"])
def test_binding_rejected_without_schema_extension(interpreter, text):
    result = interpreter.interpret(text)
    assert result.status == "UnsupportedRequest" and result.reason == "garment_colour_binding"
    assert result.structured_request is None


@pytest.mark.parametrize("condition", ["no blue", "red or green", "vintage and sporty", "light blue", "neutral colours", "cotton material", "rainy weather", "a shirt", "a jacket", "casual"])
def test_unsupported_conditions_not_silently_ignored(interpreter, condition):
    assert interpreter.interpret("Recommend an outfit with " + condition).status == "UnsupportedRequest"


def test_unsupported_intent_stops_before_extraction():
    extractor = Mock()
    result = NLPInterpreter(extractor=extractor).interpret("Explain a vintage dress")
    assert result.status == "UnsupportedRequest"
    extractor.extract.assert_not_called()


def test_safe_internal_failure():
    extractor = Mock()
    extractor.extract.side_effect = RuntimeError("secret-stack-detail")
    result = NLPInterpreter(extractor=extractor).interpret("Suggest an outfit")
    assert result.status == "ProcessingError" and "secret" not in result.message


def test_value_objects_detach_lists_and_are_immutable():
    colours = ["blue"]
    categories = [GarmentCategoryConstraint("group", "top")]
    request = StructuredOutfitRequest(colours=colours, garment_categories=categories)
    colours.append("red")
    categories.clear()
    assert request.colours == ("blue",) and len(request.garment_categories) == 1
    with pytest.raises(FrozenInstanceError):
        request.style = "casual"
    with pytest.raises(ValueError):
        StructuredOutfitRequest(colours=[["red"]])


def test_vocabulary_groups_match_existing_taxonomy():
    from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
    vocabulary = Vocabulary.load()
    assert set.union(*(set(members) for members in vocabulary.groups.values())) == set(GARMENT_STRUCTURE)
    assert vocabulary.groups["dress"] == tuple(category for category, (role, _) in GARMENT_STRUCTURE.items() if role == "dress")


def test_nlp_has_no_infrastructure_or_recommendation_dependencies():
    folder = Path(__file__).resolve().parents[1] / "app/application/nlp"
    for path in folder.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("app.infrastructure", "app.application.recommendation", "fastapi", "sqlite3")), path


def test_development_set_is_distinct_from_frozen_evaluation():
    dev = json.loads((FIXTURES / "nlp_development.v1.json").read_text())
    evaluation = json.loads((FIXTURES / "nlp_evaluation.v1.json").read_text())
    dev_text = {RequestPreprocessor().preprocess(text).normalized for text, _ in dev["examples"]}
    eval_text = {RequestPreprocessor().preprocess(text).normalized for cases in evaluation["groups"].values() for _, text, _ in cases}
    assert not dev_text & eval_text
    assert sum(map(len, evaluation["groups"].values())) == 120


def test_explicit_global_colours_are_representable(interpreter):
    result = interpreter.interpret("Suggest an outfit using red and white colours with a bottom and outerwear.")
    assert result.status == "Supported" and result.structured_request.colours == ("red", "white")


@pytest.mark.parametrize("text", ["Suggest an outfit with blue colours for a top", "Suggest an outfit and recommend an outfit", "Recommend an outfit using red colours with a white dress"])
def test_relational_and_multiple_requests_not_flattened(interpreter, text):
    assert interpreter.interpret(text).status == "UnsupportedRequest"


def test_every_configured_alias_maps_without_extra_fields(interpreter):
    for field, value, phrase, kind in interpreter.vocabulary.entries:
        result = interpreter.interpret("Please recommend an outfit with " + phrase)
        assert result.status == "Supported", phrase
        request = result.structured_request
        expected = (GarmentCategoryConstraint(kind, value),) if kind else (value,) if field == "colours" else value
        assert getattr(request, field) == expected, phrase
        assert all(getattr(request, other) is None for other in ("occasion", "style", "colours", "garment_categories", "formality") if other != field), phrase


def test_invalid_vocabulary_configuration_fails_before_interpretation(tmp_path):
    from app.application.nlp.vocabulary import DEFAULT_VOCABULARY
    raw = json.loads(DEFAULT_VOCABULARY.read_text(encoding="utf-8"))
    raw["fields"]["colours"][0]["aliases"].append("black")
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        Vocabulary.load(path)


def test_preprocessing_failure_is_controlled():
    preprocessor = Mock()
    preprocessor.preprocess.side_effect = RuntimeError("private details")
    result = NLPInterpreter(preprocessor=preprocessor).interpret("Suggest an outfit")
    assert result.status == "ProcessingError" and "private" not in result.message
