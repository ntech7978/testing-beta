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
    Pre-authenticated ``@microsoft.graph.downloadUrl`` links are fetched
    directly. SharePoint/Graph *path* URLs (e.g. ``contentUrl`` ending in
    ``/Shared Documents/...``) return 401 on a plain GET, so we fall back to the
    Graph ``/shares/{share_id}/driveItem/content`` endpoint which accepts any
    sharing or path URL.

Model:
    Defaults to ``openai/openai/gpt-4o-transcribe`` (the transcription model the
    gateway key is allowed to reach — ``whisper-1`` is not available). Override
    with the ``NINJA_TRANSCRIBE_MODEL`` env var.

Exit codes:
    0  — transcript printed to stdout
    1  — missing argument, download failure, or transcription failure
"""

import base64
import json
import sys
from pathlib import Path

import requests
from messaging.transcription import audio_ext, transcribe_bytes


def _share_id(url: str) -> str:
    """Encode a sharing/path URL as a Graph share id (``u!<base64url>``)."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    return "u!" + b64


def _download_audio(download_url: str, access_token: str) -> requests.Response:
    """Fetch the audio bytes, resolving SharePoint path URLs via Graph /shares.

    Args:
        download_url: The attachment URL (downloadUrl or SharePoint/Graph path).
        access_token: Microsoft Graph bearer token.

    Returns:
        The successful :class:`requests.Response` holding the audio bytes.

    Raises:
        RuntimeError: If both the direct and Graph /shares downloads fail.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Direct GET — works for pre-authenticated @microsoft.graph.downloadUrls.
    resp = requests.get(download_url, headers=headers, timeout=60)
    if resp.ok:
        return resp

    # 2. SharePoint/Graph path URLs 401/403 on a plain GET. Resolve them through
    #    the Graph /shares endpoint, which accepts any sharing or path URL.
    if resp.status_code in (401, 403):
        share_url = (
            "https://graph.microsoft.com/v1.0/shares/"
            f"{_share_id(download_url)}/driveItem/content"
        )
        shared = requests.get(
            share_url, headers=headers, timeout=60, allow_redirects=True
        )
        if shared.ok:
            return shared
        raise RuntimeError(
            f"Audio download failed — direct GET ({resp.status_code}) and Graph "
            f"/shares ({shared.status_code}): {shared.text[:200]}"
        )

    raise RuntimeError(
        f"Audio download failed ({resp.status_code}): {resp.text[:200]}"
    )


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
    # --- auth ---
    settings_path = Path.home() / ".agent_settings.json"
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {settings_path}: {exc}") from exc

    access_token = (settings.get("teams") or {}).get("access_token", "")
    if not access_token:
        raise RuntimeError(
            f"No 'teams.access_token' found in {settings_path}. "
            "Run: python messaging/teams/interface.py config --set-access-token <token>"
        )

    # --- download audio ---
    audio_resp = _download_audio(download_url, access_token)

    # Name the upload with an extension the model recognizes, derived from the
    # download response's content type (Teams voice notes are typically audio/mp4).
    content_type = (audio_resp.headers.get("Content-Type") or "audio/mp4").split(";")[
        0
    ].strip() or "audio/mp4"
    ext = audio_ext(download_url, content_type)

    # --- transcribe ---
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
