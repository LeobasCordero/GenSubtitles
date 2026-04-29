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
import customtkinter as ctk

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dual-mode colour palettes
# ---------------------------------------------------------------------------
# Dark palette  (default)
#   BG #121212 · Surface #1E1E1E · Text #E0E0E0
# Light palette (System/Light)
#   BG #F5F5F5 · Surface #FFFFFF · Text #212121
# Accent blue/green are stable but slightly desaturated in Light mode for
# WCAG contrast.  Error red is darker in Light (#B00020) vs Dark (#CF6679).
_PALETTES: dict[str, dict[str, str]] = {
    "Dark": {
        "bg":             "#121212",
        "surface":        "#1E1E1E",
        "input_bg":       "#2C2C2C",
        "text_primary":   "#E0E0E0",
        "text_secondary": "#BDBDBD",
        "accent":         "#2196F3",  # Blue — stable, readable on dark
        "accent_hov":     "#42A5F5",
        "secondary":      "#424242",
        "secondary_hov":  "#616161",
        "btn_secondary_text": "#E0E0E0",
        "progress_idle":  "#757575",
        "progress_proc":  "#2196F3",
        "progress_done":  "#4CAF50",  # Green — stable, readable on dark
        "progress_err":   "#CF6679",
        "menu_bg":        "#0F0F0F",
        "menu_fg":        "#E0E0E0",
        "menu_active_bg": "#2D2D2D",
    },
    "Light": {
        "bg":             "#F5F5F5",
        "surface":        "#FFFFFF",
        "input_bg":       "#EEEEEE",
        "text_primary":   "#212121",
        "text_secondary": "#616161",
        "accent":         "#1976D2",  # Slightly desaturated blue for light
        "accent_hov":     "#1565C0",
        "secondary":      "#E0E0E0",
        "secondary_hov":  "#BDBDBD",
        "btn_secondary_text": "#212121",
        "progress_idle":  "#9E9E9E",
        "progress_proc":  "#1976D2",
        "progress_done":  "#388E3C",  # Slightly desaturated green for light
        "progress_err":   "#B00020",  # Darker red — WCAG AA on white
        "menu_bg":        "#FFFFFF",
        "menu_fg":        "#212121",
        "menu_active_bg": "#F5F5F5",
    },
    "Ocean Dark": {
        "bg":                 "#0A1628",
        "surface":            "#112240",
        "input_bg":           "#1A3050",
        "text_primary":       "#CCD6F6",
        "text_secondary":     "#8892B0",
        "accent":             "#64FFDA",
        "accent_hov":         "#52E0BE",
        "secondary":          "#233554",
        "secondary_hov":      "#2D4470",
        "btn_secondary_text": "#CCD6F6",
        "progress_idle":      "#4A5568",
        "progress_proc":      "#64FFDA",
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
        "secondary":          "#2D4A35",
        "secondary_hov":      "#3A5E44",
        "btn_secondary_text": "#E2F4E8",
        "progress_idle":      "#4A7055",
        "progress_proc":      "#2ECC71",
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
        "secondary":          "#F3C5A5",
        "secondary_hov":      "#E8A880",
        "btn_secondary_text": "#2D1810",
        "progress_idle":      "#C4A080",
        "progress_proc":      "#E85D04",
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
        "secondary":          "#333333",
        "secondary_hov":      "#444444",
        "btn_secondary_text": "#F0F0F0",
        "progress_idle":      "#666666",
        "progress_proc":      "#FFFFFF",
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
# Sizes are identical in both modes (Header 20 px · Body 14 px).
# Weight is reduced in Dark mode (bold → normal) because light-on-dark
# rendering makes strokes appear thicker, causing fonts to look "pasted-on".
#
# Roles:
#   "header"     — 20 px · bold (Light) / normal (Dark)
#   "subheader"  — 16 px · bold (Light) / normal (Dark)
#   "body_bold"  — 14 px · bold (Light) / normal (Dark)
#   "body"       — 14 px · normal (both modes)
#   "mono"       — 12 px Courier · normal (both modes)

_FONT_SIZES: dict[str, int] = {
    "header":    20,
    "subheader": 16,
    "body_bold": 14,
    "body":      14,
    "mono":      12,
}
_FONT_FAMILIES: dict[str, str | None] = {
    "header":    None,   # system default
    "subheader": None,
    "body_bold": None,
    "body":      None,
    "mono":      "Courier",
}
# Roles that carry bold weight — reduced to "normal" in Dark to avoid heaviness
_BOLD_ROLES: frozenset[str] = frozenset({"header", "subheader", "body_bold"})


def font(role: str = "body") -> ctk.CTkFont:
    """Return a CTkFont for *role* appropriate for the current appearance mode.

    In Dark mode bold roles use weight='normal' to counter the heavier
    optical rendering of light text on a dark background.
    """
    mode = ctk.get_appearance_mode()
    is_dark = (mode == "Dark")
    weight = "normal" if (is_dark and role in _BOLD_ROLES) else (
        "bold" if role in _BOLD_ROLES else "normal"
    )
    family = _FONT_FAMILIES.get(role)
    size = _FONT_SIZES.get(role, 14)
    if family:
        return ctk.CTkFont(family=family, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)
