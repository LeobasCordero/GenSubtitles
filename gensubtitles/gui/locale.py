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
            "\u2022 API connection refused \u2014 The background server failed to start. Restart the application."
        ),
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
            "\u2022 Conexi\u00f3n a la API rechazada \u2014 El servidor en segundo plano no se pudo iniciar. Reinicia la aplicaci\u00f3n."
        ),
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
