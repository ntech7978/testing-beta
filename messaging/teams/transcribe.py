#!/usr/bin/env python3
"""Transcribe a Microsoft Teams audio/voice message to text.

Downloads the audio file using the Microsoft Graph access token, then sends it
to the LiteLLM transcription endpoint. Prints the transcript to stdout.

Usage:
    python messaging/teams/transcribe.py <download_url>

Auth:
    Reads ``teams.access_token`` from ``~/.agent_settings.json`` (the Graph token
    persisted by install/teams.sh). The LiteLLM API key is read via
    ``clients.litellm_client.get_config()``.

Download:
    Delegated to ``tools.graph_fetch.fetch_bytes`` — it handles pre-authenticated
    ``@microsoft.graph.downloadUrl`` links and falls back to the Graph
    ``/shares/{share_id}/driveItem/content`` endpoint for SharePoint *path* URLs
    (which 401 on a plain GET). It also loads the ``teams.access_token``.

Model:
    Defaults to ``openai/openai/gpt-4o-transcribe`` (the transcription model the
    gateway key is allowed to reach — ``whisper-1`` is not available). Override
    with the ``NINJA_TRANSCRIBE_MODEL`` env var.

Exit codes:
    0  — transcript printed to stdout
    1  — missing argument, download failure, or transcription failure
"""

import sys

import requests
from messaging.transcription import audio_ext, transcribe_bytes
from tools.graph_fetch import fetch_bytes


def transcribe(download_url: str) -> str:
    """Download ``download_url`` with Graph auth and return the transcript.

    Args:
        download_url: The file download URL from the Teams message attachment
            (``contentUrl`` / ``@microsoft.graph.downloadUrl``).

    Returns:
        Transcript text string.

    Raises:
        RuntimeError: If the download or transcription request fails.
    """
    # --- download audio ---
    # tools.graph_fetch owns auth (teams.access_token) + the direct-GET → Graph
    # /shares fallback for SharePoint path URLs, and returns (bytes, content_type).
    content, content_type = fetch_bytes(download_url)

    # Teams voice notes are typically mp4; fall back to that when the server omits
    # a usable content type, then name the upload with a recognized extension.
    if not content_type or content_type == "application/octet-stream":
        content_type = "audio/mp4"
    ext = audio_ext(download_url, content_type)

    # --- transcribe ---
    return transcribe_bytes(content, f"audio{ext}", content_type)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: transcribe.py <download_url>", file=sys.stderr)
        sys.exit(1)

    try:
        print(transcribe(sys.argv[1]))
    except (RuntimeError, requests.RequestException) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
