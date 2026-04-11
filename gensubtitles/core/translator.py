"""
gensubtitles.core.translator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Offline translation engine using Argos Translate.

Provides:
    TranslatedSegment          — namedtuple with (start, end, text) for downstream SRT generation
    translate_segments()       — translate a segment list from source to target language
    translate_file()           — translate an existing SRT/SSA subtitle file to another language
    ensure_pair_installed()    — install Argos language package on demand
    is_pair_available()        — check if a language pair is installed or remotely available
    list_installed_pairs()     — list all installed language pairs as {"from", "to"} dicts
"""
from __future__ import annotations

import logging
from collections import namedtuple
from typing import Any

logger = logging.getLogger(__name__)

TranslatedSegment = namedtuple("TranslatedSegment", ["start", "end", "text"])


def _is_installed(from_code: str, to_code: str) -> bool:
    """Return True if the from_code→to_code pair is already installed."""
    import argostranslate.translate

    for lang in argostranslate.translate.get_installed_languages():
        if lang.code == from_code:
            for t in lang.translations_to:
                if t.to_lang.code == to_code:
                    return True
    return False


def list_installed_pairs() -> list[dict]:
    """Return all installed language pairs as [{"from": code, "to": code}] dicts."""
    import argostranslate.translate

    pairs = []
    for lang in argostranslate.translate.get_installed_languages():
        for t in lang.translations_to:
            pairs.append({"from": lang.code, "to": t.to_lang.code})
    return pairs


def ensure_pair_installed(from_code: str, to_code: str) -> None:
    """
    Ensure the from_code→to_code Argos Translate package is installed.
    Downloads on first use; no-op if already cached.
    """
    import argostranslate.package

    if _is_installed(from_code, to_code):
        return  # already cached — D-05

    # Best-effort index update (D-04)
    try:
        argostranslate.package.update_package_index()
    except Exception as exc:
        logger.warning(
            "Failed to update Argos Translate package index (offline?): %s. "
            "Falling back to cached packages.",
            exc,
        )

    # Re-check after index update attempt
    if _is_installed(from_code, to_code):
        return

    # Find the package in available list
    available = argostranslate.package.get_available_packages()
    pkg = next(
        (p for p in available if p.from_code == from_code and p.to_code == to_code),
        None,
    )
    if pkg is None:
        raise RuntimeError(
            f"Language pair '{from_code}→{to_code}' could not be downloaded: "
            "package not found in the Argos Translate index and is not cached locally. "
            "Check your internet connection or call list_installed_pairs() to see what is available."
        )

    # Download with tqdm progress feedback (D-09, D-10)
    print(f"Downloading Argos Translate model: {from_code}→{to_code} ...", flush=True)
    from tqdm.auto import tqdm

    with tqdm(desc=f"Installing {from_code}→{to_code}", total=1, unit="pkg") as pbar:
        try:
            download_path = pkg.download()
            argostranslate.package.install_from_path(download_path)
            pbar.update(1)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to install language package '{from_code}→{to_code}': {exc}"
            ) from exc


def is_pair_available(from_code: str, to_code: str) -> bool:
    """
    Return True if the pair is installed or available remotely.
    Raises ValueError if neither installed nor in the remote index.
    """
    import argostranslate.package

    if _is_installed(from_code, to_code):
        return True

    available = argostranslate.package.get_available_packages()
    if any(p.from_code == from_code and p.to_code == to_code for p in available):
        return True

    raise ValueError(
        f"Language pair '{from_code}→{to_code}' is not available. "
        "Call list_installed_pairs() to see installed options."
    )


def translate_segments(
    segments: list[Any], source_lang: str, target_lang: str
) -> list:
    """
    Translate segment texts from source_lang to target_lang using Argos Translate.

    If source_lang == target_lang, a shallow copy of the original segment list is returned
    without translating any text; the segment references themselves are unchanged (TRANS-02).
    Otherwise, ensures the language package is installed (TRANS-03/TRANS-05), then
    translates each segment's .text while preserving .start and .end (TRANS-01).

    Returns a list of TranslatedSegment namedtuples (or a shallow copy of the input list when no-op).
    """
    if source_lang == target_lang:
        return list(segments)  # D-07: return original references unchanged

    ensure_pair_installed(source_lang, target_lang)

    import argostranslate.translate

    result = []
    for seg in segments:
        translated_text = argostranslate.translate.translate(
            seg.text, source_lang, target_lang
        )
        result.append(TranslatedSegment(start=seg.start, end=seg.end, text=translated_text))
    return result


def translate_file(
    input_path: "str | Path",
    target_lang: str,
    source_lang: "str | None" = None,
    output_path: "str | Path | None" = None,
) -> "Path":
    """
    Translate all subtitle text in an existing SRT or SSA file.

    Reads input_path with pysubs2 (handles .srt and .ssa/.ass), translates all
    subtitle events, and by default writes output using the same file format as
    the input. If output_path is provided, pysubs2 determines the output format
    from that path's extension.

    Args:
        input_path:  Path to the input subtitle file (.srt or .ssa).
        target_lang: Target ISO 639-1 language code.
        source_lang: Source language code. Defaults to 'en' if omitted.
        output_path: Output path. Defaults to <stem>_translated.<ext>; if a
            different extension is provided, the output is written in the
            format implied by that extension.

    Returns:
        Resolved output Path.

    Raises:
        FileNotFoundError: If input_path does not exist.
        ValueError: If source_lang equals target_lang.
    """
    from pathlib import Path as _Path
    from types import SimpleNamespace

    import pysubs2

    input_path = _Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if source_lang is None:
        source_lang = "en"
        logger.warning(
            "translate_file: source_lang not specified — defaulting to 'en'"
        )

    if source_lang == target_lang:
        raise ValueError(
            f"Source and target language are the same: {source_lang}"
        )

    ensure_pair_installed(source_lang, target_lang)

    subs = pysubs2.SSAFile.load(str(input_path))

    segments_in = [
        SimpleNamespace(start=e.start / 1000.0, end=e.end / 1000.0, text=e.plaintext)
        for e in subs
        if e.text.strip()
    ]

    translated = translate_segments(segments_in, source_lang, target_lang)

    ti = 0
    for e in subs:
        if e.text.strip():
            e.text = translated[ti].text
            ti += 1

    out = (
        _Path(output_path)
        if output_path
        else input_path.with_stem(input_path.stem + "_translated")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(out))
    return out
