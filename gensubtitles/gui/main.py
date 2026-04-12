"""
gensubtitles.gui.main
~~~~~~~~~~~~~~~~~~~~~
CustomTkinter desktop window for GenSubtitles.

Opens the FastAPI server automatically on launch and shuts it down on close.
All tkinter display-dependent imports are deferred inside method bodies so the
module can be imported in headless environments without a DISPLAY error.
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from pathlib import Path

import customtkinter as ctk

# Suppress HuggingFace Hub symlink warning (not supported without Developer Mode on Windows)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = logging.getLogger(__name__)

# Appearance defaults — use System until user settings are loaded.
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

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


def _p(key: str) -> str:
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


def _font(role: str = "body") -> ctk.CTkFont:
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


# ---------------------------------------------------------------------------
# OS theme detection
# ---------------------------------------------------------------------------

def _detect_os_theme() -> str:
    """Return the current OS theme as ``"Dark"`` or ``"Light"``.

    Resolution order:
    1. ``darkdetect`` library (cross-platform, preferred).
    2. Windows registry fallback (``AppsUseLightTheme``).
    3. macOS ``defaults read -g AppleInterfaceStyle`` subprocess fallback.
    4. Hard fallback → ``"Dark"`` (never raises).
    """
    # --- 1. darkdetect (preferred) ---
    try:
        import darkdetect  # type: ignore[import-untyped]  # noqa: PLC0415

        result = darkdetect.theme()  # "Dark" | "Light" | None
        if result in ("Dark", "Light"):
            return result
    except Exception:  # noqa: BLE001
        pass

    # --- 2. Windows registry ---
    if platform.system() == "Windows":
        try:
            import winreg  # noqa: PLC0415

            key_path = (
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "Light" if value else "Dark"
        except Exception:  # noqa: BLE001
            pass

    # --- 3. macOS defaults ---
    if platform.system() == "Darwin":
        try:
            import subprocess  # noqa: PLC0415

            result_bytes = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],  # noqa: S603,S607
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return "Dark" if result_bytes.strip().lower() == b"dark" else "Light"
        except Exception:  # noqa: BLE001
            # Command exits non-zero in Light mode (key doesn't exist)
            return "Light"

    # --- 4. Hard fallback ---
    return "Dark"


_BASE_URL = "http://127.0.0.1:8000"

_CODE_TO_LABEL: dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese",
    "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "ru": "Russian", "ar": "Arabic", "nl": "Dutch",
    "no": "Norwegian", "sv": "Swedish", "pl": "Polish",
}


def _label_to_code(label: str) -> str:
    """Return ISO code for a display label, or the label itself as fallback."""
    rev = {v: k for k, v in _CODE_TO_LABEL.items()}
    return rev.get(label, label.lower())

_STAGE_LABELS = [
    "[1/4] Extracting audio…",
    "[2/4] Transcribing…",
    "[3/4] Translating…",
    "[4/4] Writing SRT…",
]


class GenSubtitlesApp(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.title("GenSubtitles")
        self.minsize(580, 480)
        self.configure(fg_color=_p("bg"))

        # String variables for entry widgets
        self._input_var = ctk.StringVar()
        self._output_var = ctk.StringVar()
        self._source_lang_var = ctk.StringVar()
        self._target_lang_var = ctk.StringVar(value="No target")
        self._output_format_var = ctk.StringVar(value="SRT")
        self._engine_var = ctk.StringVar(value="Argos")

        # Dynamic language pairs loaded from API
        self._language_pairs: list[dict] = []

        # Server references
        self._server = None
        self._stage_timer = None
        self._elapsed_timer = None
        self._elapsed_start: float = 0.0
        self._tl_elapsed_start: float = 0.0
        self._tl_elapsed_timer = None
        self._closing = False
        self._prefetch_in_progress: set[tuple[str, str]] = set()
        self._prefetch_lock = threading.Lock()
        self._poll_in_flight = False
        self._job_active = False
        self._current_settings = None
        self._server_ready = False
        self._os_listener_active = False  # guard for the darkdetect listener thread

        self._apply_startup_settings()
        self._build_ui()
        self._apply_startup_theme()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._start_server()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Tab container
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=16, pady=16)
        self._tabview.add("Generate Subtitles")
        self._tabview.add("Translate Subtitles")

        # Inner content frame with 32px padding — centered container
        _tab_gen = self._tabview.tab("Generate Subtitles")
        self._frame = ctk.CTkFrame(_tab_gen, fg_color="transparent")
        self._frame.pack(fill="both", expand=True, padx=32, pady=(8, 32))

        # Configure grid columns: label | entry (expanding) | button
        self._frame.columnconfigure(1, weight=1)

        # Row 0 — Input video
        ctk.CTkLabel(self._frame, text="Input video *:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._entry_input = ctk.CTkEntry(
            self._frame, textvariable=self._input_var,
            fg_color=_p("input_bg"), text_color=_p("text_primary"),
        )
        self._entry_input.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        self._btn_browse_input = ctk.CTkButton(
            self._frame, text="Browse…", width=80, command=self._browse_input
        )
        self._btn_browse_input.grid(row=0, column=2, padx=(8, 0), pady=(0, 8))

        # Row 1 — Output file
        ctk.CTkLabel(self._frame, text="Output file *:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 24)
        )
        self._entry_output = ctk.CTkEntry(
            self._frame, textvariable=self._output_var,
            fg_color=_p("input_bg"), text_color=_p("text_primary"),
        )
        self._entry_output.grid(row=1, column=1, sticky="ew", pady=(0, 24))
        self._btn_browse_output = ctk.CTkButton(
            self._frame, text="Save as…", width=80, command=self._browse_output
        )
        self._btn_browse_output.grid(row=1, column=2, padx=(8, 0), pady=(0, 24))

        # Row 2 — Source language (dynamic CTkOptionMenu, populated after server starts)
        self._lbl_source_lang = ctk.CTkLabel(self._frame, text="Source language:")
        self._lbl_source_lang.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self._option_source_lang = ctk.CTkOptionMenu(
            self._frame,
            values=["Auto-detect"],
            variable=self._source_lang_var,
            command=self._on_source_lang_change,
        )
        self._option_source_lang.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 3 — Target language dropdown (populated dynamically)
        ctk.CTkLabel(self._frame, text="Target language:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._option_target_lang = ctk.CTkOptionMenu(
            self._frame,
            values=["No target"],
            variable=self._target_lang_var,
            command=self._on_target_lang_change,
        )
        self._option_target_lang.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 4 — Engine dropdown (visible only when a target language is selected)
        self._lbl_engine = ctk.CTkLabel(self._frame, text="Translation engine:")
        self._lbl_engine.grid(row=4, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self._option_engine = ctk.CTkOptionMenu(
            self._frame,
            values=["Argos", "DeepL", "LibreTranslate"],
            variable=self._engine_var,
        )
        self._option_engine.grid(row=4, column=1, columnspan=2, sticky="ew", pady=(0, 8))
        # Hidden initially — shown when a target language is selected
        self._lbl_engine.grid_remove()
        self._option_engine.grid_remove()

        # Row 5 — Output format dropdown
        ctk.CTkLabel(self._frame, text="Output format:").grid(
            row=5, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._option_output_format = ctk.CTkOptionMenu(
            self._frame,
            values=["SRT", "SSA"],
            variable=self._output_format_var,
            command=self._on_output_format_change,
        )
        self._option_output_format.grid(row=5, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 6 — Generate button (disabled until server is ready)
        self._btn_generate = ctk.CTkButton(
            self._frame, text="Generate Subtitles", command=self._on_generate, height=44,
            fg_color=_p("accent"), hover_color=_p("accent_hov"),
            state="disabled",
        )
        self._btn_generate.grid(row=6, column=0, columnspan=3, pady=(24, 0), sticky="ew")

        # Row 7 — Clear button
        self._btn_clear = ctk.CTkButton(
            self._frame,
            text="Clear",
            command=self._on_clear,
            state="disabled",
            height=44,
            fg_color=_p("secondary"),
            hover_color=_p("secondary_hov"),
        )
        self._btn_clear.grid(row=7, column=0, columnspan=3, pady=(16, 8), sticky="ew")

        # Row 8 — Elapsed time counter (hidden initially)
        self._elapsed_label = ctk.CTkLabel(self._frame, text="00:00:00")
        self._elapsed_label.grid(row=8, column=0, columnspan=3, pady=(8, 4))
        self._elapsed_label.grid_remove()

        # Row 9 — Progress bar (hidden initially)
        self._progress_bar = ctk.CTkProgressBar(
            self._frame, mode="indeterminate", height=16,
            progress_color=_p("progress_idle"),
        )
        self._progress_bar.grid(row=9, column=0, columnspan=3, pady=(32, 32), sticky="ew")
        self._progress_bar.grid_remove()

        # Row 10 — Stage label (also used for server status)
        self._stage_label = ctk.CTkLabel(self._frame, text="⏳ Starting server…", text_color=_p("text_secondary"))
        self._stage_label.grid(row=10, column=0, columnspan=3, pady=4)

        # Reactive enable/disable for Clear button
        for var in (self._input_var, self._output_var, self._target_lang_var):
            var.trace_add("write", lambda *_: self._update_clear_state())

        # Build Translate tab
        self._build_translate_tab()
        # Build Settings panel and menu bar
        self._build_settings_panel()
        self._build_menu_bar()

    def _build_menu_bar(self) -> None:
        import tkinter as tk  # noqa: PLC0415

        _menu_cfg = dict(
            bg=_p("menu_bg"), fg=_p("menu_fg"),
            activebackground=_p("menu_active_bg"), activeforeground=_p("menu_fg"),
            bd=0, tearoff=0,
        )
        menubar = tk.Menu(self, **{k: v for k, v in _menu_cfg.items() if k != "tearoff"})
        self.configure(menu=menubar)
        self._menubar = menubar

        # Settings menu
        settings_menu = tk.Menu(menubar, **_menu_cfg)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Preferences\u2026", command=self._show_settings)

        # Help menu (stubs \u2014 Plan 06 will implement the dialog bodies)
        help_menu = tk.Menu(menubar, **_menu_cfg)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Tutorial", command=self._show_tutorial)
        help_menu.add_command(label="Available Languages", command=self._show_language_pairs)
        help_menu.add_separator()
        help_menu.add_command(label="About GenSubtitles", command=self._show_about)
        self._menus = [settings_menu, help_menu]

    def _build_settings_panel(self) -> None:
        self._settings_frame = ctk.CTkFrame(self)
        # Not packed yet \u2014 shown via _show_settings

        sf = self._settings_frame
        sf.columnconfigure(1, weight=1)

        self._settings_header_lbl = ctk.CTkLabel(
            sf, text="Settings",
            font=_font("subheader"),
            text_color=_p("text_primary"),
        )
        self._settings_header_lbl.grid(
            row=0, column=0, columnspan=2, pady=(12, 8), sticky="w", padx=12
        )

        # Appearance Mode
        ctk.CTkLabel(sf, text="Appearance Mode:").grid(
            row=1, column=0, sticky="w", padx=(12, 8), pady=6
        )
        self._settings_appearance_var = ctk.StringVar(value="System")
        ctk.CTkOptionMenu(
            sf, values=["System", "Light", "Dark"],
            variable=self._settings_appearance_var,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)

        # UI Language
        ctk.CTkLabel(sf, text="UI Language:").grid(
            row=2, column=0, sticky="w", padx=(12, 8), pady=6
        )
        self._settings_lang_var = ctk.StringVar(value="English")
        ctk.CTkOptionMenu(
            sf, values=["English", "Spanish"],
            variable=self._settings_lang_var,
        ).grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        # Default Output Directory
        ctk.CTkLabel(sf, text="Default output dir:").grid(
            row=3, column=0, sticky="w", padx=(12, 8), pady=6
        )
        self._settings_outdir_var = ctk.StringVar()
        self._settings_outdir_entry = ctk.CTkEntry(
            sf, textvariable=self._settings_outdir_var,
            placeholder_text="(same directory as input)",
            fg_color=_p("input_bg"), text_color=_p("text_primary"),
        )
        self._settings_outdir_entry.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        # Save / Back buttons
        btn_frame = ctk.CTkFrame(sf, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(16, 12), padx=12, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        self._btn_settings_save = ctk.CTkButton(
            btn_frame, text="Save", command=self._save_settings, height=44,
            fg_color=_p("accent"), hover_color=_p("accent_hov"),
        )
        self._btn_settings_save.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._btn_settings_back = ctk.CTkButton(
            btn_frame, text="Back", command=self._hide_settings, height=44,
            fg_color=_p("secondary"), hover_color=_p("secondary_hov"),
        )
        self._btn_settings_back.grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _build_translate_tab(self) -> None:
        _tab_tl = self._tabview.tab("Translate Subtitles")
        tf = ctk.CTkFrame(_tab_tl, fg_color="transparent")
        tf.pack(fill="both", expand=True, padx=32, pady=(8, 32))
        tf.columnconfigure(1, weight=1)

        # Row 0 — Input subtitle file
        ctk.CTkLabel(tf, text="Input subtitle *:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._tl_input_var = ctk.StringVar()
        self._tl_entry_input = ctk.CTkEntry(
            tf, textvariable=self._tl_input_var,
            fg_color=_p("input_bg"), text_color=_p("text_primary"),
        )
        self._tl_entry_input.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        self._tl_btn_browse = ctk.CTkButton(
            tf, text="Browse…", width=80, command=self._tl_browse_input
        )
        self._tl_btn_browse.grid(row=0, column=2, padx=(8, 0), pady=(0, 8))

        # Row 1 — Output path
        ctk.CTkLabel(tf, text="Output path *:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 24)
        )
        self._tl_output_var = ctk.StringVar()
        self._tl_entry_output = ctk.CTkEntry(
            tf, textvariable=self._tl_output_var,
            fg_color=_p("input_bg"), text_color=_p("text_primary"),
        )
        self._tl_entry_output.grid(row=1, column=1, sticky="ew", pady=(0, 24))
        self._tl_btn_browse_out = ctk.CTkButton(
            tf, text="Save as…", width=80, command=self._tl_browse_output
        )
        self._tl_btn_browse_out.grid(row=1, column=2, padx=(8, 0), pady=(0, 24))

        # Row 2 — Source language
        ctk.CTkLabel(tf, text="Source language:").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._tl_source_var = ctk.StringVar(value="English")
        self._tl_option_source = ctk.CTkOptionMenu(
            tf, values=["English"], variable=self._tl_source_var
        )
        self._tl_option_source.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 3 — Target language
        ctk.CTkLabel(tf, text="Target language:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self._tl_target_var = ctk.StringVar(value="Spanish")
        self._tl_option_target = ctk.CTkOptionMenu(
            tf, values=["Spanish"], variable=self._tl_target_var,
            command=self._on_tl_target_lang_change,
        )
        self._tl_option_target.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 4 — Convert Only checkbox
        self._tl_convert_only_var = ctk.BooleanVar(value=False)
        self._tl_chk_convert = ctk.CTkCheckBox(
            tf,
            text="Convert only (no translation — change format only)",
            variable=self._tl_convert_only_var,
            command=self._tl_on_convert_only_change,
        )
        self._tl_chk_convert.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # Row 5 — Translate button (disabled until server is ready)
        self._tl_btn_translate = ctk.CTkButton(
            tf, text="Translate / Convert", command=self._on_translate, height=44,
            fg_color=_p("accent"), hover_color=_p("accent_hov"),
            state="disabled",
        )
        self._tl_btn_translate.grid(row=5, column=0, columnspan=3, pady=(24, 8), sticky="ew")

        # Row 6 — Elapsed label
        self._tl_elapsed_label = ctk.CTkLabel(tf, text="00:00:00")
        self._tl_elapsed_label.grid(row=6, column=0, columnspan=3, pady=(8, 4))
        self._tl_elapsed_label.grid_remove()

        # Row 7 — Progress bar
        self._tl_progress_bar = ctk.CTkProgressBar(
            tf, mode="indeterminate", height=16,
            progress_color=_p("progress_idle"),
        )
        self._tl_progress_bar.grid(row=7, column=0, columnspan=3, pady=(32, 32), sticky="ew")
        self._tl_progress_bar.grid_remove()

        # Row 8 — Stage label
        self._tl_stage_label = ctk.CTkLabel(tf, text="")
        self._tl_stage_label.grid(row=8, column=0, columnspan=3, pady=4)

    def _tl_browse_input(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        path = filedialog.askopenfilename(
            filetypes=[("Subtitle files", "*.srt *.ssa *.ass"), ("All files", "*.*")]
        )
        if path:
            self._tl_input_var.set(path)
            if not self._tl_output_var.get():
                p = Path(path)
                self._tl_output_var.set(str(p.with_stem(p.stem + "_translated")))

    def _tl_browse_output(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        current_output = self._tl_output_var.get().strip()
        current_input = self._tl_input_var.get().strip()

        suffix = ""
        if current_output:
            suffix = Path(current_output).suffix.lower()
        elif current_input:
            suffix = Path(current_input).suffix.lower()

        if suffix in {".ssa", ".ass"}:
            defext = ".ssa"
            ftypes = [("Subtitle files", "*.ssa *.srt"), ("All files", "*.*")]
        else:
            defext = ".srt"
            ftypes = [("Subtitle files", "*.srt *.ssa"), ("All files", "*.*")]

        path = filedialog.asksaveasfilename(
            defaultextension=defext,
            filetypes=ftypes,
        )
        if path:
            self._tl_output_var.set(path)

    def _tl_on_convert_only_change(self) -> None:
        state = "disabled" if self._tl_convert_only_var.get() else "normal"
        self._tl_option_source.configure(state=state)
        self._tl_option_target.configure(state=state)

    # ------------------------------------------------------------------
    # Browse callbacks
    # ------------------------------------------------------------------

    def _browse_input(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        path = filedialog.askopenfilename(
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.webm"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._input_var.set(path)
            if not self._output_var.get():
                ext = ".ssa" if self._output_format_var.get() == "SSA" else ".srt"
                self._output_var.set(str(Path(path).with_suffix(ext)))

    def _browse_output(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        fmt = self._output_format_var.get()
        if fmt == "SSA":
            ftypes = [("SSA subtitles", "*.ssa"), ("All files", "*.*")]
            defext = ".ssa"
        else:
            ftypes = [("SRT subtitles", "*.srt"), ("All files", "*.*")]
            defext = ".srt"
        path = filedialog.asksaveasfilename(
            defaultextension=defext,
            filetypes=ftypes,
        )
        if path:
            self._output_var.set(path)

    # ------------------------------------------------------------------
    # Clear button logic
    # ------------------------------------------------------------------

    def _on_source_lang_change(self, selection: str) -> None:
        """Filter target language dropdown to valid destinations for selected source."""
        all_labels = sorted(_CODE_TO_LABEL.values())
        if not self._language_pairs:
            # No pairs installed yet — show all known languages so user can pick;
            # the pair will be auto-downloaded at generation time.
            targets = all_labels
        elif selection == "Auto-detect":
            targets = sorted({_CODE_TO_LABEL.get(p["to"], p["to"]) for p in self._language_pairs})
            targets = targets or all_labels
        else:
            src_code = _label_to_code(selection)
            targets = [
                _CODE_TO_LABEL.get(p["to"], p["to"])
                for p in self._language_pairs if p["from"] == src_code
            ]
            targets = sorted(set(targets)) or all_labels
        targets = ["No target"] + [t for t in targets if t != "No target"]
        self._option_target_lang.configure(values=targets)
        current = self._target_lang_var.get()
        if current not in targets:
            self._target_lang_var.set(targets[0])

    def _on_target_lang_change(self, selection: str) -> None:
        """Trigger background pair download when a target language is picked."""
        # Show/hide engine row based on whether a target is selected
        if selection in ("No target", ""):
            self._lbl_engine.grid_remove()
            self._option_engine.grid_remove()
            return
        else:
            self._lbl_engine.grid()
            self._option_engine.grid()
        src_label = self._source_lang_var.get()
        if src_label == "Auto-detect":
            return
        src_code = _label_to_code(src_label)
        tgt_code = _label_to_code(selection)
        self._prefetch_pair_bg(src_code, tgt_code)

    def _prefetch_pair_bg(self, src_code: str, tgt_code: str) -> None:
        """Download Argos Translate packages for src→tgt in the background (supports two-hop routing)."""
        if src_code == tgt_code:
            return

        pair_key = (src_code, tgt_code)
        with self._prefetch_lock:
            if pair_key in self._prefetch_in_progress:
                return  # already being prefetched
            self._prefetch_in_progress.add(pair_key)

        def _worker() -> None:
            from gensubtitles.core.translator import (  # noqa: PLC0415
                _is_installed,
                ensure_route_installed,
                find_route,
            )
            try:
                route = find_route(src_code, tgt_code)
            except RuntimeError as exc:
                logger.warning("No route for %s→%s: %s", src_code, tgt_code, exc)
                msg = f"⚠ No translation route available for {src_code}→{tgt_code}"
                self.after(0, lambda m=msg: self._stage_label.configure(text=m))
                return

            if all(_is_installed(f, t) for f, t in route):
                return  # already installed, nothing to do

            via = " → ".join(f"{f}→{t}" for f, t in route)
            self.after(0, lambda v=via: self._stage_label.configure(
                text=f"⏬ Downloading {v} model…"
            ))
            try:
                ensure_route_installed(src_code, tgt_code)
                self.after(0, lambda v=via: self._stage_label.configure(
                    text=f"✓ {v} model ready"
                ))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Background prefetch failed for %s→%s: %s", src_code, tgt_code, exc)
                msg = f"⚠ Could not download model for {src_code}→{tgt_code}: {exc}"
                self.after(0, lambda m=msg: self._stage_label.configure(text=m))
            finally:
                with self._prefetch_lock:
                    self._prefetch_in_progress.discard(pair_key)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_output_format_change(self, selection: str) -> None:
        """Update output path extension when format changes."""
        current = self._output_var.get()
        if not current:
            return
        p = Path(current)
        new_ext = ".ssa" if selection == "SSA" else ".srt"
        self._output_var.set(str(p.with_suffix(new_ext)))

    def _populate_language_dropdowns(self) -> None:
        """Runs in background thread. Queries GET /languages then updates dropdowns on main thread."""
        import requests as req  # noqa: PLC0415

        pairs: list[dict] = []
        try:
            resp = req.get(f"{_BASE_URL}/languages", timeout=30)
            resp.raise_for_status()
            pairs = resp.json().get("pairs", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load language pairs from API: %s", exc)

        def _apply(pairs: list[dict] = pairs) -> None:
            self._language_pairs = pairs
            if pairs:
                sources = sorted({_CODE_TO_LABEL.get(p["from"], p["from"]) for p in pairs})
                sources = ["Auto-detect"] + sources
            else:
                sources = ["Auto-detect"] + sorted(_CODE_TO_LABEL.values())
            self._option_source_lang.configure(values=sources)
            self._source_lang_var.set("Auto-detect")
            self._on_source_lang_change("Auto-detect")
            # Also populate Translate tab dropdowns
            non_auto = [s for s in sources if s != "Auto-detect"]
            if non_auto:
                self._tl_option_source.configure(values=non_auto)
                self._tl_source_var.set(non_auto[0])
                self._tl_option_source.configure(command=self._on_tl_source_lang_change)
                self._on_tl_source_lang_change(non_auto[0])

        if not self._closing:
            self.after(0, _apply)

    def _on_tl_target_lang_change(self, selection: str) -> None:
        """Trigger background pair download when Translate tab target is picked."""
        src_label = self._tl_source_var.get()
        self._prefetch_pair_bg(_label_to_code(src_label), _label_to_code(selection))

    def _on_tl_source_lang_change(self, selection: str) -> None:
        """Filter Translate tab target dropdown to valid destinations for selected source."""
        all_labels = sorted(_CODE_TO_LABEL.values())
        if not self._language_pairs:
            targets = [t for t in all_labels if t != selection]
        else:
            src_code = _label_to_code(selection)
            targets = [
                _CODE_TO_LABEL.get(p["to"], p["to"])
                for p in self._language_pairs if p["from"] == src_code
            ]
            targets = sorted(set(targets)) or [t for t in all_labels if t != selection]
        self._tl_option_target.configure(values=targets)
        current = self._tl_target_var.get()
        if current not in targets:
            self._tl_target_var.set(targets[0])
        # NOTE: no prefetch here — this fires on init. Prefetch only on explicit target selection.

    def _update_clear_state(self) -> None:
        """Enable Clear button if any user-settable input field is non-empty/non-default; disable otherwise."""
        has_content = any(
            v.get()
            for v in (
                self._input_var,
                self._output_var,
            )
        ) or self._target_lang_var.get() not in ("No target", "")
        self._btn_clear.configure(state="normal" if has_content else "disabled")

    def _on_clear(self) -> None:
        """Reset input fields; return dropdowns to defaults."""
        self._input_var.set("")
        self._output_var.set("")
        self._source_lang_var.set("Auto-detect")
        self._target_lang_var.set("No target")
        self._output_format_var.set("SRT")

    # ------------------------------------------------------------------
    # Progress polling (replaces static stage cycling)
    # ------------------------------------------------------------------

    def _poll_progress(self) -> None:
        """Poll GET /progress every second via a background thread to avoid blocking Tk."""
        if self._closing or self._poll_in_flight or not self._job_active:
            return
        self._poll_in_flight = True

        def _fetch() -> None:
            try:
                import requests as req  # noqa: PLC0415
                resp = req.get(f"{_BASE_URL}/progress", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    self.after(0, lambda d=data: self._apply_progress(d))
            except Exception:  # noqa: BLE001
                pass  # server may not be ready yet
            finally:
                self._poll_in_flight = False
                if not self._closing and self._job_active:
                    self.after(1000, self._poll_progress)

        threading.Thread(target=_fetch, daemon=True).start()

    def _hide_generate_progress(self) -> None:
        """Reset and hide the generate-tab progress bar after state feedback delay."""
        if not self._job_active:
            self._progress_bar.configure(progress_color=_p("progress_idle"))
            self._progress_bar.grid_remove()

    def _hide_translate_progress(self) -> None:
        """Reset and hide the translate-tab progress bar after state feedback delay."""
        self._tl_progress_bar.configure(progress_color=_p("progress_idle"))
        self._tl_progress_bar.grid_remove()

    def _apply_progress(self, data: dict) -> None:
        """Apply progress data to UI widgets (must run on Tk main thread)."""
        if not self._job_active:
            return  # ignore stale progress updates after job finished
        label = data.get("label", "")
        current = data.get("current", 0)
        total = data.get("total", 0)
        stage = data.get("stage", "")
        if label:
            self._stage_label.configure(text=label)
        # Switch progress bar to determinate mode during translation
        if stage == "translating" and total > 0:
            pct = current / total
            if self._progress_bar.cget("mode") != "determinate":
                self._progress_bar.stop()
                self._progress_bar.configure(mode="determinate", progress_color=_p("progress_proc"))
            self._progress_bar.set(pct)
        elif self._progress_bar.cget("mode") != "indeterminate":
            self._progress_bar.configure(mode="indeterminate", progress_color=_p("progress_proc"))
            self._progress_bar.start()

    def _tick_elapsed(self) -> None:
        if self._closing:
            return
        elapsed = int(time.monotonic() - self._elapsed_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._elapsed_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        self._elapsed_timer = self.after(1000, self._tick_elapsed)

    # ------------------------------------------------------------------
    # Generate button logic
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        input_path = self._input_var.get().strip()
        output_path = self._output_var.get().strip()

        if not input_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Missing input", "Please select an input video file.")
            return
        if not output_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Missing output", "Please choose an output subtitle path.")
            return

        # Capture StringVar values on the main thread (Tkinter is not thread-safe)
        src_selected = self._source_lang_var.get()
        src_lang = None if src_selected in ("Auto-detect", "") else _label_to_code(src_selected)
        tgt_selected = self._target_lang_var.get()
        tgt_lang: str | None = None if tgt_selected in ("No target", "") else _label_to_code(tgt_selected)
        engine_label = self._engine_var.get()  # "Argos", "DeepL", or "LibreTranslate"
        engine_code = engine_label.lower().replace(" ", "")  # "argos", "deepl", "libretranslate"

        self._btn_generate.configure(state="disabled")
        self._btn_clear.configure(state="disabled")
        self._entry_input.configure(state="disabled")
        self._entry_output.configure(state="disabled")
        self._option_source_lang.configure(state="disabled")
        self._option_target_lang.configure(state="disabled")
        self._option_engine.configure(state="disabled")
        self._option_output_format.configure(state="disabled")
        self._btn_browse_input.configure(state="disabled")
        self._btn_browse_output.configure(state="disabled")
        self._progress_bar.grid()
        self._progress_bar.configure(mode="indeterminate", progress_color=_p("progress_proc"))
        self._progress_bar.start()
        self._job_active = True
        self._poll_progress()

        # Reset and start elapsed timer
        if self._elapsed_timer is not None:
            self.after_cancel(self._elapsed_timer)
            self._elapsed_timer = None
        self._elapsed_label.configure(text="00:00:00")
        self._elapsed_start = time.monotonic()
        self._elapsed_label.grid()
        self._tick_elapsed()

        thread = threading.Thread(
            target=self._run_api_call,
            args=(input_path, output_path, src_lang, tgt_lang, engine_code),
            daemon=True,
        )
        thread.start()

    def _run_api_call(
        self,
        input_path: str,
        output_path: str,
        src_lang: str | None,
        tgt_lang: str | None,
        engine: str = "argos",
    ) -> None:
        import requests as req  # noqa: PLC0415

        try:
            params: dict[str, str] = {}
            if src_lang:
                params["source_lang"] = src_lang
            if tgt_lang:
                params["target_lang"] = tgt_lang
            params["engine"] = engine  # always include

            with open(input_path, "rb") as fh:
                video_name = Path(input_path).name
                resp = req.post(
                    f"{_BASE_URL}/subtitles",
                    files={"file": (video_name, fh, "application/octet-stream")},
                    params=params,
                    timeout=3600,
                )

            if resp.status_code == 200:
                output_file = Path(output_path)
                final_path = output_path
                # Convert to SSA if user selected SSA format
                if self._output_format_var.get() == "SSA":
                    from gensubtitles.core.srt_writer import convert_srt_to_ssa  # noqa: PLC0415

                    temp_srt = output_file.with_suffix(".srt")
                    ssa_out = output_file.with_suffix(".ssa")
                    temp_srt.write_bytes(resp.content)
                    convert_srt_to_ssa(temp_srt, ssa_out)
                    temp_srt.unlink(missing_ok=True)
                    final_path = str(ssa_out)
                else:
                    output_file.write_bytes(resp.content)
                if not self._closing:
                    self.after(0, self._finish_generate, None, final_path)
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:  # noqa: BLE001
                    detail = resp.text
                if isinstance(detail, list):
                    detail = "; ".join(str(e) for e in detail)
                if not self._closing:
                    self.after(0, self._finish_generate, str(detail), None)
        except Exception as exc:  # noqa: BLE001
            if not self._closing:
                self.after(0, self._finish_generate, str(exc), None)

    def _finish_generate(self, error: str | None, output_path: str | None) -> None:
        # Stop progress polling first to prevent stale UI updates
        self._job_active = False

        if self._stage_timer is not None:
            self.after_cancel(self._stage_timer)
            self._stage_timer = None

        # Show final elapsed time before cancelling the timer
        elapsed = int(time.monotonic() - self._elapsed_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._elapsed_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

        if self._elapsed_timer is not None:
            self.after_cancel(self._elapsed_timer)
            self._elapsed_timer = None

        if error:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate", progress_color=_p("progress_err"))
            self._progress_bar.set(1.0)
            self._progress_bar.grid()
            self.after(2000, self._hide_generate_progress)
        else:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate", progress_color=_p("progress_done"))
            self._progress_bar.set(1.0)
            self._progress_bar.grid()
            self.after(2000, self._hide_generate_progress)
        self._btn_generate.configure(state="normal")
        self._entry_input.configure(state="normal")
        self._entry_output.configure(state="normal")
        self._option_source_lang.configure(state="normal")
        self._option_target_lang.configure(state="normal")
        self._option_engine.configure(state="normal")
        self._option_output_format.configure(state="normal")
        self._btn_browse_input.configure(state="normal")
        self._btn_browse_output.configure(state="normal")
        self._update_clear_state()

        if error:
            from tkinter import messagebox  # noqa: PLC0415

            self._stage_label.configure(text="")
            messagebox.showerror("Generation failed", error)
        else:
            self._stage_label.configure(text="✓ Done")
            if output_path is None:
                raise AssertionError("output_path must not be None on success")
            self._show_success(output_path)

    def _show_success(self, output_path: str) -> None:
        output_dir = Path(output_path).parent

        def _open_folder() -> None:
            sys_name = platform.system()
            if sys_name == "Windows":
                subprocess.Popen(["explorer", str(output_dir)])  # noqa: S603,S607
            elif sys_name == "Darwin":
                subprocess.Popen(["open", str(output_dir)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])  # noqa: S603,S607

        if not hasattr(self, "_btn_open_folder"):
            self._btn_open_folder = ctk.CTkButton(
                self._frame, text="Open Folder", command=_open_folder
            )
            self._btn_open_folder.grid(row=10, column=0, columnspan=3, pady=(4, 0), sticky="ew")
        else:
            self._btn_open_folder.configure(command=_open_folder)
            self._btn_open_folder.grid(row=10, column=0, columnspan=3, pady=(4, 0), sticky="ew")

    # ------------------------------------------------------------------
    # Theme / colour palette
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """Re-apply all hard-coded colours after an appearance-mode change.

        CustomTkinter handles its own widget colours automatically when
        set_appearance_mode() is called, but colours passed as explicit hex
        strings in constructors are static and must be refreshed here.
        """
        self.configure(fg_color=_p("bg"))

        # Entry fields
        for entry in (
            self._entry_input, self._entry_output,
            self._tl_entry_input, self._tl_entry_output,
        ):
            entry.configure(fg_color=_p("input_bg"), text_color=_p("text_primary"))

        # Accent (primary) buttons
        for btn in (self._btn_generate, self._tl_btn_translate):
            btn.configure(fg_color=_p("accent"), hover_color=_p("accent_hov"))

        # Secondary buttons
        self._btn_clear.configure(
            fg_color=_p("secondary"), hover_color=_p("secondary_hov")
        )

        # Progress bars — reset to idle colour only (active colour is set dynamically)
        for pb in (self._progress_bar, self._tl_progress_bar):
            if pb.cget("mode") == "indeterminate" and not self._job_active:
                pb.configure(progress_color=_p("progress_idle"))

        # Settings panel widgets
        if hasattr(self, "_btn_settings_save"):
            self._btn_settings_save.configure(
                fg_color=_p("accent"), hover_color=_p("accent_hov")
            )
        if hasattr(self, "_btn_settings_back"):
            self._btn_settings_back.configure(
                fg_color=_p("secondary"), hover_color=_p("secondary_hov")
            )
        if hasattr(self, "_settings_outdir_entry"):
            self._settings_outdir_entry.configure(
                fg_color=_p("input_bg"), text_color=_p("text_primary")
            )

        if hasattr(self, "_settings_header_lbl"):
            self._settings_header_lbl.configure(
                font=_font("subheader"),
                text_color=_p("text_primary"),
            )

        # tkinter Menu bar (not a CTK widget — must be reconfigured manually)
        if hasattr(self, "_menubar") and hasattr(self, "_menus"):
            _menu_clr = {
                "bg": _p("menu_bg"),
                "fg": _p("menu_fg"),
                "activebackground": _p("menu_active_bg"),
                "activeforeground": _p("menu_fg"),
            }
            self._menubar.configure(**_menu_clr)
            for menu in self._menus:
                menu.configure(**_menu_clr)

    # ------------------------------------------------------------------
    # OS theme detection & live sync
    # ------------------------------------------------------------------

    def sync_with_os(self, os_theme: str | None = None) -> None:
        """Align the application's appearance with the current OS theme.

        Only acts when the user's saved ``appearance_mode`` is ``"System"``.
        If *os_theme* is supplied (by the darkdetect listener callback) it is
        used directly; otherwise the theme is freshly detected via
        ``_detect_os_theme()``.

        Safe to call from any thread — always dispatches UI work to the Tk
        main thread.
        """
        if self._closing:
            return
        # Only auto-follow the OS when the setting is "System"
        mode = (
            self._current_settings.appearance_mode
            if self._current_settings
            else "System"
        )
        if mode != "System":
            return

        effective = os_theme if os_theme in ("Dark", "Light") else _detect_os_theme()

        def _apply(theme: str = effective) -> None:
            if self._closing:
                return
            ctk.set_appearance_mode(theme)
            self._apply_theme()
            logger.debug("OS theme sync: applied %s", theme)

        # Dispatch to Tk main thread (safe whether we're already on it or not)
        self.after(0, _apply)

    def _start_os_theme_listener(self) -> None:
        """Spawn a daemon thread that watches for OS theme changes.

        Uses ``darkdetect.listener()`` when available; the callback fires with
        ``"Dark"`` or ``"Light"`` and routes to ``sync_with_os()`` on the main
        thread.  If ``darkdetect`` is unavailable the method is a no-op — the
        initial ``sync_with_os()`` call at startup still provides correct
        one-time detection.
        """
        try:
            import darkdetect  # type: ignore[import-untyped]  # noqa: PLC0415
        except ImportError:
            logger.debug("darkdetect not available — OS theme listener disabled")
            return

        if self._os_listener_active:
            return
        self._os_listener_active = True

        def _listener_worker() -> None:
            try:
                darkdetect.listener(
                    lambda theme: (
                        None if self._closing else self.sync_with_os(theme)
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("OS theme listener exited: %s", exc)
            finally:
                self._os_listener_active = False

        t = threading.Thread(target=_listener_worker, daemon=True, name="os-theme-listener")
        t.start()

    def _stop_os_theme_listener(self) -> None:
        """Signal the listener to stop (handled via the ``_closing`` flag)."""
        self._os_listener_active = False

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _apply_startup_settings(self) -> None:
        """Load persisted settings and apply appearance mode before building UI.

        Only sets the CTk appearance mode and stores ``_current_settings``.
        Widget-level theme refresh (``_apply_theme``, ``sync_with_os``) must be
        called separately *after* ``_build_ui`` via ``_apply_startup_theme``.
        """
        try:
            from gensubtitles.core.settings import AppSettings, load_settings  # noqa: PLC0415

            self._current_settings = load_settings()
            ctk.set_appearance_mode(self._current_settings.appearance_mode)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load settings: %s", exc)
            from gensubtitles.core.settings import AppSettings  # noqa: PLC0415

            self._current_settings = AppSettings()

    def _apply_startup_theme(self) -> None:
        """Apply widget-level colours and start OS theme listener.

        Must be called *after* ``_build_ui`` so that widget references exist.
        """
        self._apply_theme()
        # Detect current OS theme immediately and start live-sync listener.
        # sync_with_os() is a no-op if appearance_mode != "System".
        self.sync_with_os()
        self._start_os_theme_listener()

    def _show_settings(self) -> None:
        """Show settings panel, hide main tabview. Populate from current settings."""
        if self._current_settings:
            self._settings_appearance_var.set(self._current_settings.appearance_mode)
            lang_label = "Spanish" if self._current_settings.ui_language == "es" else "English"
            self._settings_lang_var.set(lang_label)
            self._settings_outdir_var.set(self._current_settings.default_output_dir)
        self._tabview.pack_forget()
        self._settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def _hide_settings(self) -> None:
        """Hide settings panel, restore tabview."""
        self._settings_frame.pack_forget()
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

    def _save_settings(self) -> None:
        """Persist settings and apply immediately."""
        try:
            from gensubtitles.core.settings import AppSettings, save_settings  # noqa: PLC0415

            lang_code = "es" if self._settings_lang_var.get() == "Spanish" else "en"
            new_settings = AppSettings(
                appearance_mode=self._settings_appearance_var.get(),
                ui_language=lang_code,
                default_output_dir=self._settings_outdir_var.get().strip(),
                default_source_lang=(
                    self._current_settings.default_source_lang
                    if self._current_settings
                    else ""
                ),
            )
            save_settings(new_settings)
            self._current_settings = new_settings
            ctk.set_appearance_mode(new_settings.appearance_mode)
            self._apply_theme()
            # If the user just switched to "System", sync immediately and
            # ensure the live listener is running.
            if new_settings.appearance_mode == "System":
                self.sync_with_os()
                self._start_os_theme_listener()
        except Exception as exc:  # noqa: BLE001
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Settings error", f"Could not save settings: {exc}")
        finally:
            self._hide_settings()

    # ------------------------------------------------------------------
    # Help stubs (implemented in Plan 06)
    # ------------------------------------------------------------------

    def _show_tutorial(self) -> None:
        """Open a scrollable tutorial CTkToplevel window."""
        win = ctk.CTkToplevel(self)
        win.title("GenSubtitles \u2014 Tutorial")
        win.minsize(500, 500)
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        tutorial_text = """
GenSubtitles \u2014 Usage Guide
==========================

