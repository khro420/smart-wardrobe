"""Preference semantics and SELECT-only actual account-storage integration."""
from dataclasses import FrozenInstanceError,replace
from fractions import Fraction
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.application.recommendation.preference_normalizer import PreferenceNormalizer,InvalidPreferenceData
from app.infrastructure.persistence.active_preference_query_adapter import SqliteActivePreferenceQuery
from app.infrastructure.persistence.postgresql_repository import connection


def pref(kind="styles",values=None,weight=None,identifier="p",user="owner",active=True):
    value = {"values":values if values is not None else ["vintage"]}
    return PreferenceSnapshot(identifier,user,kind,json.dumps(value),weight,None,active)


def test_normalized_types_aliases_and_default_importance():
    rows = [pref("colours",["gray","navy blue","gray"],identifier="c"),pref("styles",["minimalist","vintage"],identifier="s"),pref("garment_categories",[{"kind":"group","value":"top"},{"kind":"category","value":"vest"}],identifier="g"),pref("formality",["casual","smart_casual"],identifier="f")]
    normalized = PreferenceNormalizer().normalize("owner",rows)
    assert len(normalized.preferences) == 4
    assert normalized.preferences[0].values == ("grey","navy")
    assert all(p.importance == 1 for p in normalized.preferences)
    with pytest.raises(FrozenInstanceError): normalized.user_id = "other"
    with pytest.raises(FrozenInstanceError): normalized.preferences[0].values = ()


@pytest.mark.parametrize("text,expected",[("minimal",("minimal",)),(" MINIMALIST ",("minimal",)),("vintage style",("vintage",)),("avoid vintage",()),("relaxed neutral outfits for campus",()),("minimal and classic",())])
def test_style_note_whole_alias_only(text,expected):
    row = replace(pref("style_note"),value_json=json.dumps({"value":text}))
    result = PreferenceNormalizer().normalize("owner",[row])
    assert (result.preferences[0].values if result.preferences else ()) == expected


def test_structured_styles_precedence_and_unsupported_diagnostics():
    note = replace(pref("style_note",identifier="n"),value_json='{"value":"minimal"}')
    result = PreferenceNormalizer().normalize("owner",[note,pref(),pref("unknown_type",identifier="u"),pref("colours",["blue"],"0",identifier="z"),pref("formality",["formal"],identifier="f")])
    assert len(result.preferences) == 1 and result.preferences[0].values == ("vintage",)
    assert {code for _,code in result.diagnostics} == {"structured_styles_precedence","unsupported_type","zero_weight","unavailable_formality_capability"}


@pytest.mark.parametrize("raw",['[]','{}','{"values":[]}','{"values":["teal"]}','{"values":"blue"}','{"values":[null]}','{"values":[true]}','invalid','{"values":[NaN]}'])
def test_malformed_supported_preferences_rejected(raw):
    with pytest.raises(InvalidPreferenceData): PreferenceNormalizer().normalize("owner",[replace(pref("colours"),value_json=raw)])


@pytest.mark.parametrize("weight",["-1","1.1","NaN","Infinity","nope"])
def test_bad_importance_rejected(weight):
    with pytest.raises(InvalidPreferenceData): PreferenceNormalizer().normalize("owner",[pref(weight=weight)])


def test_duplicate_inactive_zero_and_ownership():
    normalizer = PreferenceNormalizer()
    with pytest.raises(InvalidPreferenceData): normalizer.normalize("owner",[pref(),pref(identifier="p2")])
    with pytest.raises(InvalidPreferenceData): normalizer.normalize("owner",[pref(user="other")])
    result = normalizer.normalize("owner",[pref(),pref(identifier="p2",active=False),replace(pref(identifier="p3",weight="0"),value_json="invalid")])
    assert len(result.preferences) == 1 and result.preferences[0].importance == Fraction(1)


def test_actual_account_api_projection_scope_inactive_and_no_writes():
    owner,other = str(uuid.uuid4()),str(uuid.uuid4())
    with TestClient(app,headers={"X-User-Id":owner}) as client:
        assert client.get("/api/v1/account/profile").status_code == 200
        first = client.put("/api/v1/account/preferences/styles",json={"preference_value":{"values":["classic"]}})
        assert first.status_code == 200
        identifier = first.json()["id"]
        changed = client.put("/api/v1/account/preferences/styles",json={"preference_value":{"values":["vintage"]},"weight":.6})
        assert changed.status_code == 200 and changed.json()["id"] == identifier
    with TestClient(app,headers={"X-User-Id":other}) as client:
        assert client.put("/api/v1/account/preferences/colours",json={"preference_value":{"values":["red"]},"weight":1}).status_code == 200
    query = SqliteActivePreferenceQuery()
    with connection() as conn:
        before = [tuple(row) for row in conn.execute("SELECT * FROM user_preferences ORDER BY id")]
    rows = query.get_active_preferences(owner)
    assert len(rows) == 1 and rows[0].user_id == owner and rows[0].source == "user_profile"
    assert PreferenceNormalizer().normalize(owner,rows).preferences[0].importance == Fraction(3,5)
    with connection() as conn:
        assert [tuple(row) for row in conn.execute("SELECT * FROM user_preferences ORDER BY id")] == before
        conn.execute("UPDATE user_preferences SET is_active=0 WHERE id=?",(identifier,))
    assert query.get_active_preferences(owner) == ()
    assert len(query.get_active_preferences(other)) == 1
    with pytest.raises(ValueError): query.get_active_preferences("")
    with pytest.raises(ValueError): query.get_active_preferences("missing-account")


def test_readonly_adapter_does_not_create_missing_database(tmp_path,monkeypatch):
    import sqlite3
    from app.infrastructure.persistence import active_preference_query_adapter as adapter
    missing = tmp_path / "not-created.db"
    monkeypatch.setattr(adapter,"DATABASE_PATH",missing)
    with pytest.raises(sqlite3.OperationalError): adapter.SqliteActivePreferenceQuery().get_active_preferences("owner")
    assert not missing.exists()
