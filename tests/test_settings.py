"""
Tests for gensubtitles.core.settings — round-trip persistence and corrupt-file fallback.
"""
from __future__ import annotations

import json
from pathlib import Path
from gensubtitles.core.settings import AppSettings, load_settings, save_settings, settings_path


def test_settings_path_returns_path():
    """settings_path() returns a Path ending with settings.json."""
    p = settings_path()
    assert isinstance(p, Path)
    assert p.name == "settings.json"


def test_round_trip_save_load(tmp_path, monkeypatch):
    """Saved settings can be loaded back and match the original values."""
    fake_json = tmp_path / "settings.json"
    monkeypatch.setattr(
        "gensubtitles.core.settings.settings_path", lambda: fake_json
    )

    original = AppSettings(
        appearance_mode="Dark",
        ui_language="es",
        default_output_dir="/tmp/subs",
        default_source_lang="fr",
    )
    save_settings(original)
    loaded = load_settings()

    assert loaded.appearance_mode == "Dark"
    assert loaded.ui_language == "es"
    assert loaded.default_output_dir == "/tmp/subs"
    assert loaded.default_source_lang == "fr"


def test_load_missing_file_returns_defaults(tmp_path, monkeypatch):
    """load_settings() returns defaults when settings.json does not exist."""
    fake_json = tmp_path / "settings.json"
    monkeypatch.setattr(
        "gensubtitles.core.settings.settings_path", lambda: fake_json
    )

    loaded = load_settings()
    assert loaded == AppSettings()


def test_load_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    """load_settings() returns defaults when settings.json is malformed."""
    fake_json = tmp_path / "settings.json"
    fake_json.write_text("{{{not valid json", encoding="utf-8")
    monkeypatch.setattr(
        "gensubtitles.core.settings.settings_path", lambda: fake_json
    )

    loaded = load_settings()
    assert loaded == AppSettings()


def test_load_ignores_unknown_keys(tmp_path, monkeypatch):
    """load_settings() ignores keys not in AppSettings dataclass."""
    fake_json = tmp_path / "settings.json"
    data = {"appearance_mode": "Light", "unknown_key": "value"}
    fake_json.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "gensubtitles.core.settings.settings_path", lambda: fake_json
    )

    loaded = load_settings()
    assert loaded.appearance_mode == "Light"
    assert not hasattr(loaded, "unknown_key")


def test_save_creates_parent_dirs(tmp_path, monkeypatch):
    """save_settings() creates parent directories if they don't exist."""
    fake_json = tmp_path / "new" / "dir" / "settings.json"
    monkeypatch.setattr(
        "gensubtitles.core.settings.settings_path", lambda: fake_json
    )

    save_settings(AppSettings())
    assert fake_json.exists()


# --- GENSUBTITLES_CONFIG env var override tests ---


def test_settings_path_respects_env_var(tmp_path, monkeypatch):
    """settings_path() returns the path from GENSUBTITLES_CONFIG when set."""
    custom = tmp_path / "custom_settings.json"
    monkeypatch.setenv("GENSUBTITLES_CONFIG", str(custom))

    p = settings_path()
    assert p == custom


def test_load_settings_uses_env_var_path(tmp_path, monkeypatch):
    """load_settings() reads from GENSUBTITLES_CONFIG path when set."""
    custom = tmp_path / "env_settings.json"
    data = {"appearance_mode": "Dark", "ui_language": "es"}
    custom.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("GENSUBTITLES_CONFIG", str(custom))

    loaded = load_settings()
    assert loaded.appearance_mode == "Dark"
    assert loaded.ui_language == "es"


def test_save_settings_uses_env_var_path(tmp_path, monkeypatch):
    """save_settings() writes to GENSUBTITLES_CONFIG path when set."""
    custom = tmp_path / "subdir" / "env_settings.json"
    monkeypatch.setenv("GENSUBTITLES_CONFIG", str(custom))

    save_settings(AppSettings(appearance_mode="Light"))

    assert custom.exists()
    saved = json.loads(custom.read_text(encoding="utf-8"))
    assert saved["appearance_mode"] == "Light"