OVERVIEW
--------
GenSubtitles converts video files to subtitle files (.srt or .ssa) entirely offline.
No internet connection or API keys are required once language models are installed.

GENERATE SUBTITLES TAB
-----------------------
1. Click "Browse\u2026" next to "Input video" and select your video file (.mp4, .mkv, .avi, .mov, .webm).
2. The output subtitle path is auto-filled based on the video filename. Change it if needed.
3. Select a Source Language (or leave as Auto-detect \u2014 Whisper will identify the language automatically).
4. Select a Target Language if you want translation. Leave as "No target" to keep the original language.
5. Choose Output Format: SRT (most compatible) or SSA (richer styling).
6. Click "Generate Subtitles". Progress is shown with the elapsed timer and a progress bar.
7. When finished, the subtitle file is saved to the chosen output path.

TRANSLATE SUBTITLES TAB
------------------------
Use this tab if you already have a subtitle file and only need to translate or convert it.

1. Click "Browse\u2026" next to "Input subtitle" and select a .srt or .ssa file.
2. The output path is auto-filled as <filename>_translated.<ext>.
3. Select the source language of the subtitle file.
4. Select the target language for translation.
5. (Optional) Check "Convert only" to change file format without translation.
6. Click "Translate / Convert".

LANGUAGE MODEL INSTALLATION
-----------------------------
GenSubtitles uses Argos Translate for offline translation.
Language models are downloaded automatically on first use (internet required for download only).
After downloading, all translation works offline.

