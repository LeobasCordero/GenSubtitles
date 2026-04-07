---
status: partial
phase: 02-audio-extraction-module
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-04-07T00:00:00Z
updated: 2026-04-07T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. extract_audio produces 16kHz mono WAV
expected: Dado un archivo .mp4 con audio, llamar extract_audio(video, tmp.wav) crea un WAV en tmp.wav legible con wave.open(), con framerate==16000 y nchannels==1.
result: blocked
blocked_by: third-party
reason: "FFmpeg no está instalado en esta máquina"

### 2. Unsupported extension raises ValueError
expected: Llamar extract_audio con un archivo de extensión no soportada (e.g., .xyz) lanza ValueError antes de que se ejecute ningún proceso FFmpeg.
result: blocked
blocked_by: third-party
reason: "FFmpeg no está instalado en esta máquina"

### 3. Video sin audio lanza AudioExtractionError
expected: Llamar extract_audio en un video sin pista de audio lanza AudioExtractionError con un mensaje que menciona el problema de audio.
result: blocked
blocked_by: third-party
reason: "FFmpeg no está instalado en esta máquina"

### 4. audio_temp_context limpia el archivo temporal
expected: Al salir del bloque with audio_temp_context(...) (normal o por excepción), el archivo WAV temporal es eliminado del disco.
result: blocked
blocked_by: third-party
reason: "FFmpeg no está instalado en esta máquina"

### 5. FFmpeg ausente lanza EnvironmentError al importar
expected: Si FFmpeg no está en el PATH, al importar gensubtitles.core.audio se lanza EnvironmentError con un mensaje indicando cómo instalar FFmpeg.
result: pass

### 6. Tests de audio se saltan si FFmpeg no está disponible
expected: Ejecutar `pytest tests/test_audio.py -v` con FFmpeg ausente exitcode 0, con los 5 tests marcados como skipped (no como error).
result: pass

## Summary

total: 6
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 4

## Gaps

[none yet]
