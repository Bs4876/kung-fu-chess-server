import json

import user_settings


def test_load_returns_defaults_when_settings_file_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(user_settings, "_SETTINGS_PATH", tmp_path / "does_not_exist.json")
    assert user_settings._load() == user_settings._DEFAULTS


def test_load_returns_defaults_when_settings_file_is_invalid_json(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not valid json {")
    monkeypatch.setattr(user_settings, "_SETTINGS_PATH", path)
    assert user_settings._load() == user_settings._DEFAULTS


def test_load_applies_overrides_from_the_file(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"skin": "pieces1", "sound_enabled": False}))
    monkeypatch.setattr(user_settings, "_SETTINGS_PATH", path)
    loaded = user_settings._load()
    assert loaded["skin"] == "pieces1"
    assert loaded["sound_enabled"] is False


def test_load_falls_back_to_defaults_for_fields_missing_from_the_file(monkeypatch, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"skin": "pieces1"}))  # white_name/black_name/sound_enabled omitted
    monkeypatch.setattr(user_settings, "_SETTINGS_PATH", path)
    loaded = user_settings._load()
    assert loaded["white_name"] == user_settings._DEFAULTS["white_name"]
    assert loaded["black_name"] == user_settings._DEFAULTS["black_name"]
    assert loaded["sound_enabled"] == user_settings._DEFAULTS["sound_enabled"]


def test_module_level_constants_match_the_real_settings_json():
    # settings.json ships with the same values as the defaults, so this also
    # guards against the two silently drifting apart.
    assert user_settings.SKIN == user_settings._DEFAULTS["skin"]
    assert user_settings.SOUND_ENABLED == user_settings._DEFAULTS["sound_enabled"]
    assert user_settings.WHITE_NAME == user_settings._DEFAULTS["white_name"]
    assert user_settings.BLACK_NAME == user_settings._DEFAULTS["black_name"]
