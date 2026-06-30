#!/usr/bin/env python3
"""Shared audio-transcription core for all messaging channels.

Each channel (Teams, Slack, WhatsApp) downloads audio its own way — Graph
``/shares`` for Teams, a Slack bot token for Slack, the WhatsApp media API for
WhatsApp — but they all transcribe the resulting bytes the *same* way. This
module owns that shared part (model id, endpoint, empty-result handling, and
file-extension detection) so the channels can't drift apart again.

Channels should:

1. Download the audio bytes themselves.
2. Pick an upload filename with :func:`audio_ext` (or pass their own).
3. Call :func:`transcribe_bytes` and print/return the transcript.

Model:
    Defaults to ``openai/openai/gpt-4o-transcribe`` — the transcription model the
    LiteLLM gateway key is allowed to reach (``whisper-1`` is rejected with a 401
    and is not in the catalog). Override with the ``NINJA_TRANSCRIBE_MODEL`` env
    var.
"""

import mimetypes
import os
from pathlib import Path

import requests
from clients.litellm_client import api_url, get_config

# Transcription model. The gateway key is scoped, so the public ``whisper-1`` id
# is rejected; ``openai/openai/gpt-4o-transcribe`` is the working default.
TRANSCRIBE_MODEL = os.environ.get(
    "NINJA_TRANSCRIBE_MODEL", "openai/openai/gpt-4o-transcribe"
)

# Whisper/gpt-4o-transcribe accept these container extensions. mimetypes is
# unreliable here (e.g. guess_extension("audio/wav") returns None on many
# systems), so map the common audio content types explicitly.
_CT_EXT = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
}
_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".webm", ".flac", ".mpga", ".oga"}


def audio_ext(source: str, content_type: str) -> str:
    """Pick a Whisper-recognized file extension for the upload.

    Prefers the real extension in ``source`` (a URL or filename), then the
    content-type map, then ``mimetypes``, falling back to ``.m4a``.
    """
    src_ext = Path(source.split("?", 1)[0].split("#", 1)[0]).suffix.lower()
    if src_ext in _AUDIO_EXTS:
        return src_ext
    return _CT_EXT.get(content_type) or mimetypes.guess_extension(content_type) or ".m4a"


def transcribe_bytes(
    content: bytes, filename: str, content_type: str = "application/octet-stream"
) -> str:
    """Transcribe raw audio ``content`` via the LiteLLM transcription endpoint.

    Args:
        content: The audio file bytes.
        filename: Upload filename whose extension the model uses to detect the
            container (e.g. ``audio.wav``). Use :func:`audio_ext` to build it.
        content_type: MIME type of the audio.

    Returns:
        The transcript text.

    Raises:
        RuntimeError: On a non-2xx response, or when the model returns no
            intelligible speech (empty/punctuation-only output for silence,
            tones, or noise).
    """
    cfg = get_config()
    resp = requests.post(
        api_url("/v1/audio/transcriptions"),
        headers={"Authorization": f"Bearer {cfg['api_key']}"},
        files={"file": (filename, content, content_type)},
        data={"model": TRANSCRIBE_MODEL},
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Transcription failed ({resp.status_code}): {resp.text[:200]}"
        )

    text = resp.json().get("text", "")
    # gpt-4o-transcribe emits empty/punctuation-only output for non-speech audio
    # (silence, tones, noise). Treat that as "no speech" rather than returning junk.
    if not text.strip() or not any(ch.isalnum() for ch in text):
        raise RuntimeError(
            "Transcription returned no intelligible speech "
            "(audio may be silent, non-speech, or corrupted)."
        )
    return text
