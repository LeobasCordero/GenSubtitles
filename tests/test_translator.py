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
    fake_translate.translate = MagicMock(side_effect=lambda text, src, tgt: f"[{tgt}]{text}")

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
    """TRANS-03: update_package_index() is called before attempting download."""
    pkg = _make_fake_package("en", "fr")
    with _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    ) as (fake_pkg, _):
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


# ── progress_callback tests ──────────────────────────────────────────────────


def test_translate_segments_progress_callback_single_hop():
    """progress_callback is called with monotonic current values for single-hop route."""
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

    assert len(calls) == 3
    # All totals should be equal (1 hop * 3 segments = 3)
    assert all(t == 3 for _, t in calls)
    # Current should be monotonically increasing: 1, 2, 3
    currents = [c for c, _ in calls]
    assert currents == [1, 2, 3]


def test_translate_segments_progress_callback_multi_hop():
    """progress_callback is called with monotonic current and total == len(route) * len(segments)."""
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

    # 2 hops * 2 segments = 4 total callbacks
    assert len(calls) == 4
    # All totals should be 4
    assert all(t == 4 for _, t in calls)
    # Current should be monotonically increasing: 1, 2, 3, 4
    currents = [c for c, _ in calls]
    assert currents == sorted(currents)
    assert currents[-1] == 4


def test_translate_segments_no_callback_when_none():
    """translate_segments works correctly with progress_callback=None (default)."""
    en_lang = _make_fake_language("en", ["es"])
    with _inject_argostranslate(installed_languages=[en_lang]):
        from gensubtitles.core.translator import translate_segments

        segs = [_make_fake_segment(0.0, 1.0, "Hello")]
        result = translate_segments(segs, "en", "es", progress_callback=None)
    assert len(result) == 1
    assert result[0].text == "[es]Hello"
