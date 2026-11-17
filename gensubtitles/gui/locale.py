"""gensubtitles.gui.locale
~~~~~~~~~~~~~~~~~~~~~~~~~
Localisation string registry for the GenSubtitles desktop UI.

Extracted from gui/main.py to decouple language data from widget logic,
making it trivial to add new language pairs without touching GUI components.

Public API
----------
s(key)                — return the localised string for the active language
set_language(lang)    — set the active language code (e.g. "en", "es")
s_lang(key, lang)     — return a string for a specific language without
                        changing the active language state
LANGUAGES             — tuple of supported language codes
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Localisation string registry
# ---------------------------------------------------------------------------
_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Tab names
        "generate_tab":         "Generate",
        "translate_tab":        "Translate a file",
        # Generate tab
        "input_video_lbl":      "Video",
        "output_file_lbl":      "Subtitle file",
        "source_lang_lbl":      "Spoken language",
        "target_lang_lbl":      "Subtitle language",
        "engine_lbl":           "Translation engine",
        "output_format_lbl":    "Format",
        "generate_btn":         "Generate subtitles",
        "clear_btn":            "Clear",
        "keep_original":        "Keep original language",
        "detect_spoken":        "Detect",
        "cue_idle":             "Choose a video to generate subtitles.",
        "cue_saved":            "Subtitle saved",
        "cue_preview":          "This is how a subtitle line will look.",
        "cancel_btn":           "Cancel",
        "log_lbl":              "Log",
        "font_size_error":      "Font size must be a positive whole number.",
        "convert_format_btn":   "Convert format",
        "translate_file_btn":   "Translate subtitles",
        "settings_program":     "Program",
        "settings_caption":     "On-screen subtitle",
        "step_extract":         "Extract audio",
        "step_transcribe":      "Transcribe",
        "step_translate":       "Translate",
        "step_write":           "Write file",
        "step_status_waiting":  "Waiting",
        "step_status_done":     "Done",
        "server_failed":        "The speech model did not start. Restart the app.",
        "generation_cancelled": "Generation cancelled.",
        # Three-panel layout — Phase 999.29
        "panel_files_title":        "Initial Steps",
        "panel_process_title":      "Configuration",
        "panel_status_title":       "Control & Progress",
        "stepper_switch_lbl":       "Step-by-step mode",
        "work_dir_lbl":             "Work directory:",
        "generate_step_start_btn":  "Start Step-by-step",
        "clear_work_btn":           "Clear Work Files",
        "browse_btn":           "Browse\u2026",
        "save_as_btn":          "Save as\u2026",
        # Translate tab
        "input_sub_lbl":        "Subtitle to translate",
        "output_path_lbl":      "Saved file",
        "translate_btn":        "Translate subtitles",
        "convert_only_chk":     "Only change the format",
        # Settings panel
        "settings_header":      "Settings",
        "appearance_lbl":       "Appearance",
        "ui_lang_lbl":          "Interface language",
        "default_outdir_lbl":   "Folder for subtitle files",
        "save_btn":             "Save",
        "back_btn":             "Back",
        "subtitle_style_lbl":   "On-screen subtitle",
        "font_family_lbl":      "Font",
        "font_size_lbl":        "Size",
        "text_color_lbl":       "Text color",
        "outline_color_lbl":    "Outline color",
        "config_path_lbl":      "Settings file",
        "open_config_folder_btn": "Open Folder",
        # Menu bar
        "menu_settings":        "Settings",
        "menu_preferences":     "Preferences\u2026",
        "menu_help":            "Help",
        "menu_tutorial":        "Tutorial",
        "menu_languages":       "Available Languages",
        "menu_about":           "About GenSubtitles",
        # Dynamic status
        "starting_server":      "Preparing the speech model\u2026",
        "open_folder_btn":      "Open folder",
        "status_done":          "Subtitle saved",
        "status_translating":   "Translating\u2026",
        "status_converting":    "Converting\u2026",
        # Messagebox strings
        "msg_missing_input_title":      "Missing input",
        "msg_missing_input_video":      "Choose a video to generate subtitles.",
        "msg_missing_input_subtitle":   "Choose a subtitle file.",
        "msg_missing_output_title":     "Missing output",
        "msg_missing_output_subtitle":  "Choose where to save the subtitle file.",
        "msg_missing_output_path":      "Choose where to save the file.",
        "msg_generation_failed_title":  "Generation failed",
        "msg_translation_failed_title": "Translation failed",
        "msg_settings_error_title":     "Settings error",
        "msg_settings_error_body":      "Could not save settings: {error}",
        "msg_done_title":               "Done",
        "msg_saved_body":               "Saved: {path}",
        # Dialog strings
        "dlg_tutorial_title":   "GenSubtitles \u2014 Tutorial",
        "dlg_tutorial_close":   "Close",
        "dlg_langs_title":      "Installed Language Pairs",
        "dlg_langs_header":     "Installed Translation Pairs",
        "dlg_langs_empty":      (
            "No language pairs installed.\n"
            "Pairs are downloaded automatically on first translation."
        ),
        "dlg_langs_close":      "Close",
        "dlg_about_title":      "About GenSubtitles",
        "dlg_about_github":     "GitHub Project",
        "dlg_about_close":      "Close",
        # Phase 999.30 — 6-tab refactor
        # Tab names
        "extract_tab":              "Extract Audio",
        "transcribe_tab":           "Transcribe",
        "translate_step_tab":       "Translate",
        "write_tab":                "Write Subtitle",
        # Tab 1 new elements
        "panel_config_title":       "Configuration",
        "generate_clear_btn":       "Clear fields",
        # Tab 3 — Extract Audio
        "extract_input_lbl":        "Input video *:",
        "extract_output_lbl":       "Output audio file:",
        "extract_run_btn":          "Extract Audio",
        # Tab 4 — Transcribe
        "transcribe_input_lbl":     "Input audio *:",
        "transcribe_run_btn":       "Transcribe",
        # Tab 5 — Translate (step)
        "translate_step_input_lbl": "Input transcription *:",
        "translate_step_run_btn":   "Translate",
        # Tab 6 — Write Subtitle
        "write_input_lbl":          "Input transcription *:",
        "write_output_lbl":         "Output subtitle *:",
        "write_run_btn":            "Write Subtitle",
        "dlg_tutorial_text": (
            "GenSubtitles turns a video into a subtitle file (.srt or .ssa) on this computer.\n"
            "After the speech model is installed, generation does not need an API key.\n\n"
            "Generate\n"
            "Choose a video. The subtitle path fills in from the file name.\n"
            "Spoken language can stay on Detect. Subtitle language can stay on "
            "Keep original language, or you can pick another language.\n"
            "Format is SRT or SSA. Generate subtitles starts the whole job. "
            "The clock in the cue strip shows how long it has been running.\n\n"
            "Step by step\n"
            "Turn on Step-by-step mode to run extract, transcribe, translate, and write "
            "as four separate actions. Each button uses the video and languages already chosen.\n\n"
            "Translate a file\n"
            "Use this tab when you already have a subtitle file.\n"
            "Choose the file, the languages, and Translate subtitles.\n"
            "Only change the format switches the button to Convert format and skips translation.\n\n"
            "Language models\n"
            "Argos Translate downloads a language pair the first time you need it.\n"
            "Help, Available languages lists the pairs already on this computer.\n\n"
            "Settings\n"
            "Settings, Preferences sets appearance, interface language, and the folder for subtitle files.\n"
            "On-screen subtitle sets the font and colors used in the cue strip and in SSA files.\n\n"
            "If something fails\n"
            "FFmpeg not found: install FFmpeg and put it on PATH.\n"
            "Translation fails: the language pair may still be downloading. Check Help, Available languages.\n"
            "Blank subtitles: the default speech model is turbo (about 810 MB on first run). "
            "Confirm the download finished and that the video has an audio track.\n"
            "The speech model did not start: restart the app.\n\n"
            "Command line: see docs/cli-tutorial.md."
        ),
        # Phase 999.32 — separator, clear console, palette UI
        "log_separator":                "",
        "clear_console_on_clear_lbl":   "Clear the log when fields are cleared",
        "menu_color_palette":           "Color Palette\u2026",
        "palette_header":               "Color Palette",
        "palette_active_lbl":           "Active palette:",
        "palette_reset_btn":            "Reset to defaults",
        "palette_save_btn":             "Save",
        "palette_back_btn":             "Back",
        # Palette token labels
        "token_bg":                     "Background",
        "token_surface":                "Surface",
        "token_input_bg":               "Field background",
        "token_btn_primary_text":       "Primary button text",
        "token_time":                   "Timecode",
        "token_text_primary":           "Primary text",
        "token_text_secondary":         "Secondary text",
        "token_accent":                 "Primary button",
        "token_accent_hov":             "Primary button hover",
        "token_secondary":              "Secondary button",
        "token_secondary_hov":          "Secondary button hover",
        "token_btn_secondary_text":     "Secondary button text",
        "token_progress_idle":          "Progress idle",
        "token_progress_proc":          "Progress active",
        "token_progress_done":          "Progress done",
        "token_progress_err":           "Progress error",
        "token_menu_bg":                "Menu background",
        "token_menu_fg":                "Menu text",
        "token_menu_active_bg":         "Menu active background",
        # Log messages — warnings (D-07)
        "log_warn_no_input_video":      "Choose a video to generate subtitles.",
        "log_warn_no_input_audio":      "Extract audio before transcribing.",
        "log_warn_no_input_subtitle":   "Choose a subtitle file.",
        "log_warn_not_wav":             "Transcription needs a .wav file.",
        "log_warn_output_not_wav":      "The audio file must use a .wav extension.",
        "log_warn_no_output_dir":       "Choose a folder for the subtitle file.",
        "log_warn_no_target_lang":      "Choose a subtitle language other than the original.",
        "log_warn_no_input_transcription": "Transcribe the audio before translating.",
        "log_warn_no_input_file":       "Choose a file first.",
        "log_warn_file_not_found":      "That file was not found.",
        "log_step_success_extract":     "Audio extracted.",
        "log_step_success_transcribe":  "Transcription complete.",
        "log_step_success_translate":   "Translation complete.",
        "log_step_success_write":       "Subtitle written:",
        "log_audio_ready":              "Audio ready to transcribe:",
        "log_transcript_ready":         "Transcript ready to translate:",
        "log_translation_ready":        "Translation ready to write:",
        "log_kept_original":            "Keeping the original language. Nothing to translate.",
        "log_running_step":             "Running:",
        "log_error_generic":            "Error:",
        "log_error_extract":            "Extract failed:",
        "log_error_transcribe":         "Transcription failed:",
        "log_error_translate":          "Translation failed:",
        "log_error_write":              "Write failed:",
        "log_error_cannot_apply_output_name": "Could not apply the output name:",
    },
    "es": {
        # Tab names
        "generate_tab":         "Generar",
        "translate_tab":        "Traducir un archivo",
        # Generate tab
        "input_video_lbl":      "Vídeo",
        "output_file_lbl":      "Archivo de subtítulos",
        "source_lang_lbl":      "Idioma hablado",
        "target_lang_lbl":      "Idioma del subtítulo",
        "engine_lbl":           "Motor de traducción",
        "output_format_lbl":    "Formato",
        "generate_btn":         "Generar subtítulos",
        "clear_btn":            "Limpiar",
        "keep_original":        "Dejar el idioma original",
        "detect_spoken":        "Detectar",
        "cue_idle":             "Elige un vídeo para generar los subtítulos.",
        "cue_saved":            "Subtítulo guardado",
        "cue_preview":          "Así se verá el subtítulo.",
        "cancel_btn":           "Cancelar",
        "log_lbl":              "Registro",
        "font_size_error":      "El tamaño de la fuente tiene que ser un número entero positivo.",
        "convert_format_btn":   "Convertir formato",
        "translate_file_btn":   "Traducir subtítulos",
        "settings_program":     "Programa",
        "settings_caption":     "Subtítulo en pantalla",
        "step_extract":         "Extraer audio",
        "step_transcribe":      "Transcribir",
        "step_translate":       "Traducir",
        "step_write":           "Escribir archivo",
        "step_status_waiting":  "En espera",
        "step_status_done":     "Listo",
        "server_failed":        "El modelo de voz no arrancó. Reinicia la aplicación.",
        "generation_cancelled": "Generación cancelada.",
        # Three-panel layout — Phase 999.29
        "panel_files_title":        "Pasos iniciales",
        "panel_process_title":      "Configuraci\u00f3n",
        "panel_status_title":       "Control y Progreso",
        "stepper_switch_lbl":       "Modo paso a paso",
        "work_dir_lbl":             "Directorio de trabajo:",
        "generate_step_start_btn":  "Iniciar Proceso Paso a Paso",
        "clear_work_btn":           "Limpiar archivos de trabajo",
        "browse_btn":           "Explorar\u2026",
        "save_as_btn":          "Guardar como\u2026",
        # Translate tab
        "input_sub_lbl":        "Subtítulo a traducir",
        "output_path_lbl":      "Archivo guardado",
        "translate_btn":        "Traducir subtítulos",
        "convert_only_chk":     "Solo cambiar el formato",
        # Settings panel
        "settings_header":      "Configuración",
        "appearance_lbl":       "Apariencia",
        "ui_lang_lbl":          "Idioma de la interfaz",
        "default_outdir_lbl":   "Carpeta de los subtítulos",
        "save_btn":             "Guardar",
        "back_btn":             "Volver",
        "subtitle_style_lbl":   "Subtítulo en pantalla",
        "font_family_lbl":      "Fuente",
        "font_size_lbl":        "Tamaño",
        "text_color_lbl":       "Color del texto",
        "outline_color_lbl":    "Color del contorno",
        "config_path_lbl":      "Archivo de ajustes",
        "open_config_folder_btn": "Abrir carpeta",
        # Menu bar
        "menu_settings":        "Configuración",
        "menu_preferences":     "Preferencias\u2026",
        "menu_help":            "Ayuda",
        "menu_tutorial":        "Tutorial",
        "menu_languages":       "Idiomas disponibles",
        "menu_about":           "Acerca de GenSubtitles",
        # Dynamic status
        "starting_server":      "Preparando el modelo de voz\u2026",
        "open_folder_btn":      "Abrir carpeta",
        "status_done":          "Subtítulo guardado",
        "status_translating":   "Traduciendo\u2026",
        "status_converting":    "Convirtiendo\u2026",
        # Messagebox strings
        "msg_missing_input_title":      "Entrada faltante",
        "msg_missing_input_video":      "Elige un vídeo para generar los subtítulos.",
        "msg_missing_input_subtitle":   "Elige un archivo de subtítulos.",
        "msg_missing_output_title":     "Salida faltante",
        "msg_missing_output_subtitle":  "Elige dónde guardar el archivo de subtítulos.",
        "msg_missing_output_path":      "Elige dónde guardar el archivo.",
        "msg_generation_failed_title":  "Generación fallida",
        "msg_translation_failed_title": "Traducción fallida",
        "msg_settings_error_title":     "Error de configuración",
        "msg_settings_error_body":      "No se pudo guardar la configuración: {error}",
        "msg_done_title":               "Listo",
        "msg_saved_body":               "Guardado: {path}",
        # Dialog strings
        "dlg_tutorial_title":   "GenSubtitles \u2014 Gu\u00eda",
        "dlg_tutorial_close":   "Cerrar",
        "dlg_langs_title":      "Pares de idioma instalados",
        "dlg_langs_header":     "Pares de traducci\u00f3n instalados",
        "dlg_langs_empty":      (
            "No hay pares de idioma instalados.\n"
            "Se descargan autom\u00e1ticamente en la primera traducci\u00f3n."
        ),
        "dlg_langs_close":      "Cerrar",
        "dlg_about_title":      "Acerca de GenSubtitles",
        "dlg_about_github":     "Proyecto en GitHub",
        "dlg_about_close":      "Cerrar",
        # Phase 999.30 — 6-tab refactor
        # Nombres de tabs
        "extract_tab":              "Extraer Audio",
        "transcribe_tab":           "Transcribir",
        "translate_step_tab":       "Traducci\u00f3n",
        "write_tab":                "Escribir Subt\u00edtulo",
        # Tab 1 nuevos elementos
        "panel_config_title":       "Configuraci\u00f3n",
        "generate_clear_btn":       "Limpiar campos",
        # Tab 3 — Extraer Audio
        "extract_input_lbl":        "Video de entrada *:",
        "extract_output_lbl":       "Archivo de audio de salida:",
        "extract_run_btn":          "Extraer Audio",
        # Tab 4 — Transcribir
        "transcribe_input_lbl":     "Audio de entrada *:",
        "transcribe_run_btn":       "Transcribir",
        # Tab 5 — Traducci\u00f3n (paso)
        "translate_step_input_lbl": "Transcripci\u00f3n de entrada *:",
        "translate_step_run_btn":   "Traducir",
        # Tab 6 — Escribir Subt\u00edtulo
        "write_input_lbl":          "Transcripci\u00f3n de entrada *:",
        "write_output_lbl":         "Subt\u00edtulo de salida *:",
        "write_run_btn":            "Escribir Subt\u00edtulo",
        "dlg_tutorial_text": (
            "GenSubtitles convierte un vídeo en un archivo de subtítulos (.srt o .ssa) en este equipo.\n"
            "Cuando el modelo de voz ya está instalado, generar no pide una clave de API.\n\n"
            "Generar\n"
            "Elige un vídeo. La ruta del subtítulo se completa con el nombre del archivo.\n"
            "El idioma hablado puede quedarse en Detectar. El idioma del subtítulo puede quedarse en "
            "Dejar el idioma original, o puedes elegir otro.\n"
            "El formato es SRT o SSA. Generar subtítulos hace el trabajo completo. "
            "El reloj de la franja muestra cuánto lleva.\n\n"
            "Paso a paso\n"
            "Activa el modo paso a paso para extraer, transcribir, traducir y escribir "
            "como cuatro acciones. Cada botón usa el vídeo y los idiomas ya elegidos.\n\n"
            "Traducir un archivo\n"
            "Usa esta pestaña cuando ya tienes un subtítulo.\n"
            "Elige el archivo, los idiomas y Traducir subtítulos.\n"
            "Solo cambiar el formato pasa el botón a Convertir formato y no traduce.\n\n"
            "Modelos de idioma\n"
            "Argos Translate descarga un par de idiomas la primera vez que hace falta.\n"
            "Ayuda, Idiomas disponibles lista los pares que ya están en este equipo.\n\n"
            "Ajustes\n"
            "Configuración, Preferencias define la apariencia, el idioma de la interfaz y la carpeta de los subtítulos.\n"
            "Subtítulo en pantalla define la fuente y los colores de la franja y de los archivos SSA.\n\n"
            "Si algo falla\n"
            "FFmpeg no encontrado: instala FFmpeg y añádelo al PATH.\n"
            "La traducción falla: el par puede seguir descargándose. Revisa Ayuda, Idiomas disponibles.\n"
            "Subtítulos en blanco: el modelo de voz predeterminado es turbo (unos 810 MB la primera vez). "
            "Confirma que la descarga terminó y que el vídeo tiene audio.\n"
            "El modelo de voz no arrancó: reinicia la aplicación.\n\n"
            "Línea de comandos: consulta docs/cli-tutorial.md."
        ),
        "log_separator":                "",
        "clear_console_on_clear_lbl":   "Vaciar el registro al limpiar los campos",
        "menu_color_palette":           "Paleta de colores\u2026",
        "palette_header":               "Paleta de colores",
        "palette_active_lbl":           "Paleta activa:",
        "palette_reset_btn":            "Restablecer",
        "palette_save_btn":             "Guardar",
        "palette_back_btn":             "Volver",
        # Etiquetas de tokens
        "token_bg":                     "Fondo",
        "token_surface":                "Superficie",
        "token_input_bg":               "Fondo de los campos",
        "token_btn_primary_text":       "Texto del botón primario",
        "token_time":                   "Código de tiempo",
        "token_text_primary":           "Texto principal",
        "token_text_secondary":         "Texto secundario",
        "token_accent":                 "Bot\u00f3n primario",
        "token_accent_hov":             "Bot\u00f3n primario (hover)",
        "token_secondary":              "Bot\u00f3n secundario",
        "token_secondary_hov":          "Bot\u00f3n secundario (hover)",
        "token_btn_secondary_text":     "Texto bot\u00f3n secundario",
        "token_progress_idle":          "Progreso inactivo",
        "token_progress_proc":          "Progreso activo",
        "token_progress_done":          "Progreso completado",
        "token_progress_err":           "Progreso error",
        "token_menu_bg":                "Fondo men\u00fa",
        "token_menu_fg":                "Texto men\u00fa",
        "token_menu_active_bg":         "Fondo men\u00fa activo",
        # Mensajes de log — advertencias (D-07)
        "log_warn_no_input_video":      "Elige un vídeo para generar los subtítulos.",
        "log_warn_no_input_audio":      "Extrae el audio antes de transcribir.",
        "log_warn_no_input_subtitle":   "Elige un archivo de subtítulos.",
        "log_warn_not_wav":             "La transcripción necesita un archivo .wav.",
        "log_warn_output_not_wav":      "El audio debe usar la extensión .wav.",
        "log_warn_no_output_dir":       "Elige una carpeta para el archivo de subtítulos.",
        "log_warn_no_target_lang":      "Elige un idioma de subtítulo distinto del original.",
        "log_warn_no_input_transcription": "Transcribe el audio antes de traducir.",
        "log_warn_no_input_file":       "Elige un archivo primero.",
        "log_warn_file_not_found":      "Ese archivo no se encontró.",
        "log_step_success_extract":     "Audio extraído.",
        "log_step_success_transcribe":  "Transcripción lista.",
        "log_step_success_translate":   "Traducción lista.",
        "log_step_success_write":       "Subtítulo escrito:",
        "log_audio_ready":              "Audio listo para transcribir:",
        "log_transcript_ready":         "Transcripción lista para traducir:",
        "log_translation_ready":        "Traducción lista para escribir:",
        "log_kept_original":            "Se deja el idioma original. No hay nada que traducir.",
        "log_running_step":             "En curso:",
        "log_error_generic":            "Error:",
        "log_error_extract":            "La extracción falló:",
        "log_error_transcribe":         "La transcripción falló:",
        "log_error_translate":          "La traducción falló:",
        "log_error_write":              "La escritura falló:",
        "log_error_cannot_apply_output_name": "No se pudo aplicar el nombre de salida:",
    },
}

LANGUAGES: tuple[str, ...] = tuple(_STRINGS.keys())

_active_lang: str = "en"


def set_language(lang: str) -> None:
    """Set the active language for subsequent ``s()`` calls."""
    global _active_lang
    _active_lang = lang


def s(key: str) -> str:
    """Return the localised string for *key* in the active language."""
    locale_dict = _STRINGS.get(_active_lang, _STRINGS["en"])
    return locale_dict.get(key, _STRINGS["en"].get(key, key))


def s_lang(key: str, lang: str) -> str:
    """Return the localised string for *key* in *lang* without altering state."""
    locale_dict = _STRINGS.get(lang, _STRINGS["en"])
    return locale_dict.get(key, _STRINGS["en"].get(key, key))
