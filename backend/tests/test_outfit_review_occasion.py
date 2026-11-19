"""Existing pinned MiniLM+spaCy CPU adapter; no inference worker or GPU use."""
import pytest
from app.application.outfit_review.occasion import interpret


@pytest.mark.parametrize("text,context,role,formality", [
    ("I'm going to the library to study.", "academic.library_study", "unspecified", None),
    ("I have a job interview as a candidate.", "professional.job_interview", "candidate", None),
    ("I have a job interview as a candidate in smart casual.", "professional.job_interview", "candidate", "smart_casual"),
    ("I'm going to a friend's wedding.", "ceremony.wedding", "unspecified", None),
])
def test_pinned_cpu_occasion_interpretation_without_inferred_defaults(text,context,role,formality):
    result=interpret(text)
    assert result.original_text==text
    assert (result.context,result.role,result.formality)==(context,role,formality)
    assert not result.inferred_dress_code


def test_exact_style_requirement_kept_separate_from_observed_clothing():
    result=interpret("I want to look sporty for a date.")
    assert result.context=="social.date"
    assert len(result.requirements)==1
    assert '"role":"all_selected"' in result.requirements[0]
    assert '"values":["sporty"]' in result.requirements[0]


@pytest.mark.parametrize("text",["Please buy a striped shirt for me.","I'm attending a wedding in black tie."])
def test_unsupported_meaning_is_clarification_not_default_or_silent_drop(text):
    with pytest.raises(ValueError):interpret(text)
