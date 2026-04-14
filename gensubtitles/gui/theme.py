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

import customtkinter as ctk

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
        "progress_idle":  "#9E9E9E",
        "progress_proc":  "#1976D2",
        "progress_done":  "#388E3C",  # Slightly desaturated green for light
        "progress_err":   "#B00020",  # Darker red — WCAG AA on white
        "menu_bg":        "#FFFFFF",
        "menu_fg":        "#212121",
        "menu_active_bg": "#F5F5F5",
    },
}


def p(key: str) -> str:
    """Return the colour token for the current effective appearance mode."""
    mode = ctk.get_appearance_mode()  # resolves "System" → "Dark" or "Light"
    return _PALETTES.get(mode, _PALETTES["Dark"])[key]


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
