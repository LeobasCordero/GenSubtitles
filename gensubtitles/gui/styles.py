"""gensubtitles.gui.styles
~~~~~~~~~~~~~~~~~~~~~~~~~
Spacing / dimension constants and widget-style helper functions for the
GenSubtitles desktop UI.

Complements :mod:`gensubtitles.gui.theme`, which owns colour palettes and
typography.  This module owns:

* **Spacing constants** — recurring ``padx`` / ``pady`` values (4 → 32 px).
* **Dimension constants** — button heights, button widths, progress bar height.
* **Widget-style helpers** — thin wrappers that call ``widget.configure()``
  with the correct colour / font tokens resolved at *call* time (not import
  time) so the current appearance mode is always respected.

Import these symbols in ``main.py`` and apply helpers immediately after widget
construction (apply-after-construction pattern).
"""
from __future__ import annotations

from .theme import font, p

# ---------------------------------------------------------------------------
# Spacing constants
# ---------------------------------------------------------------------------
# Based on the recurring padx/pady values observed in main.py.
#   XS  =  4 px   — tight inner padding
#   SM  =  8 px   — standard row gap
#   MD  = 12 px   — medium inner padding
#   LG  = 16 px   — section inset / standard outer padding
#   XL  = 24 px   — larger row gaps (before/after primary actions)
#   XXL = 32 px   — tab content horizontal inset

SPACING_XS: int = 4
SPACING_SM: int = 8
SPACING_MD: int = 12
SPACING_LG: int = 16
SPACING_XL: int = 24
SPACING_XXL: int = 32

# ---------------------------------------------------------------------------
# Dimension constants
# ---------------------------------------------------------------------------
# Heights
BTN_HEIGHT_PRIMARY: int = 44   # Generate, Translate, Save, Back, Clear buttons
BTN_HEIGHT_CANCEL: int = 36    # Cancel button
BTN_HEIGHT_MINI: int = 28      # Colour-swatch buttons

# Widths
BTN_WIDTH_BROWSE: int = 80     # Browse… / Save as… buttons
BTN_WIDTH_NARROW: int = 100    # Other small buttons (e.g. Open Folder)
BTN_WIDTH_SWATCH: int = 36     # Colour-swatch buttons

# Other dimensions
PROGRESS_BAR_HEIGHT: int = 16

# ---------------------------------------------------------------------------
# Widget-style helpers
# ---------------------------------------------------------------------------
# Each helper resolves colour tokens at call time so that appearance-mode
# changes (Dark ↔ Light) are always reflected correctly.


def apply_entry_style(widget: object) -> None:
    """Apply input-field colours to *widget* (CTkEntry)."""
    widget.configure(  # type: ignore[union-attr]
        fg_color=p("input_bg"),
        text_color=p("text_primary"),
    )


def apply_accent_btn_style(widget: object) -> None:
    """Apply primary / accent colours to *widget* (CTkButton)."""
    widget.configure(  # type: ignore[union-attr]
        fg_color=p("accent"),
        hover_color=p("accent_hov"),
    )


def apply_secondary_btn_style(widget: object) -> None:
    """Apply secondary colours to *widget* (CTkButton)."""
    widget.configure(  # type: ignore[union-attr]
        fg_color=p("secondary"),
        hover_color=p("secondary_hov"),
    )


def apply_cancel_btn_style(widget: object) -> None:
    """Apply cancel / destructive colours to *widget* (CTkButton)."""
    widget.configure(  # type: ignore[union-attr]
        fg_color=p("progress_err"),
        hover_color=p("secondary_hov"),
        text_color=("#FFFFFF", "#FFFFFF"),
    )


def apply_progress_bar_style(widget: object) -> None:
    """Apply idle progress colour to *widget* (CTkProgressBar)."""
    widget.configure(  # type: ignore[union-attr]
        progress_color=p("progress_idle"),
    )


def apply_stage_label_style(widget: object) -> None:
    """Apply secondary-text colour to a stage / status label (CTkLabel)."""
    apply_secondary_label_style(widget)


def apply_secondary_label_style(widget: object) -> None:
    """Apply secondary-text colour to *widget* (CTkLabel)."""
    widget.configure(  # type: ignore[union-attr]
        text_color=p("text_secondary"),
    )


def apply_settings_header_style(widget: object) -> None:
    """Apply subheader font and primary-text colour to *widget* (CTkLabel)."""
    widget.configure(  # type: ignore[union-attr]
        font=font("subheader"),
        text_color=p("text_primary"),
    )


def apply_window_bg(widget: object) -> None:
    """Apply background colour to the top-level window *widget* (CTk)."""
    widget.configure(  # type: ignore[union-attr]
        fg_color=p("bg"),
    )
