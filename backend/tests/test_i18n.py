import json

from app.i18n import Catalog, catalog


def test_czech_is_available_and_translates():
    assert "cs" in catalog.available()
    assert catalog.translate("app.title", "cs") == "HEMA Squire"


def test_interpolation():
    assert catalog.translate("email.common.greeting", "cs", name="Jano") == "Ahoj Jano,"


def test_missing_locale_falls_back_to_default():
    assert catalog.translate("app.title", "xx") == "HEMA Squire"


def test_missing_key_everywhere_returns_key():
    assert catalog.translate("no.such.key", "cs") == "no.such.key"


def test_new_locale_discovered_without_code_changes(tmp_path):
    (tmp_path / "cs.json").write_text(json.dumps({"a": {"b": "česky"}}))
    (tmp_path / "pl.json").write_text(json.dumps({"a": {"b": "po polsku"}}))
    cat = Catalog(directory=tmp_path)
    assert cat.available() == ["cs", "pl"]
    assert cat.translate("a.b", "pl") == "po polsku"


def test_partial_locale_falls_back_per_key(tmp_path):
    (tmp_path / "cs.json").write_text(json.dumps({"x": "cz-x", "y": "cz-y"}))
    (tmp_path / "en.json").write_text(json.dumps({"x": "en-x"}))
    cat = Catalog(directory=tmp_path)
    assert cat.translate("x", "en") == "en-x"
    assert cat.translate("y", "en") == "cz-y"
