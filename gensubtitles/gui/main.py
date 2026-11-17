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
from hashlib import sha256
from pathlib import Path

import customtkinter as ctk
from .theme import font, p
from .styles import (
    BTN_HEIGHT_PRIMARY, BTN_HEIGHT_CANCEL, BTN_HEIGHT_MINI,
    BTN_WIDTH_NARROW, BTN_WIDTH_SWATCH, ENTRY_WIDTH_SMALL,
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


def _is_keep_original(value: str) -> bool:
    """True when the subtitle language should stay the spoken language."""
    labels = {s_lang("keep_original", lang) for lang in LANGUAGES}
    return value in labels or value in ("", "No target")


def _is_detect(value: str) -> bool:
    """True when Whisper should detect the spoken language."""
    labels = {s_lang("detect_spoken", lang) for lang in LANGUAGES}
    return value in labels or value in ("", "Auto-detect")


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
        """Build the two-tab window: generate (with optional steps) and translate a file."""
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=16, pady=16)
        self._tabview.add("Generate Subtitles")
        self._tabview.add("Translate Subtitles")

        _startup_lang = (
            getattr(self._current_settings, "ui_language", "en")
            if self._current_settings else "en"
        )
        set_language(_startup_lang)
        self._source_lang_var.set(s("detect_spoken"))
        self._target_lang_var.set(s("keep_original"))

        tab = self._tabview.tab("Generate Subtitles")
        gen = ctk.CTkFrame(tab, fg_color="transparent")
        gen.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        gen.columnconfigure(0, weight=1)
        self._gen_frame = gen
        self._files_frame = gen

        row = 0
        self._lbl_input_video = ctk.CTkLabel(gen, text=s("input_video_lbl"), anchor="w")
        self._lbl_input_video.grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1
        input_row = ctk.CTkFrame(gen, fg_color="transparent")
        input_row.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        input_row.columnconfigure(0, weight=1)
        self._entry_input = ctk.CTkEntry(input_row, textvariable=self._input_var)
        apply_entry_style(self._entry_input)
        self._entry_input.grid(row=0, column=0, sticky="ew")
        self._btn_browse_input = ctk.CTkButton(
            input_row, text=s("browse_btn"), height=BTN_HEIGHT_PRIMARY,
            command=self._browse_input,
        )
        apply_secondary_btn_style(self._btn_browse_input)
        self._btn_browse_input.grid(row=0, column=1, padx=(8, 0))
        row += 1

        self._lbl_output_file = ctk.CTkLabel(gen, text=s("output_file_lbl"), anchor="w")
        self._lbl_output_file.grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1
        output_row = ctk.CTkFrame(gen, fg_color="transparent")
        output_row.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        output_row.columnconfigure(0, weight=1)
        self._entry_output = ctk.CTkEntry(output_row, textvariable=self._output_var)
        apply_entry_style(self._entry_output)
        self._entry_output.grid(row=0, column=0, sticky="ew")
        self._btn_browse_output = ctk.CTkButton(
            output_row, text=s("save_as_btn"), height=BTN_HEIGHT_PRIMARY,
            command=self._browse_output,
        )
        apply_secondary_btn_style(self._btn_browse_output)
        self._btn_browse_output.grid(row=0, column=1, padx=(8, 0))
        row += 1

        lang_row = ctk.CTkFrame(gen, fg_color="transparent")
        lang_row.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        lang_row.columnconfigure(0, weight=1)
        lang_row.columnconfigure(1, weight=1)
        self._lbl_source_lang = ctk.CTkLabel(lang_row, text=s("source_lang_lbl"), anchor="w")
        self._lbl_source_lang.grid(row=0, column=0, sticky="w")
        self._lbl_target_lang = ctk.CTkLabel(lang_row, text=s("target_lang_lbl"), anchor="w")
        self._lbl_target_lang.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._option_source_lang = ctk.CTkOptionMenu(
            lang_row,
            values=[s("detect_spoken")],
            variable=self._source_lang_var,
            command=self._on_source_lang_change,
        )
        self._option_source_lang.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self._option_target_lang = ctk.CTkOptionMenu(
            lang_row,
            values=[s("keep_original")],
            variable=self._target_lang_var,
            command=self._on_target_lang_change,
        )
        self._option_target_lang.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))
        row += 1

        fmt_row = ctk.CTkFrame(gen, fg_color="transparent")
        fmt_row.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        fmt_row.columnconfigure(0, weight=1)
        fmt_row.columnconfigure(1, weight=1)
        self._lbl_output_format = ctk.CTkLabel(fmt_row, text=s("output_format_lbl"), anchor="w")
        self._lbl_output_format.grid(row=0, column=0, sticky="w")
        self._lbl_engine = ctk.CTkLabel(fmt_row, text=s("engine_lbl"), anchor="w")
        self._lbl_engine.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._option_output_format = ctk.CTkOptionMenu(
            fmt_row,
            values=["SRT", "SSA"],
            variable=self._output_format_var,
            command=self._on_output_format_change,
        )
        self._option_output_format.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        engine_values = ["Argos"]
        if self._current_settings and self._current_settings.deepl_api_key:
            engine_values.append("DeepL")
        if self._current_settings and self._current_settings.libretranslate_url:
            engine_values.append("LibreTranslate")
        self._option_engine = ctk.CTkOptionMenu(
            fmt_row, values=engine_values, variable=self._engine_var,
        )
        self._option_engine.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))
        self._lbl_engine.grid_remove()
        self._option_engine.grid_remove()
        row += 1

        self._cue_frame = ctk.CTkFrame(gen, fg_color=p("surface"))
        self._cue_frame.grid(row=row, column=0, sticky="ew", pady=(8, 8))
        self._cue_frame.columnconfigure(0, weight=1)
        self._elapsed_label = ctk.CTkLabel(
            self._cue_frame, text="", font=font("clock"), text_color=p("time"), anchor="w",
        )
        self._elapsed_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self._cue_line = ctk.CTkLabel(
            self._cue_frame,
            text=s("cue_idle"),
            font=font("body"),
            text_color=p("text_primary"),
            anchor="center",
            justify="center",
        )
        self._cue_line.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))
        self._progress_bar = ctk.CTkProgressBar(self._cue_frame, height=PROGRESS_BAR_HEIGHT)
        apply_progress_bar_style(self._progress_bar)
        self._progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        self._progress_bar.grid_remove()
        row += 1

        self._stage_label = ctk.CTkLabel(gen, text=s("starting_server"), anchor="w")
        apply_stage_label_style(self._stage_label)
        self._stage_label.grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        self._stepper_var = ctk.BooleanVar(value=False)
        self._stepper_switch = ctk.CTkSwitch(
            gen,
            text=s("stepper_switch_lbl"),
            variable=self._stepper_var,
            command=self._on_stepper_toggle,
        )
        self._stepper_switch.grid(row=row, column=0, sticky="w", pady=(4, 4))
        row += 1

        self._stepper_frame = ctk.CTkFrame(gen, fg_color="transparent")
        self._stepper_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self._stepper_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self._step_status_labels: dict[str, ctk.CTkLabel] = {}
        self._step_buttons: dict[str, ctk.CTkButton] = {}
        self._step_label_keys = {
            "extract": "step_extract",
            "transcribe": "step_transcribe",
            "translate": "step_translate",
            "write": "step_write",
        }
        step_cmds = {
            "extract": self._on_step_extract,
            "transcribe": self._on_step_transcribe,
            "translate": self._on_step_translate,
            "write": self._on_step_write,
        }
        for col, key in enumerate(self._step_label_keys):
            cell = ctk.CTkFrame(self._stepper_frame, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="nsew", padx=4)
            cell.columnconfigure(0, weight=1)
            ctk.CTkLabel(
                cell, text=str(col + 1), font=font("help"), text_color=p("text_secondary"),
            ).grid(row=0, column=0, sticky="w")
            name = ctk.CTkLabel(cell, text=s(self._step_label_keys[key]), font=font("body"), anchor="w")
            name.grid(row=1, column=0, sticky="ew")
            setattr(self, f"_step_name_{key}", name)
            status = ctk.CTkLabel(
                cell, text=s("step_status_waiting"), font=font("help"),
                text_color=p("text_secondary"), anchor="w",
            )
            status.grid(row=2, column=0, sticky="ew", pady=(0, 4))
            self._step_status_labels[key] = status
            btn = ctk.CTkButton(
                cell,
                text=s(self._step_label_keys[key]),
                command=step_cmds[key],
                state="disabled",
                height=BTN_HEIGHT_PRIMARY,
                text_color_disabled=("#757575", "#9E9E9E"),
            )
            apply_secondary_btn_style(btn)
            btn.grid(row=3, column=0, sticky="ew")
            self._step_buttons[key] = btn
        self._stepper_frame.grid_remove()
        row += 1

        btn_row = ctk.CTkFrame(gen, fg_color="transparent")
        btn_row.grid(row=row, column=0, sticky="ew", pady=(8, 4))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        self._btn_generate = ctk.CTkButton(
            btn_row,
            text=s("generate_btn"),
            command=self._on_generate,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._btn_generate)
        self._btn_generate.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._btn_clear = ctk.CTkButton(
            btn_row,
            text=s("generate_clear_btn"),
            command=self._on_clear,
            state="disabled",
            height=BTN_HEIGHT_PRIMARY,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_secondary_btn_style(self._btn_clear)
        self._btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        for var in (self._input_var, self._output_var, self._target_lang_var):
            var.trace_add("write", lambda *_: self._update_clear_state())
        row += 1

        self._btn_cancel = ctk.CTkButton(
            gen,
            text=s("cancel_btn"),
            command=self._on_cancel,
            height=BTN_HEIGHT_CANCEL,
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_cancel_btn_style(self._btn_cancel)
        self._btn_cancel.grid(row=row, column=0, sticky="ew", pady=(4, 0))
        self._btn_cancel.grid_remove()
        row += 1

        self._open_folder_row = row
        row += 1

        self._log_label = ctk.CTkLabel(gen, text=s("log_lbl"), anchor="w", font=font("help"))
        apply_secondary_label_style(self._log_label)
        self._log_label.grid(row=row, column=0, sticky="w", pady=(8, 2))
        row += 1
        self._log_textbox = ctk.CTkTextbox(
            gen,
            state="disabled",
            height=90,
            fg_color=p("input_bg"),
            font=font("mono"),
            activate_scrollbars=True,
        )
        self._log_textbox.grid(row=row, column=0, sticky="nsew", pady=(0, 4))
        gen.rowconfigure(row, weight=1)

        self._step_audio_path: Path | None = None
        self._step_transcription_path: Path | None = None
        self._step_translation_path: Path | None = None

        self._build_translate_tab()
        self._build_settings_panel()
        self._build_palette_panel()
        self._build_menu_bar()

    def _set_cue_idle(self) -> None:
        """Show the invitation line in the cue strip."""
        self._cue_line.configure(text=s("cue_idle"), font=font("body"), text_color=p("text_primary"))

    def _set_cue_saved(self) -> None:
        """Show the saved line in the user's subtitle face."""
        family = "Arial"
        size = 20
        color = p("text_primary")
        if self._current_settings is not None:
            family = self._current_settings.subtitle_font_family or family
            size = int(self._current_settings.subtitle_font_size or size)
            color = self._current_settings.subtitle_text_color or color
        self._cue_line.configure(
            text=s("cue_saved"),
            font=ctk.CTkFont(family=family, size=max(size, 18)),
            text_color=color,
        )

    def _on_stepper_toggle(self) -> None:
        """Show the four-step row only while step-by-step mode is on."""
        if self._stepper_var.get():
            self._stepper_frame.grid()
            self._btn_generate.configure(state="disabled")
        else:
            self._stepper_frame.grid_remove()
            if self._server_ready and not self._job_active:
                self._btn_generate.configure(state="normal")

    def _mark_step(self, key: str) -> None:
        label = self._step_status_labels.get(key)
        if label is not None:
            label.configure(text=s("step_status_done"), text_color=p("time"))

    def _log_to(self, textbox: "ctk.CTkTextbox", msg: str) -> None:
        """Append *msg* to any CTkTextbox log widget with auto-scroll."""
        try:
            textbox.configure(state="normal")
            textbox.insert("end", msg + "\n")
            textbox.configure(state="disabled")
            textbox.see("end")
        except Exception:  # noqa: BLE001
            pass

    def _log_separator(self, textbox: "ctk.CTkTextbox") -> None:
        """Append a visual separator line to *textbox* (D-03)."""
        self._log_to(textbox, s("log_separator"))

    def _clear_console(self, textbox: "ctk.CTkTextbox") -> None:
        """Erase all text from *textbox* (D-04)."""
        textbox.configure(state="normal")
        textbox.delete("1.0", "end")
        textbox.configure(state="disabled")

    def _get_active_tab_log_textbox(self) -> "ctk.CTkTextbox | None":
        """Return the log textbox for the currently selected tab, or None (D-04)."""
        tab_name = self._tabview.get()
        for attr, tab_key in (
            ("_log_textbox",                "generate_tab"),
            ("_extract_log_textbox",        "extract_tab"),
            ("_transcribe_log_textbox",     "transcribe_tab"),
            ("_translate_step_log_textbox", "translate_step_tab"),
            ("_write_log_textbox",          "write_tab"),
        ):
            if tab_name == s(tab_key):
                return getattr(self, attr, None)
        return None

    def _set_all_action_buttons(self, state: str) -> None:
        """Enable or disable all action, browse, and clear buttons across all tabs (D-02).

        Args:
            state: "normal" or "disabled"
        """
        buttons = [
            # Tab 1 — Generate
            "_btn_clear",
            "_btn_browse_input",
            "_btn_browse_output",
            # Tab 2 — Translate Subtitles
            "_tl_btn_browse",
            "_tl_btn_browse_out",
            # Tab 3 — Extract Audio
            "_extract_btn_run",
            "_extract_btn_clear",
            "_extract_btn_browse_input",
            "_extract_btn_browse_output",
            # Tab 4 — Transcribe
            "_transcribe_btn_run",
            "_transcribe_btn_clear",
            "_transcribe_btn_browse",
            # Tab 5 — Translate Step
            "_translate_step_btn_run",
            "_translate_step_btn_clear",
            "_translate_step_btn_browse",
            # Tab 6 — Write Subtitle
            "_write_btn_run",
            "_write_btn_clear",
            "_write_btn_browse_input",
            "_write_btn_browse_output",
        ]
        for attr in buttons:
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.configure(state=state)

        # Tab 1 generate / Tab 2 translate — only re-enable when server is ready
        # and inputs are valid; setting to disabled is always safe.
        if state == "disabled":
            for attr in ("_btn_generate", "_tl_btn_translate"):
                btn = getattr(self, attr, None)
                if btn is not None:
                    btn.configure(state="disabled")
        # Re-enable is NOT done here for _btn_generate/_tl_btn_translate —
        # their state is managed by _on_server_ready, _finish_generate, _finish_translate.

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
        self._log_separator(_tb)
        self._log_to(_tb, f"{s('log_running_step')} {step_key}")
        self._set_all_action_buttons("disabled")

        def _worker() -> None:
            try:
                import requests as req  # noqa: PLC0415
                resp = req.post(f"{server.BASE_URL}{api_endpoint}", json=payload, timeout=(5, None))
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
                        self.after(0, lambda d=detail: self._log_to(_tb, f"{s('log_error_generic')} {d}"))
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    self.after(0, on_error, str(exc))
                else:
                    self.after(0, lambda e=exc: self._log_to(_tb, f"{s('log_error_generic')} {e}"))
            finally:
                self.after(0, lambda: self._set_all_action_buttons("normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_step_success(self, step_key: str) -> None:
        """Legacy callback — kept for compatibility. Step tabs use per-tab on_success callbacks."""
        self._log(f"\u2713 Step {step_key} completed")

    def _on_step_error(self, step_key: str, detail: str) -> None:
        """Legacy callback — kept for compatibility. Step tabs use per-tab on_error callbacks."""
        self._log(f"\u2717 Step error ({step_key}): {str(detail)[:120]}")

    def _on_step_extract(self) -> None:
        """Extract audio from the video chosen on Generate."""
        video = self._input_var.get().strip()
        if not video:
            self._log(s("log_warn_no_input_video"))
            return
        video_path = Path(video)
        if not video_path.is_file():
            self._log(s("log_warn_file_not_found"))
            return
        work = self._step_workspace(video_path, "extract", "video")
        work.mkdir(parents=True, exist_ok=True)
        payload: dict = {"video_path": video, "work_dir": str(work)}

        def _on_success() -> None:
            self._log(s("log_step_success_extract"))
            wavs = sorted(work.glob("*.wav"), key=lambda item: item.stat().st_mtime, reverse=True)
            if wavs:
                self._step_audio_path = wavs[0]
                self._log(f"{s('log_audio_ready')} {wavs[0].name}")
                self._mark_step("extract")

        def _on_error(detail: str) -> None:
            self._log(f"{s('log_error_extract')} {detail[:200]}")

        self._run_step_in_bg(
            "extract", "/steps/extract", payload,
            log_textbox=self._log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_step_transcribe(self) -> None:
        """Transcribe the audio produced by the extract step."""
        from gensubtitles.core.steps import TRANSCRIPTION_FILENAME  # noqa: PLC0415
        import shutil  # noqa: PLC0415

        audio = self._step_audio_path
        if audio is None or not Path(audio).is_file():
            self._log(s("log_warn_no_input_audio"))
            return
        audio_path = Path(audio)
        work = self._step_workspace(audio_path, "transcribe", "audio")
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy2(audio_path, work / "audio.wav")
        src = self._source_lang_var.get()
        src_code = None if _is_detect(src) else _label_to_code(src)
        payload = {"work_dir": str(work), "source_lang": src_code, "device": "auto"}

        def _on_success() -> None:
            self._log(s("log_step_success_transcribe"))
            path = work / TRANSCRIPTION_FILENAME
            if path.exists():
                self._step_transcription_path = path
                self._log(f"{s('log_transcript_ready')} {path.name}")
                self._mark_step("transcribe")

        def _on_error(detail: str) -> None:
            self._log(f"{s('log_error_transcribe')} {detail[:200]}")

        self._run_step_in_bg(
            "transcribe", "/steps/transcribe", payload,
            log_textbox=self._log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_step_translate(self) -> None:
        """Translate the transcript, or keep it when the original language is requested."""
        from gensubtitles.core.steps import TRANSLATION_FILENAME  # noqa: PLC0415
        import shutil  # noqa: PLC0415

        trans = self._step_transcription_path
        if trans is None or not Path(trans).is_file():
            self._log(s("log_warn_no_input_transcription"))
            return
        tgt = self._target_lang_var.get()
        if _is_keep_original(tgt):
            self._step_translation_path = Path(trans)
            self._log(s("log_kept_original"))
            self._mark_step("translate")
            return
        trans_path = Path(trans)
        work = self._step_workspace(trans_path, "translate", "transcription")
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy2(trans_path, work / "transcription.json")
        payload = {
            "work_dir": str(work),
            "target_lang": _label_to_code(tgt),
            "engine": self._engine_var.get().lower().replace(" ", ""),
        }

        def _on_success() -> None:
            self._log(s("log_step_success_translate"))
            path = work / TRANSLATION_FILENAME
            if path.exists():
                self._step_translation_path = path
                self._log(f"{s('log_translation_ready')} {path.name}")
                self._mark_step("translate")

        def _on_error(detail: str) -> None:
            self._log(f"{s('log_error_translate')} {detail[:200]}")

        self._run_step_in_bg(
            "translate", "/steps/translate", payload,
            log_textbox=self._log_textbox,
            on_success=_on_success,
            on_error=_on_error,
        )

    def _on_step_write(self) -> None:
        """Write the subtitle file from the latest transcript or translation."""
        from gensubtitles.core.steps import SRT_FILENAME  # noqa: PLC0415
        from gensubtitles.core.srt_writer import convert_srt_to_ssa  # noqa: PLC0415
        import shutil  # noqa: PLC0415

        source = self._step_translation_path or self._step_transcription_path
        if source is None or not Path(source).is_file():
            self._log(s("log_warn_no_input_file"))
            return
        trans_path = Path(source)
        work = self._step_workspace(trans_path, "write", "segments")
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy2(trans_path, work / "translation.json")

        fmt = self._output_format_var.get().upper()
        output_path = self._output_var.get().strip()
        if not output_path:
            self._log(s("log_warn_no_output_dir"))
            return
        output_obj = Path(output_path)
        if fmt == "SSA":
            tmp_srt = work / SRT_FILENAME
            payload = {"work_dir": str(work), "output_path": str(tmp_srt)}
        else:
            payload = {"work_dir": str(work), "output_path": str(output_obj)}

        def _on_success() -> None:
            if fmt == "SSA":
                tmp_path = work / SRT_FILENAME
                try:
                    style = None
                    if self._current_settings is not None:
                        style = {
                            "fontname": self._current_settings.subtitle_font_family,
                            "fontsize": self._current_settings.subtitle_font_size,
                            "primarycolor": self._current_settings.subtitle_text_color,
                            "outlinecolor": self._current_settings.subtitle_outline_color,
                        }
                    convert_srt_to_ssa(tmp_path, output_obj, style=style)
                    self._log(f"{s('log_step_success_write')} {output_obj}")
                    self._mark_step("write")
                    self._set_cue_saved()
                except (OSError, ValueError) as exc:
                    self._log(f"{s('log_error_write')} {str(exc)[:200]}")
                    return
                finally:
                    tmp_path.unlink(missing_ok=True)
            else:
                self._log(f"{s('log_step_success_write')} {output_obj}")
                self._mark_step("write")
                self._set_cue_saved()

        def _on_error(detail: str) -> None:
            self._log(f"{s('log_error_write')} {detail[:200]}")

        self._run_step_in_bg(
            "write", "/steps/write", payload,
            log_textbox=self._log_textbox,
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
        settings_menu.add_command(label=s("menu_color_palette"), command=self._show_palette_panel)

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
        """Preferences in two groups: the program, then the on-screen subtitle."""
        self._settings_frame = ctk.CTkFrame(self)
        sf = self._settings_frame
        sf.columnconfigure(1, weight=1)

        self._settings_header_lbl = ctk.CTkLabel(sf, text=s("settings_header"))
        apply_settings_header_style(self._settings_header_lbl)
        self._settings_header_lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 4))

        self._lbl_settings_program = ctk.CTkLabel(sf, text=s("settings_program"), anchor="w")
        apply_settings_header_style(self._lbl_settings_program)
        self._lbl_settings_program.grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(8, 4))

        self._lbl_appearance_mode = ctk.CTkLabel(sf, text=s("appearance_lbl"))
        self._lbl_appearance_mode.grid(row=2, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_appearance_var = ctk.StringVar(value="System")
        ctk.CTkOptionMenu(
            sf, values=["System", "Light", "Dark"], variable=self._settings_appearance_var,
        ).grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        self._lbl_ui_language_setting = ctk.CTkLabel(sf, text=s("ui_lang_lbl"))
        self._lbl_ui_language_setting.grid(row=3, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_lang_var = ctk.StringVar(value="English")
        ctk.CTkOptionMenu(
            sf, values=["English", "Spanish"], variable=self._settings_lang_var,
        ).grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        self._lbl_default_outdir = ctk.CTkLabel(sf, text=s("default_outdir_lbl"))
        self._lbl_default_outdir.grid(row=4, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_outdir_var = ctk.StringVar()
        self._settings_outdir_entry = ctk.CTkEntry(
            sf, textvariable=self._settings_outdir_var,
            placeholder_text="(same directory as input)",
        )
        apply_entry_style(self._settings_outdir_entry)
        self._settings_outdir_entry.grid(row=4, column=1, sticky="ew", padx=(0, 12), pady=6)

        self._clear_console_var = ctk.BooleanVar(value=False)
        self._lbl_clear_console = ctk.CTkLabel(sf, text=s("clear_console_on_clear_lbl"), anchor="w")
        self._lbl_clear_console.grid(row=5, column=0, sticky="w", padx=(12, 8), pady=6)
        self._clear_console_switch = ctk.CTkSwitch(
            sf, text="", variable=self._clear_console_var, width=48,
        )
        self._clear_console_switch.grid(row=5, column=1, sticky="w", padx=(0, 12), pady=6)

        self._lbl_settings_caption = ctk.CTkLabel(sf, text=s("settings_caption"), anchor="w")
        apply_settings_header_style(self._lbl_settings_caption)
        self._lbl_settings_caption.grid(row=6, column=0, columnspan=3, sticky="w", padx=12, pady=(16, 4))
        self._lbl_subtitle_style = self._lbl_settings_caption

        self._lbl_font_family = ctk.CTkLabel(sf, text=s("font_family_lbl"))
        self._lbl_font_family.grid(row=7, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_font_var = ctk.StringVar(value="Arial")
        self._settings_font_menu = ctk.CTkOptionMenu(
            sf,
            values=["Arial", "Helvetica", "Verdana", "Trebuchet MS", "Tahoma"],
            variable=self._settings_font_var,
            command=self._refresh_caption_preview,
        )
        self._settings_font_menu.grid(row=7, column=1, sticky="ew", padx=(0, 12), pady=6)

        self._lbl_font_size = ctk.CTkLabel(sf, text=s("font_size_lbl"))
        self._lbl_font_size.grid(row=8, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_font_size_var = ctk.StringVar(value="20")
        self._settings_font_size_entry = ctk.CTkEntry(
            sf, textvariable=self._settings_font_size_var, width=ENTRY_WIDTH_SMALL,
        )
        apply_entry_style(self._settings_font_size_entry)
        self._settings_font_size_entry.grid(row=8, column=1, sticky="w", padx=(0, 12), pady=6)
        self._settings_font_size_var.trace_add("write", lambda *_: self._refresh_caption_preview())

        self._lbl_text_color = ctk.CTkLabel(sf, text=s("text_color_lbl"))
        self._lbl_text_color.grid(row=9, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_text_color_var = ctk.StringVar(value="#FFFFFF")
        self._btn_text_color_swatch = ctk.CTkButton(
            sf, text="", width=BTN_WIDTH_SWATCH, height=BTN_HEIGHT_MINI,
            fg_color=self._settings_text_color_var.get(),
            hover_color=self._settings_text_color_var.get(),
            command=self._on_pick_text_color,
        )
        self._btn_text_color_swatch.grid(row=9, column=1, sticky="w", padx=(0, 12), pady=6)

        self._lbl_outline_color = ctk.CTkLabel(sf, text=s("outline_color_lbl"))
        self._lbl_outline_color.grid(row=10, column=0, sticky="w", padx=(12, 8), pady=6)
        self._settings_outline_color_var = ctk.StringVar(value="#000000")
        self._btn_outline_color_swatch = ctk.CTkButton(
            sf, text="", width=BTN_WIDTH_SWATCH, height=BTN_HEIGHT_MINI,
            fg_color=self._settings_outline_color_var.get(),
            hover_color=self._settings_outline_color_var.get(),
            command=self._on_pick_outline_color,
        )
        self._btn_outline_color_swatch.grid(row=10, column=1, sticky="w", padx=(0, 12), pady=6)

        self._lbl_caption_preview = ctk.CTkLabel(sf, text=s("cue_preview"), anchor="w")
        self._lbl_caption_preview.grid(row=11, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 8))

        self._lbl_config_path_label = ctk.CTkLabel(sf, text=s("config_path_lbl"))
        apply_secondary_label_style(self._lbl_config_path_label)
        self._lbl_config_path_label.grid(row=12, column=0, sticky="w", padx=(12, 8), pady=6)
        self._lbl_config_path_value = ctk.CTkLabel(
            sf, text="", wraplength=260, anchor="w", justify="left",
        )
        apply_secondary_label_style(self._lbl_config_path_value)
        self._lbl_config_path_value.grid(row=12, column=1, sticky="ew", padx=(0, 8), pady=6)

        def _open_config_folder() -> None:
            from gensubtitles.core.settings import settings_path  # noqa: PLC0415
            config_dir = settings_path().parent
            sys_name = platform.system()
            if sys_name == "Windows":
                subprocess.Popen(["explorer", str(config_dir)])  # noqa: S603,S607
            elif sys_name == "Darwin":
                subprocess.Popen(["open", str(config_dir)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(config_dir)])  # noqa: S603,S607

        self._btn_open_config_folder = ctk.CTkButton(
            sf, text=s("open_config_folder_btn"), height=BTN_HEIGHT_PRIMARY,
            command=_open_config_folder,
        )
        apply_secondary_btn_style(self._btn_open_config_folder)
        self._btn_open_config_folder.grid(row=13, column=1, sticky="w", padx=(0, 12), pady=6)

        btn_frame = ctk.CTkFrame(sf, fg_color="transparent")
        btn_frame.grid(row=14, column=0, columnspan=3, pady=(16, 12), padx=12, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        self._btn_settings_save = ctk.CTkButton(
            btn_frame, text=s("save_btn"), command=self._save_settings, height=BTN_HEIGHT_PRIMARY,
        )
        apply_accent_btn_style(self._btn_settings_save)
        self._btn_settings_save.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._btn_settings_back = ctk.CTkButton(
            btn_frame, text=s("back_btn"), command=self._hide_settings, height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._btn_settings_back)
        self._btn_settings_back.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        self._refresh_caption_preview()

    def _refresh_caption_preview(self, _value: str | None = None) -> None:
        """Paint the settings sample with the subtitle font and text color."""
        if not hasattr(self, "_lbl_caption_preview"):
            return
        family = self._settings_font_var.get() or "Arial"
        raw = self._settings_font_size_var.get().strip() or "20"
        size = int(raw) if raw.isdigit() else 20
        color = self._settings_text_color_var.get() or "#FFFFFF"
        self._lbl_caption_preview.configure(
            text=s("cue_preview"),
            font=ctk.CTkFont(family=family, size=max(size, 12)),
            text_color=color,
        )

    _PALETTE_TOKEN_KEYS: tuple = (
        "bg", "surface", "input_bg", "text_primary", "text_secondary",
        "accent", "accent_hov", "btn_primary_text", "secondary", "secondary_hov", "btn_secondary_text",
        "time",
        "progress_idle", "progress_proc", "progress_done", "progress_err",
        "menu_bg", "menu_fg", "menu_active_bg",
    )

    def _build_palette_panel(self) -> None:
        """Build the color palette editor panel (D-06)."""
        from gensubtitles.gui import theme as _theme  # noqa: PLC0415

        self._palette_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        # Not packed yet — shown via _show_palette_panel

        pf = self._palette_frame
        pf.columnconfigure(0, weight=1)

        # Header
        self._palette_header_lbl = ctk.CTkLabel(
            pf, text=s("palette_header"), font=font("header"), anchor="w",
        )
        self._palette_header_lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 4))

        # Active palette label + dropdown
        self._palette_active_lbl = ctk.CTkLabel(pf, text=s("palette_active_lbl"), anchor="w")
        self._palette_active_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(4, 2))

        self._palette_name_var = ctk.StringVar(value=(
            self._current_settings.active_palette if self._current_settings else "Default Dark"
        ))
        self._palette_dropdown = ctk.CTkOptionMenu(
            pf,
            values=list(_theme.PALETTE_NAMES),
            variable=self._palette_name_var,
            command=self._on_palette_selected,
        )
        self._palette_dropdown.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))

        # Token swatch rows — one per token key
        self._palette_swatch_btns: dict[str, ctk.CTkButton] = {}
        for idx, token_key in enumerate(self._PALETTE_TOKEN_KEYS):
            row_n = 3 + idx
            lbl = ctk.CTkLabel(pf, text=s(f"token_{token_key}"), anchor="w", width=200)
            lbl.grid(row=row_n, column=0, sticky="w", padx=12, pady=2)
            setattr(self, f"_palette_token_lbl_{token_key}", lbl)

            initial_color = p(token_key)
            swatch = ctk.CTkButton(
                pf, text="", width=36, height=28,
                fg_color=initial_color, hover_color=initial_color,
                command=lambda tk=token_key: self._on_pick_palette_token(tk),
            )
            swatch.grid(row=row_n, column=1, padx=(8, 4), pady=2)
            self._palette_swatch_btns[token_key] = swatch

            hex_lbl = ctk.CTkLabel(
                pf, text=initial_color, anchor="w", width=90,
                font=font("mono"),
            )
            hex_lbl.grid(row=row_n, column=2, padx=(0, 12), pady=2, sticky="w")
            setattr(self, f"_palette_hex_lbl_{token_key}", hex_lbl)

        # Bottom buttons row
        btn_row_n = 3 + len(self._PALETTE_TOKEN_KEYS)
        btn_row = ctk.CTkFrame(pf, fg_color="transparent")
        btn_row.grid(row=btn_row_n, column=0, columnspan=3, sticky="ew", padx=12, pady=(12, 12))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)

        self._btn_palette_reset = ctk.CTkButton(
            btn_row, text=s("palette_reset_btn"), command=self._on_palette_reset,
        )
        apply_secondary_btn_style(self._btn_palette_reset)
        self._btn_palette_reset.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._btn_palette_save = ctk.CTkButton(
            btn_row, text=s("palette_save_btn"), command=self._on_palette_save,
        )
        apply_accent_btn_style(self._btn_palette_save)
        self._btn_palette_save.grid(row=0, column=1, sticky="ew", padx=4)

        self._btn_palette_back = ctk.CTkButton(
            btn_row, text=s("palette_back_btn"), command=self._hide_palette_panel,
        )
        apply_secondary_btn_style(self._btn_palette_back)
        self._btn_palette_back.grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def _show_palette_panel(self) -> None:
        """Show palette editor, hide all other panels (D-06)."""
        self._refresh_palette_swatches()
        if hasattr(self, "_settings_frame"):
            self._settings_frame.pack_forget()
        self._tabview.pack_forget()
        self._palette_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def _hide_palette_panel(self) -> None:
        """Hide palette panel, restore tabview (D-06)."""
        self._palette_frame.pack_forget()
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

    def _refresh_palette_swatches(self) -> None:
        """Reload all swatch buttons with current palette token colors (D-06)."""
        from gensubtitles.gui import theme as _theme  # noqa: PLC0415

        palette_name = self._palette_name_var.get()
        if palette_name in ("Default Dark", "Default Light"):
            mode = "Dark" if "Dark" in palette_name else "Light"
            tokens = dict(_theme._PALETTES.get(mode, {}))
        else:
            tokens = dict(_theme._PALETTES.get(palette_name, {}))

        # Apply saved overrides for this palette
        if self._current_settings and self._current_settings.active_palette == palette_name:
            tokens.update(self._current_settings.palette_overrides or {})

        for token_key, swatch_btn in self._palette_swatch_btns.items():
            color = tokens.get(token_key, "#888888")
            swatch_btn.configure(fg_color=color, hover_color=color)
            hex_lbl = getattr(self, f"_palette_hex_lbl_{token_key}", None)
            if hex_lbl is not None:
                hex_lbl.configure(text=color)

    def _on_palette_selected(self, palette_name: str) -> None:
        """Called when user picks a different palette in the dropdown (D-06)."""
        self._refresh_palette_swatches()

    def _on_pick_palette_token(self, token_key: str) -> None:
        """Open OS color picker for a single palette token (D-06)."""
        import tkinter.colorchooser  # noqa: PLC0415

        swatch_btn = self._palette_swatch_btns.get(token_key)
        current = swatch_btn.cget("fg_color") if swatch_btn else "#888888"
        if isinstance(current, (list, tuple)):
            current = current[0]
        result = tkinter.colorchooser.askcolor(color=current, title=f"Choose color for {token_key}")
        if result[1] is not None:
            hex_color = result[1]
            if swatch_btn:
                swatch_btn.configure(fg_color=hex_color, hover_color=hex_color)
            hex_lbl = getattr(self, f"_palette_hex_lbl_{token_key}", None)
            if hex_lbl is not None:
                hex_lbl.configure(text=hex_color)

    def _on_palette_save(self) -> None:
        """Collect swatch colors, persist to settings, apply palette (D-06)."""
        from gensubtitles.gui import theme as _theme  # noqa: PLC0415
        from gensubtitles.core.settings import save_settings  # noqa: PLC0415
        import dataclasses  # noqa: PLC0415

        palette_name = self._palette_name_var.get()
        if palette_name in ("Default Dark", "Default Light"):
            mode = "Dark" if "Dark" in palette_name else "Light"
            base_tokens = _theme._PALETTES.get(mode, {})
        else:
            base_tokens = _theme._PALETTES.get(palette_name, {})

        palette_overrides: dict = {}
        for token_key, swatch_btn in self._palette_swatch_btns.items():
            swatch_color = swatch_btn.cget("fg_color")
            if isinstance(swatch_color, (list, tuple)):
                swatch_color = swatch_color[0]
            swatch_color = swatch_color.upper()
            if swatch_color != base_tokens.get(token_key, "").upper():
                palette_overrides[token_key] = swatch_color

        if self._current_settings is not None:
            self._current_settings = dataclasses.replace(
                self._current_settings,
                active_palette=palette_name,
                palette_overrides=palette_overrides,
            )
            save_settings(self._current_settings)

        _theme.set_active_palette(palette_name, palette_overrides)
        self._apply_theme()
        self._hide_palette_panel()

    def _on_palette_reset(self) -> None:
        """Clear all overrides in the editor for the current palette (D-06)."""
        from gensubtitles.gui import theme as _theme  # noqa: PLC0415

        palette_name = self._palette_name_var.get()
        if palette_name in ("Default Dark", "Default Light"):
            mode = "Dark" if "Dark" in palette_name else "Light"
            base_tokens = _theme._PALETTES.get(mode, {})
        else:
            base_tokens = _theme._PALETTES.get(palette_name, {})

        for token_key, swatch_btn in self._palette_swatch_btns.items():
            if token_key in base_tokens:
                color = base_tokens[token_key]
                swatch_btn.configure(fg_color=color, hover_color=color)
                hex_lbl = getattr(self, f"_palette_hex_lbl_{token_key}", None)
                if hex_lbl is not None:
                    hex_lbl.configure(text=color)

    def _build_translate_tab(self) -> None:
        """Single column for translating or converting an existing subtitle file."""
        tab = self._tabview.tab("Translate Subtitles")
        tf = ctk.CTkFrame(tab, fg_color="transparent")
        tf.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        tf.columnconfigure(0, weight=1)

        self._lbl_tl_input_sub = ctk.CTkLabel(tf, text=s("input_sub_lbl"), anchor="w")
        self._lbl_tl_input_sub.grid(row=0, column=0, sticky="w", pady=(0, 2))
        in_row = ctk.CTkFrame(tf, fg_color="transparent")
        in_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        in_row.columnconfigure(0, weight=1)
        self._tl_input_var = ctk.StringVar()
        self._tl_entry_input = ctk.CTkEntry(in_row, textvariable=self._tl_input_var)
        apply_entry_style(self._tl_entry_input)
        self._tl_entry_input.grid(row=0, column=0, sticky="ew")
        self._tl_btn_browse = ctk.CTkButton(
            in_row, text=s("browse_btn"), height=BTN_HEIGHT_PRIMARY, command=self._tl_browse_input,
        )
        apply_secondary_btn_style(self._tl_btn_browse)
        self._tl_btn_browse.grid(row=0, column=1, padx=(8, 0))

        self._lbl_tl_output_path = ctk.CTkLabel(tf, text=s("output_path_lbl"), anchor="w")
        self._lbl_tl_output_path.grid(row=2, column=0, sticky="w", pady=(0, 2))
        out_row = ctk.CTkFrame(tf, fg_color="transparent")
        out_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        out_row.columnconfigure(0, weight=1)
        self._tl_output_var = ctk.StringVar()
        self._tl_entry_output = ctk.CTkEntry(out_row, textvariable=self._tl_output_var)
        apply_entry_style(self._tl_entry_output)
        self._tl_entry_output.grid(row=0, column=0, sticky="ew")
        self._tl_btn_browse_out = ctk.CTkButton(
            out_row, text=s("save_as_btn"), height=BTN_HEIGHT_PRIMARY, command=self._tl_browse_output,
        )
        apply_secondary_btn_style(self._tl_btn_browse_out)
        self._tl_btn_browse_out.grid(row=0, column=1, padx=(8, 0))

        self._lbl_tl_source_lang = ctk.CTkLabel(tf, text=s("source_lang_lbl"), anchor="w")
        self._lbl_tl_source_lang.grid(row=4, column=0, sticky="w", pady=(0, 2))
        self._tl_source_var = ctk.StringVar(value="English")
        self._tl_option_source = ctk.CTkOptionMenu(
            tf, values=["English"], variable=self._tl_source_var,
        )
        self._tl_option_source.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        self._lbl_tl_target_lang = ctk.CTkLabel(tf, text=s("target_lang_lbl"), anchor="w")
        self._lbl_tl_target_lang.grid(row=6, column=0, sticky="w", pady=(0, 2))
        self._tl_target_var = ctk.StringVar(value="Spanish")
        self._tl_option_target = ctk.CTkOptionMenu(
            tf, values=["Spanish"], variable=self._tl_target_var,
            command=self._on_tl_target_lang_change,
        )
        self._tl_option_target.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        self._tl_convert_only_var = ctk.BooleanVar(value=False)
        self._tl_chk_convert = ctk.CTkCheckBox(
            tf,
            text=s("convert_only_chk"),
            variable=self._tl_convert_only_var,
            command=self._tl_on_convert_only_change,
        )
        self._tl_chk_convert.grid(row=8, column=0, sticky="w", pady=(0, 8))

        self._tl_btn_translate = ctk.CTkButton(
            tf,
            text=s("translate_file_btn"),
            command=self._on_translate,
            height=BTN_HEIGHT_PRIMARY,
            state="disabled",
            text_color_disabled=("#757575", "#9E9E9E"),
        )
        apply_accent_btn_style(self._tl_btn_translate)
        self._tl_btn_translate.grid(row=9, column=0, sticky="ew", pady=(8, 8))

        self._tl_elapsed_label = ctk.CTkLabel(
            tf, text="", font=font("clock"), text_color=p("time"), anchor="w",
        )
        self._tl_elapsed_label.grid(row=10, column=0, sticky="w")
        self._tl_elapsed_label.grid_remove()

        self._tl_progress_bar = ctk.CTkProgressBar(tf, height=PROGRESS_BAR_HEIGHT)
        apply_progress_bar_style(self._tl_progress_bar)
        self._tl_progress_bar.grid(row=11, column=0, sticky="ew", pady=(4, 4))
        self._tl_progress_bar.grid_remove()

        self._tl_stage_label = ctk.CTkLabel(tf, text="", anchor="w")
        apply_stage_label_style(self._tl_stage_label)
        self._tl_stage_label.grid(row=12, column=0, sticky="w", pady=4)

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
            _in_row, text=s("browse_btn"),
            command=self._on_browse_extract_input,
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
            _out_row, text=s("save_as_btn"),
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
        self._extract_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: (
                self._clear_tab_vars(self._extract_input_var, self._extract_output_var),
                self._clear_console(self._extract_log_textbox)
                if self._current_settings and self._current_settings.clear_console_on_clear
                else None,
            ),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._extract_btn_clear)
        self._extract_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

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
            _in_row, text=s("browse_btn"),
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
        self._transcribe_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: (
                self._clear_tab_vars(self._transcribe_input_var),
                self._clear_console(self._transcribe_log_textbox)
                if self._current_settings and self._current_settings.clear_console_on_clear
                else None,
            ),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._transcribe_btn_clear)
        self._transcribe_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

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
            _in_row, text=s("browse_btn"),
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
            frame,
            values=["Auto-detect"],
            variable=self._translate_step_source_var,
            command=self._on_translate_step_source_change,
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
        self._translate_step_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: (
                self._clear_tab_vars(self._translate_step_input_var),
                self._clear_console(self._translate_step_log_textbox)
                if self._current_settings and self._current_settings.clear_console_on_clear
                else None,
            ),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._translate_step_btn_clear)
        self._translate_step_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

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
            _in_row, text=s("browse_btn"),
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
            _out_row, text=s("save_as_btn"),
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
        self._write_btn_clear = ctk.CTkButton(
            _btn_row, text=s("clear_btn"),
            command=lambda: (
                self._clear_tab_vars(self._write_input_var, self._write_output_var),
                self._clear_console(self._write_log_textbox)
                if self._current_settings and self._current_settings.clear_console_on_clear
                else None,
            ),
            height=BTN_HEIGHT_PRIMARY,
        )
        apply_secondary_btn_style(self._write_btn_clear)
        self._write_btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0))

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
        label_key = "convert_format_btn" if self._tl_convert_only_var.get() else "translate_file_btn"
        self._tl_btn_translate.configure(text=s(label_key))

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

    def _target_labels_for_source(self, selection: str) -> list[str]:
        """Return target language labels; packages download on demand if missing."""
        all_labels = sorted(_CODE_TO_LABEL.values())
        pairs = [p for p in self._language_pairs if p.get("from") != p.get("to")]
        if not pairs:
            return all_labels
        if _is_detect(selection):
            targets = sorted({_CODE_TO_LABEL.get(p["to"], p["to"]) for p in pairs})
            return targets or all_labels
        src_code = _label_to_code(selection)
        targets = [
            _CODE_TO_LABEL.get(p["to"], p["to"])
            for p in pairs if p["from"] == src_code
        ]
        # Prefer installed destinations, but always offer the full known list so
        # missing Argos packages can still be downloaded on first use.
        installed = sorted(set(targets))
        extras = [t for t in all_labels if t not in installed]
        return installed + extras if installed else all_labels

    def _on_source_lang_change(self, selection: str) -> None:
        """Filter target language dropdown to valid destinations for selected source."""
        targets = [s("keep_original")] + [
            t for t in self._target_labels_for_source(selection)
            if not _is_keep_original(t)
        ]
        self._option_target_lang.configure(values=targets)
        current = self._target_lang_var.get()
        if current not in targets:
            self._target_lang_var.set(targets[0])

    def _on_target_lang_change(self, selection: str) -> None:
        """Trigger background pair download when a target language is picked."""
        no_target = _is_keep_original(selection)
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
        if _is_detect(src_label):
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
                msg = f"No translation route for {src_code} to {tgt_code}"
                self.after(0, lambda m=msg: (self._stage_label.configure(text=m), self._log(m)))
                return

            if all(_is_installed(f, t) for f, t in route):
                return  # already installed, nothing to do

            via = " → ".join(f"{f}→{t}" for f, t in route)
            self.after(0, lambda v=via: (self._stage_label.configure(
                text=f"Downloading {v}…"
            ), self._log(f"Downloading {v}…")))
            try:
                ensure_route_installed(src_code, tgt_code)
                self.after(0, lambda v=via: (self._stage_label.configure(
                    text=f"{v} ready"
                ), self._log(f"{v} ready")))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Background prefetch failed for %s→%s: %s", src_code, tgt_code, exc)
                msg = f"Could not download the model for {src_code} to {tgt_code}: {exc}"
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
                sources = [s("detect_spoken")] + sources
            else:
                sources = [s("detect_spoken")] + sorted(_CODE_TO_LABEL.values())
            self._option_source_lang.configure(values=sources)
            self._source_lang_var.set(s("detect_spoken"))
            self._on_source_lang_change(s("detect_spoken"))
            # Translate tab: always offer the full known language list so users
            # can pick destinations whose Argos packages are not installed yet.
            all_labels = sorted(_CODE_TO_LABEL.values())
            self._tl_option_source.configure(values=all_labels)
            if self._tl_source_var.get() not in all_labels:
                self._tl_source_var.set("English" if "English" in all_labels else all_labels[0])
            self._tl_option_source.configure(command=self._on_tl_source_lang_change)
            self._on_tl_source_lang_change(self._tl_source_var.get())

        if not self._closing:
            self.after(0, _apply)

    def _on_tl_target_lang_change(self, selection: str) -> None:
        """Trigger background pair download when Translate tab target is picked."""
        src_label = self._tl_source_var.get()
        self._prefetch_pair_bg(_label_to_code(src_label), _label_to_code(selection))

    def _on_tl_source_lang_change(self, selection: str) -> None:
        """Refresh Translate tab target dropdown for the selected source."""
        targets = [t for t in self._target_labels_for_source(selection) if t != selection]
        if not targets:
            targets = [t for t in sorted(_CODE_TO_LABEL.values()) if t != selection]
        self._tl_option_target.configure(values=targets)
        current = self._tl_target_var.get()
        if current not in targets:
            preferred = "Spanish" if "Spanish" in targets else targets[0]
            self._tl_target_var.set(preferred)
        # NOTE: no prefetch here — this fires on init. Prefetch only on explicit target selection.

    def _update_clear_state(self) -> None:
        """Enable Clear button if any user-settable input field is non-empty/non-default; disable otherwise."""
        has_content = any(
            v.get()
            for v in (
                self._input_var,
                self._output_var,
            )
        ) or not _is_keep_original(self._target_lang_var.get())
        self._btn_clear.configure(state="normal" if has_content else "disabled")

    def _on_clear(self) -> None:
        """Reset input fields; return dropdowns to defaults."""
        self._input_var.set("")
        self._output_var.set("")
        self._source_lang_var.set(s("detect_spoken"))
        self._target_lang_var.set(s("keep_original"))
        self._output_format_var.set("SRT")
        # D-04: Clear console of active tab if setting enabled
        if self._current_settings and self._current_settings.clear_console_on_clear:
            tb = self._get_active_tab_log_textbox()
            if tb is not None:
                self._clear_console(tb)

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
        src_lang = None if _is_detect(src_selected) else _label_to_code(src_selected)
        tgt_selected = self._target_lang_var.get()
        tgt_lang: str | None = None if _is_keep_original(tgt_selected) else _label_to_code(tgt_selected)
        engine_label = self._engine_var.get()  # "Argos", "DeepL", or "LibreTranslate"
        engine_code = engine_label.lower().replace(" ", "")  # "argos", "deepl", "libretranslate"

        self._set_all_action_buttons("disabled")
        self._entry_input.configure(state="disabled")
        self._entry_output.configure(state="disabled")
        self._option_source_lang.configure(state="disabled")
        self._option_target_lang.configure(state="disabled")
        self._option_engine.configure(state="disabled")
        self._option_output_format.configure(state="disabled")
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
        self._set_all_action_buttons("normal")
        self._btn_generate.configure(state="normal")
        # _set_all_action_buttons never re-enables Tab 1/2 primaries; restore both.
        self._tl_btn_translate.configure(state="normal")
        self._entry_input.configure(state="normal")
        self._entry_output.configure(state="normal")
        self._option_source_lang.configure(state="normal")
        self._option_target_lang.configure(state="normal")
        self._option_engine.configure(state="normal")
        self._option_output_format.configure(state="normal")
        self._update_clear_state()

        if error:
            from tkinter import messagebox  # noqa: PLC0415

            self._stage_label.configure(text="")
            self._log("")
            messagebox.showerror(s("msg_generation_failed_title"), error)
        elif cancelled:
            self._stage_label.configure(text=s("generation_cancelled"))
            self._log(s("generation_cancelled"))
            self._set_cue_idle()
        else:
            self._stage_label.configure(text=s("status_done"))
            self._log(s("status_done"))
            self._set_cue_saved()
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
                self._gen_frame, text=s("open_folder_btn"), command=_open_folder,
                height=BTN_HEIGHT_PRIMARY,
            )
            apply_secondary_btn_style(self._btn_open_folder)
            self._btn_open_folder.grid(row=self._open_folder_row, column=0, pady=(4, 0), sticky="ew")
        else:
            self._btn_open_folder.configure(text=s("open_folder_btn"), command=_open_folder)
            self._btn_open_folder.grid(row=self._open_folder_row, column=0, pady=(4, 0), sticky="ew")

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
        if hasattr(self, "_cue_frame"):
            self._cue_frame.configure(fg_color=p("surface"))
        if hasattr(self, "_elapsed_label"):
            self._elapsed_label.configure(text_color=p("time"), font=font("clock"))
        if hasattr(self, "_tl_elapsed_label"):
            self._tl_elapsed_label.configure(text_color=p("time"), font=font("clock"))

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
            # Apply saved palette BEFORE building UI so p() resolves correctly (D-06)
            from gensubtitles.gui import theme as _theme  # noqa: PLC0415
            _theme.set_active_palette(
                self._current_settings.active_palette,
                self._current_settings.palette_overrides,
            )
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
            self._refresh_caption_preview()

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
            self._clear_console_var.set(self._current_settings.clear_console_on_clear)
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
                s("font_size_error"),
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
                clear_console_on_clear=self._clear_console_var.get(),
                active_palette=(
                    self._current_settings.active_palette if self._current_settings else "Default Dark"
                ),
                palette_overrides=(
                    self._current_settings.palette_overrides if self._current_settings else {}
                ),
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
        self._stepper_switch.configure(text=s("stepper_switch_lbl"))
        self._log_label.configure(text=s("log_lbl"))
        self._btn_cancel.configure(text=s("cancel_btn"))
        for _step_key, _step_btn in self._step_buttons.items():
            _step_btn.configure(text=s(self._step_label_keys[_step_key]))
            getattr(self, f"_step_name_{_step_key}").configure(text=s(self._step_label_keys[_step_key]))
        if not self._job_active:
            self._set_cue_idle()
        if _is_keep_original(self._target_lang_var.get()):
            self._target_lang_var.set(s("keep_original"))
        if _is_detect(self._source_lang_var.get()):
            self._source_lang_var.set(s("detect_spoken"))
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
        self._tl_chk_convert.configure(text=s("convert_only_chk"))
        self._tl_on_convert_only_change()

        # Settings panel
        self._settings_header_lbl.configure(text=s("settings_header"))
        self._lbl_settings_program.configure(text=s("settings_program"))
        self._refresh_caption_preview()
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
        self._settings_menu.entryconfigure(1, label=s("menu_color_palette"))
        if hasattr(self, "_lbl_clear_console"):
            self._lbl_clear_console.configure(text=s("clear_console_on_clear_lbl"))
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

        # Palette panel (D-06)
        if hasattr(self, "_palette_header_lbl"):
            self._palette_header_lbl.configure(text=s("palette_header"))
        if hasattr(self, "_palette_active_lbl"):
            self._palette_active_lbl.configure(text=s("palette_active_lbl"))
        if hasattr(self, "_btn_palette_reset"):
            self._btn_palette_reset.configure(text=s("palette_reset_btn"))
        if hasattr(self, "_btn_palette_save"):
            self._btn_palette_save.configure(text=s("palette_save_btn"))
        if hasattr(self, "_btn_palette_back"):
            self._btn_palette_back.configure(text=s("palette_back_btn"))
        for token_key in self._PALETTE_TOKEN_KEYS:
            lbl = getattr(self, f"_palette_token_lbl_{token_key}", None)
            if lbl is not None:
                lbl.configure(text=s(f"token_{token_key}"))

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
            font=font("body"),
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

        self._set_all_action_buttons("disabled")
        # Also disable Tab 2-specific widgets not covered by _set_all_action_buttons
        _tab2_widgets = (
            self._tl_entry_input, self._tl_entry_output,
            self._tl_option_source, self._tl_option_target, self._tl_chk_convert,
        )
        for w in _tab2_widgets:
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

        self._set_all_action_buttons("normal")
        # Re-enable Tab 2-specific widgets (including _tl_btn_translate which
        # _set_all_action_buttons does not re-enable by design)
        _tab2_widgets = (
            self._tl_btn_translate, self._tl_entry_input, self._tl_entry_output,
            self._tl_option_source, self._tl_option_target, self._tl_chk_convert,
        )
        for w in _tab2_widgets:
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
                self._progress_bar.configure(mode="determinate", progress_color=p("progress_proc"))
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
        if not self._stepper_var.get():
            self._btn_generate.configure(state="normal")
        self._tl_btn_translate.configure(state="normal")
        for _step_btn in self._step_buttons.values():
            _step_btn.configure(state="normal")
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
        text = detail or s("server_failed")
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
