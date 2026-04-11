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

_LANG_MAP: dict[str, str] = {"Spanish": "es", "English": "en"}

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
        self.minsize(540, 440)

        # String variables for entry widgets
        self._input_var = ctk.StringVar()
        self._output_var = ctk.StringVar()
        self._source_lang_var = ctk.StringVar()
        self._target_lang_var = ctk.StringVar(value="Spanish")
        self._target_lang_other_var = ctk.StringVar()

        # Server references
        self._server = None
        self._stage_timer = None
        self._elapsed_timer = None
        self._elapsed_start: float = 0.0
        self._closing = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._start_server()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._frame = ctk.CTkFrame(self)
        self._frame.pack(fill="both", expand=True, padx=20, pady=20)

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

        # Row 2 — Source language (hidden — Whisper auto-detects)
        self._lbl_source_lang = ctk.CTkLabel(self._frame, text="Source language:")
        self._lbl_source_lang.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self._lbl_source_lang.grid_remove()
        self._entry_source_lang = ctk.CTkEntry(
            self._frame,
            textvariable=self._source_lang_var,
            placeholder_text="auto-detect",
        )
        self._entry_source_lang.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)
        self._entry_source_lang.grid_remove()

        # Row 3 — Target language dropdown
        ctk.CTkLabel(self._frame, text="Target language:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self._option_target_lang = ctk.CTkOptionMenu(
            self._frame,
            values=["Spanish", "English", "Other"],
            variable=self._target_lang_var,
            command=self._on_target_lang_change,
        )
        self._option_target_lang.grid(row=3, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 4 — Other free-text entry (hidden at rest)
        self._entry_target_lang_other = ctk.CTkEntry(
            self._frame,
            textvariable=self._target_lang_other_var,
            placeholder_text="language code, e.g. fr",
        )
        self._entry_target_lang_other.grid(row=4, column=1, columnspan=2, sticky="ew", pady=4)
        self._entry_target_lang_other.grid_remove()

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
        for var in (self._input_var, self._output_var, self._target_lang_other_var):
            var.trace_add("write", lambda *_: self._update_clear_state())

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
                self._output_var.set(str(Path(path).with_suffix(".srt")))

    def _browse_output(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT subtitles", "*.srt")],
        )
        if path:
            self._output_var.set(path)

    # ------------------------------------------------------------------
    # Clear button logic
    # ------------------------------------------------------------------

    def _on_target_lang_change(self, selection: str) -> None:
        """Show/hide the 'Other' free-text entry based on dropdown selection."""
        if selection == "Other":
            self._entry_target_lang_other.grid(
                row=4, column=1, columnspan=2, sticky="ew", pady=4
            )
        else:
            self._entry_target_lang_other.grid_remove()
        self._update_clear_state()

    def _update_clear_state(self) -> None:
        """Enable Clear button if any user-settable input field is non-empty/non-default; disable otherwise."""
        has_content = any(
            v.get()
            for v in (
                self._input_var,
                self._output_var,
                self._target_lang_other_var,
            )
        ) or self._target_lang_var.get() != "Spanish"
        self._btn_clear.configure(state="normal" if has_content else "disabled")

    def _on_clear(self) -> None:
        """Reset input fields; return dropdown to default and hide Other entry."""
        self._input_var.set("")
        self._output_var.set("")
        self._source_lang_var.set("")
        self._target_lang_var.set("Spanish")
        self._target_lang_other_var.set("")
        self._entry_target_lang_other.grid_remove()

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
        src_lang = self._source_lang_var.get().strip() or None
        selected = self._target_lang_var.get()
        if selected in _LANG_MAP:
            tgt_lang: str | None = _LANG_MAP[selected]
        else:  # "Other"
            tgt_lang = self._target_lang_other_var.get().strip() or None

        self._btn_generate.configure(state="disabled")
        self._btn_clear.configure(state="disabled")
        self._entry_input.configure(state="disabled")
        self._entry_output.configure(state="disabled")
        self._entry_source_lang.configure(state="disabled")
        self._option_target_lang.configure(state="disabled")
        self._entry_target_lang_other.configure(state="disabled")
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
        self._elapsed_label.grid(row=7, column=0, columnspan=3, pady=4)
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
                if not self._closing:
                    self.after(0, self._finish_generate, None, output_path)
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
        if self._elapsed_timer is not None:
            self.after_cancel(self._elapsed_timer)
            self._elapsed_timer = None

        self._progress_bar.stop()
        self._progress_bar.grid_remove()
        self._btn_generate.configure(state="normal")
        self._entry_input.configure(state="normal")
        self._entry_output.configure(state="normal")
        self._entry_source_lang.configure(state="normal")
        self._option_target_lang.configure(state="normal")
        self._entry_target_lang_other.configure(state="normal")
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

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

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
