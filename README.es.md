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

## Uso de CLI

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
| `--model`, `-m` | Tamaño del modelo Whisper: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `turbo` | `small` |
| `--target-lang`, `-t` | Código de idioma ISO 639-1 de destino para la traducción (ej., `es`, `fr`, `de`) | Ninguno (sin traducción) |
| `--source-lang`, `-s` | Código de idioma de origen (omitir para detección automática) | Detección automática |
| `--device` | Dispositivo de cálculo: `auto`, `cpu`, `cuda` | `auto` |

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
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  -F "target_lang=es" \
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
