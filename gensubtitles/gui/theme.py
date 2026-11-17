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
# Named extras use popular high-contrast schemes (Nord, Dracula, Catppuccin
# Mocha, Solarized Light). Light ``time`` is darkened for WCAG AA on cream.
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
        "progress_proc":  "#9A6B2F",
        "time":           "#9A6B2F",
        "progress_done":  "#6E6256",
        "progress_err":   "#A33B32",
        "menu_bg":        "#F7F3EC",
        "menu_fg":        "#1A1612",
        "menu_active_bg": "#E4DCD0",
    },
    # Nord — polar night / snow storm / frost
    "Nord": {
        "bg":                 "#2E3440",
        "surface":            "#3B4252",
        "input_bg":           "#434C5E",
        "text_primary":       "#ECEFF4",
        "text_secondary":     "#D8DEE9",
        "accent":             "#88C0D0",
        "accent_hov":         "#8FBCBB",
        "btn_primary_text":   "#2E3440",
        "secondary":          "#4C566A",
        "secondary_hov":      "#5E6A7D",
        "btn_secondary_text": "#ECEFF4",
        "progress_idle":      "#4C566A",
        "progress_proc":      "#88C0D0",
        "time":               "#EBCB8B",
        "progress_done":      "#A3BE8C",
        "progress_err":       "#BF616A",
        "menu_bg":            "#242933",
        "menu_fg":            "#ECEFF4",
        "menu_active_bg":     "#434C5E",
    },
    # Dracula
    "Dracula": {
        "bg":                 "#282A36",
        "surface":            "#44475A",
        "input_bg":           "#383A4A",
        "text_primary":       "#F8F8F2",
        "text_secondary":     "#BD93F9",
        "accent":             "#BD93F9",
        "accent_hov":         "#A87FE3",
        "btn_primary_text":   "#282A36",
        "secondary":          "#6272A4",
        "secondary_hov":      "#7282B4",
        "btn_secondary_text": "#F8F8F2",
        "progress_idle":      "#6272A4",
        "progress_proc":      "#8BE9FD",
        "time":               "#F1FA8C",
        "progress_done":      "#50FA7B",
        "progress_err":       "#FF5555",
        "menu_bg":            "#21222C",
        "menu_fg":            "#F8F8F2",
        "menu_active_bg":     "#44475A",
    },
    # Catppuccin Mocha
    "Catppuccin Mocha": {
        "bg":                 "#1E1E2E",
        "surface":            "#313244",
        "input_bg":           "#45475A",
        "text_primary":       "#CDD6F4",
        "text_secondary":     "#A6ADC8",
        "accent":             "#89B4FA",
        "accent_hov":         "#74A8F0",
        "btn_primary_text":   "#1E1E2E",
        "secondary":          "#45475A",
        "secondary_hov":      "#585B70",
        "btn_secondary_text": "#CDD6F4",
        "progress_idle":      "#6C7086",
        "progress_proc":      "#89B4FA",
        "time":               "#F9E2AF",
        "progress_done":      "#A6E3A1",
        "progress_err":       "#F38BA8",
        "menu_bg":            "#181825",
        "menu_fg":            "#CDD6F4",
        "menu_active_bg":     "#45475A",
    },
    # Solarized Light
    "Solarized Light": {
        "bg":                 "#FDF6E3",
        "surface":            "#EEE8D5",
        "input_bg":           "#E6DFC8",
        "text_primary":       "#073642",
        "text_secondary":     "#586E75",
        "accent":             "#268BD2",
        "accent_hov":         "#1F75B0",
        "btn_primary_text":   "#FDF6E3",
        "secondary":          "#EEE8D5",
        "secondary_hov":      "#E0D9C0",
        "btn_secondary_text": "#073642",
        "progress_idle":      "#93A1A1",
        "progress_proc":      "#B58900",
        "time":               "#B58900",
        "progress_done":      "#859900",
        "progress_err":       "#DC322F",
        "menu_bg":            "#EEE8D5",
        "menu_fg":            "#073642",
        "menu_active_bg":     "#E6DFC8",
    },
}

# Legacy palette names from Phase 999.32 → current popular schemes.
_LEGACY_PALETTE_NAMES: dict[str, str] = {
    "Ocean Dark": "Nord",
    "Emerald": "Dracula",
    "Sunset": "Catppuccin Mocha",
    "Monochrome": "Solarized Light",
}

# Palettes whose background is light (sync CTk appearance to Light).
_LIGHT_PALETTE_NAMES: frozenset[str] = frozenset({
    "Default Light",
    "Solarized Light",
})

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


def resolve_palette_name(palette_name: str) -> str:
    """Map legacy palette names to current ``PALETTE_NAMES`` entries."""
    return _LEGACY_PALETTE_NAMES.get(palette_name, palette_name)


def appearance_mode_for_palette(palette_name: str) -> str:
    """Return ``\"Dark\"`` or ``\"Light\"`` matching *palette_name* luminance."""
    name = resolve_palette_name(palette_name)
    return "Light" if name in _LIGHT_PALETTE_NAMES else "Dark"


def set_active_palette(
    palette_name: str,
    user_overrides: "dict[str, str] | None" = None,
) -> None:
    """Set the active named palette and optional per-token user overrides.

    Call this after loading settings (in _apply_startup_settings) and after
    the user saves the palette panel.

    Args:
        palette_name: A key in _PALETTES, or "Default Dark" / "Default Light"
                      to use the mode-based fallback. Legacy names are remapped.
        user_overrides: Dict of {token_key: hex_color} for user customizations.
                        Pass None or {} to clear any previous overrides.
    """
    palette_name = resolve_palette_name(palette_name)
    _active_palette_tokens.clear()
    _user_overrides.clear()
    if palette_name == "Default Dark":
        _active_palette_tokens.update(_PALETTES["Dark"])
    elif palette_name == "Default Light":
        _active_palette_tokens.update(_PALETTES["Light"])
    else:
        tokens = _PALETTES.get(palette_name, {})
        if not tokens:
            _log.warning(
                "theme.set_active_palette(): unknown palette %r; using Dark",
                palette_name,
            )
            _active_palette_tokens.update(_PALETTES["Dark"])
        else:
            _active_palette_tokens.update(tokens)
    if user_overrides:
        _user_overrides.update(user_overrides)


#: Constant listing all palette names in display order.
PALETTE_NAMES: tuple[str, ...] = (
    "Default Dark", "Default Light",
    "Nord", "Dracula", "Catppuccin Mocha", "Solarized Light",
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


def menu_font_tuple() -> tuple[str, int]:
    """Return a ``(family, size)`` tuple for native ``tk.Menu`` items."""
    family = _UI_FAMILY or "TkMenuFont"
    return (family, _FONT_SIZES["body"])
