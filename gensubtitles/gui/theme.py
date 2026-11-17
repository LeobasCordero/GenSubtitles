"""gensubtitles.gui.theme
~~~~~~~~~~~~~~~~~~~~~~~~
Colour palettes and typography scale for the GenSubtitles desktop UI.

Extracted from gui/main.py to centralise the primary palette and
typography definitions, so most future theme changes can be made here.

Public API
----------
p(key)        — return the colour token for the current appearance mode
font(role)    — return a CTkFont for the given typographic role
"""
from __future__ import annotations

import logging
import sys

import customtkinter as ctk

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dual-mode colour palettes
# ---------------------------------------------------------------------------
# Work palettes (default Dark / Light): a captioning bench.
#   Night #161410 · Graphite #2A2724 · Text #F4F1E8 · Time #D6A15A · Fault #C45B52
# Amber is only the clock and the active progress bar. Primary buttons are a
# dark fill with an explicit text colour so light accents stay readable.
_PALETTES: dict[str, dict[str, str]] = {
    "Dark": {
        "bg":             "#161410",
        "surface":        "#2A2724",
        "input_bg":       "#2A2724",
        "text_primary":   "#F4F1E8",
        "text_secondary": "#A39A90",
        "accent":         "#4A3F34",
        "accent_hov":     "#5C4E40",
        "btn_primary_text": "#F4F1E8",
        "secondary":      "#3A332C",
        "secondary_hov":  "#4A423A",
        "btn_secondary_text": "#F4F1E8",
        "progress_idle":  "#6E665E",
        "progress_proc":  "#D6A15A",
        "time":           "#D6A15A",
        "progress_done":  "#A39A90",
        "progress_err":   "#C45B52",
        "menu_bg":        "#100E0C",
        "menu_fg":        "#F4F1E8",
        "menu_active_bg": "#2A2724",
    },
    "Light": {
        "bg":             "#EDE6DC",
        "surface":        "#F7F3EC",
        "input_bg":       "#E4DCD0",
        "text_primary":   "#1A1612",
        "text_secondary": "#6E6256",
        "accent":         "#2A2118",
        "accent_hov":     "#3D3226",
        "btn_primary_text": "#F4F1E8",
        "secondary":      "#D9D0C4",
        "secondary_hov":  "#C9BEB0",
        "btn_secondary_text": "#1A1612",
        "progress_idle":  "#B5AA9C",
        "progress_proc":  "#D6A15A",
        "time":           "#D6A15A",
        "progress_done":  "#6E6256",
        "progress_err":   "#A33B32",
        "menu_bg":        "#F7F3EC",
        "menu_fg":        "#1A1612",
        "menu_active_bg": "#E4DCD0",
    },
    "Ocean Dark": {
        "bg":                 "#0A1628",
        "surface":            "#112240",
        "input_bg":           "#1A3050",
        "text_primary":       "#CCD6F6",
        "text_secondary":     "#8892B0",
        "accent":             "#64FFDA",
        "accent_hov":         "#52E0BE",
        "btn_primary_text":   "#0A1628",
        "secondary":          "#233554",
        "secondary_hov":      "#2D4470",
        "btn_secondary_text": "#CCD6F6",
        "progress_idle":      "#4A5568",
        "progress_proc":      "#64FFDA",
        "time":               "#64FFDA",
        "progress_done":      "#52E0BE",
        "progress_err":       "#FF6B6B",
        "menu_bg":            "#061122",
        "menu_fg":            "#CCD6F6",
        "menu_active_bg":     "#1A3050",
    },
    "Emerald": {
        "bg":                 "#0D1F12",
        "surface":            "#1A3020",
        "input_bg":           "#243D28",
        "text_primary":       "#E2F4E8",
        "text_secondary":     "#A8C9B0",
        "accent":             "#2ECC71",
        "accent_hov":         "#27AE60",
        "btn_primary_text":   "#0D1F12",
        "secondary":          "#2D4A35",
        "secondary_hov":      "#3A5E44",
        "btn_secondary_text": "#E2F4E8",
        "progress_idle":      "#4A7055",
        "progress_proc":      "#2ECC71",
        "time":               "#2ECC71",
        "progress_done":      "#27AE60",
        "progress_err":       "#E74C3C",
        "menu_bg":            "#080F0A",
        "menu_fg":            "#E2F4E8",
        "menu_active_bg":     "#1A3020",
    },
    "Sunset": {
        "bg":                 "#FFF8F0",
        "surface":            "#FFFFFF",
        "input_bg":           "#FDE8D8",
        "text_primary":       "#2D1810",
        "text_secondary":     "#7A4030",
        "accent":             "#E85D04",
        "accent_hov":         "#C44E00",
        "btn_primary_text":   "#FFF8F0",
        "secondary":          "#F3C5A5",
        "secondary_hov":      "#E8A880",
        "btn_secondary_text": "#2D1810",
        "progress_idle":      "#C4A080",
        "progress_proc":      "#E85D04",
        "time":               "#E85D04",
        "progress_done":      "#388E3C",
        "progress_err":       "#C62828",
        "menu_bg":            "#FFFFFF",
        "menu_fg":            "#2D1810",
        "menu_active_bg":     "#FDE8D8",
    },
    "Monochrome": {
        "bg":                 "#0C0C0C",
        "surface":            "#1A1A1A",
        "input_bg":           "#252525",
        "text_primary":       "#F0F0F0",
        "text_secondary":     "#A0A0A0",
        "accent":             "#FFFFFF",
        "accent_hov":         "#E0E0E0",
        "btn_primary_text":   "#0C0C0C",
        "secondary":          "#333333",
        "secondary_hov":      "#444444",
        "btn_secondary_text": "#F0F0F0",
        "progress_idle":      "#666666",
        "progress_proc":      "#FFFFFF",
        "time":               "#FFFFFF",
        "progress_done":      "#CCCCCC",
        "progress_err":       "#FF4444",
        "menu_bg":            "#080808",
        "menu_fg":            "#F0F0F0",
        "menu_active_bg":     "#252525",
    },
}

