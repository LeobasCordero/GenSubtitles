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
from hashlib import sha1
from pathlib import Path

import customtkinter as ctk
from .theme import font, p
from .styles import (
    BTN_HEIGHT_PRIMARY, BTN_HEIGHT_CANCEL, BTN_HEIGHT_MINI,
    BTN_WIDTH_BROWSE, BTN_WIDTH_NARROW, BTN_WIDTH_SWATCH, ENTRY_WIDTH_SMALL,
    PROGRESS_BAR_HEIGHT,
    apply_entry_style, apply_accent_btn_style, apply_secondary_btn_style,
    apply_cancel_btn_style, apply_progress_bar_style, apply_stage_label_style,
    apply_secondary_label_style, apply_settings_header_style, apply_window_bg,
)
from .locale import s, set_language, s_lang, LANGUAGES
from . import server

# Suppress HuggingFace Hub symlink warning (not supported without Developer Mode on Windows)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

logger = logging.getLogger(__name__)

# Appearance defaults — use System until user settings are loaded.
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

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
        self.minsize(900, 560)
        self.configure(fg_color=p("bg"))

        # String variables for entry widgets
        self._input_var = ctk.StringVar()
        self._output_var = ctk.StringVar()
        self._source_lang_var = ctk.StringVar()
        self._target_lang_var = ctk.StringVar(value="No target")
        self._output_format_var = ctk.StringVar(value="SRT")
        self._engine_var = ctk.StringVar(value="Argos")

        # Phase 999.30 — per-tab StringVars for step tabs 3-6
        self._extract_input_var = ctk.StringVar()
        self._extract_output_var = ctk.StringVar()
        self._transcribe_input_var = ctk.StringVar()
        self._translate_step_input_var = ctk.StringVar()
        self._translate_step_source_var = ctk.StringVar()
        self._translate_step_target_var = ctk.StringVar(value="No target")
        self._translate_step_engine_var = ctk.StringVar(value="Argos")
        self._write_input_var = ctk.StringVar()
        self._write_output_var = ctk.StringVar()
        self._write_format_var = ctk.StringVar(value="SRT")

        # Dynamic language pairs loaded from API
        self._language_pairs: list[dict] = []

        # Server references
        self._stage_timer = None
        self._elapsed_timer = None
        self._elapsed_start: float = 0.0
        self._tl_elapsed_start: float = 0.0
        self._tl_elapsed_timer = None
        self._closing = False
        self._prefetch_in_progress: set[tuple[str, str]] = set()
        self._prefetch_lock = threading.Lock()
        self._job_active = False
        self._current_job_id: str | None = None
        self._current_settings = None
        self._server_ready = False
        self._os_listener_active = False  # guard for the darkdetect listener thread

        self._apply_startup_settings()
        self._build_ui()
        self._apply_startup_theme()
        self._apply_startup_target_lang()
        self._apply_ui_language()   # apply saved ui_language to all widget labels
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._start_server()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Tab container — unchanged
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=16, pady=16)
        self._tabview.add("Generate Subtitles")
        self._tabview.add("Translate Subtitles")
        self._tabview.add("Extract Audio")    # Tab 3 — built by Plan 03
        self._tabview.add("Transcribe")       # Tab 4 — built by Plan 03
        self._tabview.add("Translate")        # Tab 5 — built by Plan 03
        self._tabview.add("Write Subtitle")   # Tab 6 — built by Plan 03

        _tab_gen = self._tabview.tab("Generate Subtitles")

        # ── Two-panel container (D-02) ────────────────────────────────────────────
        self._panels_frame = ctk.CTkFrame(_tab_gen, fg_color="transparent")
        self._panels_frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        self._panels_frame.columnconfigure(0, weight=1)
        self._panels_frame.columnconfigure(1, weight=1)
        self._panels_frame.rowconfigure(0, weight=1)

        # ── Panel frames ─────────────────────────────────────────────────────────
        self._files_frame = ctk.CTkFrame(
            self._panels_frame, corner_radius=12, fg_color=p("surface")
        )
        self._files_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=0)
        self._files_frame.columnconfigure(0, weight=1)

        self._config_frame = ctk.CTkFrame(
            self._panels_frame, corner_radius=12, fg_color=p("surface")
        )
        self._config_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=0)
        self._config_frame.columnconfigure(0, weight=1)

        # ── files_frame: video + output ──────────────────────────────────────────
        _startup_lang = (
            getattr(self._current_settings, "ui_language", "en")
            if self._current_settings else "en"
        )
        set_language(_startup_lang)

        # Input video group
        self._lbl_input_video = ctk.CTkLabel(
            self._files_frame, text=s("input_video_lbl"), anchor="w"
        )
        self._lbl_input_video.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        _input_row = ctk.CTkFrame(self._files_frame, fg_color="transparent")
        _input_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        _input_row.columnconfigure(0, weight=1)
        self._entry_input = ctk.CTkEntry(_input_row, textvariable=self._input_var)
        apply_entry_style(self._entry_input)
        self._entry_input.grid(row=0, column=0, sticky="ew")
        self._btn_browse_input = ctk.CTkButton(
            _input_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=self._browse_input,
        )
        apply_secondary_btn_style(self._btn_browse_input)
        self._btn_browse_input.grid(row=0, column=1, padx=(8, 0))

        # Output file group
        self._lbl_output_file = ctk.CTkLabel(
            self._files_frame, text=s("output_file_lbl"), anchor="w"
        )
        self._lbl_output_file.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 2))
        _output_row = ctk.CTkFrame(self._files_frame, fg_color="transparent")
        _output_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        _output_row.columnconfigure(0, weight=1)
        self._entry_output = ctk.CTkEntry(_output_row, textvariable=self._output_var)
        apply_entry_style(self._entry_output)
        self._entry_output.grid(row=0, column=0, sticky="ew")
        self._btn_browse_output = ctk.CTkButton(
            _output_row, text=s("save_as_btn"), width=BTN_WIDTH_BROWSE,
            command=self._browse_output,
        )
        apply_secondary_btn_style(self._btn_browse_output)
        self._btn_browse_output.grid(row=0, column=1, padx=(8, 0))

        # ── config_frame: "Configuration" ────────────────────────────────────────
        self._lbl_config_title = ctk.CTkLabel(
            self._config_frame, text=s("panel_config_title"), font=font("subheader"),
            anchor="w",
        )
        self._lbl_config_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        # Source language
        self._lbl_source_lang = ctk.CTkLabel(
            self._config_frame, text=s("source_lang_lbl"), anchor="w"
        )
        self._lbl_source_lang.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 2))
        self._option_source_lang = ctk.CTkOptionMenu(
            self._config_frame,
            values=["Auto-detect"],
            variable=self._source_lang_var,
            command=self._on_source_lang_change,
        )
        self._option_source_lang.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Target language
        self._lbl_target_lang = ctk.CTkLabel(
            self._config_frame, text=s("target_lang_lbl"), anchor="w"
        )
        self._lbl_target_lang.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 2))
        self._option_target_lang = ctk.CTkOptionMenu(
            self._config_frame,
            values=["No target"],
            variable=self._target_lang_var,
            command=self._on_target_lang_change,
        )
        self._option_target_lang.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Engine dropdown (hidden initially — shown when target lang selected)
        _engine_values = ["Argos"]
        if self._current_settings and self._current_settings.deepl_api_key:
            _engine_values.append("DeepL")
        if self._current_settings and self._current_settings.libretranslate_url:
            _engine_values.append("LibreTranslate")
        self._lbl_engine = ctk.CTkLabel(
            self._config_frame, text=s("engine_lbl"), anchor="w"
        )
        self._lbl_engine.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 2))
        self._option_engine = ctk.CTkOptionMenu(
            self._config_frame,
            values=_engine_values,
            variable=self._engine_var,
        )
        self._option_engine.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._lbl_engine.grid_remove()
        self._option_engine.grid_remove()

        # Output format
        self._lbl_output_format = ctk.CTkLabel(
            self._config_frame, text=s("output_format_lbl"), anchor="w"
        )
        self._lbl_output_format.grid(row=7, column=0, sticky="w", padx=12, pady=(0, 2))
        self._option_output_format = ctk.CTkOptionMenu(
            self._config_frame,
            values=["SRT", "SSA"],
            variable=self._output_format_var,
            command=self._on_output_format_change,
        )
        self._option_output_format.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Generate button (accent)
        self._btn_generate = ctk.CTkButton(
            self._config_frame,
            text=s("generate_btn"),
            command=self._on_generate,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._btn_generate)
        self._btn_generate.grid(row=9, column=0, sticky="ew", padx=12, pady=(4, 4))

        # Clear fields button (secondary)
        self._btn_clear = ctk.CTkButton(
            self._config_frame,
            text=s("generate_clear_btn"),
            command=self._on_clear,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_secondary_btn_style(self._btn_clear)
        self._btn_clear.grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Reactive enable/disable for Clear button
        for var in (self._input_var, self._output_var, self._target_lang_var):
            var.trace_add("write", lambda *_: self._update_clear_state())

        # Stage label (status feedback)
        stage_text = s("starting_server")
        self._stage_label = ctk.CTkLabel(self._config_frame, text=stage_text)
        apply_stage_label_style(self._stage_label)
        self._stage_label.grid(row=11, column=0, pady=4)

        # Log textbox (D-03)
        self._log_textbox = ctk.CTkTextbox(
            self._config_frame,
            state="disabled",
            height=120,
            fg_color=p("input_bg"),
            font=font("mono"),
            activate_scrollbars=True,
        )
        self._log_textbox.grid(row=12, column=0, sticky="ew", padx=12, pady=(0, 4))

        # Elapsed label (hidden until generate runs)
        self._elapsed_label = ctk.CTkLabel(self._config_frame, text="00:00:00")
        self._elapsed_label.grid(row=13, column=0, pady=(4, 0))
        self._elapsed_label.grid_remove()

        # Progress bar (hidden until generate runs)
        self._progress_bar = ctk.CTkProgressBar(
            self._config_frame, height=PROGRESS_BAR_HEIGHT,
        )
        apply_progress_bar_style(self._progress_bar)
        self._progress_bar.grid(row=14, column=0, sticky="ew", padx=12, pady=(4, 4))
        self._progress_bar.grid_remove()

        # Cancel button (hidden until generate runs)
        self._btn_cancel = ctk.CTkButton(
            self._config_frame,
            text="Cancel",
            command=self._on_cancel,
            height=BTN_HEIGHT_CANCEL,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_cancel_btn_style(self._btn_cancel)
        self._btn_cancel.grid(row=15, column=0, sticky="ew", padx=12, pady=(4, 0))
        self._btn_cancel.grid_remove()

        # Build remaining tabs and panels — unchanged
        self._build_translate_tab()
        self._build_extract_tab()
        self._build_transcribe_tab()
        self._build_translate_step_tab()
        self._build_write_tab()
        self._build_settings_panel()
        self._build_menu_bar()

    def _log_to(self, textbox: "ctk.CTkTextbox", msg: str) -> None:
        self._switch_stepper.grid(row=_row, column=0, sticky="w", padx=12, pady=(0, 8))
        _row += 1

        # ── Work directory picker (hidden by default — visible when switch ON) ─
        _work_dir_row = ctk.CTkFrame(sf, fg_color="transparent")
        _work_dir_row.columnconfigure(0, weight=1)
        _work_dir_row.grid(row=_row, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._work_dir_row_frame = _work_dir_row  # keep ref for show/hide
        self._lbl_work_dir = ctk.CTkLabel(_work_dir_row, text=s("work_dir_lbl"), anchor="w")
        self._lbl_work_dir.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self._entry_work_dir = ctk.CTkEntry(_work_dir_row, textvariable=self._work_dir_var)
        apply_entry_style(self._entry_work_dir)
        self._entry_work_dir.grid(row=1, column=0, sticky="ew")
        self._btn_browse_work_dir = ctk.CTkButton(
            _work_dir_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=self._browse_work_dir,
        )
        apply_secondary_btn_style(self._btn_browse_work_dir)
        self._btn_browse_work_dir.grid(row=1, column=1, padx=(8, 0))
        _work_dir_row.grid_remove()  # hidden until switch is ON
        _row += 1

        # ── 4-stage horizontal flow ───────────────────────────────────────
        self._stepper_frame = ctk.CTkFrame(sf, fg_color=p("surface"))
        self._stepper_frame.grid(row=_row, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._stepper_frame.columnconfigure((0, 1, 2, 3), weight=1)
        _row += 1

        _stage_defs = [
            ("extract",    "1. Extract"),
            ("transcribe", "2. Transcribe"),
            ("translate",  "3. Translate"),
            ("write",      "4. Write SRT"),
        ]
        _btn_commands = {
            "extract":    self._on_step_extract,
            "transcribe": self._on_step_transcribe,
            "translate":  self._on_step_translate,
            "write":      self._on_step_write,
        }

        self._step_status_labels: dict[str, ctk.CTkLabel] = {}
        self._step_buttons: dict[str, ctk.CTkButton] = {}

        for col, (stage_key, stage_name) in enumerate(_stage_defs):
            sub = ctk.CTkFrame(self._stepper_frame, fg_color="transparent")
            sub.grid(row=0, column=col, padx=4, pady=6, sticky="nsew")
            sub.columnconfigure(0, weight=1)

            ctk.CTkLabel(sub, text=stage_name, font=font("body")).grid(
                row=0, column=0, sticky="ew", pady=(0, 2)
            )
            status_lbl = ctk.CTkLabel(sub, text="—", font=font("body"))
            apply_secondary_label_style(status_lbl)
            status_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 4))
            self._step_status_labels[stage_key] = status_lbl

            btn = ctk.CTkButton(
                sub, text=stage_name.split(". ", 1)[-1],
                command=_btn_commands[stage_key],
                state="disabled",
                height=BTN_HEIGHT_MINI,
                text_color_disabled=("#757575", "#9E9E9E"),
            )
            apply_secondary_btn_style(btn)
            btn.grid(row=2, column=0, sticky="ew")
            self._step_buttons[stage_key] = btn

        # ── Main action button (dynamic text) ────────────────────────────
        self._btn_generate = ctk.CTkButton(
            sf,
            text=s("generate_btn"),  # default: full-pipeline text (switch OFF)
            command=self._on_generate,
            height=BTN_HEIGHT_PRIMARY,
            state="disabled",
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._btn_generate)
        self._btn_generate.grid(row=_row, column=0, sticky="ew", padx=12, pady=(8, 0))
        _row += 1

        # ── Elapsed time counter (hidden initially) ───────────────────────
        self._elapsed_label = ctk.CTkLabel(sf, text="00:00:00")
        self._elapsed_label.grid(row=_row, column=0, pady=(4, 0))
        self._elapsed_label.grid_remove()
        _row += 1

        # ── Progress bar (hidden initially) ──────────────────────────────
        self._progress_bar = ctk.CTkProgressBar(
            sf, mode="indeterminate", height=PROGRESS_BAR_HEIGHT,
        )
        apply_progress_bar_style(self._progress_bar)
        self._progress_bar.grid(row=_row, column=0, sticky="ew", padx=12, pady=(4, 4))
        self._progress_bar.grid_remove()
        _row += 1

        # ── Stage label (status text) ─────────────────────────────────────
        _startup_lang = (
            getattr(self._current_settings, "ui_language", "en")
            if self._current_settings else "en"
        )
        stage_text = s("starting_server")
        self._stage_label = ctk.CTkLabel(sf, text=stage_text)
        apply_stage_label_style(self._stage_label)
        self._stage_label.grid(row=_row, column=0, pady=4)
        _row += 1

        # ── Activity log textbox ──────────────────────────────────────────
        self._log_textbox = ctk.CTkTextbox(
            sf,
            state="disabled",
            height=100,
            fg_color=p("input_bg"),
            font=font("mono"),
            wrap="word",
        )
        self._log_textbox.grid(row=_row, column=0, sticky="ew", padx=12, pady=(0, 4))
        _row += 1

        # ── Clear Work Files button ───────────────────────────────────────
        self._btn_clear_work = ctk.CTkButton(
            sf,
            text=s("clear_work_btn"),
            command=self._on_clear_work,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_secondary_btn_style(self._btn_clear_work)
        self._btn_clear_work.grid(row=_row, column=0, sticky="ew", padx=12, pady=(0, 8))
        _row += 1

        # ── Cancel button (hidden initially) ─────────────────────────────
        self._btn_cancel = ctk.CTkButton(
            sf,
            text="Cancel",
            command=self._on_cancel,
            height=BTN_HEIGHT_CANCEL,
        )
        apply_cancel_btn_style(self._btn_cancel)
        self._btn_cancel.grid(row=_row, column=0, sticky="ew", padx=12, pady=(4, 0))
        self._btn_cancel.grid_remove()  # hidden by default

        # Start work_dir polling
        self._work_dir_var.trace_add("write", self._on_work_dir_changed)
        self._schedule_stepper_refresh()

    def _log_to(self, textbox: "ctk.CTkTextbox", msg: str) -> None:
        """Append *msg* to any CTkTextbox log widget with auto-scroll."""
        try:
            textbox.configure(state="normal")
            textbox.insert("end", msg + "\n")
            textbox.configure(state="disabled")
            textbox.see("end")
        except Exception:  # noqa: BLE001
            pass

    def _get_tab_work_dir(
        self,
        input_var: "ctk.StringVar",
        fallback_vars: "list[ctk.StringVar] | None" = None,
    ) -> "Path | None":
        """Return work-dir path derived from *input_var*, or first non-empty fallback.

        Fallback chain (D-05): tab's own input → _input_var (Tab 1 video) → _extract_input_var (Tab 3 audio).
        """
        val = input_var.get().strip()
        if val:
            return Path(val).parent
        if fallback_vars:
            for fv in fallback_vars:
                fv_val = fv.get().strip()
                if fv_val:
                    return Path(fv_val).parent
        return None

    def _log(self, msg: str) -> None:
        """Append a message to the Tab 1 activity log textbox with auto-scroll."""
        self._log_to(self._log_textbox, msg)

    def _run_step_in_bg(
        self,
        step_key: str,
        api_endpoint: str,
        payload: dict,
        *,
        log_textbox: "ctk.CTkTextbox | None" = None,
        on_success: "Callable[[], None] | None" = None,
        on_error: "Callable[[str], None] | None" = None,
    ) -> None:
        """Execute a step API call in a background thread.

        Routes log messages to *log_textbox* (defaults to Tab 1 _log_textbox).
        Calls *on_success* or *on_error* on the main thread when done.
        """
        _tb = log_textbox if log_textbox is not None else self._log_textbox
        self._log_to(_tb, f"\u23f3 Running step: {step_key}")

        def _worker() -> None:
            try:
                import requests as req  # noqa: PLC0415
                resp = req.post(f"{server.BASE_URL}{api_endpoint}", json=payload, timeout=600)
                if resp.status_code == 200:
                    if on_success:
                        self.after(0, on_success)
                else:
                    try:
                        detail = resp.json().get("detail", f"HTTP {resp.status_code}")
                    except Exception:  # noqa: BLE001
                        detail = f"HTTP {resp.status_code}"
                    if on_error:
                        self.after(0, on_error, detail)
                    else:
                        self.after(0, lambda d=detail: self._log_to(_tb, f"\u2717 Error: {d}"))
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    self.after(0, on_error, str(exc))
                else:
                    self.after(0, lambda e=exc: self._log_to(_tb, f"\u2717 Error: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_step_success(self, step_key: str) -> None:
        """Legacy callback — kept for compatibility. Step tabs use per-tab on_success callbacks."""
        self._log(f"\u2713 Step {step_key} completed")

    def _on_step_error(self, step_key: str, detail: str) -> None:
        """Legacy callback — kept for compatibility. Step tabs use per-tab on_error callbacks."""
        self._log(f"\u2717 Step error ({step_key}): {str(detail)[:120]}")

    def _browse_file_to_var(
        self,
        var: "ctk.StringVar",
        filetypes: "list[tuple[str, str]] | None" = None,
    ) -> None:
        """Open file-open dialog and set *var* to the selected path."""
        from tkinter import filedialog  # noqa: PLC0415
        path = filedialog.askopenfilename(filetypes=filetypes or [("All files", "*.*")])
        if path:
            var.set(path)

    def _save_file_to_var(
        self,
        var: "ctk.StringVar",
        defaultextension: str = ".srt",
        filetypes: "list[tuple[str, str]] | None" = None,
    ) -> None:
        """Open file-save dialog and set *var* to the chosen path."""
        from tkinter import filedialog  # noqa: PLC0415
        path = filedialog.asksaveasfilename(
            defaultextension=defaultextension,
            filetypes=filetypes or [("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _clear_tab_vars(self, *vars: "ctk.StringVar") -> None:
        """Clear one or more StringVars (used by step tab Clear buttons)."""
        for v in vars:
            v.set("")

    def _on_translate_step_target_change(self, value: str) -> None:
        """Show/hide engine dropdown in Tab 5 based on target language selection."""
        if value and value not in ("No target", ""):
            self._translate_step_lbl_engine.grid()
            self._translate_step_option_engine.grid()
        else:
            self._translate_step_lbl_engine.grid_remove()
            self._translate_step_option_engine.grid_remove()

    def _on_tab3_extract(self) -> None:
        """Tab 3: Extract Audio button handler."""
        video = self._extract_input_var.get().strip()
        if not video:
            self._log_to(self._extract_log_textbox, "\u26a0\ufe0f Please select an input video file.")
            return
        work = self._get_tab_work_dir(
            self._extract_input_var,
            fallback_vars=[self._input_var],
        )
        if work is None:
            self._log_to(self._extract_log_textbox, "\u26a0\ufe0f Cannot determine output directory.")
            return
        work.mkdir(parents=True, exist_ok=True)
        payload: dict = {"video_path": video, "work_dir": str(work)}

        def _on_success() -> None:
            self._log_to(self._extract_log_textbox, "\u2713 Audio extracted successfully.")
            # Pre-fill Tab 4 input (D-04)
            wavs = sorted(work.glob("*.wav"))
            if wavs:
                self._transcribe_input_var.set(str(wavs[0]))
                self._log_to(self._extract_log_textbox, f"\u2192 Pre-filled Tab 4 input: {wavs[0].name}")

        def _on_error(detail: str) -> None:
            self._log_to(self._extract_log_textbox, f"\u2717 Extract failed: {detail[:200]}")

        self._run_step_in_bg(
            "extract", "/steps/extract", payload,
            log_textbox=self._extract_log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_tab4_transcribe(self) -> None:
        """Tab 4: Transcribe button handler."""
        from gensubtitles.core.steps import TRANSCRIPTION_FILENAME  # noqa: PLC0415
        audio = self._transcribe_input_var.get().strip()
        if not audio:
            self._log_to(self._transcribe_log_textbox, "\u26a0\ufe0f Please select an input audio file.")
            return
        work = self._get_tab_work_dir(
            self._transcribe_input_var,
            fallback_vars=[self._extract_input_var, self._input_var],
        )
        if work is None:
            self._log_to(self._transcribe_log_textbox, "\u26a0\ufe0f Cannot determine work directory.")
            return
        src = self._source_lang_var.get()
        src_code = None if src in ("Auto-detect", "") else _label_to_code(src)
        payload = {"work_dir": str(work), "source_lang": src_code, "device": "auto"}

        def _on_success() -> None:
            self._log_to(self._transcribe_log_textbox, "\u2713 Transcription complete.")
            # Pre-fill Tab 5 input (D-04)
            transcription_path = work / TRANSCRIPTION_FILENAME
            if transcription_path.exists():
                self._translate_step_input_var.set(str(transcription_path))
                self._log_to(self._transcribe_log_textbox, f"\u2192 Pre-filled Tab 5 input: {TRANSCRIPTION_FILENAME}")

        def _on_error(detail: str) -> None:
            self._log_to(self._transcribe_log_textbox, f"\u2717 Transcription failed: {detail[:200]}")

        self._run_step_in_bg(
            "transcribe", "/steps/transcribe", payload,
            log_textbox=self._transcribe_log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_tab5_translate(self) -> None:
        """Tab 5: Translate step button handler."""
        from gensubtitles.core.steps import TRANSLATION_FILENAME  # noqa: PLC0415
        trans_file = self._translate_step_input_var.get().strip()
        if not trans_file:
            self._log_to(self._translate_step_log_textbox, "\u26a0\ufe0f Please select a transcription file.")
            return
        tgt = self._translate_step_target_var.get()
        if tgt in ("No target", ""):
            self._log_to(self._translate_step_log_textbox, "\u26a0\ufe0f Please select a target language.")
            return
        work = self._get_tab_work_dir(
            self._translate_step_input_var,
            fallback_vars=[self._transcribe_input_var, self._input_var],
        )
        if work is None:
            self._log_to(self._translate_step_log_textbox, "\u26a0\ufe0f Cannot determine work directory.")
            return
        tgt_code = _label_to_code(tgt)
        eng = self._translate_step_engine_var.get().lower()
        payload = {"work_dir": str(work), "target_lang": tgt_code, "engine": eng}

        def _on_success() -> None:
            self._log_to(self._translate_step_log_textbox, "\u2713 Translation complete.")
            # Pre-fill Tab 6 input (D-04)
            translation_path = work / TRANSLATION_FILENAME
            if translation_path.exists():
                self._write_input_var.set(str(translation_path))
                self._log_to(self._translate_step_log_textbox, f"\u2192 Pre-filled Tab 6 input: {TRANSLATION_FILENAME}")

        def _on_error(detail: str) -> None:
            self._log_to(self._translate_step_log_textbox, f"\u2717 Translation failed: {detail[:200]}")

        self._run_step_in_bg(
            "translate", "/steps/translate", payload,
            log_textbox=self._translate_step_log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_tab6_write(self) -> None:
        """Tab 6: Write Subtitle button handler."""
        trans_file = self._write_input_var.get().strip()
        if not trans_file:
            self._log_to(self._write_log_textbox, "\u26a0\ufe0f Please select an input file.")
            return
        work = self._get_tab_work_dir(
            self._write_input_var,
            fallback_vars=[self._translate_step_input_var, self._input_var],
        )
        if work is None:
            self._log_to(self._write_log_textbox, "\u26a0\ufe0f Cannot determine work directory.")
            return
        output_path = self._write_output_var.get().strip()
        if not output_path:
            from gensubtitles.core.steps import SRT_FILENAME  # noqa: PLC0415
            output_path = str(work / SRT_FILENAME)
        payload = {"work_dir": str(work), "output_path": output_path}

        def _on_success() -> None:
            self._log_to(self._write_log_textbox, f"\u2713 Subtitle written: {output_path}")

        def _on_error(detail: str) -> None:
            self._log_to(self._write_log_textbox, f"\u2717 Write failed: {detail[:200]}")

        self._run_step_in_bg(
            "write", "/steps/write", payload,
            log_textbox=self._write_log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _build_menu_bar(self) -> None:
        import tkinter as tk  # noqa: PLC0415

        _menu_cfg = dict(
            bg=p("menu_bg"), fg=p("menu_fg"),
            activebackground=p("menu_active_bg"), activeforeground=p("menu_fg"),
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
        self._settings_menu = settings_menu
        self._help_menu = help_menu
        self._menus = [settings_menu, help_menu]

    def _build_settings_panel(self) -> None:
        self._settings_frame = ctk.CTkFrame(self)
        # Not packed yet \u2014 shown via _show_settings

        sf = self._settings_frame
        sf.columnconfigure(1, weight=1)

        self._settings_header_lbl = ctk.CTkLabel(sf, text="Settings")
        apply_settings_header_style(self._settings_header_lbl)
        self._settings_header_lbl.grid(
            row=0, column=0, columnspan=2, pady=(12, 8), sticky="w", padx=12
        )

        # Appearance Mode
        self._lbl_appearance_mode = ctk.CTkLabel(sf, text="Appearance Mode:")
        self._lbl_appearance_mode.grid(row=1, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_appearance_var = ctk.StringVar(value="System")
        ctk.CTkOptionMenu(
            sf, values=["System", "Light", "Dark"],
            variable=self._settings_appearance_var,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=6)

        # UI Language
        self._lbl_ui_language_setting = ctk.CTkLabel(sf, text="UI Language:")
        self._lbl_ui_language_setting.grid(row=2, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_lang_var = ctk.StringVar(value="English")
        ctk.CTkOptionMenu(
            sf, values=["English", "Spanish"],
            variable=self._settings_lang_var,
        ).grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        # Default Output Directory
        self._lbl_default_outdir = ctk.CTkLabel(sf, text="Default output dir:")
        self._lbl_default_outdir.grid(row=3, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_outdir_var = ctk.StringVar()
        self._settings_outdir_entry = ctk.CTkEntry(
            sf, textvariable=self._settings_outdir_var,
            placeholder_text="(same directory as input)",
        )
        apply_entry_style(self._settings_outdir_entry)
        self._settings_outdir_entry.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        # Subtitle Style section
        self._lbl_subtitle_style = ctk.CTkLabel(
            sf, text="Subtitle Style",
            font=font("body"),
        )
        apply_secondary_label_style(self._lbl_subtitle_style)
        self._lbl_subtitle_style.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=(12, 8), pady=(16, 2)
        )

        # Font family
        self._lbl_font_family = ctk.CTkLabel(sf, text="Font family:")
        self._lbl_font_family.grid(row=5, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_font_var = ctk.StringVar(value="Arial")
        self._settings_font_menu = ctk.CTkOptionMenu(
            sf,
            values=["Arial", "Helvetica", "Verdana", "Trebuchet MS", "Tahoma"],
            variable=self._settings_font_var,
        )
        self._settings_font_menu.grid(row=5, column=1, sticky="ew", padx=(0, 12), pady=6)

        # Font size
        self._lbl_font_size = ctk.CTkLabel(sf, text="Font size:")
        self._lbl_font_size.grid(row=6, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_font_size_var = ctk.StringVar(value="20")
        self._settings_font_size_entry = ctk.CTkEntry(
            sf, textvariable=self._settings_font_size_var, width=ENTRY_WIDTH_SMALL,
        )
        apply_entry_style(self._settings_font_size_entry)
        self._settings_font_size_entry.grid(row=6, column=1, sticky="w", padx=(0, 12), pady=6)

        # Text color
        self._lbl_text_color = ctk.CTkLabel(sf, text="Text color:")
        self._lbl_text_color.grid(row=7, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_text_color_var = ctk.StringVar(value="#FFFFFF")
        self._btn_text_color_swatch = ctk.CTkButton(
            sf, text="", width=BTN_WIDTH_SWATCH, height=BTN_HEIGHT_MINI,
            fg_color=self._settings_text_color_var.get(),
            hover_color=self._settings_text_color_var.get(),
            command=self._on_pick_text_color,
        )
        self._btn_text_color_swatch.grid(row=7, column=1, sticky="w", padx=(0, 12), pady=6)

        # Outline color
        self._lbl_outline_color = ctk.CTkLabel(sf, text="Outline color:")
        self._lbl_outline_color.grid(row=8, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_outline_color_var = ctk.StringVar(value="#000000")
        self._btn_outline_color_swatch = ctk.CTkButton(
            sf, text="", width=BTN_WIDTH_SWATCH, height=BTN_HEIGHT_MINI,
            fg_color=self._settings_outline_color_var.get(),
            hover_color=self._settings_outline_color_var.get(),
            command=self._on_pick_outline_color,
        )
        self._btn_outline_color_swatch.grid(row=8, column=1, sticky="w", padx=(0, 12), pady=6)

        # Config file path (read-only info row)
        self._lbl_config_path_label = ctk.CTkLabel(
            sf, text=s("config_path_lbl"),
        )
        apply_secondary_label_style(self._lbl_config_path_label)
        self._lbl_config_path_label.grid(row=9, column=0, sticky="w", padx=(12, 8), pady=6)
        self._lbl_config_path_value = ctk.CTkLabel(
            sf, text="",
            wraplength=260,
            anchor="w",
            justify="left",
        )
        apply_secondary_label_style(self._lbl_config_path_value)
        self._lbl_config_path_value.grid(row=9, column=1, sticky="ew", padx=(0, 8), pady=6)

        def _open_config_folder() -> None:
            from gensubtitles.core.settings import settings_path  # noqa: PLC0415
            config_dir = settings_path().parent
            sys_name = platform.system()
            if sys_name == "Windows":
                subprocess.Popen(["explorer", str(config_dir)])  # noqa: S603,S607
            elif sys_name == "Darwin":
                subprocess.Popen(["open", str(config_dir)])      # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(config_dir)])  # noqa: S603,S607

        self._btn_open_config_folder = ctk.CTkButton(
            sf,
            text=s("open_config_folder_btn"),
            width=BTN_WIDTH_NARROW,
            command=_open_config_folder,
        )
        apply_secondary_btn_style(self._btn_open_config_folder)
        self._btn_open_config_folder.grid(row=9, column=2, padx=(0, 12), pady=6, sticky="e")

        # Save / Back buttons
        btn_frame = ctk.CTkFrame(sf, fg_color="transparent")
        btn_frame.grid(row=10, column=0, columnspan=3, pady=(16, 12), padx=12, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        self._btn_settings_save = ctk.CTkButton(
            btn_frame, text="Save", command=self._save_settings, height=BTN_HEIGHT_PRIMARY,
        )
        apply_accent_btn_style(self._btn_settings_save)
        self._btn_settings_save.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._btn_settings_back = ctk.CTkButton(
            btn_frame, text="Back", command=self._hide_settings, height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._btn_settings_back)
        self._btn_settings_back.grid(row=0, column=1, padx=(4, 0), sticky="ew")

    def _build_translate_tab(self) -> None:
        _tab_tl = self._tabview.tab("Translate Subtitles")
        tf = ctk.CTkFrame(_tab_tl, fg_color="transparent")
        tf.pack(fill="both", expand=True, padx=32, pady=(8, 32))
        tf.columnconfigure(1, weight=1)

        # Row 0 — Input subtitle file
        self._lbl_tl_input_sub = ctk.CTkLabel(tf, text="Input subtitle *:")
        self._lbl_tl_input_sub.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self._tl_input_var = ctk.StringVar()
        self._tl_entry_input = ctk.CTkEntry(tf, textvariable=self._tl_input_var)
        apply_entry_style(self._tl_entry_input)
        self._tl_entry_input.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        self._tl_btn_browse = ctk.CTkButton(
            tf, text="Browse…", width=BTN_WIDTH_BROWSE, command=self._tl_browse_input
        )
        self._tl_btn_browse.grid(row=0, column=2, padx=(8, 0), pady=(0, 8))

        # Row 1 — Output path
        self._lbl_tl_output_path = ctk.CTkLabel(tf, text="Output path *:")
        self._lbl_tl_output_path.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 24))
        self._tl_output_var = ctk.StringVar()
        self._tl_entry_output = ctk.CTkEntry(tf, textvariable=self._tl_output_var)
        apply_entry_style(self._tl_entry_output)
        self._tl_entry_output.grid(row=1, column=1, sticky="ew", pady=(0, 24))
        self._tl_btn_browse_out = ctk.CTkButton(
            tf, text="Save as…", width=BTN_WIDTH_BROWSE, command=self._tl_browse_output
        )
        self._tl_btn_browse_out.grid(row=1, column=2, padx=(8, 0), pady=(0, 24))

        # Row 2 — Source language
        self._lbl_tl_source_lang = ctk.CTkLabel(tf, text="Source language:")
        self._lbl_tl_source_lang.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        self._tl_source_var = ctk.StringVar(value="English")
        self._tl_option_source = ctk.CTkOptionMenu(
            tf, values=["English"], variable=self._tl_source_var
        )
        self._tl_option_source.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 8))

        # Row 3 — Target language
        self._lbl_tl_target_lang = ctk.CTkLabel(tf, text="Target language:")
        self._lbl_tl_target_lang.grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
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
            tf, text="Translate / Convert", command=self._on_translate,
            height=BTN_HEIGHT_PRIMARY,
            state="disabled",
        )
        apply_accent_btn_style(self._tl_btn_translate)
        self._tl_btn_translate.grid(row=5, column=0, columnspan=3, pady=(24, 8), sticky="ew")

        # Row 6 — Elapsed label
        self._tl_elapsed_label = ctk.CTkLabel(tf, text="00:00:00")
        self._tl_elapsed_label.grid(row=6, column=0, columnspan=3, pady=(8, 4))
        self._tl_elapsed_label.grid_remove()

        # Row 7 — Progress bar
        self._tl_progress_bar = ctk.CTkProgressBar(
            tf, mode="indeterminate", height=PROGRESS_BAR_HEIGHT,
        )
        apply_progress_bar_style(self._tl_progress_bar)
        self._tl_progress_bar.grid(row=7, column=0, columnspan=3, pady=(32, 32), sticky="ew")
        self._tl_progress_bar.grid_remove()

        # Row 8 — Stage label
        self._tl_stage_label = ctk.CTkLabel(tf, text="")
        self._tl_stage_label.grid(row=8, column=0, columnspan=3, pady=4)

    def _build_extract_tab(self) -> None:
        """Build Tab 3 — Extract Audio (D-01, D-03)."""
        tab = self._tabview.tab("Extract Audio")
        frame = ctk.CTkFrame(tab, fg_color=p("surface"), corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        frame.columnconfigure(0, weight=1)

        # Input video
        self._extract_lbl_input = ctk.CTkLabel(frame, text=s("extract_input_lbl"), anchor="w")
        self._extract_lbl_input.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        _in_row = ctk.CTkFrame(frame, fg_color="transparent")
        _in_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        _in_row.columnconfigure(0, weight=1)
        self._extract_entry_input = ctk.CTkEntry(_in_row, textvariable=self._extract_input_var)
        apply_entry_style(self._extract_entry_input)
        self._extract_entry_input.grid(row=0, column=0, sticky="ew")
        self._extract_btn_browse_input = ctk.CTkButton(
            _in_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._browse_file_to_var(
                self._extract_input_var,
                filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.webm"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._extract_btn_browse_input)
        self._extract_btn_browse_input.grid(row=0, column=1, padx=(8, 0))

        # Output audio
        self._extract_lbl_output = ctk.CTkLabel(frame, text=s("extract_output_lbl"), anchor="w")
        self._extract_lbl_output.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 2))
        _out_row = ctk.CTkFrame(frame, fg_color="transparent")
        _out_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        _out_row.columnconfigure(0, weight=1)
        self._extract_entry_output = ctk.CTkEntry(_out_row, textvariable=self._extract_output_var)
        apply_entry_style(self._extract_entry_output)
        self._extract_entry_output.grid(row=0, column=0, sticky="ew")
        self._extract_btn_browse_output = ctk.CTkButton(
            _out_row, text=s("save_as_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._save_file_to_var(
                self._extract_output_var,
                defaultextension=".wav",
                filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._extract_btn_browse_output)
        self._extract_btn_browse_output.grid(row=0, column=1, padx=(8, 0))

        # Action + clear buttons
        _btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        _btn_row.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 4))
        _btn_row.columnconfigure(0, weight=1)
        _btn_row.columnconfigure(1, weight=1)
        self._extract_btn_run = ctk.CTkButton(
            _btn_row, text=s("extract_run_btn"),
            command=self._on_tab3_extract,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._extract_btn_run)
        self._extract_btn_run.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _extract_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: self._clear_tab_vars(self._extract_input_var, self._extract_output_var),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(_extract_btn_clear)
        _extract_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Log textbox (D-03)
        self._extract_log_textbox = ctk.CTkTextbox(
            frame, state="disabled", height=140,
            fg_color=p("input_bg"), font=font("mono"), activate_scrollbars=True,
        )
        self._extract_log_textbox.grid(row=5, column=0, sticky="nsew", padx=12, pady=(4, 12))
        frame.rowconfigure(5, weight=1)

    def _build_transcribe_tab(self) -> None:
        """Build Tab 4 — Transcribe (D-01, D-03)."""
        tab = self._tabview.tab("Transcribe")
        frame = ctk.CTkFrame(tab, fg_color=p("surface"), corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        frame.columnconfigure(0, weight=1)

        # Input audio
        self._transcribe_lbl_input = ctk.CTkLabel(frame, text=s("transcribe_input_lbl"), anchor="w")
        self._transcribe_lbl_input.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        _in_row = ctk.CTkFrame(frame, fg_color="transparent")
        _in_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        _in_row.columnconfigure(0, weight=1)
        self._transcribe_entry_input = ctk.CTkEntry(_in_row, textvariable=self._transcribe_input_var)
        apply_entry_style(self._transcribe_entry_input)
        self._transcribe_entry_input.grid(row=0, column=0, sticky="ew")
        self._transcribe_btn_browse = ctk.CTkButton(
            _in_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._browse_file_to_var(
                self._transcribe_input_var,
                filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._transcribe_btn_browse)
        self._transcribe_btn_browse.grid(row=0, column=1, padx=(8, 0))

        # Source language dropdown (reuses existing _source_lang_var)
        self._transcribe_lbl_source = ctk.CTkLabel(frame, text=s("source_lang_lbl"), anchor="w")
        self._transcribe_lbl_source.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 2))
        self._transcribe_option_source = ctk.CTkOptionMenu(
            frame, values=["Auto-detect"], variable=self._source_lang_var,
        )
        self._transcribe_option_source.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Action + clear buttons
        _btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        _btn_row.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 4))
        _btn_row.columnconfigure(0, weight=1)
        _btn_row.columnconfigure(1, weight=1)
        self._transcribe_btn_run = ctk.CTkButton(
            _btn_row, text=s("transcribe_run_btn"),
            command=self._on_tab4_transcribe,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._transcribe_btn_run)
        self._transcribe_btn_run.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _transcribe_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: self._clear_tab_vars(self._transcribe_input_var),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(_transcribe_btn_clear)
        _transcribe_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Log textbox
        self._transcribe_log_textbox = ctk.CTkTextbox(
            frame, state="disabled", height=140,
            fg_color=p("input_bg"), font=font("mono"), activate_scrollbars=True,
        )
        self._transcribe_log_textbox.grid(row=5, column=0, sticky="nsew", padx=12, pady=(4, 12))
        frame.rowconfigure(5, weight=1)

    def _build_translate_step_tab(self) -> None:
        """Build Tab 5 — Translate step (D-01, D-03)."""
        tab = self._tabview.tab("Translate")
        frame = ctk.CTkFrame(tab, fg_color=p("surface"), corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        frame.columnconfigure(0, weight=1)

        # Input transcription
        self._translate_step_lbl_input = ctk.CTkLabel(frame, text=s("translate_step_input_lbl"), anchor="w")
        self._translate_step_lbl_input.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        _in_row = ctk.CTkFrame(frame, fg_color="transparent")
        _in_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        _in_row.columnconfigure(0, weight=1)
        self._translate_step_entry_input = ctk.CTkEntry(_in_row, textvariable=self._translate_step_input_var)
        apply_entry_style(self._translate_step_entry_input)
        self._translate_step_entry_input.grid(row=0, column=0, sticky="ew")
        self._translate_step_btn_browse = ctk.CTkButton(
            _in_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._browse_file_to_var(
                self._translate_step_input_var,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._translate_step_btn_browse)
        self._translate_step_btn_browse.grid(row=0, column=1, padx=(8, 0))

        # Source language
        self._translate_step_lbl_source = ctk.CTkLabel(frame, text=s("source_lang_lbl"), anchor="w")
        self._translate_step_lbl_source.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 2))
        self._translate_step_option_source = ctk.CTkOptionMenu(
            frame, values=["Auto-detect"], variable=self._translate_step_source_var,
        )
        self._translate_step_option_source.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Target language
        self._translate_step_lbl_target = ctk.CTkLabel(frame, text=s("target_lang_lbl"), anchor="w")
        self._translate_step_lbl_target.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 2))
        self._translate_step_option_target = ctk.CTkOptionMenu(
            frame, values=["No target"], variable=self._translate_step_target_var,
            command=self._on_translate_step_target_change,
        )
        self._translate_step_option_target.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Engine dropdown (hidden initially)
        _engine_values = ["Argos"]
        if self._current_settings and self._current_settings.deepl_api_key:
            _engine_values.append("DeepL")
        if self._current_settings and self._current_settings.libretranslate_url:
            _engine_values.append("LibreTranslate")
        self._translate_step_lbl_engine = ctk.CTkLabel(frame, text=s("engine_lbl"), anchor="w")
        self._translate_step_lbl_engine.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 2))
        self._translate_step_option_engine = ctk.CTkOptionMenu(
            frame, values=_engine_values, variable=self._translate_step_engine_var,
        )
        self._translate_step_option_engine.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._translate_step_lbl_engine.grid_remove()
        self._translate_step_option_engine.grid_remove()

        # Action + clear buttons
        _btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        _btn_row.grid(row=8, column=0, sticky="ew", padx=12, pady=(4, 4))
        _btn_row.columnconfigure(0, weight=1)
        _btn_row.columnconfigure(1, weight=1)
        self._translate_step_btn_run = ctk.CTkButton(
            _btn_row, text=s("translate_step_run_btn"),
            command=self._on_tab5_translate,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._translate_step_btn_run)
        self._translate_step_btn_run.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _translate_step_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: self._clear_tab_vars(self._translate_step_input_var),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(_translate_step_btn_clear)
        _translate_step_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Log textbox
        self._translate_step_log_textbox = ctk.CTkTextbox(
            frame, state="disabled", height=140,
            fg_color=p("input_bg"), font=font("mono"), activate_scrollbars=True,
        )
        self._translate_step_log_textbox.grid(row=9, column=0, sticky="nsew", padx=12, pady=(4, 12))
        frame.rowconfigure(9, weight=1)

    def _build_write_tab(self) -> None:
        """Build Tab 6 — Write Subtitle (D-01, D-03)."""
        tab = self._tabview.tab("Write Subtitle")
        frame = ctk.CTkFrame(tab, fg_color=p("surface"), corner_radius=12)
        frame.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        frame.columnconfigure(0, weight=1)

        # Input transcription/translation
        self._write_lbl_input = ctk.CTkLabel(frame, text=s("write_input_lbl"), anchor="w")
        self._write_lbl_input.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        _in_row = ctk.CTkFrame(frame, fg_color="transparent")
        _in_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        _in_row.columnconfigure(0, weight=1)
        self._write_entry_input = ctk.CTkEntry(_in_row, textvariable=self._write_input_var)
        apply_entry_style(self._write_entry_input)
        self._write_entry_input.grid(row=0, column=0, sticky="ew")
        self._write_btn_browse_input = ctk.CTkButton(
            _in_row, text=s("browse_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._browse_file_to_var(
                self._write_input_var,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._write_btn_browse_input)
        self._write_btn_browse_input.grid(row=0, column=1, padx=(8, 0))

        # Output subtitle path
        self._write_lbl_output = ctk.CTkLabel(frame, text=s("write_output_lbl"), anchor="w")
        self._write_lbl_output.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 2))
        _out_row = ctk.CTkFrame(frame, fg_color="transparent")
        _out_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        _out_row.columnconfigure(0, weight=1)
        self._write_entry_output = ctk.CTkEntry(_out_row, textvariable=self._write_output_var)
        apply_entry_style(self._write_entry_output)
        self._write_entry_output.grid(row=0, column=0, sticky="ew")
        self._write_btn_browse_output = ctk.CTkButton(
            _out_row, text=s("save_as_btn"), width=BTN_WIDTH_BROWSE,
            command=lambda: self._save_file_to_var(
                self._write_output_var,
                defaultextension=".srt",
                filetypes=[("SRT", "*.srt"), ("SSA", "*.ssa"), ("All files", "*.*")],
            ),
        )
        apply_secondary_btn_style(self._write_btn_browse_output)
        self._write_btn_browse_output.grid(row=0, column=1, padx=(8, 0))

        # Output format dropdown
        self._write_lbl_format = ctk.CTkLabel(frame, text=s("output_format_lbl"), anchor="w")
        self._write_lbl_format.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 2))
        self._write_option_format = ctk.CTkOptionMenu(
            frame, values=["SRT", "SSA"], variable=self._write_format_var,
        )
        self._write_option_format.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Action + clear buttons
        _btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        _btn_row.grid(row=6, column=0, sticky="ew", padx=12, pady=(4, 4))
        _btn_row.columnconfigure(0, weight=1)
        _btn_row.columnconfigure(1, weight=1)
        self._write_btn_run = ctk.CTkButton(
            _btn_row, text=s("write_run_btn"),
            command=self._on_tab6_write,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._write_btn_run)
        self._write_btn_run.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _write_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: self._clear_tab_vars(self._write_input_var, self._write_output_var),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(_write_btn_clear)
        _write_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Log textbox
        self._write_log_textbox = ctk.CTkTextbox(
            frame, state="disabled", height=140,
            fg_color=p("input_bg"), font=font("mono"), activate_scrollbars=True,
        )
        self._write_log_textbox.grid(row=7, column=0, sticky="nsew", padx=12, pady=(4, 12))
        frame.rowconfigure(7, weight=1)

    def _tl_browse_input(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        path = filedialog.askopenfilename(
            filetypes=[("Subtitle files", "*.srt *.ssa *.ass"), ("All files", "*.*")]
        )
        if path:
            self._tl_input_var.set(path)
            if not self._tl_output_var.get():
                fpath = Path(path)
                self._tl_output_var.set(str(fpath.with_stem(fpath.stem + "_translated")))

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
        no_target = selection in ("No target", "")
        # Show/hide engine row based on whether a target is selected
        if no_target:
            self._lbl_engine.grid_remove()
            self._option_engine.grid_remove()
        else:
            self._lbl_engine.grid()
            self._option_engine.grid()
        # Auto-save target_lang to settings (BUG-3, D-09)
        try:
            from gensubtitles.core.settings import save_settings  # noqa: PLC0415
            if self._current_settings is not None:
                tgt_code = _label_to_code(selection) if not no_target else ""
                import dataclasses  # noqa: PLC0415
                self._current_settings = dataclasses.replace(
                    self._current_settings, target_lang=tgt_code
                )
                save_settings(self._current_settings)
        except Exception:  # noqa: BLE001
            pass
        if no_target:
            return
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
                self.after(0, lambda m=msg: (self._stage_label.configure(text=m), self._log(m)))
                return

            if all(_is_installed(f, t) for f, t in route):
                return  # already installed, nothing to do

            via = " → ".join(f"{f}→{t}" for f, t in route)
            self.after(0, lambda v=via: (self._stage_label.configure(
                text=f"⏬ Downloading {v} model…"
            ), self._log(f"⏬ Downloading {v} model…")))
            try:
                ensure_route_installed(src_code, tgt_code)
                self.after(0, lambda v=via: (self._stage_label.configure(
                    text=f"✓ {v} model ready"
                ), self._log(f"✓ {v} model ready")))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Background prefetch failed for %s→%s: %s", src_code, tgt_code, exc)
                msg = f"⚠ Could not download model for {src_code}→{tgt_code}: {exc}"
                self.after(0, lambda m=msg: (self._stage_label.configure(text=m), self._log(m)))
            finally:
                with self._prefetch_lock:
                    self._prefetch_in_progress.discard(pair_key)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_output_format_change(self, selection: str) -> None:
        """Update output path extension when format changes."""
        current = self._output_var.get()
        if not current:
            return
        fpath = Path(current)
        new_ext = ".ssa" if selection == "SSA" else ".srt"
        self._output_var.set(str(fpath.with_suffix(new_ext)))

    def _populate_language_dropdowns(self) -> None:
        """Runs in background thread. Queries GET /languages then updates dropdowns on main thread."""
        import requests as req  # noqa: PLC0415

        pairs: list[dict] = []
        try:
            resp = req.get(f"{server.BASE_URL}/languages", timeout=30)
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

    def _on_cancel(self) -> None:
        """Send DELETE request to API in background; disable cancel button only if a job is active."""
        job_id = self._current_job_id
        if not job_id:
            return
        self._btn_cancel.configure(state="disabled")

        def _do_cancel() -> None:
            try:
                import requests as req  # noqa: PLC0415
                req.delete(f"{server.BASE_URL}/subtitles/{job_id}", timeout=5)
            except Exception:  # noqa: BLE001
                pass  # server might be busy; cancellation happens server-side regardless

        threading.Thread(target=_do_cancel, daemon=True).start()

    def _hide_generate_progress(self) -> None:
        """Reset and hide the generate-tab progress bar after state feedback delay."""
        if not self._job_active:
            self._progress_bar.configure(progress_color=p("progress_idle"))
            self._progress_bar.grid_remove()

    def _hide_translate_progress(self) -> None:
        """Reset and hide the translate-tab progress bar after state feedback delay."""
        self._tl_progress_bar.configure(progress_color=p("progress_idle"))
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
            self._log(label)
        # Switch progress bar to determinate mode during translation
        if stage == "translating" and total > 0:
            pct = current / total
            if self._progress_bar.cget("mode") != "determinate":
                self._progress_bar.stop()
                self._progress_bar.configure(mode="determinate", progress_color=p("progress_proc"))
            self._progress_bar.set(pct)
        elif self._progress_bar.cget("mode") != "indeterminate":
            self._progress_bar.configure(mode="indeterminate", progress_color=p("progress_proc"))
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
        # Hide "Open Folder" button from a previous run (BUG-1, D-01)
        if hasattr(self, "_btn_open_folder"):
            self._btn_open_folder.grid_remove()
        input_path = self._input_var.get().strip()
        output_path = self._output_var.get().strip()

        if not input_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror(s("msg_missing_input_title"), s("msg_missing_input_video"))
            return
        if not output_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror(s("msg_missing_output_title"), s("msg_missing_output_subtitle"))
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
        self._progress_bar.configure(mode="indeterminate", progress_color=p("progress_proc"))
        self._progress_bar.start()
        self._job_active = True
        self._btn_cancel.grid()
        self._btn_cancel.configure(state="normal")

        # Reset and start elapsed timer
        if self._elapsed_timer is not None:
            self.after_cancel(self._elapsed_timer)
            self._elapsed_timer = None
        self._elapsed_label.configure(text="00:00:00")
        self._elapsed_start = time.monotonic()
        self._elapsed_label.grid()
        self._tick_elapsed()

        thread = threading.Thread(
            target=self._run_sse_flow,
            args=(input_path, output_path, src_lang, tgt_lang, engine_code),
            daemon=True,
        )
        thread.start()

    def _run_sse_flow(
        self,
        input_path: str,
        output_path: str,
        src_lang: str | None,
        tgt_lang: str | None,
        engine: str = "argos",
    ) -> None:
        """Background thread: POST /subtitles/async → SSE stream → GET /result → save."""
        import json as _json  # noqa: PLC0415
        import requests as req  # noqa: PLC0415

        try:
            params: dict[str, str] = {}
            if src_lang:
                params["source_lang"] = src_lang
            if tgt_lang:
                params["target_lang"] = tgt_lang
            params["engine"] = engine

            # Step 1: POST /subtitles/async — returns job_id immediately
            with open(input_path, "rb") as fh:
                video_name = Path(input_path).name
                resp = req.post(
                    f"{server.BASE_URL}/subtitles/async",
                    files={"file": (video_name, fh, "application/octet-stream")},
                    params=params,
                    timeout=30,  # short — should respond immediately
                )
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:  # noqa: BLE001
                    detail = resp.text
                if isinstance(detail, list):
                    detail = "; ".join(str(e) for e in detail)
                if not self._closing:
                    self.after(0, self._finish_generate, str(detail), None)
                return

            job_id = resp.json()["job_id"]
            self._current_job_id = job_id

            # Step 2: GET /subtitles/{job_id}/stream — SSE stream of progress events
            with req.get(
                f"{server.BASE_URL}/subtitles/{job_id}/stream",
                stream=True,
                timeout=(5, None),  # fail fast if server unreachable; keep stream reads unbounded
            ) as stream_resp:
                for line in stream_resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    try:
                        data = _json.loads(line[5:].strip())
                    except Exception:  # noqa: BLE001
                        continue
                    stage = data.get("stage", "")
                    if not self._closing:
                        self.after(0, lambda d=data: self._apply_progress(d))
                    if stage == "done":
                        break
                    if stage == "error":
                        friendly = data.get("label", "Generation failed")
                        if not self._closing:
                            self.after(0, self._finish_generate, friendly, None)
                        return
                    if stage == "cancelled":
                        if not self._closing:
                            self.after(0, self._finish_generate, None, None, True)
                        return

            # Step 3: GET /subtitles/{job_id}/result — fetch SRT bytes
            result_resp = req.get(
                f"{server.BASE_URL}/subtitles/{job_id}/result",
                timeout=60,
            )
            if result_resp.status_code != 200:
                if not self._closing:
                    self.after(0, self._finish_generate, "Failed to retrieve subtitle result", None)
                return

            # Save to disk
            output_file = Path(output_path)
            final_path = output_path
            if self._output_format_var.get() == "SSA":
                from gensubtitles.core.srt_writer import convert_srt_to_ssa  # noqa: PLC0415
                temp_srt = output_file.with_suffix(".srt")
                ssa_out = output_file.with_suffix(".ssa")
                temp_srt.write_bytes(result_resp.content)
                style: dict | None = None
                if self._current_settings:
                    style = {
                        "fontname": self._current_settings.subtitle_font_family,
                        "fontsize": self._current_settings.subtitle_font_size,
                        "primarycolor": self._current_settings.subtitle_text_color,
                        "outlinecolor": self._current_settings.subtitle_outline_color,
                    }
                convert_srt_to_ssa(temp_srt, ssa_out, style=style)
                temp_srt.unlink(missing_ok=True)
                final_path = str(ssa_out)
            else:
                output_file.write_bytes(result_resp.content)
            if not self._closing:
                self.after(0, self._finish_generate, None, final_path)

        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, (req.exceptions.ConnectionError, req.exceptions.Timeout)):
                msg = "Cannot connect to the API server. Make sure the server is running."
            elif isinstance(exc, req.exceptions.RequestException):
                msg = f"Network error: {type(exc).__name__}"
            else:
                msg = "An unexpected error occurred during subtitle generation."
            if not self._closing:
                self.after(0, self._finish_generate, msg, None)

    def _finish_generate(self, error: str | None, output_path: str | None, cancelled: bool = False) -> None:
        # Stop progress first to prevent stale UI updates
        self._job_active = False
        self._current_job_id = None
        if not self._closing:
            self._btn_cancel.grid_remove()
            self._btn_cancel.configure(state="normal")

        if self._stage_timer is not None:
            self.after_cancel(self._stage_timer)
            self._stage_timer = None

        # Show final elapsed time before cancelling the timer
        elapsed = int(time.monotonic() - self._elapsed_start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        secs = elapsed % 60
        self._elapsed_label.configure(text=f"{h:02d}:{m:02d}:{secs:02d}")

        if self._elapsed_timer is not None:
            self.after_cancel(self._elapsed_timer)
            self._elapsed_timer = None

        if error:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate", progress_color=p("progress_err"))
            self._progress_bar.set(1.0)
            self._progress_bar.grid()
            self.after(2000, self._hide_generate_progress)
        elif cancelled:
            self._progress_bar.stop()
            self._progress_bar.grid_remove()
        else:
            self._progress_bar.stop()
            self._progress_bar.configure(mode="determinate", progress_color=p("progress_done"))
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
            self._log("")
            messagebox.showerror(s("msg_generation_failed_title"), error)
        elif cancelled:
            self._stage_label.configure(text="Generation cancelled.")
            self._log("Generation cancelled.")
        else:
            self._stage_label.configure(text=s("status_done"))
            self._log(s("status_done"))
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
                self._config_frame, text=s("open_folder_btn"), command=_open_folder
            )
            self._btn_open_folder.grid(row=16, column=0, padx=12, pady=(4, 0), sticky="ew")
        else:
            self._btn_open_folder.configure(text=s("open_folder_btn"), command=_open_folder)
            self._btn_open_folder.grid(row=16, column=0, padx=12, pady=(4, 0), sticky="ew")

    # ------------------------------------------------------------------
    # Theme / colour palette
    # ------------------------------------------------------------------

    def _apply_theme(self) -> None:
        """Re-apply all hard-coded colours after an appearance-mode change.

        CustomTkinter handles its own widget colours automatically when
        set_appearance_mode() is called, but colours passed as explicit hex
        strings in constructors are static and must be refreshed here.
        """
        apply_window_bg(self)

        # Entry fields
        for entry in (
            self._entry_input, self._entry_output,
            self._tl_entry_input, self._tl_entry_output,
        ):
            apply_entry_style(entry)

        # Accent (primary) buttons
        for btn in (self._btn_generate, self._tl_btn_translate):
            apply_accent_btn_style(btn)

        # Secondary buttons
        apply_secondary_btn_style(self._btn_clear)

        # Log textboxes — apply fg_color for theme switch
        for _tb_attr in ("_log_textbox", "_extract_log_textbox", "_transcribe_log_textbox",
                         "_translate_step_log_textbox", "_write_log_textbox"):
            _tb = getattr(self, _tb_attr, None)
            if _tb is not None:
                _tb.configure(fg_color=p("input_bg"))

        # Cancel button
        apply_cancel_btn_style(self._btn_cancel)

        # Stage / status labels
        apply_stage_label_style(self._stage_label)
        apply_stage_label_style(self._tl_stage_label)

        # Progress bars — reset to idle colour only (active colour is set dynamically)
        for pb in (self._progress_bar, self._tl_progress_bar):
            if pb.cget("mode") == "indeterminate" and not self._job_active:
                apply_progress_bar_style(pb)

        # Settings panel widgets
        if hasattr(self, "_btn_settings_save"):
            apply_accent_btn_style(self._btn_settings_save)
        if hasattr(self, "_btn_settings_back"):
            apply_secondary_btn_style(self._btn_settings_back)
        if hasattr(self, "_settings_outdir_entry"):
            apply_entry_style(self._settings_outdir_entry)
        if hasattr(self, "_settings_font_size_entry"):
            apply_entry_style(self._settings_font_size_entry)
        if hasattr(self, "_lbl_subtitle_style"):
            apply_secondary_label_style(self._lbl_subtitle_style)
        if hasattr(self, "_settings_header_lbl"):
            apply_settings_header_style(self._settings_header_lbl)
        if hasattr(self, "_btn_open_config_folder"):
            apply_secondary_btn_style(self._btn_open_config_folder)
        if hasattr(self, "_lbl_config_path_label"):
            apply_secondary_label_style(self._lbl_config_path_label)
        if hasattr(self, "_lbl_config_path_value"):
            apply_secondary_label_style(self._lbl_config_path_value)

        # tkinter Menu bar (not a CTK widget — must be reconfigured manually)
        if hasattr(self, "_menubar") and hasattr(self, "_menus"):
            _menu_clr = {
                "bg": p("menu_bg"),
                "fg": p("menu_fg"),
                "activebackground": p("menu_active_bg"),
                "activeforeground": p("menu_fg"),
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

    def _apply_startup_target_lang(self) -> None:
        """Initialize target language dropdown from saved settings (BUG-3).

        Must be called after _build_ui so _option_target_lang and _target_lang_var exist.
        """
        if not self._current_settings:
            return
        saved_code = self._current_settings.target_lang
        if not saved_code:
            return
        label = _CODE_TO_LABEL.get(saved_code)
        if label is None:
            return
        # Set the StringVar — triggers no command callback
        self._target_lang_var.set(label)
        # Manually trigger show/hide of engine row (no prefetch needed at startup)
        self._lbl_engine.grid()
        self._option_engine.grid()

    def _on_pick_text_color(self) -> None:
        """Open OS color picker for subtitle text color."""
        import tkinter.colorchooser  # noqa: PLC0415
        current = self._settings_text_color_var.get() or "#FFFFFF"
        result = tkinter.colorchooser.askcolor(color=current, title="Choose text color")
        if result[1] is not None:
            hex_color = result[1]
            self._settings_text_color_var.set(hex_color)
            self._btn_text_color_swatch.configure(
                fg_color=hex_color, hover_color=hex_color
            )

    def _on_pick_outline_color(self) -> None:
        """Open OS color picker for subtitle outline color."""
        import tkinter.colorchooser  # noqa: PLC0415
        current = self._settings_outline_color_var.get() or "#000000"
        result = tkinter.colorchooser.askcolor(color=current, title="Choose outline color")
        if result[1] is not None:
            hex_color = result[1]
            self._settings_outline_color_var.set(hex_color)
            self._btn_outline_color_swatch.configure(
                fg_color=hex_color, hover_color=hex_color
            )

    def _show_settings(self) -> None:
        """Show settings panel, hide main tabview. Populate from current settings."""
        if self._current_settings:
            self._settings_appearance_var.set(self._current_settings.appearance_mode)
            lang_label = "Spanish" if self._current_settings.ui_language == "es" else "English"
            self._settings_lang_var.set(lang_label)
            self._settings_outdir_var.set(self._current_settings.default_output_dir)
            self._settings_font_var.set(
                self._current_settings.subtitle_font_family or "Arial"
            )
            self._settings_font_size_var.set(
                str(self._current_settings.subtitle_font_size or 20)
            )
            text_col = self._current_settings.subtitle_text_color or "#FFFFFF"
            self._settings_text_color_var.set(text_col)
            self._btn_text_color_swatch.configure(
                fg_color=text_col, hover_color=text_col
            )
            outline_col = self._current_settings.subtitle_outline_color or "#000000"
            self._settings_outline_color_var.set(outline_col)
            self._btn_outline_color_swatch.configure(
                fg_color=outline_col, hover_color=outline_col
            )
        self._tabview.pack_forget()
        from gensubtitles.core.settings import settings_path  # noqa: PLC0415
        self._lbl_config_path_value.configure(text=str(settings_path()))
        self._settings_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def _hide_settings(self) -> None:
        """Hide settings panel, restore tabview."""
        self._settings_frame.pack_forget()
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

    def _save_settings(self) -> None:
        """Persist settings and apply immediately."""
        from tkinter import messagebox  # noqa: PLC0415

        # Validate font size before attempting to build AppSettings so we can
        # show a targeted error without closing the settings panel.
        font_size_raw = self._settings_font_size_var.get().strip() or "20"
        if not font_size_raw.isdigit() or int(font_size_raw) <= 0:
            messagebox.showerror(
                s("msg_settings_error_title"),
                "Font size must be a positive integer (e.g. 20).",
            )
            return

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
                target_lang=(
                    self._current_settings.target_lang
                    if self._current_settings
                    else ""
                ),
                deepl_api_key=(
                    self._current_settings.deepl_api_key
                    if self._current_settings
                    else ""
                ),
                libretranslate_url=(
                    self._current_settings.libretranslate_url
                    if self._current_settings
                    else ""
                ),
                libretranslate_api_key=(
                    self._current_settings.libretranslate_api_key
                    if self._current_settings
                    else ""
                ),
                subtitle_font_family=self._settings_font_var.get(),
                subtitle_font_size=int(font_size_raw),
                subtitle_text_color=self._settings_text_color_var.get() or "#FFFFFF",
                subtitle_outline_color=self._settings_outline_color_var.get() or "#000000",
            )
            save_settings(new_settings)
            self._current_settings = new_settings
            # Refresh engine dropdown to reflect any credential changes (BUG-2, D-04)
            _engine_values = ["Argos"]
            if new_settings.deepl_api_key:
                _engine_values.append("DeepL")
            if new_settings.libretranslate_url:
                _engine_values.append("LibreTranslate")
            self._option_engine.configure(values=_engine_values)
            if self._engine_var.get() not in _engine_values:
                self._engine_var.set("Argos")  # D-05: reset if selection was removed
            ctk.set_appearance_mode(new_settings.appearance_mode)
            self._apply_theme()
            set_language(new_settings.ui_language)
            self._apply_ui_language()
            # If the user just switched to "System", sync immediately and
            # ensure the live listener is running.
            if new_settings.appearance_mode == "System":
                self.sync_with_os()
                self._start_os_theme_listener()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(s("msg_settings_error_title"), s("msg_settings_error_body").format(error=exc))
            return
        self._hide_settings()


    def _relabel_tabview_headers(self) -> None:
        """Update existing CTkTabview header labels for the active UI language.

        CustomTkinter does not expose a public tab rename API, so this method
        performs a guarded in-place relabel of known tab names by updating the
        internal tab-name structures and segmented-button values.
        """
        tab_name_map = {
            "Generate Subtitles":    s("generate_tab"),
            "Translate Subtitles":   s("translate_tab"),
            # Phase 999.30 — new tabs
            "Extract Audio":         s("extract_tab"),
            "Transcribe":            s("transcribe_tab"),
            "Translate":             s("translate_step_tab"),
            "Write Subtitle":        s("write_tab"),
            # Localized sources — EN
            s_lang("generate_tab",       "en"): s("generate_tab"),
            s_lang("translate_tab",      "en"): s("translate_tab"),
            s_lang("extract_tab",        "en"): s("extract_tab"),
            s_lang("transcribe_tab",     "en"): s("transcribe_tab"),
            s_lang("translate_step_tab", "en"): s("translate_step_tab"),
            s_lang("write_tab",          "en"): s("write_tab"),
            # Localized sources — ES
            s_lang("generate_tab",       "es"): s("generate_tab"),
            s_lang("translate_tab",      "es"): s("translate_tab"),
            s_lang("extract_tab",        "es"): s("extract_tab"),
            s_lang("transcribe_tab",     "es"): s("transcribe_tab"),
            s_lang("translate_step_tab", "es"): s("translate_step_tab"),
            s_lang("write_tab",          "es"): s("write_tab"),
        }

        for widget in self.__dict__.values():
            if not isinstance(widget, ctk.CTkTabview):
                continue

            try:
                name_list = getattr(widget, "_name_list", None)
                tab_dict = getattr(widget, "_tab_dict", None)
                segmented_button = getattr(widget, "_segmented_button", None)
                current_name = widget.get()

                if not isinstance(name_list, list) or not isinstance(tab_dict, dict):
                    continue

                renamed = False
                new_name_list = []
                new_tab_dict = {}

                for old_name in name_list:
                    new_name = tab_name_map.get(old_name, old_name)
                    if new_name != old_name:
                        renamed = True
                    new_name_list.append(new_name)
                    new_tab_dict[new_name] = tab_dict.get(old_name)

                if not renamed:
                    continue

                # Deliberately updating private CTk internals — no public rename API exists
                widget._name_list = new_name_list
                widget._tab_dict = new_tab_dict

                if segmented_button is not None and hasattr(segmented_button, "configure"):
                    segmented_button.configure(values=new_name_list)

                if current_name in tab_name_map:
                    widget.set(tab_name_map[current_name])
                else:
                    widget.set(current_name)
            except Exception as exc:  # pragma: no cover - best effort for CTk internals
                logger.debug("Unable to relabel CTkTabview headers: %s", exc)

    def _apply_ui_language(self) -> None:
        """Re-label all static widget text using the current ui_language setting.

        Called on startup (after _build_ui) and immediately after _save_settings.
        """
        lang = getattr(self._current_settings, "ui_language", "en") if self._current_settings else "en"
        set_language(lang)
        # Tab headers
        self._relabel_tabview_headers()

        # Generate Subtitles tab
        self._lbl_input_video.configure(text=s("input_video_lbl"))
        self._lbl_output_file.configure(text=s("output_file_lbl"))
        self._lbl_source_lang.configure(text=s("source_lang_lbl"))
        self._lbl_target_lang.configure(text=s("target_lang_lbl"))
        self._lbl_engine.configure(text=s("engine_lbl"))
        self._lbl_output_format.configure(text=s("output_format_lbl"))
        self._btn_generate.configure(text=s("generate_btn"))
        self._btn_clear.configure(text=s("generate_clear_btn"))
        self._lbl_config_title.configure(text=s("panel_config_title"))
        self._btn_browse_input.configure(text=s("browse_btn"))
        self._btn_browse_output.configure(text=s("save_as_btn"))
        # Stage label — update if currently showing a known status string
        _known_statuses = {s_lang(key, lang_code) for lang_code in LANGUAGES for key in ("starting_server", "status_done")}
        current_stage_text = self._stage_label.cget("text")
        if current_stage_text in _known_statuses:
            for key in ("starting_server", "status_done"):
                if current_stage_text in {s_lang(key, lang_code) for lang_code in LANGUAGES}:
                    self._stage_label.configure(text=s(key))
                    self._log(s(key))
                    break

        # Translate Subtitles tab
        self._lbl_tl_input_sub.configure(text=s("input_sub_lbl"))
        self._lbl_tl_output_path.configure(text=s("output_path_lbl"))
        self._lbl_tl_source_lang.configure(text=s("source_lang_lbl"))
        self._lbl_tl_target_lang.configure(text=s("target_lang_lbl"))
        self._tl_btn_browse.configure(text=s("browse_btn"))
        self._tl_btn_browse_out.configure(text=s("save_as_btn"))
        self._tl_btn_translate.configure(text=s("translate_btn"))
        self._tl_chk_convert.configure(text=s("convert_only_chk"))

        # Settings panel
        self._settings_header_lbl.configure(text=s("settings_header"))
        self._lbl_appearance_mode.configure(text=s("appearance_lbl"))
        self._lbl_ui_language_setting.configure(text=s("ui_lang_lbl"))
        self._lbl_default_outdir.configure(text=s("default_outdir_lbl"))
        self._btn_settings_save.configure(text=s("save_btn"))
        self._btn_settings_back.configure(text=s("back_btn"))
        self._lbl_subtitle_style.configure(text=s("subtitle_style_lbl"))
        self._lbl_font_family.configure(text=s("font_family_lbl"))
        self._lbl_font_size.configure(text=s("font_size_lbl"))
        self._lbl_text_color.configure(text=s("text_color_lbl"))
        self._lbl_outline_color.configure(text=s("outline_color_lbl"))
        self._lbl_config_path_label.configure(text=s("config_path_lbl"))
        self._btn_open_config_folder.configure(text=s("open_config_folder_btn"))

        # Open Folder button (created lazily in _show_success — may not exist yet)
        if hasattr(self, "_btn_open_folder"):
            self._btn_open_folder.configure(text=s("open_folder_btn"))

        # Menu bar — resolve cascade indices dynamically
        menubar_end = self._menubar.index("end")
        menubar_cascades = []
        if menubar_end is not None:
            for idx in range(menubar_end + 1):
                if self._menubar.type(idx) == "cascade":
                    menubar_cascades.append(idx)

        if len(menubar_cascades) >= 1:
            self._menubar.entryconfigure(menubar_cascades[0], label=s("menu_settings"))
        if len(menubar_cascades) >= 2:
            self._menubar.entryconfigure(menubar_cascades[1], label=s("menu_help"))
        self._settings_menu.entryconfigure(0, label=s("menu_preferences"))
        self._help_menu.entryconfigure(0, label=s("menu_tutorial"))
        self._help_menu.entryconfigure(1, label=s("menu_languages"))
        self._help_menu.entryconfigure(3, label=s("menu_about"))

        # Step tabs (Phase 999.30)
        if hasattr(self, "_extract_lbl_input"):
            self._extract_lbl_input.configure(text=s("extract_input_lbl"))
            self._extract_lbl_output.configure(text=s("extract_output_lbl"))
            self._extract_btn_run.configure(text=s("extract_run_btn"))
            self._extract_btn_browse_input.configure(text=s("browse_btn"))
            self._extract_btn_browse_output.configure(text=s("save_as_btn"))
        if hasattr(self, "_transcribe_lbl_input"):
            self._transcribe_lbl_input.configure(text=s("transcribe_input_lbl"))
            self._transcribe_lbl_source.configure(text=s("source_lang_lbl"))
            self._transcribe_btn_run.configure(text=s("transcribe_run_btn"))
            self._transcribe_btn_browse.configure(text=s("browse_btn"))
        if hasattr(self, "_translate_step_lbl_input"):
            self._translate_step_lbl_input.configure(text=s("translate_step_input_lbl"))
            self._translate_step_lbl_source.configure(text=s("source_lang_lbl"))
            self._translate_step_lbl_target.configure(text=s("target_lang_lbl"))
            self._translate_step_lbl_engine.configure(text=s("engine_lbl"))
            self._translate_step_btn_run.configure(text=s("translate_step_run_btn"))
            self._translate_step_btn_browse.configure(text=s("browse_btn"))
        if hasattr(self, "_write_lbl_input"):
            self._write_lbl_input.configure(text=s("write_input_lbl"))
            self._write_lbl_output.configure(text=s("write_output_lbl"))
            self._write_lbl_format.configure(text=s("output_format_lbl"))
            self._write_btn_run.configure(text=s("write_run_btn"))
            self._write_btn_browse_input.configure(text=s("browse_btn"))
            self._write_btn_browse_output.configure(text=s("save_as_btn"))

    # ------------------------------------------------------------------
    # Help stubs (implemented in Plan 06)
    # ------------------------------------------------------------------

    def _show_tutorial(self) -> None:
        """Open a scrollable tutorial CTkToplevel window."""
        win = ctk.CTkToplevel(self)
        win.title(s("dlg_tutorial_title"))
        win.minsize(500, 500)
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        label = ctk.CTkLabel(
            scroll,
            text=s("dlg_tutorial_text"),
            justify="left",
            anchor="nw",
            wraplength=440,
            font=font("mono"),
            text_color=p("text_primary"),
        )
        label.pack(fill="both", expand=True)

        ctk.CTkButton(win, text=s("dlg_tutorial_close"), command=win.destroy).pack(pady=(0, 12))

    def _show_language_pairs(self) -> None:
        """Open a dialog listing currently installed language pairs."""
        win = ctk.CTkToplevel(self)
        win.title(s("dlg_langs_title"))
        win.minsize(360, 300)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=s("dlg_langs_header"),
            font=font("body_bold"),
            text_color=p("text_primary"),
        ).pack(pady=(16, 8))

        pairs = self._language_pairs
        if not pairs:
            ctk.CTkLabel(
                win,
                text=s("dlg_langs_empty"),
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

        ctk.CTkButton(win, text=s("dlg_langs_close"), command=win.destroy).pack(pady=(8, 16))

    def _show_about(self) -> None:
        """Open About GenSubtitles dialog."""
        import gensubtitles  # noqa: PLC0415

        version = getattr(gensubtitles, "__version__", "0.1.0")

        win = ctk.CTkToplevel(self, fg_color=p("bg"))
        win.title(s("dlg_about_title"))
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="GenSubtitles",
            font=font("header"),
            text_color=p("text_primary"),
        ).pack(pady=(24, 4))
        ctk.CTkLabel(win, text=f"Version {version}", font=font("body"), text_color=p("text_primary")).pack(pady=4)
        ctk.CTkLabel(
            win,
            text="Automatic offline subtitle generation\nusing Whisper + Argos Translate.",
            justify="center",
            font=font("body"),
            text_color=p("text_primary"),
        ).pack(pady=8)
        ctk.CTkLabel(win, text="License: MIT", text_color="gray").pack(pady=4)

        def _open_github() -> None:
            import webbrowser  # noqa: PLC0415

            webbrowser.open("https://github.com/leocg/GenSubtitles")

        ctk.CTkButton(
            win,
            text=s("dlg_about_github"),
            command=_open_github,
            fg_color=p("accent"),
            hover_color=p("accent_hov"),
        ).pack(pady=(8, 4))
        ctk.CTkButton(
            win, text=s("dlg_about_close"), command=win.destroy,
            fg_color=p("secondary"),
            hover_color=p("secondary_hov"),
        ).pack(pady=(4, 24))

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _on_translate(self) -> None:
        input_path = self._tl_input_var.get().strip()
        output_path = self._tl_output_var.get().strip()

        if not input_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror(s("msg_missing_input_title"), s("msg_missing_input_subtitle"))
            return
        if not output_path:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showerror(s("msg_missing_output_title"), s("msg_missing_output_path"))
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
        self._tl_progress_bar.configure(progress_color=p("progress_proc"))
        self._tl_progress_bar.start()
        self._tl_stage_label.configure(
            text=s("status_translating") if not convert_only else s("status_converting")
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
                    style: dict | None = None
                    if self._current_settings:
                        style = {
                            "fontname": self._current_settings.subtitle_font_family,
                            "fontsize": self._current_settings.subtitle_font_size,
                            "primarycolor": self._current_settings.subtitle_text_color,
                            "outlinecolor": self._current_settings.subtitle_outline_color,
                        }
                    convert_srt_to_ssa(input_path, output_path, style=style)
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
            self._tl_progress_bar.configure(mode="determinate", progress_color=p("progress_err"))
            self._tl_progress_bar.set(1.0)
            self._tl_progress_bar.grid()
            self.after(2000, self._hide_translate_progress)
        else:
            self._tl_progress_bar.stop()
            self._tl_progress_bar.configure(mode="determinate", progress_color=p("progress_done"))
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

            messagebox.showerror(s("msg_translation_failed_title"), error)
        else:
            from tkinter import messagebox  # noqa: PLC0415

            messagebox.showinfo(s("msg_done_title"), s("msg_saved_body").format(path=output_path))

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _start_server(self) -> None:
        server.start(
            on_progress=lambda m, prog: self.after(
                0, lambda: self._apply_startup_progress(m, prog)
            ),
            on_ready=lambda: self.after(0, self._on_server_ready),
            on_failed=lambda detail: self.after(
                0, lambda: self._on_server_failed(detail)
            ),
            is_closing=lambda: self._closing,
        )
        # Show startup progress bar immediately (widget work stays in main.py)
        self._progress_bar.configure(mode="indeterminate", progress_color=p("progress_idle"))
        self._progress_bar.grid()
        self._progress_bar.start()

    def _apply_startup_progress(self, message: str, progress: int) -> None:
        """Update progress bar and label during model download/load phases."""
        self._stage_label.configure(text=message)
        self._log(message)
        if progress >= 0:
            # Determinate — real percentage available (downloading)
            if self._progress_bar.cget("mode") != "determinate":
                self._progress_bar.stop()
                self._progress_bar.configure(mode="determinate", progress_color=p("accent"))
            self._progress_bar.set(progress / 100)
        else:
            # Indeterminate — loading into memory or waiting
            if self._progress_bar.cget("mode") != "indeterminate":
                self._progress_bar.configure(mode="indeterminate", progress_color=p("progress_idle"))
                self._progress_bar.start()

    def _on_server_ready(self) -> None:
        """Called on main thread once the local API server responds."""
        self._server_ready = True
        self._progress_bar.stop()
        self._progress_bar.grid_remove()
        self._progress_bar.configure(progress_color=p("progress_idle"))
        self._btn_generate.configure(state="normal")
        self._tl_btn_translate.configure(state="normal")
        self._stage_label.configure(text="", text_color=p("text_secondary"))
        self._log("")
        # Run in background — list_installed_pairs() can be slow on first Argos load
        threading.Thread(target=self._populate_language_dropdowns, daemon=True).start()
        # Enable step tab action buttons (D-06 / D-03)
        for btn_attr in ("_extract_btn_run", "_transcribe_btn_run", "_translate_step_btn_run", "_write_btn_run"):
            btn = getattr(self, btn_attr, None)
            if btn is not None:
                btn.configure(state="normal")

    def _on_server_failed(self, detail: str = "") -> None:
        """Called on main thread if the server never became reachable."""
        self._progress_bar.stop()
        self._progress_bar.configure(mode="determinate", progress_color=p("progress_err"))
        self._progress_bar.set(1.0)
        text = f"❌ {detail}" if detail else "❌ Server failed to start. Restart the app."
        self._stage_label.configure(
            text=text,
            text_color=p("progress_err"),
        )
        self._log(text)

    def on_closing(self) -> None:
        self._closing = True
        self._stop_os_theme_listener()
        server.stop()
        self.destroy()


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    app = GenSubtitlesApp()
    app.mainloop()


if __name__ == "__main__":
    main()
