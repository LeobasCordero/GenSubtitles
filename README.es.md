# GenSubtitles

Generación automática de subtítulos de vídeo — offline, sin claves API requeridas. Transcribe y opcionalmente traduce el audio del vídeo utilizando Whisper y Argos Translate.

## Instalación

### 1. Dependencia del sistema: FFmpeg

FFmpeg debe estar instalado antes de ejecutar GenSubtitles.

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
winget install --id Gyan.FFmpeg
```

Verificar la instalación:
```bash
ffmpeg -version
```

### 2. Dependencias de Python

**Usando uv (recomendado):**
```bash
uv sync
```

**Usando pip:**
```bash
pip install -r requirements.txt
```

Requiere Python ≥ 3.11.

## Inicio rápido

Elige el modo de uso que mejor se adapte a tus necesidades:

- **GUI (escritorio):** `python main.py gui` — ver [Uso de la GUI](#uso-de-la-gui)
- **CLI (línea de comandos):** `python main.py --input video.mp4` — ver [Uso de CLI](#uso-de-cli)
- **API (servidor REST):** `python main.py serve` — ver [Uso de la API](#uso-de-la-api)

## Uso de la GUI

### Generar subtítulos

1. Inicia la aplicación: `python main.py gui`
2. Haz clic en **Browse…** y elige tu archivo de vídeo (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`).
3. Revisa el campo **Output**. Al elegir el vídeo con **Browse…**, la GUI lo pre-rellena automáticamente con una ruta de salida predeterminada; este campo debe tener siempre un valor. Si lo deseas, puedes cambiarlo por una ruta personalizada.
4. Establece el **Source Language** (déjalo en blanco para detección automática) y opcionalmente un **Target Language** para activar la traducción.
5. Haz clic en **Generate** para iniciar. El progreso se muestra en el área de estado.

> **Primera ejecución:** Whisper descargará el modelo configurado en el primer uso. El valor predeterminado es `medium` (~1,5 GB). En el servidor API, el tamaño del modelo se controla mediante la variable de entorno `WHISPER_MODEL_SIZE`; también puedes usar `small` (~470 MB) o `tiny` (~75 MB) para reducir la descarga inicial.

### Configuración de traducción

Usa los menús desplegables **Source Language** y **Target Language** del formulario principal:

- Deja **Source Language** en blanco para que Whisper detecte automáticamente el idioma hablado.
- Establece **Target Language** con un código ISO 639-1 (p. ej., `es` para español, `fr` para francés) para traducir los subtítulos tras la transcripción.
- Deja **Target Language** en blanco para omitir la traducción y obtener el subtítulo en el idioma original.

La traducción en la GUI usa **Argos Translate** por defecto (offline, sin clave API). Los modelos de Argos para cada par de idiomas se descargan la primera vez (~50–200 MB) y se almacenan en caché localmente.

> **Nota:** La GUI también puede usar **DeepL** y **LibreTranslate** cuando están configurados. Estos motores aparecen en el selector de motor solo si has definido `deepl_api_key` (para DeepL) o `libretranslate_url` (para LibreTranslate) en la configuración. Si no están configurados, la GUI usará Argos Translate. En CLI también puedes seleccionarlos explícitamente con `--engine deepl` o `--engine libretranslate`.

### Configurar la aplicación (Diálogo de Configuración)

