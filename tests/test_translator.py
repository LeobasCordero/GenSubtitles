"""
Phase 4 translator tests — covers TRANS-01 through TRANS-05.
All tests mock argostranslate via sys.modules for hermetic, offline execution.
"""
from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_fake_segment(start: float, end: float, text: str):
    """Minimal segment stub with .start/.end/.text (mirrors faster-whisper Segment)."""
    return SimpleNamespace(start=start, end=end, text=text)


def _make_fake_language(code: str, translations_to_codes: list[str]):
    """Fake argostranslate Language with .code and .translations_to."""
    translations = [
        SimpleNamespace(to_lang=SimpleNamespace(code=tc))
        for tc in translations_to_codes
    ]
    return SimpleNamespace(code=code, translations_to=translations)


def _make_fake_package(from_code: str, to_code: str, download_path: str = "/tmp/fake.argosmodel"):
    """Fake Package with .from_code, .to_code, .download()."""
    pkg = MagicMock()
    pkg.from_code = from_code
    pkg.to_code = to_code
    pkg.download.return_value = download_path
    return pkg


def _batch_aware_translate(text: str, src: str, tgt: str) -> str:
    """
    Default mock side_effect for argostranslate.translate.translate.
    Handles both plain strings and XML-marker batch strings produced by the
    batched translation path (e.g. "<1>Hello</1><2>World</2>").
    For batch input the translation prefix is inserted *inside* each marker so
    callers can round-trip the markers correctly.
    """
    import re as _re

    if _re.search(r"<\d+>", text):
        return _re.sub(
            r"<(\d+)>(.*?)</\1>",
            lambda m: f"<{m.group(1)}>[{tgt}]{m.group(2)}</{m.group(1)}>",
            text,
            flags=_re.DOTALL,
        )
    return f"[{tgt}]{text}"


@contextmanager
def _inject_argostranslate(installed_languages=None, available_packages=None):
    """
    Context manager that injects fake argostranslate modules into sys.modules
    for the duration of the with-block and restores originals on exit via patch.dict.
    Yields (fake_pkg_mod, fake_translate_mod) for per-test assertion.
    """
    if installed_languages is None:
        installed_languages = []
    if available_packages is None:
        available_packages = []

    fake_pkg = ModuleType("argostranslate.package")
    fake_pkg.update_package_index = MagicMock()
    fake_pkg.get_available_packages = MagicMock(return_value=available_packages)
    fake_pkg.install_from_path = MagicMock()

    fake_translate = ModuleType("argostranslate.translate")
    fake_translate.get_installed_languages = MagicMock(return_value=installed_languages)
    fake_translate.translate = MagicMock(side_effect=_batch_aware_translate)

    fake_root = ModuleType("argostranslate")
    fake_root.package = fake_pkg
    fake_root.translate = fake_translate

    with patch.dict(
        "sys.modules",
        {
            "argostranslate": fake_root,
            "argostranslate.package": fake_pkg,
            "argostranslate.translate": fake_translate,
        },
    ):
        yield fake_pkg, fake_translate


# ── TRANS-01: translation changes text and preserves timestamps ───────────────


def test_translate_segments_translates_text():
    """TRANS-01: Each segment's .text is translated."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(
        installed_languages=[en_lang],
        available_packages=[],
    ) as (fake_pkg, fake_translate):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 2.5, "Hello")]
        result = translate_segments(segs, "en", "es")

    assert len(result) == 1
    assert result[0].text == "[es]Hello"


def test_translate_segments_preserves_timestamps():
    """TRANS-01: .start and .end on translated segments match input."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(1.5, 4.0, "World")]
        result = translate_segments(segs, "en", "es")

    assert result[0].start == 1.5
    assert result[0].end == 4.0


def test_translate_segments_returns_translated_segment_type():
    """TRANS-01: Result items are TranslatedSegment namedtuples."""
    from collections import namedtuple

    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import TranslatedSegment, translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hi")]
        result = translate_segments(segs, "en", "es")

    assert isinstance(result[0], TranslatedSegment)
    assert hasattr(result[0], "start")
    assert hasattr(result[0], "end")
    assert hasattr(result[0], "text")


# ── TRANS-02: same-language is a no-op ────────────────────────────────────────


