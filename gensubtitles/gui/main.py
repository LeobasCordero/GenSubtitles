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
import platform
import subprocess
import threading
import time
from pathlib import Path

import customtkinter as ctk

logger = logging.getLogger(__name__)

# Appearance defaults
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

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

        # String variables for entry widgets
        self._input_var = ctk.StringVar()
        self._output_var = ctk.StringVar()
        self._source_lang_var = ctk.StringVar()
        self._target_lang_var = ctk.StringVar(value="No target")
        self._output_format_var = ctk.StringVar(value="SRT")

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

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._start_server()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Tab container
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)
        self._tabview.add("Generate Subtitles")
        self._tabview.add("Translate Subtitles")

        # Use Generate tab frame as parent for existing content
        self._frame = self._tabview.tab("Generate Subtitles")

        # Configure grid columns: label | entry (expanding) | button
        self._frame.columnconfigure(1, weight=1)

        # Row 0 — Input video
        ctk.CTkLabel(self._frame, text="Input video *:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._entry_input = ctk.CTkEntry(self._frame, textvariable=self._input_var)
        self._entry_input.grid(row=0, column=1, sticky="ew", pady=4)
        self._btn_browse_input = ctk.CTkButton(
            self._frame, text="Browse…", width=80, command=self._browse_input
        )
        self._btn_browse_input.grid(row=0, column=2, padx=(8, 0), pady=4)

        # Row 1 — Output SRT
        ctk.CTkLabel(self._frame, text="Output SRT *:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._entry_output = ctk.CTkEntry(self._frame, textvariable=self._output_var)
        self._entry_output.grid(row=1, column=1, sticky="ew", pady=4)
        self._btn_browse_output = ctk.CTkButton(
            self._frame, text="Save as…", width=80, command=self._browse_output
        )
        self._btn_browse_output.grid(row=1, column=2, padx=(8, 0), pady=4)

        # Row 2 — Source language (dynamic CTkOptionMenu, populated after server starts)
        self._lbl_source_lang = ctk.CTkLabel(self._frame, text="Source language:")
        self._lbl_source_lang.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self._option_source_lang = ctk.CTkOptionMenu(
            self._frame,
            values=["Auto-detect"],
            variable=self._source_lang_var,
            command=self._on_source_lang_change,
        )
        self._option_source_lang.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 3 — Target language dropdown (populated dynamically)
        ctk.CTkLabel(self._frame, text="Target language:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._option_target_lang = ctk.CTkOptionMenu(
            self._frame,
            values=["No target"],
            variable=self._target_lang_var,
        )
        self._option_target_lang.grid(row=3, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 4 — Output format dropdown
        ctk.CTkLabel(self._frame, text="Output format:").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._option_output_format = ctk.CTkOptionMenu(
            self._frame,
            values=["SRT", "SSA"],
            variable=self._output_format_var,
            command=self._on_output_format_change,
        )
        self._option_output_format.grid(row=4, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 5 — Generate button
        self._btn_generate = ctk.CTkButton(
            self._frame, text="Generate Subtitles", command=self._on_generate
        )
        self._btn_generate.grid(row=5, column=0, columnspan=3, pady=(12, 4), sticky="ew")

        # Row 6 — Clear button
        self._btn_clear = ctk.CTkButton(
            self._frame,
            text="Clear",
            command=self._on_clear,
            state="disabled",
        )
        self._btn_clear.grid(row=6, column=0, columnspan=3, pady=(0, 4), sticky="ew")

        # Row 7 — Elapsed time counter (hidden initially)
        self._elapsed_label = ctk.CTkLabel(self._frame, text="00:00:00")
        self._elapsed_label.grid(row=7, column=0, columnspan=3, pady=4)
        self._elapsed_label.grid_remove()

        # Row 8 — Progress bar (hidden initially)
        self._progress_bar = ctk.CTkProgressBar(self._frame, mode="indeterminate")
        self._progress_bar.grid(row=8, column=0, columnspan=3, pady=4, sticky="ew")
        self._progress_bar.grid_remove()

        # Row 9 — Stage label
        self._stage_label = ctk.CTkLabel(self._frame, text="")
        self._stage_label.grid(row=9, column=0, columnspan=3, pady=4)

        # Reactive enable/disable for Clear button
        for var in (self._input_var, self._output_var, self._target_lang_var):
            var.trace_add("write", lambda *_: self._update_clear_state())

        # Build Translate tab
        self._build_translate_tab()

    def _build_translate_tab(self) -> None:
        tf = self._tabview.tab("Translate Subtitles")
        tf.columnconfigure(1, weight=1)

        # Row 0 — Input subtitle file
        ctk.CTkLabel(tf, text="Input subtitle *:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._tl_input_var = ctk.StringVar()
        self._tl_entry_input = ctk.CTkEntry(tf, textvariable=self._tl_input_var)
        self._tl_entry_input.grid(row=0, column=1, sticky="ew", pady=4)
        self._tl_btn_browse = ctk.CTkButton(
            tf, text="Browse…", width=80, command=self._tl_browse_input
        )
        self._tl_btn_browse.grid(row=0, column=2, padx=(8, 0), pady=4)

        # Row 1 — Output path
        ctk.CTkLabel(tf, text="Output path *:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._tl_output_var = ctk.StringVar()
        self._tl_entry_output = ctk.CTkEntry(tf, textvariable=self._tl_output_var)
        self._tl_entry_output.grid(row=1, column=1, sticky="ew", pady=4)
        self._tl_btn_browse_out = ctk.CTkButton(
            tf, text="Save as…", width=80, command=self._tl_browse_output
        )
        self._tl_btn_browse_out.grid(row=1, column=2, padx=(8, 0), pady=4)

        # Row 2 — Source language
        ctk.CTkLabel(tf, text="Source language:").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._tl_source_var = ctk.StringVar(value="English")
        self._tl_option_source = ctk.CTkOptionMenu(
            tf, values=["English"], variable=self._tl_source_var
        )
        self._tl_option_source.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 3 — Target language
        ctk.CTkLabel(tf, text="Target language:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._tl_target_var = ctk.StringVar(value="Spanish")
        self._tl_option_target = ctk.CTkOptionMenu(
            tf, values=["Spanish"], variable=self._tl_target_var
        )
        self._tl_option_target.grid(row=3, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 4 — Convert Only checkbox
        self._tl_convert_only_var = ctk.BooleanVar(value=False)
        self._tl_chk_convert = ctk.CTkCheckBox(
            tf,
            text="Convert only (no translation — change format only)",
            variable=self._tl_convert_only_var,
            command=self._tl_on_convert_only_change,
        )
        self._tl_chk_convert.grid(row=4, column=0, columnspan=3, sticky="w", pady=4)

        # Row 5 — Translate button
        self._tl_btn_translate = ctk.CTkButton(
            tf, text="Translate / Convert", command=self._on_translate
        )
        self._tl_btn_translate.grid(row=5, column=0, columnspan=3, pady=(12, 4), sticky="ew")

        # Row 6 — Elapsed label
        self._tl_elapsed_label = ctk.CTkLabel(tf, text="00:00:00")
        self._tl_elapsed_label.grid(row=6, column=0, columnspan=3, pady=4)
        self._tl_elapsed_label.grid_remove()

        # Row 7 — Progress bar
        self._tl_progress_bar = ctk.CTkProgressBar(tf, mode="indeterminate")
        self._tl_progress_bar.grid(row=7, column=0, columnspan=3, pady=4, sticky="ew")
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

        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("Subtitle files", "*.srt *.ssa"), ("All files", "*.*")],
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
        if selection == "Auto-detect" or not self._language_pairs:
            targets = sorted({_CODE_TO_LABEL.get(p["to"], p["to"]) for p in self._language_pairs})
            targets = targets or ["No target"]
        else:
            src_code = _label_to_code(selection)
            targets = [
                _CODE_TO_LABEL.get(p["to"], p["to"])
                for p in self._language_pairs if p["from"] == src_code
            ]
            targets = sorted(set(targets)) or ["No target"]
        self._option_target_lang.configure(values=targets)
        self._target_lang_var.set(targets[0])

    def _on_output_format_change(self, selection: str) -> None:
        """Update output path extension when format changes."""
        current = self._output_var.get()
        if not current:
            return
        p = Path(current)
        new_ext = ".ssa" if selection == "SSA" else ".srt"
        self._output_var.set(str(p.with_suffix(new_ext)))

    def _populate_language_dropdowns(self) -> None:
        """Called after server is ready. Queries GET /languages and updates dropdowns."""
        import requests as req  # noqa: PLC0415

        try:
            resp = req.get(f"{_BASE_URL}/languages", timeout=5)
            resp.raise_for_status()
            self._language_pairs = resp.json().get("pairs", [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load language pairs from API: %s", exc)
            self._language_pairs = []

        if not self._language_pairs:
            return  # leave defaults
        sources = sorted({_CODE_TO_LABEL.get(p["from"], p["from"]) for p in self._language_pairs})
        sources = ["Auto-detect"] + sources
        self._option_source_lang.configure(values=sources)
        self._source_lang_var.set("Auto-detect")
        self._on_source_lang_change("Auto-detect")
        # Also populate Translate tab dropdowns
        non_auto = [s for s in sources if s != "Auto-detect"]
        if non_auto:
            self._tl_option_source.configure(values=non_auto)
            self._tl_source_var.set(non_auto[0])
            self._tl_option_target.configure(values=non_auto)
            if len(non_auto) > 1:
                self._tl_target_var.set(non_auto[1])
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
    # Stage label cycling
    # ------------------------------------------------------------------

    def _advance_stage(self, idx: int) -> None:
        if self._closing:
            return
        if idx < len(_STAGE_LABELS):
            self._stage_label.configure(text=_STAGE_LABELS[idx])
            self._stage_timer = self.after(2500, self._advance_stage, idx + 1)

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

            messagebox.showerror("Missing output", "Please choose an output .srt path.")
            return

        # Capture StringVar values on the main thread (Tkinter is not thread-safe)
        src_selected = self._source_lang_var.get()
        src_lang = None if src_selected in ("Auto-detect", "") else _label_to_code(src_selected)
        tgt_selected = self._target_lang_var.get()
        tgt_lang: str | None = None if tgt_selected in ("No target", "") else _label_to_code(tgt_selected)

        self._btn_generate.configure(state="disabled")
        self._btn_clear.configure(state="disabled")
        self._entry_input.configure(state="disabled")
        self._entry_output.configure(state="disabled")
        self._option_source_lang.configure(state="disabled")
        self._option_target_lang.configure(state="disabled")
        self._option_output_format.configure(state="disabled")
        self._btn_browse_input.configure(state="disabled")
        self._btn_browse_output.configure(state="disabled")
        self._progress_bar.grid()
        self._progress_bar.start()
        self._advance_stage(0)

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
            args=(input_path, output_path, src_lang, tgt_lang),
            daemon=True,
        )
        thread.start()

    def _run_api_call(
        self,
        input_path: str,
        output_path: str,
        src_lang: str | None,
        tgt_lang: str | None,
    ) -> None:
        import requests as req  # noqa: PLC0415

        try:
            params: dict[str, str] = {}
            if src_lang:
                params["source_lang"] = src_lang
            if tgt_lang:
                params["target_lang"] = tgt_lang

            with open(input_path, "rb") as fh:
                video_name = Path(input_path).name
                resp = req.post(
                    f"{_BASE_URL}/subtitles",
                    files={"file": (video_name, fh, "application/octet-stream")},
                    params=params,
                    timeout=3600,
                )

            if resp.status_code == 200:
                Path(output_path).write_bytes(resp.content)
                # Convert to SSA if user selected SSA format
                final_path = output_path
                if self._output_format_var.get() == "SSA":
                    from gensubtitles.core.srt_writer import convert_srt_to_ssa  # noqa: PLC0415

                    ssa_out = Path(output_path).with_suffix(".ssa")
                    convert_srt_to_ssa(output_path, ssa_out)
                    Path(output_path).unlink(missing_ok=True)
                    final_path = str(ssa_out)
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

        self._progress_bar.stop()
        self._progress_bar.grid_remove()
        self._btn_generate.configure(state="normal")
        self._entry_input.configure(state="normal")
        self._entry_output.configure(state="normal")
        self._option_source_lang.configure(state="normal")
        self._option_target_lang.configure(state="normal")
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
        self._tl_progress_bar.stop()
        self._tl_progress_bar.grid_remove()
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

            for _ in range(60):  # up to 60 seconds
                time.sleep(1)
                try:
                    req.get(f"{_BASE_URL}/languages", timeout=1)
                    if not self._closing:
                        self.after(0, self._populate_language_dropdowns)
                    return
                except Exception:  # noqa: BLE001
                    continue

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        threading.Thread(target=_wait_for_server, daemon=True).start()

    def _stop_server(self) -> None:
        if self._server is not None:
            self._server.should_exit = True

    def on_closing(self) -> None:
        self._closing = True
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
