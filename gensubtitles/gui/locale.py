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
        "generate_tab":         "Generate Subtitles",
        "translate_tab":        "Translate Subtitles",
        # Generate tab
        "input_video_lbl":      "Input video *:",
        "output_file_lbl":      "Output file *:",
        "source_lang_lbl":      "Source language:",
        "target_lang_lbl":      "Target language:",
        "engine_lbl":           "Translation engine:",
        "output_format_lbl":    "Output format:",
        "generate_btn":         "Generate Subtitles",
        "clear_btn":            "Clear",
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
        "input_sub_lbl":        "Input subtitle *:",
        "output_path_lbl":      "Output path *:",
        "translate_btn":        "Translate / Convert",
        "convert_only_chk":     "Convert only (no translation \u2014 change format only)",
        # Settings panel
        "settings_header":      "Settings",
        "appearance_lbl":       "Appearance Mode:",
        "ui_lang_lbl":          "UI Language:",
        "default_outdir_lbl":   "Default output dir:",
        "save_btn":             "Save",
        "back_btn":             "Back",
        "subtitle_style_lbl":   "Subtitle Style",
        "font_family_lbl":      "Font family:",
        "font_size_lbl":        "Font size:",
        "text_color_lbl":       "Text color:",
        "outline_color_lbl":    "Outline color:",
        "config_path_lbl":      "Config file:",
        "open_config_folder_btn": "Open Folder",
        # Menu bar
        "menu_settings":        "Settings",
        "menu_preferences":     "Preferences\u2026",
        "menu_help":            "Help",
        "menu_tutorial":        "Tutorial",
        "menu_languages":       "Available Languages",
        "menu_about":           "About GenSubtitles",
        # Dynamic status
        "starting_server":      "\u23f3 Starting server\u2026",
        "open_folder_btn":      "Open Folder",
        "status_done":          "\u2713 Done",
        "status_translating":   "Translating\u2026",
        "status_converting":    "Converting\u2026",
        # Messagebox strings
        "msg_missing_input_title":      "Missing input",
        "msg_missing_input_video":      "Please select an input video file.",
        "msg_missing_input_subtitle":   "Please select a subtitle file.",
        "msg_missing_output_title":     "Missing output",
        "msg_missing_output_subtitle":  "Please choose an output subtitle path.",
        "msg_missing_output_path":      "Please choose an output path.",
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
            "GenSubtitles \u2014 Usage Guide\n"
            "==========================\n\n"
            "OVERVIEW\n"
            "--------\n"
            "GenSubtitles converts video files to subtitle files (.srt or .ssa) entirely offline.\n"
            "No internet connection or API keys are required once language models are installed.\n\n"
            "GENERATE SUBTITLES TAB\n"
            "-----------------------\n"
            '1. Click "Browse\u2026" next to "Input video" and select your video file (.mp4, .mkv, .avi, .mov, .webm).\n'
            "2. The output subtitle path is auto-filled based on the video filename. Change it if needed.\n"
            '3. Select a Source Language (or leave as Auto-detect \u2014 Whisper will identify the language automatically).\n'
            '4. Select a Target Language if you want translation. Leave as "No target" to keep the original language.\n'
            "5. Choose Output Format: SRT (most compatible) or SSA (richer styling).\n"
            '6. Click "Generate Subtitles". Progress is shown with the elapsed timer and a progress bar.\n'
            "7. When finished, the subtitle file is saved to the chosen output path.\n\n"
            "TRANSLATE SUBTITLES TAB\n"
            "------------------------\n"
            "Use this tab if you already have a subtitle file and only need to translate or convert it.\n\n"
            '1. Click "Browse\u2026" next to "Input subtitle" and select a .srt or .ssa file.\n'
            "2. The output path is auto-filled as <filename>_translated.<ext>.\n"
            "3. Select the source language of the subtitle file.\n"
            "4. Select the target language for translation.\n"
            '5. (Optional) Check "Convert only" to change file format without translation.\n'
            '6. Click "Translate / Convert".\n\n'
            "LANGUAGE MODEL INSTALLATION\n"
            "-----------------------------\n"
            "GenSubtitles uses Argos Translate for offline translation.\n"
            "Language models are downloaded automatically on first use (internet required for download only).\n"
            "After downloading, all translation works offline.\n\n"
            "Use Help > Available Languages to see which pairs are currently installed.\n\n"
            "SETTINGS\n"
            "---------\n"
            "Access via the Settings menu > Preferences.\n"
            "- Appearance Mode: Light, Dark, or follow System setting.\n"
            "- UI Language: English or Spanish.\n"
            "- Default output directory: pre-fills output path (leave blank to use same folder as input).\n\n"
            "TROUBLESHOOTING\n"
            "----------------\n"
            "\u2022 \"FFmpeg not found\" \u2014 Install FFmpeg and ensure it is in your system PATH.\n"
            "\u2022 Translation fails \u2014 The selected language pair may not be installed. Check Help > Available Languages.\n"
            "\u2022 Subtitles are blank \u2014 The default speech model is `medium` (~1.5 GB first-run download). "
            "If this is the first run, make sure the model download completed successfully and that you had internet "
            "access during setup. Also check whether the video has an audio track.\n"
            "\u2022 API connection refused \u2014 The background server failed to start. Restart the application.\n"
            "\n"
            "CLI users: see docs/cli-tutorial.md for a step-by-step terminal walkthrough."
        ),
        # Phase 999.32 — separator, clear console, palette UI
        "log_separator":                "══════════════════════════════════════════════════",
        "clear_console_on_clear_lbl":   "Clear console on Clear fields:",
        "menu_color_palette":           "Color Palette\u2026",
        "palette_header":               "Color Palette",
        "palette_active_lbl":           "Active palette:",
        "palette_reset_btn":            "Reset to defaults",
        "palette_save_btn":             "Save",
        "palette_back_btn":             "Back",
        # Palette token labels
        "token_bg":                     "Background",
        "token_surface":                "Surface / Card",
        "token_input_bg":               "Input / Console bg",
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
        "log_warn_no_input_video":      "\u26a0\ufe0f Please select an input video file.",
        "log_warn_no_input_audio":      "\u26a0\ufe0f Please select an input audio file.",
        "log_warn_no_input_subtitle":   "\u26a0\ufe0f Please select a subtitle file.",
        "log_warn_not_wav":             "\u26a0\ufe0f Transcribe step requires a .wav file.",
        "log_warn_output_not_wav":      "\u26a0\ufe0f Output audio file must use .wav extension.",
        "log_warn_no_output_dir":       "\u26a0\ufe0f Cannot determine output directory.",
        "log_warn_no_target_lang":      "\u26a0\ufe0f Please select a target language.",
        "log_warn_no_input_transcription": "\u26a0\ufe0f Please select a transcription file.",
        "log_warn_no_input_file":       "\u26a0\ufe0f Please select an input file.",
        "log_warn_file_not_found":      "\u26a0\ufe0f Selected file was not found.",
        # Log messages — progress / success (D-07)
        "log_step_success_extract":     "\u2713 Audio extracted successfully.",
        "log_step_success_transcribe":  "\u2713 Transcription complete.",
        "log_step_success_translate":   "\u2713 Translation complete.",
        "log_step_success_write":       "\u2713 Subtitle written:",
        "log_prefill_tab4":             "\u2192 Pre-filled Tab 4 input:",
        "log_prefill_tab5":             "\u2192 Pre-filled Tab 5 input:",
        "log_prefill_tab6":             "\u2192 Pre-filled Tab 6 input:",
        # Log messages — errors (D-07)
        "log_error_extract":            "\u2717 Extract failed:",
        "log_error_transcribe":         "\u2717 Transcription failed:",
        "log_error_translate":          "\u2717 Translation failed:",
        "log_error_write":              "\u2717 Write failed:",
        "log_error_cannot_apply_output_name": "\u26a0\ufe0f Could not apply custom output name:",
    },
    "es": {
        # Tab names
        "generate_tab":         "Generar Subtítulos",
        "translate_tab":        "Traducir Subtítulos",
        # Generate tab
        "input_video_lbl":      "Video de entrada *:",
        "output_file_lbl":      "Archivo de salida *:",
        "source_lang_lbl":      "Idioma de origen:",
        "target_lang_lbl":      "Idioma de destino:",
        "engine_lbl":           "Motor de traducción:",
        "output_format_lbl":    "Formato de salida:",
        "generate_btn":         "Generar Subtítulos",
        "clear_btn":            "Limpiar",
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
        "input_sub_lbl":        "Subtítulo de entrada *:",
        "output_path_lbl":      "Ruta de salida *:",
        "translate_btn":        "Traducir / Convertir",
        "convert_only_chk":     "Solo convertir (sin traducción \u2014 solo cambiar formato)",
        # Settings panel
        "settings_header":      "Configuración",
        "appearance_lbl":       "Modo de apariencia:",
        "ui_lang_lbl":          "Idioma de la interfaz:",
        "default_outdir_lbl":   "Directorio de salida predeterminado:",
        "save_btn":             "Guardar",
        "back_btn":             "Volver",
        "subtitle_style_lbl":   "Estilo de subtítulo",
        "font_family_lbl":      "Familia de fuente:",
        "font_size_lbl":        "Tamaño de fuente:",
        "text_color_lbl":       "Color del texto:",
        "outline_color_lbl":    "Color del borde:",
        "config_path_lbl":      "Archivo de config:",
        "open_config_folder_btn": "Abrir carpeta",
        # Menu bar
        "menu_settings":        "Configuración",
        "menu_preferences":     "Preferencias\u2026",
        "menu_help":            "Ayuda",
        "menu_tutorial":        "Tutorial",
        "menu_languages":       "Idiomas disponibles",
        "menu_about":           "Acerca de GenSubtitles",
        # Dynamic status
        "starting_server":      "\u23f3 Iniciando servidor\u2026",
        "open_folder_btn":      "Abrir carpeta",
        "status_done":          "\u2713 Listo",
        "status_translating":   "Traduciendo\u2026",
        "status_converting":    "Convirtiendo\u2026",
        # Messagebox strings
        "msg_missing_input_title":      "Entrada faltante",
        "msg_missing_input_video":      "Por favor selecciona un archivo de video de entrada.",
        "msg_missing_input_subtitle":   "Por favor selecciona un archivo de subtítulos.",
        "msg_missing_output_title":     "Salida faltante",
        "msg_missing_output_subtitle":  "Por favor elige una ruta de salida para los subtítulos.",
        "msg_missing_output_path":      "Por favor elige una ruta de salida.",
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
            "GenSubtitles \u2014 Gu\u00eda de uso\n"
            "==========================\n\n"
            "RESUMEN\n"
            "-------\n"
            "GenSubtitles convierte archivos de video en archivos de subt\u00edtulos (.srt o .ssa) completamente sin conexi\u00f3n.\n"
            "No se requiere conexi\u00f3n a internet ni claves de API una vez instalados los modelos de idioma.\n\n"
            "PESTA\u00d1A GENERAR SUBT\u00cdTULOS\n"
            "---------------------------\n"
            '1. Haz clic en "Explorar\u2026" junto a "Video de entrada" y selecciona tu archivo de video (.mp4, .mkv, .avi, .mov, .webm).\n'
            "2. La ruta del subt\u00edtulo de salida se completa autom\u00e1ticamente seg\u00fan el nombre del video. C\u00e1mbiala si es necesario.\n"
            "3. Selecciona un Idioma de origen (o d\u00e9jalo en Detecci\u00f3n autom\u00e1tica \u2014 Whisper identificar\u00e1 el idioma autom\u00e1ticamente).\n"
            '4. Selecciona un Idioma de destino si deseas traducci\u00f3n. D\u00e9jalo en "Sin destino" para conservar el idioma original.\n'
            "5. Elige el Formato de salida: SRT (m\u00e1s compatible) o SSA (con estilos m\u00e1s ricos).\n"
            '6. Haz clic en "Generar Subt\u00edtulos". El progreso se muestra con el contador de tiempo transcurrido y una barra de progreso.\n'
            "7. Cuando termina, el archivo de subt\u00edtulos se guarda en la ruta de salida elegida.\n\n"
            "PESTA\u00d1A TRADUCIR SUBT\u00cdTULOS\n"
            "----------------------------\n"
            "Usa esta pesta\u00f1a si ya tienes un archivo de subt\u00edtulos y solo necesitas traducirlo o convertirlo.\n\n"
            '1. Haz clic en "Explorar\u2026" junto a "Subt\u00edtulo de entrada" y selecciona un archivo .srt o .ssa.\n'
            "2. La ruta de salida se completa autom\u00e1ticamente como <nombre>_translated.<ext>.\n"
            "3. Selecciona el idioma de origen del archivo de subt\u00edtulos.\n"
            "4. Selecciona el idioma de destino para la traducci\u00f3n.\n"
            '5. (Opcional) Marca "Solo convertir" para cambiar el formato del archivo sin traducci\u00f3n.\n'
            '6. Haz clic en "Traducir / Convertir".\n\n'
            "INSTALACI\u00d3N DE MODELOS DE IDIOMA\n"
            "----------------------------------\n"
            "GenSubtitles usa Argos Translate para traducci\u00f3n sin conexi\u00f3n.\n"
            "Los modelos de idioma se descargan autom\u00e1ticamente en el primer uso (se requiere internet solo para la descarga).\n"
            "Despu\u00e9s de la descarga, toda la traducci\u00f3n funciona sin conexi\u00f3n.\n\n"
            "Usa Ayuda > Idiomas disponibles para ver qu\u00e9 pares est\u00e1n instalados actualmente.\n\n"
            "CONFIGURACI\u00d3N\n"
            "--------------\n"
            "Accede desde el men\u00fa Configuraci\u00f3n > Preferencias.\n"
            "- Modo de apariencia: Claro, Oscuro o seguir la configuraci\u00f3n del sistema.\n"
            "- Idioma de la interfaz: Ingl\u00e9s o Espa\u00f1ol.\n"
            "- Directorio de salida predeterminado: pre-completa la ruta de salida (dejar en blanco para usar la misma carpeta que la entrada).\n\n"
            "SOLUCI\u00d3N DE PROBLEMAS\n"
            "----------------------\n"
            "\u2022 \"FFmpeg no encontrado\" \u2014 Instala FFmpeg y aseg\u00farate de que est\u00e9 en el PATH del sistema.\n"
            "\u2022 La traducci\u00f3n falla \u2014 Es posible que el par de idiomas seleccionado no est\u00e9 instalado. Verifica en Ayuda > Idiomas disponibles.\n"
            "\u2022 Los subt\u00edtulos est\u00e1n en blanco \u2014 El modelo de voz predeterminado es `medium` (~1.5 GB, descarga en el primer uso). "
            "Si es la primera ejecuci\u00f3n, aseg\u00farate de que la descarga del modelo se complet\u00f3 correctamente y que ten\u00edas acceso "
            "a internet durante la configuraci\u00f3n. Tambi\u00e9n verifica si el video tiene pista de audio.\n"
            "\u2022 Conexi\u00f3n a la API rechazada \u2014 El servidor en segundo plano no se pudo iniciar. Reinicia la aplicaci\u00f3n.\n"
            "\n"
            "Usuarios de CLI: consulta docs/cli-tutorial.md para una gu\u00eda paso a paso en terminal."
        ),
        # Phase 999.32 — separador, consola limpia, paleta
        "log_separator":                "\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550",
        "clear_console_on_clear_lbl":   "Limpiar consola al limpiar campos:",
        "menu_color_palette":           "Paleta de colores\u2026",
        "palette_header":               "Paleta de colores",
        "palette_active_lbl":           "Paleta activa:",
        "palette_reset_btn":            "Restablecer",
        "palette_save_btn":             "Guardar",
        "palette_back_btn":             "Volver",
        # Etiquetas de tokens
        "token_bg":                     "Fondo",
        "token_surface":                "Superficie / Tarjeta",
        "token_input_bg":               "Fondo de entrada / consola",
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
        "log_warn_no_input_video":      "\u26a0\ufe0f Por favor selecciona un archivo de video de entrada.",
        "log_warn_no_input_audio":      "\u26a0\ufe0f Por favor selecciona un archivo de audio de entrada.",
        "log_warn_no_input_subtitle":   "\u26a0\ufe0f Por favor selecciona un archivo de subt\u00edtulos.",
        "log_warn_not_wav":             "\u26a0\ufe0f El paso de transcripci\u00f3n requiere un archivo .wav.",
        "log_warn_output_not_wav":      "\u26a0\ufe0f El archivo de audio de salida debe usar extensi\u00f3n .wav.",
        "log_warn_no_output_dir":       "\u26a0\ufe0f No se puede determinar el directorio de salida.",
        "log_warn_no_target_lang":      "\u26a0\ufe0f Por favor selecciona un idioma de destino.",
        "log_warn_no_input_transcription": "\u26a0\ufe0f Por favor selecciona un archivo de transcripci\u00f3n.",
        "log_warn_no_input_file":       "\u26a0\ufe0f Por favor selecciona un archivo de entrada.",
        "log_warn_file_not_found":      "\u26a0\ufe0f El archivo seleccionado no fue encontrado.",
        # Mensajes de log — progreso / éxito (D-07)
        "log_step_success_extract":     "\u2713 Audio extra\u00eddo correctamente.",
        "log_step_success_transcribe":  "\u2713 Transcripci\u00f3n completada.",
        "log_step_success_translate":   "\u2713 Traducci\u00f3n completada.",
        "log_step_success_write":       "\u2713 Subt\u00edtulo escrito:",
        "log_prefill_tab4":             "\u2192 Pre-llenado Tab 4 entrada:",
        "log_prefill_tab5":             "\u2192 Pre-llenado Tab 5 entrada:",
        "log_prefill_tab6":             "\u2192 Pre-llenado Tab 6 entrada:",
        # Mensajes de log — errores (D-07)
        "log_error_extract":            "\u2717 Extracci\u00f3n fallida:",
        "log_error_transcribe":         "\u2717 Transcripci\u00f3n fallida:",
        "log_error_translate":          "\u2717 Traducci\u00f3n fallida:",
        "log_error_write":              "\u2717 Escritura fallida:",
        "log_error_cannot_apply_output_name": "\u26a0\ufe0f No se pudo aplicar el nombre de salida personalizado:",
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