Use Help > Available Languages to see which pairs are currently installed.

SETTINGS
---------
Access via the Settings menu > Preferences.
- Appearance Mode: Light, Dark, or follow System setting.
- UI Language: English or Spanish.
- Default output directory: pre-fills output path (leave blank to use same folder as input).

TROUBLESHOOTING
----------------
\u2022 "FFmpeg not found" \u2014 Install FFmpeg and ensure it is in your system PATH.
\u2022 Translation fails \u2014 The selected language pair may not be installed. Check Help > Available Languages.
\u2022 Subtitles are blank \u2014 The default speech model is `medium` (~1.5 GB first-run download). If this is the first run, make sure the model download completed successfully and that you had internet access during setup. Also check whether the video has an audio track.
\u2022 API connection refused \u2014 The background server failed to start. Restart the application.
"""

        label = ctk.CTkLabel(
            scroll,
            text=tutorial_text.strip(),
            justify="left",
            anchor="nw",
            wraplength=440,
            font=_font("mono"),
            text_color=_p("text_primary"),
        )
        label.pack(fill="both", expand=True)

        ctk.CTkButton(win, text="Close", command=win.destroy).pack(pady=(0, 12))

    def _show_language_pairs(self) -> None:
        """Open a dialog listing currently installed language pairs."""
        win = ctk.CTkToplevel(self)
        win.title("Installed Language Pairs")
        win.minsize(360, 300)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="Installed Translation Pairs",
            font=_font("body_bold"),
            text_color=_p("text_primary"),
        ).pack(pady=(16, 8))

        pairs = self._language_pairs
        if not pairs:
            ctk.CTkLabel(
                win,
                text=(
                    "No language pairs installed.\n"
                    "Pairs are downloaded automatically on first translation."
                ),
            ).pack(pady=20)
        else:
            scroll = ctk.CTkScrollableFrame(win)
            scroll.pack(fill="both", expand=True, padx=16, pady=8)
            for p in sorted(pairs, key=lambda x: (x["from"], x["to"])):
                src_label = _CODE_TO_LABEL.get(p["from"], p["from"].upper())
                dst_label = _CODE_TO_LABEL.get(p["to"], p["to"].upper())
                ctk.CTkLabel(
                    scroll,
                    text=f"  {src_label}  \u2192  {dst_label}",
                    anchor="w",
                ).pack(fill="x", pady=2)

        ctk.CTkButton(win, text="Close", command=win.destroy).pack(pady=(8, 16))

    def _show_about(self) -> None:
        """Open About GenSubtitles dialog."""
        import gensubtitles  # noqa: PLC0415

        version = getattr(gensubtitles, "__version__", "0.1.0")

        win = ctk.CTkToplevel(self)
        win.title("About GenSubtitles")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="GenSubtitles",
            font=_font("header"),
            text_color=_p("text_primary"),
        ).pack(pady=(24, 4))
        ctk.CTkLabel(win, text=f"Version {version}", font=_font("body"), text_color=_p("text_primary")).pack(pady=4)
        ctk.CTkLabel(
            win,
            text="Automatic offline subtitle generation\nusing Whisper + Argos Translate.",
            justify="center",
            font=_font("body"),
            text_color=_p("text_primary"),
        ).pack(pady=8)
        ctk.CTkLabel(win, text="License: MIT", text_color="gray").pack(pady=4)

        def _open_github() -> None:
            import webbrowser  # noqa: PLC0415

            webbrowser.open("https://github.com/leocg/GenSubtitles")

        ctk.CTkButton(win, text="GitHub Project", command=_open_github).pack(pady=(8, 4))
        ctk.CTkButton(
            win, text="Close", command=win.destroy, fg_color="gray"
        ).pack(pady=(4, 24))

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _on_translate(self) -> None:
        input_path = self._tl_input_var.get().strip()
        output_path = self._tl_output_var.get().strip()

        if not input_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Missing input", "Please select a subtitle file.")
            return
        if not output_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Missing output", "Please choose an output path.")
            return

        convert_only = self._tl_convert_only_var.get()
        src_lang = _label_to_code(self._tl_source_var.get()) if not convert_only else None
        tgt_lang = _label_to_code(self._tl_target_var.get()) if not convert_only else None

        _widgets = (
            self._tl_btn_translate, self._tl_btn_browse, self._tl_btn_browse_out,
            self._tl_entry_input, self._tl_entry_output,
            self._tl_option_source, self._tl_option_target, self._tl_chk_convert,
        )
        for w in _widgets:
            w.configure(state="disabled")

        self._tl_progress_bar.grid()
        self._tl_progress_bar.configure(progress_color=_p("progress_proc"))
        self._tl_progress_bar.start()
        self._tl_stage_label.configure(
            text="Translating…" if not convert_only else "Converting…"
        )
        self._tl_elapsed_label.configure(text="00:00:00")
        self._tl_elapsed_start = time.monotonic()
        self._tl_elapsed_label.grid()
        self._tick_tl_elapsed()

        threading.Thread(
            target=self._run_translate,
            args=(input_path, output_path, src_lang, tgt_lang, convert_only),
            daemon=True,
        ).start()

    def _tick_tl_elapsed(self) -> None:
        if self._closing:
            return
        elapsed = int(time.monotonic() - self._tl_elapsed_start)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        self._tl_elapsed_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        self._tl_elapsed_timer = self.after(1000, self._tick_tl_elapsed)

    def _run_translate(
        self,
        input_path: str,
        output_path: str,
        src_lang: str | None,
        tgt_lang: str | None,
        convert_only: bool,
    ) -> None:
        try:
            src_ext = Path(input_path).suffix.lower()
            dst_ext = Path(output_path).suffix.lower()

            if convert_only:
                from gensubtitles.core.srt_writer import (  # noqa: PLC0415
                    convert_ssa_to_srt,
                    convert_srt_to_ssa,
                )

                if src_ext == ".srt" and dst_ext in (".ssa", ".ass"):
                    convert_srt_to_ssa(input_path, output_path)
                elif src_ext in (".ssa", ".ass") and dst_ext == ".srt":
                    convert_ssa_to_srt(input_path, output_path)
                else:
                    import shutil  # noqa: PLC0415

                    shutil.copy2(input_path, output_path)
            else:
                from gensubtitles.core.translator import translate_file  # noqa: PLC0415

                translate_file(input_path, tgt_lang, src_lang, output_path)

            if not self._closing:
                self.after(0, self._finish_translate, None, output_path)
        except Exception as exc:  # noqa: BLE001
            if not self._closing:
                self.after(0, self._finish_translate, str(exc), None)

    def _finish_translate(self, error: str | None, output_path: str | None) -> None:
        if self._tl_elapsed_timer is not None:
            self.after_cancel(self._tl_elapsed_timer)
            self._tl_elapsed_timer = None
        if error:
            self._tl_progress_bar.stop()
            self._tl_progress_bar.configure(mode="determinate", progress_color=_p("progress_err"))
            self._tl_progress_bar.set(1.0)
            self._tl_progress_bar.grid()
            self.after(2000, self._hide_translate_progress)
        else:
            self._tl_progress_bar.stop()
            self._tl_progress_bar.configure(mode="determinate", progress_color=_p("progress_done"))
            self._tl_progress_bar.set(1.0)
            self._tl_progress_bar.grid()
            self.after(2000, self._hide_translate_progress)
        self._tl_elapsed_label.grid_remove()
        self._tl_stage_label.configure(text="")

        _widgets = (
            self._tl_btn_translate, self._tl_btn_browse, self._tl_btn_browse_out,
            self._tl_entry_input, self._tl_entry_output,
            self._tl_option_source, self._tl_option_target, self._tl_chk_convert,
        )
        for w in _widgets:
            w.configure(state="normal")

        if error:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror("Translation failed", error)
        else:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showinfo("Done", f"Saved: {output_path}")

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _start_server(self) -> None:
        import uvicorn  # noqa: PLC0415

        _SERVER_BIND_TIMEOUT = 30  # seconds to wait for Uvicorn to bind

        def _run() -> None:
            try:
                config = uvicorn.Config(
                    "gensubtitles.api.main:app",
                    host="127.0.0.1",
                    port=8000,
                    log_level="error",
                )
                self._server = uvicorn.Server(config)
                self._server.run()
            except OSError as exc:
                logger.error("GUI server failed to start: %s", exc)

        def _wait_for_server() -> None:
            import requests as req  # noqa: PLC0415

            # Phase 1: wait until the HTTP server binds and /status responds
            deadline = time.monotonic() + _SERVER_BIND_TIMEOUT
            while not self._closing:
                if not thread.is_alive():
                    if not self._closing:
                        self.after(0, lambda: self._on_server_failed(
                            "Server process exited unexpectedly. Check port 8000.",
                        ))
                    return
                if time.monotonic() > deadline:
                    if not self._closing:
                        self.after(0, lambda: self._on_server_failed(
                            "Server did not start within "
                            f"{_SERVER_BIND_TIMEOUT}s. Check port 8000.",
                        ))
                    return
                time.sleep(1)
                try:
                    req.get(f"{_BASE_URL}/status", timeout=1)
                    break  # server is up
                except Exception:  # noqa: BLE001
                    continue

            # Phase 2: poll /status until model is ready, updating the GUI label
            while not self._closing:
                if not thread.is_alive():
                    if not self._closing:
                        self.after(0, lambda: self._on_server_failed(
                            "Server process exited unexpectedly during model loading.",
                        ))
                    return
                time.sleep(1)
                try:
                    resp = req.get(f"{_BASE_URL}/status", timeout=2)
                    data = resp.json()
                    stage = data.get("stage", "")
                    message = data.get("message", "")
                    progress = data.get("progress", -1)
                    if not self._closing:
                        self.after(0, lambda m=message, p=progress: self._apply_startup_progress(m, p))
                    if stage == "ready":
                        if not self._closing:
                            self._server_ready = True
                            self.after(0, self._on_server_ready)
                        return
                    if stage == "error":
                        if not self._closing:
                            self.after(0, lambda m=message: self._on_server_failed(m))
                        return
                except Exception:  # noqa: BLE001
                    continue

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        threading.Thread(target=_wait_for_server, daemon=True).start()
        # Show startup progress bar immediately
        self._progress_bar.configure(mode="indeterminate", progress_color=_p("progress_idle"))
        self._progress_bar.grid()
        self._progress_bar.start()

    def _stop_server(self) -> None:
        if self._server is not None:
            self._server.should_exit = True

    def _apply_startup_progress(self, message: str, progress: int) -> None:
        """Update progress bar and label during model download/load phases."""
        self._stage_label.configure(text=message)
        if progress >= 0:
            # Determinate — real percentage available (downloading)
            if self._progress_bar.cget("mode") != "determinate":
                self._progress_bar.stop()
                self._progress_bar.configure(mode="determinate", progress_color=_p("accent"))
            self._progress_bar.set(progress / 100)
        else:
            # Indeterminate — loading into memory or waiting
            if self._progress_bar.cget("mode") != "indeterminate":
                self._progress_bar.configure(mode="indeterminate", progress_color=_p("progress_idle"))
                self._progress_bar.start()

    def _on_server_ready(self) -> None:
        """Called on main thread once the local API server responds."""
        self._server_ready = True
        self._progress_bar.stop()
        self._progress_bar.grid_remove()
        self._progress_bar.configure(progress_color=_p("progress_idle"))
        self._btn_generate.configure(state="normal")
        self._tl_btn_translate.configure(state="normal")
        self._stage_label.configure(text="", text_color=_p("text_secondary"))
        # Run in background — list_installed_pairs() can be slow on first Argos load
        threading.Thread(target=self._populate_language_dropdowns, daemon=True).start()

    def _on_server_failed(self, detail: str = "") -> None:
        """Called on main thread if the server never became reachable."""
        self._progress_bar.stop()
        self._progress_bar.configure(mode="determinate", progress_color=_p("progress_err"))
        self._progress_bar.set(1.0)
        text = f"❌ {detail}" if detail else "❌ Server failed to start. Restart the app."
        self._stage_label.configure(
            text=text,
            text_color=_p("progress_err"),
        )

    def on_closing(self) -> None:
        self._closing = True
        self._stop_os_theme_listener()
        self._stop_server()
        self.destroy()


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    app = GenSubtitlesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
