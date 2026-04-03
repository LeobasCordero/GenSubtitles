"""
Phase 4 translator tests — covers TRANS-01 through TRANS-05.
All tests mock argostranslate via sys.modules for hermetic, offline execution.
"""
from __future__ import annotations

import logging
import sys
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


def _inject_argostranslate(installed_languages=None, available_packages=None):
    """
    Inject fake argostranslate modules into sys.modules.
    Returns (fake_pkg_mod, fake_translate_mod) for per-test assertion.
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

    sys.modules["argostranslate"] = fake_root
    sys.modules["argostranslate.package"] = fake_pkg
    sys.modules["argostranslate.translate"] = fake_translate

    return fake_pkg, fake_translate


# ── TRANS-01: translation changes text and preserves timestamps ───────────────


def test_translate_segments_translates_text():
    """TRANS-01: Each segment's .text is translated."""
    en_lang = _make_fake_language("en", ["es"])
    fake_pkg, fake_translate = _inject_argostranslate(
        installed_languages=[en_lang],
        available_packages=[],
    )

    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(0.0, 2.5, "Hello")]
    result = translate_segments(segs, "en", "es")

    assert len(result) == 1
    assert result[0].text == "[es]Hello"


def test_translate_segments_preserves_timestamps():
    """TRANS-01: .start and .end on translated segments match input."""
    en_lang = _make_fake_language("en", ["es"])
    _inject_argostranslate(installed_languages=[en_lang])

    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(1.5, 4.0, "World")]
    result = translate_segments(segs, "en", "es")

    assert result[0].start == 1.5
    assert result[0].end == 4.0


def test_translate_segments_returns_translated_segment_type():
    """TRANS-01: Result items are TranslatedSegment namedtuples."""
    from collections import namedtuple

    en_lang = _make_fake_language("en", ["es"])
    _inject_argostranslate(installed_languages=[en_lang])

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
    _inject_argostranslate()

    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(0.0, 1.0, "Hello")]
    result = translate_segments(segs, "en", "en")

    assert result is not segs  # returns a new list
    assert result[0] is segs[0]  # but same segment objects


def test_translate_segments_same_lang_no_argos_call():
    """TRANS-02: argostranslate.translate.translate() is never called when source==target."""
    _, fake_translate = _inject_argostranslate()

    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(0.0, 1.0, "Hello")]
    translate_segments(segs, "fr", "fr")

    fake_translate.translate.assert_not_called()


# ── TRANS-03: packages installed on first use ─────────────────────────────────


def test_ensure_pair_installed_downloads_missing_pair():
    """TRANS-03: download() and install_from_path() are called for an absent pair."""
    pkg = _make_fake_package("en", "fr")
    fake_pkg, _ = _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    )

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
    fake_pkg, _ = _inject_argostranslate(
        installed_languages=[],
        available_packages=[pkg],
    )
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
    _inject_argostranslate(installed_languages=[], available_packages=[])

    from gensubtitles.core.translator import is_pair_available

    with pytest.raises(ValueError, match="en→tlh"):
        is_pair_available("en", "tlh")


def test_is_pair_available_true_when_installed():
    """TRANS-04: Returns True when pair is already installed."""
    en_lang = _make_fake_language("en", ["fr"])
    _inject_argostranslate(installed_languages=[en_lang])

    from gensubtitles.core.translator import is_pair_available

    assert is_pair_available("en", "fr") is True


def test_is_pair_available_true_when_remote_only():
    """TRANS-04: Returns True when pair exists in available packages (not yet installed)."""
    pkg = _make_fake_package("en", "de")
    _inject_argostranslate(installed_languages=[], available_packages=[pkg])

    from gensubtitles.core.translator import is_pair_available

    assert is_pair_available("en", "de") is True


def test_translate_segments_unknown_pair_raises_runtime_error():
    """TRANS-04: translate_segments raises RuntimeError when pair cannot be installed."""
    _inject_argostranslate(installed_languages=[], available_packages=[])

    from gensubtitles.core.translator import translate_segments

    segs = [_make_fake_segment(0.0, 1.0, "Hello")]
    with pytest.raises(RuntimeError):
        translate_segments(segs, "en", "klingon")


# ── TRANS-05: models cached, not re-downloaded ────────────────────────────────


def test_ensure_pair_installed_no_op_when_already_installed():
    """TRANS-05: No download when pair is already installed."""
    en_lang = _make_fake_language("en", ["fr"])
    fake_pkg, _ = _inject_argostranslate(installed_languages=[en_lang])

    from gensubtitles.core.translator import ensure_pair_installed

    ensure_pair_installed("en", "fr")

    fake_pkg.install_from_path.assert_not_called()


def test_ensure_pair_installed_no_download_call_when_cached():
    """TRANS-05: pkg.download() is never called when pair is in installed languages."""
    en_lang = _make_fake_language("en", ["fr"])
    pkg = _make_fake_package("en", "fr")
    _inject_argostranslate(installed_languages=[en_lang], available_packages=[pkg])

    from gensubtitles.core.translator import ensure_pair_installed

    ensure_pair_installed("en", "fr")

    pkg.download.assert_not_called()


# ── Network failure / offline mode (D-04, D-05, D-06, D-11) ─────────────────


def test_ensure_pair_installed_offline_with_cached_proceeds():
    """D-05: If update_package_index fails but pair is cached, no error raised."""
    en_lang = _make_fake_language("en", ["fr"])
    fake_pkg, _ = _inject_argostranslate(installed_languages=[en_lang])
    fake_pkg.update_package_index.side_effect = ConnectionError("offline")

    from gensubtitles.core.translator import ensure_pair_installed

    # Should not raise — pair is cached, update failure is tolerated
    ensure_pair_installed("en", "fr")


def test_ensure_pair_installed_offline_without_cache_raises_runtime_error():
    """D-06: If offline and pair is not cached, RuntimeError is raised."""
    fake_pkg, _ = _inject_argostranslate(installed_languages=[], available_packages=[])
    fake_pkg.update_package_index.side_effect = ConnectionError("offline")

    from gensubtitles.core.translator import ensure_pair_installed

    with pytest.raises(RuntimeError):
        ensure_pair_installed("en", "fr")


def test_update_index_failure_logs_warning(caplog):
    """D-11: Warning is emitted via logging when update_package_index raises."""
    # Pair NOT pre-installed so update_package_index is actually called
    pkg = _make_fake_package("en", "fr")
    fake_pkg, _ = _inject_argostranslate(installed_languages=[], available_packages=[pkg])
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
    _inject_argostranslate(installed_languages=[en_lang])

    from gensubtitles.core.translator import translate_segments

    result = translate_segments([], "en", "es")
    assert result == []


def test_list_installed_pairs_returns_dicts():
    """list_installed_pairs returns list of {"from": ..., "to": ...} dicts."""
    en_lang = _make_fake_language("en", ["es", "fr"])
    _inject_argostranslate(installed_languages=[en_lang])

    from gensubtitles.core.translator import list_installed_pairs

    pairs = list_installed_pairs()
    assert {"from": "en", "to": "es"} in pairs
    assert {"from": "en", "to": "fr"} in pairs