def test_translate_segments_same_lang_returns_originals():
    """TRANS-02: source == target returns original segment objects (same identity)."""
    with _inject_argostranslate():
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hello")]
        result = translate_segments(segs, "en", "en")

    assert result is not segs  # returns a new list
    assert result[0] is segs[0]  # but same segment objects


def test_translate_segments_same_lang_no_argos_call():
    """TRANS-02: argostranslate.translate.translate() is never called when source==target."""
    with _inject_argostranslate() as (_, fake_translate):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hello")]
        translate_segments(segs, "fr", "fr")

        fake_translate.translate.assert_not_called()


# ── TRANS-03: packages installed on first use ─────────────────────────────────


def test_ensure_pair_installed_downloads_missing_pair():
    """TRANS-03: download() and install_from_path() are called for an absent pair."""
    pkg = _make_fake_package("en", "fr")
    with _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    ) as (fake_pkg, _):
        from gensubtitles.core.translator import ensure_pair_installed

        with patch("tqdm.auto.tqdm") as mock_tqdm:
            mock_tqdm.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_tqdm.return_value.__exit__ = MagicMock(return_value=False)
            ensure_pair_installed("en", "fr")

    pkg.download.assert_called_once()
    fake_pkg.install_from_path.assert_called_once_with(pkg.download.return_value)


def test_ensure_pair_installed_calls_update_index_before_download():
    """TRANS-03: update_package_index() is called when package not in cache."""
    pkg = _make_fake_package("en", "fr")
    with _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    ) as (fake_pkg, _):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None  # ensure cache is empty so refresh is needed

        call_order = []
        fake_pkg.update_package_index.side_effect = lambda: call_order.append("update")
        pkg.download.side_effect = lambda: call_order.append("download") or "/tmp/fake.argosmodel"

        from gensubtitles.core.translator import ensure_pair_installed

        with patch("tqdm.auto.tqdm") as mock_tqdm:
            mock_tqdm.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_tqdm.return_value.__exit__ = MagicMock(return_value=False)
            ensure_pair_installed("en", "fr")

    assert call_order.index("update") < call_order.index("download")


# ── TRANS-04: fails gracefully for unsupported pairs ─────────────────────────


def test_is_pair_available_raises_for_unknown_pair():
    """TRANS-04: ValueError is raised with pair name in message for unsupported pair."""
    with _inject_argostranslate(installed_languages=[], available_packages=[]):
        from gensubtitles.core.translator import is_pair_available

        with pytest.raises(ValueError, match="en→tlh"):
            is_pair_available("en", "tlh")


