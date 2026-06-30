#!/usr/bin/env python3
"""Transcribe a Slack audio/voice message to text.

Downloads the audio file using the Slack bot token, then transcribes the bytes
via the shared transcription core. Prints the transcript to stdout.

Usage:
    python messaging/slack/transcribe.py <download_url>

Auth:
    Reads ``bot_token`` from ``~/.agent_settings.json``.
    The LiteLLM API key is read via ``clients.litellm_client.get_config()``.

Model:
    Uses ``messaging.transcription`` (default ``openai/openai/gpt-4o-transcribe``;
    override with ``NINJA_TRANSCRIBE_MODEL``). ``whisper-1`` is not reachable by
    the gateway key.

Exit codes:
    0  — transcript printed to stdout
    1  — missing argument, download failure, or transcription failure
"""

import json
import sys
from pathlib import Path

import requests
from messaging.transcription import audio_ext, transcribe_bytes


def transcribe(download_url: str) -> str:
    """Download ``download_url`` with Slack auth and return the transcript.

    Args:
        download_url: The ``url_private_download`` value from the Slack file object.

    Returns:
        Transcript text string.

    Raises:
        RuntimeError: If the download or transcription request fails.
    """
    # --- auth ---
    settings_path = Path.home() / ".agent_settings.json"
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {settings_path}: {exc}") from exc

    bot_token = settings.get("bot_token", "")
    if not bot_token:
        raise RuntimeError(
            f"No 'bot_token' found in {settings_path}. "
            "Run: python messaging/slack/interface.py config --set-channel <channel>"
        )

    # --- download audio ---
    audio_resp = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {bot_token}"},
        timeout=60,
    )
    if not audio_resp.ok:
        raise RuntimeError(
            f"Audio download failed ({audio_resp.status_code}): {audio_resp.text[:200]}"
        )

    # --- transcribe ---
    content_type = (audio_resp.headers.get("Content-Type") or "audio/webm").split(";")[
        0
    ].strip() or "audio/webm"
    ext = audio_ext(download_url, content_type)
    return transcribe_bytes(audio_resp.content, f"audio{ext}", content_type)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: transcribe.py <download_url>", file=sys.stderr)
        sys.exit(1)

    try:
        print(transcribe(sys.argv[1]))
    except (RuntimeError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