Abre el diálogo de configuración desde el botón **Settings** o el menú de la aplicación para ajustar las preferencias. Los cambios se guardan automáticamente en `settings.json` (ver [Configuración](#configuración)).

| Ajuste | Opciones | Predeterminado |
|--------|---------|----------------|
| `appearance_mode` | `Light`, `Dark`, `System` | `System` |
| `ui_language` | `en`, `es` | `en` |
| `default_output_dir` | Ruta absoluta, o en blanco (mismo directorio que el vídeo) | _(en blanco)_ |
| `default_source_lang` | Código ISO 639-1, o en blanco (detección automática) | _(en blanco)_ |
| `target_lang` | Código ISO 639-1, o en blanco (sin traducción) | _(en blanco)_ |
| `deepl_api_key` | Clave gratuita de [deepl.com](https://deepl.com) | _(en blanco)_ |
| `libretranslate_url` | p. ej., `http://localhost:5000` | _(en blanco)_ |
| `libretranslate_api_key` | En blanco para instancias abiertas | _(en blanco)_ |

### Menú de Ayuda

El menú **Help** de la barra de menú ofrece:

- **Installed Language Pairs** — Lista todos los modelos de Argos Translate descargados y listos para uso offline.
- **Tutorial** — Abre una guía de inicio rápido.
- **About** — Muestra la versión de la aplicación y la información de licencia.

## Uso de CLI

> Para una guía paso a paso completa, consulta el [Tutorial de CLI](docs/cli-tutorial.md).

### generate (predeterminado)

```bash
python main.py --input video.mp4 [OPTIONS]
```

Genera subtítulos a partir de un archivo de vídeo y escribe un archivo `.srt` o `.ssa`.

| Flag | Descripción | Predeterminado |
|------|-------------|----------------|
| `--input`, `-i` | Vídeo de entrada (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`) | Requerido |
| `--output`, `-o` | Ruta de destino para el subtítulo | `<input>.<format>` |
| `--model`, `-m` | Modelo Whisper: `tiny` / `base` / `small` / `medium` / `large-v1` / `large-v2` / `large-v3` / `turbo` | `medium` |
| `--target-lang`, `-t` | Código ISO 639-1 de destino (p. ej., `es`). Omitir = sin traducción | Ninguno |
| `--source-lang`, `-s` | Código de idioma de origen. Omitir = detección automática de Whisper | Auto |
| `--device` | Dispositivo: `auto` / `cpu` / `cuda` | `auto` |
| `--format`, `-f` | Formato de salida: `srt` o `ssa` | `srt` |
| `--engine` | Motor de traducción: `argos` (offline, predeterminado) / `deepl` / `libretranslate` | `argos` |

**Ejemplos:**
```bash
# Básico — genera subtitles.srt en el mismo directorio que el vídeo
python main.py --input video.mp4

# Con traducción al español
python main.py --input video.mp4 --target-lang es

# Salida SSA con DeepL
python main.py --input video.mp4 --target-lang fr --format ssa --engine deepl

# Modelo más pequeño en CPU
python main.py --input video.mp4 --model small --device cpu
```

> **Primera ejecución:** El modelo `medium` requiere una descarga única de ~1,5 GB. Usa `--model small` (~470 MB) o `--model tiny` (~75 MB) para reducir la descarga inicial.

### translate

```bash
python main.py translate <file> --target-lang <code> [OPTIONS]
```

Traduce un archivo de subtítulos `.srt` o `.ssa` existente sin volver a transcribir.

| Argumento / Flag | Descripción | Predeterminado |
|-----------------|-------------|----------------|
| `<file>` | Archivo de subtítulos de entrada (`.srt` o `.ssa`) | Requerido |
| `--target-lang`, `-t` | Código ISO 639-1 de destino | Requerido |
| `--source-lang`, `-s` | Código de idioma de origen | `en` |
| `--output`, `-o` | Ruta de salida | `<input>_translated.<ext>` |

**Ejemplo:**
```bash
python main.py translate subtitles.srt --target-lang es
```

### convert

```bash
python main.py convert <input> <output>
```

Convierte un archivo de subtítulos entre formatos (`.srt` ↔ `.ssa`). El formato de salida se deduce de la extensión del archivo de destino.

**Ejemplo:**
```bash
python main.py convert subtitles.srt subtitles.ssa
```

### serve

```bash
python main.py serve [--host HOST] [--port PORT] [--reload]
```

Inicia el servidor de la API REST de GenSubtitles (FastAPI).

| Flag | Descripción | Predeterminado |
|------|-------------|----------------|
| `--host` | Dirección de enlace del servidor | `127.0.0.1` |
| `--port` | Puerto de escucha | `8000` |
| `--reload` | Habilita la recarga automática (modo desarrollo) | `false` |

**Ejemplo:**
```bash
# Exponer en todas las interfaces
python main.py serve --host 0.0.0.0 --port 8000
```

## Uso de la API

GenSubtitles proporciona una API REST impulsada por FastAPI.

**Iniciar el servidor:**
```bash
python main.py serve
```

O usando uvicorn directamente:
```bash
uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
```

### POST /subtitles

Sube un archivo de vídeo y recibe un archivo de subtítulos en respuesta.

**Ejemplo básico:**
```bash
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  --output subtitles.srt
```

**Con traducción:**
```bash
curl -X POST "http://localhost:8000/subtitles?target_lang=es" \
  -F "file=@video.mp4" \
  --output subtitles.srt
```

**Parámetros de consulta:**
- `target_lang` (opcional): Código ISO 639-1 de destino para la traducción
- `source_lang` (opcional): Forzar idioma de origen (omitir para detección automática)
- `engine` (opcional): Motor de traducción a usar (`argos`, `deepl` o `libretranslate`)

### Documentación interactiva de la API

FastAPI proporciona documentación interactiva en:
```
http://localhost:8000/docs
```

## Configuración

Los ajustes se guardan como JSON en:
- **Linux:** `~/.config/GenSubtitles/settings.json`
- **macOS:** `~/Library/Application Support/GenSubtitles/settings.json`
- **Windows:** `%APPDATA%\GenSubtitles\settings.json`

El archivo se crea cuando se guardan los ajustes por primera vez (por ejemplo, desde el diálogo de configuración de la GUI), por lo que puede no existir todavía en el primer inicio. Puedes editarlo directamente cuando exista o usar el diálogo de configuración de la GUI.

### Campos de configuración

| Campo | Tipo | Predeterminado | Descripción |
|-------|------|----------------|-------------|
| `appearance_mode` | string | `"System"` | Tema de la interfaz: `"Light"`, `"Dark"` o `"System"` |
| `ui_language` | string | `"en"` | Idioma de la interfaz: `"en"` o `"es"` |
| `default_output_dir` | string | `""` | Directorio de salida predeterminado. Vacío = mismo directorio que el vídeo de entrada |
| `default_source_lang` | string | `""` | Idioma de origen predeterminado (ISO 639-1). Vacío = detección automática de Whisper |
| `target_lang` | string | `""` | Idioma de destino predeterminado para traducción. Vacío = sin traducción |
| `deepl_api_key` | string | `""` | Clave de API gratuita de DeepL (necesaria para usar `--engine deepl`) |
| `libretranslate_url` | string | `""` | URL del servidor LibreTranslate (p. ej., `"http://localhost:5000"`) |
| `libretranslate_api_key` | string | `""` | Clave de API de LibreTranslate. Vacío = instancia abierta |

## Solución de problemas

### FFmpeg no encontrado

**Error:**
```
EnvironmentError: FFmpeg not found in PATH
```

**Solución:** Instala FFmpeg usando los comandos de la sección de Instalación. Verifica con `ffmpeg -version` y reinicia tu terminal para actualizar el PATH.

### Fallo en la descarga del modelo de Argos

**Error:** Tiempo de espera de red agotado o error HTTP durante la descarga.

**Solución:** Verifica tu conexión a internet y vuelve a intentarlo. Los modelos se descargan una vez y se almacenan en caché. Si los fallos persisten, inténtalo con una conexión estable.

### Directorio de salida faltante

**Error:** `FileNotFoundError` o errores de permisos al escribir el archivo de subtítulos.

**Solución:** Asegúrate de que el directorio de salida existe y es escribible. Usa `--output` para especificar una ruta válida:
```bash
python main.py --input video.mp4 --output /ruta/al/directorio/subtitles.srt
```

### DeepL / LibreTranslate no funcionan

La GUI soporta DeepL y LibreTranslate cuando están correctamente configurados. Si estos motores no funcionan, verifica lo siguiente:

- **DeepL:** Asegúrate de que `deepl_api_key` esté configurada en el diálogo de configuración o en `settings.json`. Se requiere una [clave de API gratuita de DeepL](https://deepl.com) válida.
- **LibreTranslate:** Asegúrate de que `libretranslate_url` apunte a un servidor accesible (p. ej., `http://localhost:5000`). Verifica que el servidor esté en ejecución y sea alcanzable.
- **Errores de red:** Ambos motores requieren conectividad. Verifica tu conexión a internet y la configuración de firewall.

También puedes usar estos motores vía CLI:
```bash
python main.py --input video.mp4 --target-lang es --engine deepl
python main.py --input video.mp4 --target-lang es --engine libretranslate
```

### Primera ejecución — descarga de modelo grande

El modelo `medium` predeterminado requiere una descarga de ~1,5 GB. Usa un modelo más pequeño para reducir la descarga inicial:
```bash
python main.py --input video.mp4 --model small   # ~470 MB
python main.py --input video.mp4 --model tiny    # ~75 MB
```

## Licencia

MIT
