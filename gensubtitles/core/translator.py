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
import re as _re
from collections import namedtuple
from typing import Any

from gensubtitles.core.settings import load_settings

logger = logging.getLogger(__name__)

TranslatedSegment = namedtuple("TranslatedSegment", ["start", "end", "text"])

# Module-level cache for available packages (refreshed once per session)
_pkg_index_cache: list | None = None


def _get_available_packages(force_refresh: bool = False) -> list:
    """Return cached list of available Argos Translate packages."""
    import argostranslate.package

    global _pkg_index_cache  # noqa: PLW0603
    if _pkg_index_cache is None or force_refresh:
        try:
            argostranslate.package.update_package_index()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not update package index: %s", exc)
        _pkg_index_cache = argostranslate.package.get_available_packages()
    return _pkg_index_cache


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


def find_route(from_code: str, to_code: str) -> list[tuple[str, str]]:
    """
    Find a translation route from from_code to to_code.

    Returns a list of (from, to) hops:
    - Direct pair available → [(from, to)]
    - No direct pair, but both from→en and en→to exist → [(from, 'en'), ('en', to)]
    - Otherwise raises RuntimeError.

    Preference order:
    1. Direct installed pair (no network)
    2. Direct remotely-available pair (preferred over pivot for quality)
    3. Installed English pivot (no network, but 2-hop)
    4. Remote English pivot
    """
    available: set[tuple[str, str]] | None = None

    def _is_available(f: str, t: str) -> bool:
        nonlocal available
        if available is None:
            available = {(p.from_code, p.to_code) for p in _get_available_packages()}
        return (f, t) in available

    def _reachable(f: str, t: str) -> bool:
        return _is_installed(f, t) or _is_available(f, t)

    # 1. Check installed direct pair first (avoids network for common cases)
    if _is_installed(from_code, to_code):
        return [(from_code, to_code)]

    # 2. Prefer a direct route whenever one is available, including remotely
    if _reachable(from_code, to_code):
        return [(from_code, to_code)]

    # 3. If no direct route exists, prefer an already-installed English pivot
    if from_code != "en" and to_code != "en":
        if _is_installed(from_code, "en") and _is_installed("en", to_code):
            return [(from_code, "en"), ("en", to_code)]

    # 4. Fall back to an English pivot with remote packages
    if from_code != "en" and to_code != "en":
        if _reachable(from_code, "en") and _reachable("en", to_code):
            return [(from_code, "en"), ("en", to_code)]

    raise RuntimeError(
        f"Language pair '{from_code}\u2192{to_code}' is not available: "
        "no direct package and no English pivot route found in the Argos Translate index."
    )


def ensure_route_installed(from_code: str, to_code: str) -> list[tuple[str, str]]:
    """
    Ensure all packages needed to translate from_code→to_code are installed.

    Returns the route as a list of (from, to) hops.
    """
    route = find_route(from_code, to_code)
    for hop_from, hop_to in route:
        ensure_pair_installed(hop_from, hop_to)
    return route