def test_is_pair_available_true_when_installed():
    """TRANS-04: Returns True when pair is already installed."""
    en_lang = _make_fake_language("en", ["fr"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import is_pair_available

        assert is_pair_available("en", "fr") is True


def test_is_pair_available_true_when_remote_only():
    """TRANS-04: Returns True when pair exists in available packages (not yet installed)."""
    pkg = _make_fake_package("en", "de")
    with _inject_argostranslate(installed_languages=[], available_packages=[pkg]):
        from gensubtitles.core.translator import is_pair_available

        assert is_pair_available("en", "de") is True


def test_translate_segments_unknown_pair_raises_runtime_error():
    """TRANS-04: translate_segments raises RuntimeError when pair cannot be installed."""
    with _inject_argostranslate(installed_languages=[], available_packages=[]):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hello")]
        with pytest.raises(RuntimeError):
            translate_segments(segs, "en", "klingon")


# ── TRANS-05: models cached, not re-downloaded ────────────────────────────────


def test_ensure_pair_installed_no_op_when_already_installed():
    """TRANS-05: No download when pair is already installed."""
    en_lang = _make_fake_language("en", ["fr"])
    with _inject_argostranslate(installed_languages=[en_lang]) as (fake_pkg, _):
        from gensubtitles.core.translator import ensure_pair_installed

        ensure_pair_installed("en", "fr")

    fake_pkg.install_from_path.assert_not_called()


def test_ensure_pair_installed_no_download_call_when_cached():
    """TRANS-05: pkg.download() is never called when pair is in installed languages."""
    en_lang = _make_fake_language("en", ["fr"])
    pkg = _make_fake_package("en", "fr")
    with _inject_argostranslate(installed_languages=[en_lang], available_packages=[pkg]):
        from gensubtitles.core.translator import ensure_pair_installed

        ensure_pair_installed("en", "fr")

    pkg.download.assert_not_called()


def test_ensure_pair_installed_uses_cached_index_first():
    """ensure_pair_installed() tries cached index before force-refreshing."""
    pkg = _make_fake_package("en", "de")
    with _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    ) as (fake_pkg, _):
        import gensubtitles.core.translator as _mod
        # Pre-seed the cache so first call uses it
        _mod._pkg_index_cache = [pkg]

        from gensubtitles.core.translator import ensure_pair_installed

        try:
            with patch("tqdm.auto.tqdm") as mock_tqdm:
                mock_tqdm.return_value.__enter__ = MagicMock(return_value=MagicMock())
                mock_tqdm.return_value.__exit__ = MagicMock(return_value=False)
                ensure_pair_installed("en", "de")
        finally:
            _mod._pkg_index_cache = None  # reset to avoid leaking into other tests

    # Package found in cache — should NOT have called update_package_index
    fake_pkg.update_package_index.assert_not_called()
    pkg.download.assert_called_once()


# ── Network failure / offline mode (D-04, D-05, D-06, D-11) ─────────────────


def test_ensure_pair_installed_offline_with_cached_proceeds():
    """D-05: If update_package_index fails but pair is cached, no error raised."""
    en_lang = _make_fake_language("en", ["fr"])
    with _inject_argostranslate(installed_languages=[en_lang]) as (fake_pkg, _):
        fake_pkg.update_package_index.side_effect = ConnectionError("offline")

        from gensubtitles.core.translator import ensure_pair_installed

        # Should not raise — pair is cached, update failure is tolerated
        ensure_pair_installed("en", "fr")


def test_ensure_pair_installed_offline_without_cache_raises_runtime_error():
    """D-06: If offline and pair is not cached, RuntimeError is raised."""
    with _inject_argostranslate(installed_languages=[], available_packages=[]) as (fake_pkg, _):
        fake_pkg.update_package_index.side_effect = ConnectionError("offline")

        from gensubtitles.core.translator import ensure_pair_installed

        with pytest.raises(RuntimeError):
            ensure_pair_installed("en", "fr")


def test_update_index_failure_logs_warning(caplog):
    """D-11: Warning is emitted via logging when update_package_index raises."""
    # Pair NOT pre-installed so update_package_index is actually called
    pkg = _make_fake_package("en", "fr")
    with _inject_argostranslate(installed_languages=[], available_packages=[pkg]) as (fake_pkg, _):
        fake_pkg.update_package_index.side_effect = ConnectionError("no network")

        from gensubtitles.core.translator import ensure_pair_installed

        with caplog.at_level(logging.WARNING, logger="gensubtitles.core.translator"):
            with patch("tqdm.auto.tqdm") as mock_tqdm:
                mock_tqdm.return_value.__enter__ = MagicMock(return_value=MagicMock())
                mock_tqdm.return_value.__exit__ = MagicMock(return_value=False)
                ensure_pair_installed("en", "fr")

    assert any("offline" in record.message or "package index" in record.message for record in caplog.records)


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_translate_segments_empty_list():
    """Edge case: empty segment list returns empty list."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        result = translate_segments([], "en", "es")
    assert result == []


def test_list_installed_pairs_returns_dicts():
    """list_installed_pairs returns list of {"from": ..., "to": ...} dicts."""
    en_lang = _make_fake_language("en", ["es", "fr"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import list_installed_pairs

        pairs = list_installed_pairs()
    assert {"from": "en", "to": "es"} in pairs
    assert {"from": "en", "to": "fr"} in pairs


# ── translate_file() tests ────────────────────────────────────────────────────


def test_translate_file_missing_input_raises():
    """translate_file() raises FileNotFoundError if input path does not exist."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_file

        with pytest.raises(FileNotFoundError, match="not found"):
            translate_file("/nonexistent/file.srt", "es", "en")


# ── TRANS-BATCH: context-batching Argos path ──────────────────────────────────


def test_translate_segments_batch_calls_translate_once_per_hop():
    """TRANS-BATCH-01: For N segments, argostranslate.translate.translate is called
    once per hop (not once per segment)."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]) as (_, fake_translate):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(i, i + 1, f"seg{i}") for i in range(3)]
        translate_segments(segs, "en", "es")

    # 3 segments → 1 batch call (not 3)
    assert fake_translate.translate.call_count == 1


def test_translate_segments_batch_output_correct():
    """TRANS-BATCH-02: Marker round-trip returns the correct translated text for each segment."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        segs = [
            _make_fake_segment(0.0, 1.0, "Hello"),
            _make_fake_segment(1.0, 2.0, "World"),
        ]
        result = translate_segments(segs, "en", "es")

    assert result[0].text == "[es]Hello"
    assert result[1].text == "[es]World"
    assert result[0].start == 0.0
    assert result[1].end == 2.0


