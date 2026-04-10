---
status: complete
phase: 06-core-pipeline-assembly
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md]
started: 2026-04-07T00:00:00Z
updated: 2026-04-07T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 8 pipeline tests pasan sin FFmpeg ni GPU
expected: `pytest tests/test_pipeline.py -v` retorna exit code 0 con 8 tests passed.
result: pass

### 2. run_pipeline importa sin EnvironmentError
expected: `from gensubtitles.core.pipeline import run_pipeline, PipelineResult` importa sin error aunque FFmpeg no esté instalado.
result: pass

### 3. PipelineResult tiene los 4 campos esperados
expected: PipelineResult tiene los campos srt_path, detected_language, segment_count, audio_duration_seconds.
result: pass
note: Es un dataclass, no namedtuple. Campos verificados con dataclasses.fields().

### 4. FileNotFoundError si video no existe
expected: Llamar run_pipeline con un video inexistente lanza FileNotFoundError antes de ejecutar FFmpeg.
result: pass

### 5. Translation skipped si target_lang=None
expected: Llamar run_pipeline sin target_lang no descarga modelos Argos ni llama a translate_segments.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
