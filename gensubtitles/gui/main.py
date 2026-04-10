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
import threading
from pathlib import Path

import customtkinter as ctk

logger = logging.getLogger(__name__)

# Appearance defaults
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

_BASE_URL = "http://127.0.0.1:8000"

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
        self._model_var = ctk.StringVar(value="small")
        self._device_var = ctk.StringVar(value="auto")
        self._source_lang_var = ctk.StringVar()
        self._target_lang_var = ctk.StringVar()

        # Server references
        self._server = None
        self._stage_timer = None

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
        ctk.CTkLabel(self._frame, text="Input video:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkEntry(self._frame, textvariable=self._input_var).grid(
            row=0, column=1, sticky="ew", pady=4
        )
        ctk.CTkButton(self._frame, text="Browse…", width=80, command=self._browse_input).grid(
            row=0, column=2, padx=(8, 0), pady=4
        )

        # Row 1 — Output SRT
        ctk.CTkLabel(self._frame, text="Output SRT:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkEntry(self._frame, textvariable=self._output_var).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ctk.CTkButton(self._frame, text="Save as…", width=80, command=self._browse_output).grid(
            row=1, column=2, padx=(8, 0), pady=4
        )

        # Row 2 — Model size
        ctk.CTkLabel(self._frame, text="Model size:").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkOptionMenu(
            self._frame,
            variable=self._model_var,
            values=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "turbo"],
        ).grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 3 — Device
        ctk.CTkLabel(self._frame, text="Device:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkOptionMenu(
            self._frame,
            variable=self._device_var,
            values=["auto", "cpu", "cuda"],
        ).grid(row=3, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 4 — Source language
        ctk.CTkLabel(self._frame, text="Source language:").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkEntry(
            self._frame,
            textvariable=self._source_lang_var,
            placeholder_text="auto-detect",
        ).grid(row=4, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 5 — Target language
        ctk.CTkLabel(self._frame, text="Target language:").grid(
            row=5, column=0, sticky="w", padx=(0, 8), pady=4
        )
        ctk.CTkEntry(
            self._frame,
            textvariable=self._target_lang_var,
            placeholder_text="(none — no translation)",
        ).grid(row=5, column=1, columnspan=2, sticky="ew", pady=4)

        # Row 6 — Generate button
        self._btn_generate = ctk.CTkButton(
            self._frame, text="Generate Subtitles", command=self._on_generate
        )
        self._btn_generate.grid(row=6, column=0, columnspan=3, pady=(12, 4), sticky="ew")

        # Row 7 — Progress bar (hidden initially)
        self._progress_bar = ctk.CTkProgressBar(self._frame, mode="indeterminate")
        self._progress_bar.grid(row=7, column=0, columnspan=3, pady=4, sticky="ew")
        self._progress_bar.grid_remove()

        # Row 8 — Stage label
        self._stage_label = ctk.CTkLabel(self._frame, text="")
        self._stage_label.grid(row=8, column=0, columnspan=3, pady=4)

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

    def _browse_output(self) -> None:
        from tkinter import filedialog  # noqa: PLC0415

        path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT subtitles", "*.srt")],
        )
        if path:
            self._output_var.set(path)

    # ------------------------------------------------------------------
    # Generate button logic (stub — implemented in plan 02)
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        pass  # TODO: implemented in plan 02

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
