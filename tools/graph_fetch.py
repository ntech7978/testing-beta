#!/usr/bin/env python3
"""Download a Microsoft Teams / SharePoint attachment to disk (or stdout).

Microsoft sends attachment links in two flavours:

* **Pre-authenticated** ``@microsoft.graph.downloadUrl`` links — a plain
  authenticated ``GET`` returns the bytes.
* **SharePoint / Graph *path* URLs** (e.g. a ``contentUrl`` ending in
  ``/Shared Documents/folder/file.ext``) — a plain ``GET`` returns **401**.
  These must be resolved through the Graph ``/shares`` endpoint:
  ``/shares/{share_id}/driveItem/content`` where
  ``share_id = "u!" + base64url(url)``.

This tool tries the direct download first and transparently falls back to the
``/shares`` route, so callers don't have to care which kind of URL they have.
It is the shared download primitive behind ``messaging/teams/transcribe.py`` and
any future file-attachment handling (PDF/doc explain, image OCR, etc.).

Auth:
    Reads ``teams.access_token`` from ``~/.agent_settings.json`` (the Graph token
    persisted by install/teams.sh).

Usage:
    # Save to a path (prints the path on success)
    python tools/graph_fetch.py "<url>" -o /tmp/file.wav

    # Save to a temp file and print its path
    python tools/graph_fetch.py "<url>"

    # Stream raw bytes to stdout (for piping)
    python tools/graph_fetch.py "<url>" --stdout > file.bin

    # JSON metadata (path, bytes, content_type)
    python tools/graph_fetch.py "<url>" -o /tmp/f.pdf --json

Python API:
    from tools.graph_fetch import fetch_bytes, fetch_to_file
    content, content_type = fetch_bytes(url)
    path = fetch_to_file(url, "/tmp/file.pdf")

Exit codes:
    0  — success
    1  — missing argument / auth / download failure
"""

import argparse
import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

GRAPH_SHARES = "https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/content"


def get_access_token() -> str:
    """Return the Microsoft Graph access token from ``~/.agent_settings.json``."""
    settings_path = Path.home() / ".agent_settings.json"
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read {settings_path}: {exc}") from exc
    token = (settings.get("teams") or {}).get("access_token", "")
    if not token:
        raise RuntimeError(
            f"No 'teams.access_token' found in {settings_path}. "
            "Run: python messaging/teams/interface.py config --set-access-token <token>"
        )
    return token


def share_id(url: str) -> str:
    """Encode a sharing/path URL as a Graph share id (``u!<base64url>``)."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    return "u!" + b64


def fetch_bytes(url: str, token: str | None = None, *, timeout: float = 60.0):
    """Download ``url`` and return ``(content_bytes, content_type)``.

    Tries a direct authenticated GET first (pre-authenticated downloadUrls),
    then falls back to the Graph ``/shares`` endpoint for SharePoint/path URLs.

    Raises:
        RuntimeError: If both download strategies fail.
    """
    token = token or get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.ok:
        return resp.content, _content_type(resp)

    if resp.status_code in (401, 403):
        shared = requests.get(
            GRAPH_SHARES.format(share_id=share_id(url)),
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        if shared.ok:
            return shared.content, _content_type(shared)
        raise RuntimeError(
            f"Download failed — direct GET ({resp.status_code}) and Graph "
            f"/shares ({shared.status_code}): {shared.text[:200]}"
        )

    raise RuntimeError(f"Download failed ({resp.status_code}): {resp.text[:200]}")


def fetch_to_file(url: str, out_path: str | None = None, token: str | None = None) -> str:
    """Download ``url`` to ``out_path`` (or a temp file) and return the path."""
    content, _ = fetch_bytes(url, token)
    if out_path is None:
        suffix = Path(unquote(urlsplit(url).path)).suffix or ".bin"
        fd, out_path = tempfile.mkstemp(suffix=suffix, prefix="graph_fetch_")
        os.close(fd)
    Path(out_path).write_bytes(content)
    return out_path


def _content_type(resp: requests.Response) -> str:
    return (resp.headers.get("Content-Type") or "application/octet-stream").split(";")[
        0
    ].strip() or "application/octet-stream"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download a Teams/SharePoint attachment (downloadUrl or path URL)."
    )
    parser.add_argument("url", help="Attachment URL (downloadUrl or SharePoint path)")
    parser.add_argument("-o", "--output", help="Write to this path (default: temp file)")
    parser.add_argument(
        "--stdout", action="store_true", help="Stream raw bytes to stdout"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print JSON metadata (path, bytes, type)"
    )
    args = parser.parse_args(argv)

    try:
        if args.stdout:
            content, _ = fetch_bytes(args.url)
            sys.stdout.buffer.write(content)
            return 0
        content, content_type = fetch_bytes(args.url)
        out_path = args.output
        if out_path is None:
            suffix = Path(unquote(urlsplit(args.url).path)).suffix or ".bin"
            fd, out_path = tempfile.mkstemp(suffix=suffix, prefix="graph_fetch_")
            os.close(fd)
        Path(out_path).write_bytes(content)
        if args.json:
            print(
                json.dumps(
                    {
                        "path": out_path,
                        "bytes": len(content),
                        "content_type": content_type,
                    }
                )
            )
        else:
            print(out_path)
        return 0
    except (RuntimeError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
