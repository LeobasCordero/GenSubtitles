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
2. Haz clic en **Select Video** y elige tu archivo de vídeo (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`).
3. Opcionalmente, establece una ruta de **Output** personalizada. Si se deja en blanco, el archivo de subtítulos se guarda en el mismo directorio que el vídeo.
4. Elige un **modelo Whisper** en el menú desplegable. Los modelos más grandes son más precisos pero más lentos. El valor predeterminado es `medium`.
5. Establece el **Source Language** (déjalo en blanco para detección automática) y opcionalmente un **Target Language** para activar la traducción.
6. Haz clic en **Generate** para iniciar. El progreso se muestra en el área de estado.

> **Primera ejecución:** El modelo Whisper seleccionado se descarga en el primer uso. El modelo `medium` ocupa ~1,5 GB. Usa `small` (~470 MB) o `tiny` (~75 MB) para reducir la descarga inicial.

### Configuración de traducción

Usa los menús desplegables **Source Language** y **Target Language** del formulario principal:

- Deja **Source Language** en blanco para que Whisper detecte automáticamente el idioma hablado.
- Establece **Target Language** con un código ISO 639-1 (p. ej., `es` para español, `fr` para francés) para traducir los subtítulos tras la transcripción.
- Deja **Target Language** en blanco para omitir la traducción y obtener el subtítulo en el idioma original.

La traducción en la GUI usa **Argos Translate** (offline, sin clave API). Los modelos de Argos para cada par de idiomas se descargan la primera vez (~50–200 MB) y se almacenan en caché localmente.

> **Nota:** DeepL y LibreTranslate están disponibles via CLI (`--engine deepl`/`--engine libretranslate`); el soporte en la GUI llegará en una próxima versión.

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

### Documentación interactiva de la API

FastAPI proporciona documentación interactiva en:
```
http://localhost:8000/docs
```

## Configuración

Los ajustes se guardan como JSON en:
- **Linux / macOS:** `~/.config/GenSubtitles/settings.json`
- **Windows:** `%APPDATA%\GenSubtitles\settings.json`

El archivo se crea automáticamente en el primer inicio. Puedes editarlo directamente o usar el diálogo de configuración de la GUI.

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

### DeepL / LibreTranslate no funcionan en la GUI

DeepL y LibreTranslate no están activos en la GUI todavía. Usa el flag `--engine` en la CLI:
```bash
python main.py --input video.mp4 --target-lang es --engine deepl
python main.py --input video.mp4 --target-lang es --engine libretranslate
```

El soporte en la GUI está previsto para una versión futura.

### Primera ejecución — descarga de modelo grande

El modelo `medium` predeterminado requiere una descarga de ~1,5 GB. Usa un modelo más pequeño para reducir la descarga inicial:
```bash
python main.py --input video.mp4 --model small   # ~470 MB
python main.py --input video.mp4 --model tiny    # ~75 MB
```

## Licencia

MIT

GenSubtitles proporciona una interfaz de línea de comandos con 6 flags configurables.

**Uso básico (detecta automáticamente la ruta de salida):**
```bash
python main.py --input video.mp4
```

**Ruta de salida personalizada:**
```bash
python main.py --input video.mp4 --output subtitles.srt
```

**Con traducción al español:**
```bash
python main.py --input video.mp4 --target-lang es
```

**Modelo y dispositivo personalizados:**
```bash
python main.py --input video.mp4 --model base --device cpu
```

### Flags disponibles

| Flag | Descripción | Por defecto |
|------|-------------|-------------|
| `--input`, `-i` | Ruta al archivo de vídeo de entrada (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`) | Requerido |
| `--output`, `-o` | Ruta de destino del archivo `.srt` | `<input>.srt` |
| `--model`, `-m` | Tamaño del modelo Whisper: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `turbo` | `medium` |
| `--target-lang`, `-t` | Código de idioma ISO 639-1 de destino para la traducción (ej., `es`, `fr`, `de`) | Ninguno (sin traducción) |
| `--source-lang`, `-s` | Código de idioma de origen (omitir para detección automática) | Detección automática |
| `--device` | Dispositivo de cálculo: `auto`, `cpu`, `cuda` | `auto` |

> **Primera ejecución:** El modelo por defecto (`medium`) requiere una descarga única de ~1,5 GB.
> Usa `--model small` (~470 MB) o `--model tiny` (~75 MB) para una descarga inicial más pequeña.

Para las opciones completas:
```bash
python main.py --help
```

## Uso de API

GenSubtitles proporciona una API REST impulsada por FastAPI.

### Iniciar el servidor

**Usando el punto de entrada principal:**
```bash
python main.py serve
```

**Usando uvicorn directamente:**
```bash
uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
```

### Endpoints

#### POST /subtitles

Sube un archivo de vídeo y recibe un archivo de subtítulos SRT en respuesta.

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
- `target_lang` (opcional): Código de idioma ISO 639-1 de destino para la traducción
- `source_lang` (opcional): Forzar la detección del idioma de origen (omitir para detección automática)

#### Documentación interactiva de la API

FastAPI proporciona documentación interactiva de la API en:
```
http://localhost:8000/docs
```

## Traducción de Idiomas

GenSubtitles utiliza Argos Translate para la generación de subtítulos multilingües.

**Descarga del modelo por primera vez:**
- En el primer uso de un par de idiomas (por ejemplo, inglés → español), Argos Translate descarga el modelo requerido (~50-200 MB dependiendo del par de idiomas)
- Los modelos se descargan desde internet — la primera traducción requiere conectividad de red
- Los modelos descargados se almacenan en caché localmente en el directorio de caché apropiado del sistema operativo

**Ejecuciones posteriores:**
- Después de la descarga inicial, todas las ejecuciones de traducción son completamente offline
- Los modelos permanecen en caché entre sesiones

**Idiomas compatibles:**
Usa códigos ISO 639-1 con el flag `--target-lang` (por ejemplo, `es` para español, `fr` para francés, `de` para alemán, `pt` para portugués).

## Solución de Problemas

### FFmpeg no encontrado

**Error:**
```
EnvironmentError: FFmpeg not found in PATH
```

**Solución:**
Instala FFmpeg usando los comandos de la sección de Instalación anterior. Después de la instalación, verifica con `ffmpeg -version` y reinicia tu terminal para actualizar el PATH.

### Fallo en la descarga del modelo de Argos

**Error:**
Tiempo de espera de red agotado o error HTTP durante la descarga del modelo.

**Solución:**
Verifica tu conexión a internet y vuelve a intentar el comando. Los modelos de idiomas se descargan una vez en el primer uso y se almacenan en caché localmente. Si los fallos de descarga persisten, inténtalo de nuevo con una conexión de red estable.

### Directorio de salida faltante

**Error:**
```
FileNotFoundError
```
o errores de permisos al escribir el archivo SRT.

**Solución:**
Asegúrate de que el directorio de salida existe y es escribible. Puedes usar el flag `--output` para especificar una ruta válida:
```bash
python main.py --input video.mp4 --output /ruta/a/directorio/escribible/subtitles.srt
```

## Licencia

MIT
