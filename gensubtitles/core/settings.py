"""
gensubtitles.core.settings
~~~~~~~~~~~~~~~~~~~~~~~~~~
Application settings persistence.
Settings are stored as JSON in the OS user config directory.

Provides:
    AppSettings
        Dataclass with all user-configurable settings and their defaults.

    DEFAULT_SETTINGS
        Module-level constant: AppSettings with all fields at default values.

    load_settings() -> AppSettings
        Load from OS user config dir. Returns defaults if file missing or corrupt.

    save_settings(settings: AppSettings) -> None
        Persist AppSettings to JSON.

    settings_path() -> Path
        Return the resolved path to settings.json (for diagnostics).
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    appearance_mode: str = "System"   # "Light" | "Dark" | "System"
    ui_language: str = "en"           # "en" | "es"
    default_output_dir: str = ""      # absolute path or "" (use same dir as input)
    default_source_lang: str = ""     # ISO 639-1 code or "" (Whisper auto-detect)
    deepl_api_key: str = ""           # DeepL Free API key
    libretranslate_url: str = ""      # e.g. "http://localhost:5000"
    libretranslate_api_key: str = ""  # empty = open instance


DEFAULT_SETTINGS = AppSettings()


def settings_path() -> Path:
    """Return the resolved path to settings.json (for diagnostics)."""
    from platformdirs import user_config_dir

    return Path(user_config_dir("GenSubtitles")) / "settings.json"


def load_settings() -> AppSettings:
    """Load settings from the OS user config directory.

    Returns:
        AppSettings populated from settings.json if it exists and is valid,
        or AppSettings with all defaults if the file is missing or corrupt.
    """
    path = settings_path()
    if not path.exists():
        return AppSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        valid_keys = AppSettings.__dataclass_fields__
        return AppSettings(**{k: v for k, v in data.items() if k in valid_keys})
    except Exception:
        logger.warning(
            "load_settings: could not parse %s — using defaults", path
        )
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Persist AppSettings to JSON in the OS user config directory.

    Args:
        settings: AppSettings instance to persist.
    """
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