def test_translate_segments_batch_mismatch_raises_runtime_error():
    """TRANS-BATCH-03: If translated batch returns fewer markers than segments,
    RuntimeError is raised with specific count message."""
    en_lang = _make_fake_language("en", ["es"])

    def too_few_markers(text: str, src: str, tgt: str) -> str:
        """Returns only marker <1> regardless of how many were sent."""
        return "<1>[es]only one</1>"

    with _inject_argostranslate(installed_languages=[en_lang]) as (_, fake_translate):
        fake_translate.translate.side_effect = too_few_markers
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(i, i + 1, f"s{i}") for i in range(3)]
        with pytest.raises(
            RuntimeError,
            match=r"Batched translation marker mismatch: expected 3 segments, got 1",
        ):
            translate_segments(segs, "en", "es")


def test_translate_segments_two_hop_batches_independently():
    """TRANS-BATCH-04: A two-hop pivot route (ja→en→es) batches each hop separately —
    translate() is called once per hop (2 total calls for 2 hops, N segments)."""
    ja_lang = _make_fake_language("ja", ["en"])
    en_lang = _make_fake_language("en", ["es"])
    hop_calls: list[tuple[str, str]] = []

    def record_hops(text: str, src: str, tgt: str) -> str:
        hop_calls.append((src, tgt))
        return _batch_aware_translate(text, src, tgt)

    with _inject_argostranslate(installed_languages=[ja_lang, en_lang]) as (_, fake_translate):
        fake_translate.translate.side_effect = record_hops
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0, 1, "こんにちは"), _make_fake_segment(1, 2, "世界")]
        translate_segments(segs, "ja", "es")

    # 2 hops → 2 batch calls (not 2 * N)
    assert len(hop_calls) == 2
    assert hop_calls[0] == ("ja", "en")
    assert hop_calls[1] == ("en", "es")


# ── TRANS-ENGINE: DeepL + LibreTranslate engine dispatch ──────────────────────


def test_translate_segments_deepl_missing_key_raises():
    """TRANS-ENGINE-01: engine='deepl' with empty deepl_api_key → RuntimeError with exact message."""
    from unittest.mock import patch as _patch

    from gensubtitles.core.settings import AppSettings

    with _patch(
        "gensubtitles.core.translator.load_settings",
        return_value=AppSettings(deepl_api_key=""),
    ):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0, 1, "Hello")]
        with pytest.raises(
            RuntimeError,
            match="DeepL API key not configured. Set deepl_api_key in settings.",
        ):
            translate_segments(segs, "en", "es", engine="deepl")


def test_translate_segments_libretranslate_missing_url_raises():
    """TRANS-ENGINE-02: engine='libretranslate' with empty libretranslate_url → RuntimeError."""
    from unittest.mock import patch as _patch

    from gensubtitles.core.settings import AppSettings

    with _patch(
        "gensubtitles.core.translator.load_settings",
        return_value=AppSettings(libretranslate_url=""),
    ):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0, 1, "Hello")]
        with pytest.raises(
            RuntimeError,
            match="LibreTranslate URL not configured. Set libretranslate_url in settings.",
        ):
            translate_segments(segs, "en", "es", engine="libretranslate")


def test_translate_segments_deepl_calls_api():
    """TRANS-ENGINE-03: engine='deepl', valid key → deepl.Translator(key).translate_text
    called with all segment texts as a list."""
    from unittest.mock import MagicMock as _MM
    from unittest.mock import patch as _patch

    from gensubtitles.core.settings import AppSettings

    fake_result = [_MM(text="Hola"), _MM(text="Mundo")]
    fake_translator = _MM()
    fake_translator.translate_text.return_value = fake_result
    fake_deepl = _MM()
    fake_deepl.Translator.return_value = fake_translator

    with (
        _patch("gensubtitles.core.translator.load_settings", return_value=AppSettings(deepl_api_key="test-key")),
        _patch.dict("sys.modules", {"deepl": fake_deepl}),
    ):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0, 1, "Hello"), _make_fake_segment(1, 2, "World")]
        result = translate_segments(segs, "en", "es", engine="deepl")

    fake_deepl.Translator.assert_called_once_with("test-key")
    fake_translator.translate_text.assert_called_once_with(["Hello", "World"], target_lang="ES")
    assert result[0].text == "Hola"
    assert result[1].text == "Mundo"