def ensure_pair_installed(from_code: str, to_code: str) -> None:
    """
    Ensure the from_code→to_code Argos Translate package is installed.
    Downloads on first use; no-op if already cached.
    """
    import argostranslate.package

    if _is_installed(from_code, to_code):
        return  # already cached — D-05

    # Try the cached index first (avoids network on repeated calls)
    available = _get_available_packages()

    pkg = next(
        (p for p in available if p.from_code == from_code and p.to_code == to_code),
        None,
    )

    # If not found in cache, force a single refresh and retry
    if pkg is None:
        available = _get_available_packages(force_refresh=True)

        # Re-check installed state after refresh (another thread may have installed it)
        if _is_installed(from_code, to_code):
            return

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
    segments: list[Any], source_lang: str, target_lang: str,
    progress_callback: "Any | None" = None,
    engine: str = "argos",
) -> list:
    """
    Translate segment texts from source_lang to target_lang.

    engine: 'argos' (default), 'deepl', or 'libretranslate'.

    If source_lang == target_lang, a shallow copy of the original segment list is returned
    without translating any text; the segment references themselves are unchanged (TRANS-02).

    progress_callback: optional callable(current: int, total: int) called after each hop
    (Argos engine only).

    Returns a list of TranslatedSegment namedtuples (or a shallow copy of the input list when no-op).
    """
    if source_lang == target_lang:
        return list(segments)  # D-07: return original references unchanged

    if not segments:
        return []

    # --- Non-Argos engines: direct API call, no pivot chain ---
    if engine == "deepl":
        texts = [seg.text for seg in segments]
        translated_texts = _translate_deepl(texts, target_lang)
        return [
            TranslatedSegment(start=seg.start, end=seg.end, text=t)
            for seg, t in zip(segments, translated_texts)
        ]

    if engine == "libretranslate":
        texts = [seg.text for seg in segments]
        translated_texts = _translate_libretranslate(texts, source_lang, target_lang)
        return [
            TranslatedSegment(start=seg.start, end=seg.end, text=t)
            for seg, t in zip(segments, translated_texts)
        ]

    if engine != "argos":
        raise ValueError(
            f"Unknown engine '{engine}'. Choose argos, deepl, or libretranslate."
        )

    # --- Argos engine: context-batching via XML numbered markers ---
    route = ensure_route_installed(source_lang, target_lang)

    import argostranslate.translate

    current = list(segments)
    for hop_idx, (hop_from, hop_to) in enumerate(route):
        # Build the batch string using numbered XML markers (D-01)
        batch = "".join(
            f"<{i + 1}>{seg.text}</{i + 1}>" for i, seg in enumerate(current)
        )

        # Translate the entire batch as a single string
        translated_batch = argostranslate.translate.translate(batch, hop_from, hop_to)

        # Parse markers back out
        matches = _re.findall(r"<(\d+)>(.*?)</\1>", translated_batch, _re.DOTALL)
        texts_by_idx: dict[int, str] = {int(m[0]): m[1] for m in matches}

        # D-02: on marker mismatch, fall back to per-segment translation
        expected_keys = set(range(1, len(current) + 1))
        actual_keys = set(texts_by_idx)
        if actual_keys != expected_keys:
            logger.warning(
                "Batched translation marker mismatch (expected %s, got %s). "
                "Argos Translate stripped the XML markers — falling back to "
                "per-segment translation.",
                sorted(expected_keys),
                sorted(actual_keys),
            )
            current = [
                TranslatedSegment(
                    start=seg.start,
                    end=seg.end,
                    text=argostranslate.translate.translate(seg.text, hop_from, hop_to),
                )
                for seg in current
            ]
        else:
            current = [
                TranslatedSegment(start=seg.start, end=seg.end, text=texts_by_idx[i + 1])
                for i, seg in enumerate(current)
            ]

        if progress_callback is not None:
            progress_callback(hop_idx + 1, len(route))

    return current


def _translate_deepl(texts: list[str], target_lang: str) -> list[str]:
    """Translate a list of texts using DeepL Free API."""
    settings = load_settings()
    api_key = settings.deepl_api_key
    if not api_key:
        raise RuntimeError(
            "DeepL API key not configured. Set deepl_api_key in settings."
        )

    import deepl  # noqa: PLC0415
    try:
        translator = deepl.Translator(api_key)
        results = translator.translate_text(texts, target_lang=target_lang.upper())
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"DeepL translation failed: {exc}") from exc
    return [r.text for r in results]


def _translate_libretranslate(
    texts: list[str], source_lang: str, target_lang: str
) -> list[str]:
    """Translate a list of texts using LibreTranslate REST API."""
    try:
        import requests  # noqa: PLC0415
    except ImportError:
        raise RuntimeError(
            "The 'requests' package is required for LibreTranslate but is not installed. "
            "Reinstall with: pip install gensubtitles"
        )

    settings = load_settings()
    url = settings.libretranslate_url
    api_key = settings.libretranslate_api_key  # empty string = open instance
    if not url:
        raise RuntimeError(
            "LibreTranslate URL not configured. Set libretranslate_url in settings."
        )
    endpoint = f"{url.rstrip('/')}/translate"
    translated = []
    for text in texts:
        payload: dict = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if api_key:
            payload["api_key"] = api_key
        try:
            resp = requests.post(endpoint, json=payload, timeout=30)
            resp.raise_for_status()
            translated.append(resp.json()["translatedText"])
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"LibreTranslate translation failed: {exc}") from exc
    return translated


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
    if not input_path.is_file():
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

    ensure_route_installed(source_lang, target_lang)

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
