"""
gensubtitles.exceptions
~~~~~~~~~~~~~~~~~~~~~~~
Shared exception hierarchy for all GenSubtitles modules.

Import from here in core modules to avoid circular imports:
    from gensubtitles.exceptions import AudioExtractionError
"""


class GenSubtitlesError(RuntimeError):
    """Base exception for all GenSubtitles errors."""


class AudioExtractionError(GenSubtitlesError):
    """
    Raised when FFmpeg fails to extract audio from a video file.

    The exception message includes the full FFmpeg stderr output for diagnostics.
    """


class TranscriptionError(GenSubtitlesError):
    """Raised when faster-whisper transcription fails."""