def test_translate_segments_libretranslate_calls_api():
    """TRANS-ENGINE-04: engine='libretranslate', valid url → requests.post called for each segment."""
    from unittest.mock import MagicMock as _MM
    from unittest.mock import patch as _patch

    from gensubtitles.core.settings import AppSettings

    fake_resp = _MM()
    fake_resp.json.return_value = {"translatedText": "Hola"}
    fake_requests = _MM()
    fake_requests.post.return_value = fake_resp

    with (
        _patch(
            "gensubtitles.core.translator.load_settings",
            return_value=AppSettings(libretranslate_url="http://localhost:5000"),
        ),
        _patch.dict("sys.modules", {"requests": fake_requests}),
    ):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0, 1, "Hello")]
        result = translate_segments(segs, "en", "es", engine="libretranslate")

    fake_requests.post.assert_called_once()
    call_kwargs = fake_requests.post.call_args
    assert "http://localhost:5000/translate" in str(call_kwargs)
    assert result[0].text == "Hola"


def test_translate_segments_unknown_engine_raises_value_error():
    """TRANS-ENGINE-05: Unknown engine name → ValueError."""
    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(0, 1, "Hello")]
    with pytest.raises(ValueError, match="Unknown engine 'xyz_engine'"):
        translate_segments(segs, "en", "es", engine="xyz_engine")


def test_translate_file_same_lang_raises():
    """translate_file() raises ValueError when source equals target."""
    import tempfile
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_file

        # Create a minimal SRT file
        with tempfile.NamedTemporaryFile(suffix=".srt", mode="w", delete=False) as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\nHello\n\n")
            f.flush()
            try:
                with pytest.raises(ValueError, match="same"):
                    translate_file(f.name, "en", "en")
            finally:
                import os
                os.unlink(f.name)


def test_translate_file_basic_srt(tmp_path):
    """translate_file() translates an SRT file and writes output."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_file

        srt_content = "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        input_file = tmp_path / "input.srt"
        input_file.write_text(srt_content, encoding="utf-8")

        result = translate_file(input_file, "es", "en")
        assert result.exists()
        assert "_translated" in result.stem


def test_translate_file_custom_output_path(tmp_path):
    """translate_file() respects a custom output_path."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_file

        srt_content = "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        input_file = tmp_path / "input.srt"
        input_file.write_text(srt_content, encoding="utf-8")

        custom_out = tmp_path / "custom_output.srt"
        result = translate_file(input_file, "es", "en", output_path=custom_out)
        assert result == custom_out
        assert custom_out.exists()


def test_translate_file_defaults_source_to_en(tmp_path, caplog):
    """translate_file() defaults source_lang to 'en' when omitted."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_file

        srt_content = "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        input_file = tmp_path / "input.srt"
        input_file.write_text(srt_content, encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="gensubtitles.core.translator"):
            result = translate_file(input_file, "es")

        assert result.exists()
        assert any("defaulting to 'en'" in r.message for r in caplog.records)


# ── Route selection tests (direct vs pivot) ───────────────────────────────────


def test_find_route_direct_when_installed():
    """find_route() returns direct route when pair is already installed."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang], available_packages=[]):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None  # reset cache
        from gensubtitles.core.translator import find_route

        route = find_route("en", "es")
    assert route == [("en", "es")]


def test_find_route_direct_when_available_remotely():
    """find_route() returns direct route when pair is available remotely (not installed)."""
    pkg = _make_fake_package("en", "de")
    with _inject_argostranslate(installed_languages=[], available_packages=[pkg]):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import find_route

        route = find_route("en", "de")
    assert route == [("en", "de")]