# ---------------------------------------------------------------------------
# Runtime palette override state (Phase 999.32)
# ---------------------------------------------------------------------------
# Mutable module-level state so p() resolves the active palette at call time.
# set_active_palette() is called from GenSubtitlesApp._apply_startup_settings()
# and from the palette panel Save handler.

_active_palette_tokens: dict[str, str] = {}  # tokens for non-default palette
_user_overrides: dict[str, str] = {}         # user's per-token customizations

#: Names of palettes that use mode-based fallback (no tokens override needed).
_DEFAULT_PALETTE_NAMES: frozenset[str] = frozenset({"Default Dark", "Default Light"})


def set_active_palette(
    palette_name: str,
    user_overrides: "dict[str, str] | None" = None,
) -> None:
    """Set the active named palette and optional per-token user overrides.

    Call this after loading settings (in _apply_startup_settings) and after
    the user saves the palette panel.

    Args:
        palette_name: A key in _PALETTES, or "Default Dark" / "Default Light"
                      to use the mode-based fallback.
        user_overrides: Dict of {token_key: hex_color} for user customizations.
                        Pass None or {} to clear any previous overrides.
    """
    _active_palette_tokens.clear()
    _user_overrides.clear()
    if palette_name == "Default Dark":
        _active_palette_tokens.update(_PALETTES["Dark"])
    elif palette_name == "Default Light":
        _active_palette_tokens.update(_PALETTES["Light"])
    else:
        tokens = _PALETTES.get(palette_name, {})
        _active_palette_tokens.update(tokens)
    if user_overrides:
        _user_overrides.update(user_overrides)


#: Constant listing all palette names in display order.
PALETTE_NAMES: tuple[str, ...] = (
    "Default Dark", "Default Light",
    "Ocean Dark", "Emerald", "Sunset", "Monochrome",
)


def p(key: str) -> str:
    """Return the colour token for the current effective appearance mode.

    Resolution order:
    1. Per-token user overrides (_user_overrides) — highest priority.
    2. Active named palette tokens (_active_palette_tokens) — non-default palette.
    3. Mode-based _PALETTES fallback — Default Dark / Default Light.
    """
    if key in _user_overrides:
        return _user_overrides[key]
    if _active_palette_tokens:
        val = _active_palette_tokens.get(key)
        if val is None:
            _log.warning("theme.p(): unknown token %r; falling back to Dark palette", key)
            return _PALETTES["Dark"].get(key, "#888888")
        return val
    mode = ctk.get_appearance_mode()  # resolves "System" → "Dark" or "Light"
    val = _PALETTES.get(mode, _PALETTES["Dark"]).get(key)
    if val is None:
        _log.warning("theme.p(): unknown token %r; falling back to Dark palette", key)
        return _PALETTES["Dark"].get(key, "#888888")
    return val


# ---------------------------------------------------------------------------
# Typography scale
# ---------------------------------------------------------------------------
# Clock 28 · section 18 · body 14 · help 13. Bold stays bold in Dark so
# section titles keep their rank. Courier is only the log role.
# Segoe UI on Windows; the system face elsewhere.

_UI_FAMILY: str | None = "Segoe UI" if sys.platform == "win32" else None

_FONT_SIZES: dict[str, int] = {
    "clock":     28,
    "header":    18,
    "subheader": 18,
    "body_bold": 14,
    "body":      14,
    "help":      13,
    "mono":      12,
}
_FONT_FAMILIES: dict[str, str | None] = {
    "clock":     _UI_FAMILY,
    "header":    _UI_FAMILY,
    "subheader": _UI_FAMILY,
    "body_bold": _UI_FAMILY,
    "body":      _UI_FAMILY,
    "help":      _UI_FAMILY,
    "mono":      "Courier",
}
_BOLD_ROLES: frozenset[str] = frozenset({"header", "subheader", "body_bold"})


def font(role: str = "body", family: str | None = None) -> ctk.CTkFont:
    """Return a CTkFont for *role*.

    *family* overrides the role family (used for the subtitle preview).
    Bold roles stay bold in every appearance mode.
    """
    weight = "bold" if role in _BOLD_ROLES else "normal"
    chosen = family if family is not None else _FONT_FAMILIES.get(role)
    size = _FONT_SIZES.get(role, 14)
    if chosen:
        return ctk.CTkFont(family=chosen, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)