def test_find_route_pivot_when_direct_missing():
    """find_route() returns English pivot route when direct pair is unavailable."""
    fr_lang = _make_fake_language("fr", ["en"])
    en_lang = _make_fake_language("en", ["es"])
    # Only fr→en and en→es are installed; no direct fr→es
    with _inject_argostranslate(installed_languages=[fr_lang, en_lang], available_packages=[]):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import find_route

        route = find_route("fr", "es")
    assert route == [("fr", "en"), ("en", "es")]


def test_find_route_raises_when_no_route():
    """find_route() raises RuntimeError when no route exists (direct or pivot)."""
    with _inject_argostranslate(installed_languages=[], available_packages=[]):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import find_route

        with pytest.raises(RuntimeError, match="not available"):
            find_route("xx", "yy")


def test_ensure_route_installed_installs_both_hops():
    """ensure_route_installed() installs both hops of a pivot route."""
    # Only remote packages, nothing installed
    pkg_fr_en = _make_fake_package("fr", "en")
    pkg_en_es = _make_fake_package("en", "es")
    with _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg_fr_en, pkg_en_es],
    ) as (fake_pkg, _):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import ensure_route_installed

        with patch("tqdm.auto.tqdm") as mock_tqdm:
            mock_tqdm.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_tqdm.return_value.__exit__ = MagicMock(return_value=False)
            route = ensure_route_installed("fr", "es")

    assert route == [("fr", "en"), ("en", "es")]
    pkg_fr_en.download.assert_called_once()
    pkg_en_es.download.assert_called_once()


def test_find_route_prefers_installed_over_network():
    """find_route() checks installed pairs first, avoiding network fetch when installed."""
    en_lang = _make_fake_language("en", ["es"])
    pkg = _make_fake_package("en", "es")
    with _inject_argostranslate(installed_languages=[en_lang], available_packages=[pkg]) as (fake_pkg, _):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import find_route

        route = find_route("en", "es")

    assert route == [("en", "es")]
    # Should not have fetched remote index since pair is installed
    fake_pkg.update_package_index.assert_not_called()
    fake_pkg.get_available_packages.assert_not_called()


def test_find_route_prefers_direct_remote_over_installed_pivot():
    """find_route() prefers a direct remote pair over an installed English pivot."""
    # fr→en and en→es are installed (pivot route available)
    # fr→es is only available remotely (direct route)
    fr_lang = _make_fake_language("fr", ["en"])
    en_lang = _make_fake_language("en", ["es"])
    pkg_fr_es = _make_fake_package("fr", "es")
    with _inject_argostranslate(
        installed_languages=[fr_lang, en_lang],
        available_packages=[pkg_fr_es],
    ):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import find_route

        route = find_route("fr", "es")

    # Should pick the direct remote route, not the installed pivot
    assert route == [("fr", "es")]


# ── progress_callback tests ──────────────────────────────────────────────────


def test_translate_segments_progress_callback_single_hop():
    """progress_callback is called once per hop for single-hop route."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        segs = [
            _make_fake_segment(0.0, 1.0, "Hello"),
            _make_fake_segment(1.0, 2.0, "World"),
            _make_fake_segment(2.0, 3.0, "Foo"),
        ]
        calls: list[tuple[int, int]] = []
        translate_segments(segs, "en", "es", progress_callback=lambda c, t: calls.append((c, t)))

    # 1 hop → 1 callback
    assert len(calls) == 1
    assert calls[0] == (1, 1)


def test_translate_segments_progress_callback_multi_hop():
    """progress_callback is called once per hop for multi-hop route."""
    fr_lang = _make_fake_language("fr", ["en"])
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[fr_lang, en_lang]):
        import gensubtitles.core.translator as _mod
        _mod._pkg_index_cache = None
        from gensubtitles.core.translator import translate_segments

        segs = [
            _make_fake_segment(0.0, 1.0, "Bonjour"),
            _make_fake_segment(1.0, 2.0, "Monde"),
        ]
        calls: list[tuple[int, int]] = []
        translate_segments(segs, "fr", "es", progress_callback=lambda c, t: calls.append((c, t)))

    # 2 hops → 2 callbacks
    assert len(calls) == 2
    assert calls == [(1, 2), (2, 2)]


def test_translate_segments_no_callback_when_none():
    """translate_segments works correctly with progress_callback=None (default)."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hello")]
        result = translate_segments(segs, "en", "es", progress_callback=None)
    assert len(result) == 1
    assert result[0].text == "[es]Hello"
