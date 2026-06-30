"""Tests for ``messaging/teams/transcribe.py``.

Guards the #6 de-dup: Teams must download via the shared
``tools.graph_fetch.fetch_bytes`` (not a private copy of the /shares logic) and
hand the bytes to the shared ``transcribe_bytes``. All network-free.
"""

import messaging.teams.transcribe as TT


def test_transcribe_routes_through_graph_fetch(monkeypatch):
    calls = {}

    def fake_fetch_bytes(url, *a, **k):
        calls["fetch_url"] = url
        return b"AUDIODATA", "audio/wav"

    def fake_transcribe_bytes(content, filename, content_type):
        calls["content"] = content
        calls["filename"] = filename
        calls["content_type"] = content_type
        return "the transcript"

    monkeypatch.setattr(TT, "fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(TT, "transcribe_bytes", fake_transcribe_bytes)

    out = TT.transcribe("https://host/sites/x/Shared Documents/clip.wav")

    assert out == "the transcript"
    # downloaded via the shared helper, with the given URL
    assert calls["fetch_url"] == "https://host/sites/x/Shared Documents/clip.wav"
    # the downloaded bytes are forwarded unchanged to the shared transcriber
    assert calls["content"] == b"AUDIODATA"
    # extension derived from the URL/content-type (.wav here)
    assert calls["filename"] == "audio.wav"
    assert calls["content_type"] == "audio/wav"


def test_octet_stream_falls_back_to_mp4(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        TT, "fetch_bytes", lambda url, *a, **k: (b"x", "application/octet-stream")
    )
    monkeypatch.setattr(
        TT,
        "transcribe_bytes",
        lambda content, filename, content_type: calls.update(
            filename=filename, content_type=content_type
        )
        or "ok",
    )

    # URL has no usable suffix → generic content type must fall back to mp4/.m4a
    TT.transcribe("https://host/driveItem/content")
    assert calls["content_type"] == "audio/mp4"
    assert calls["filename"] == "audio.m4a"


def test_no_private_download_helpers_remain():
    # The /shares logic now lives only in tools.graph_fetch; Teams must not
    # reintroduce its own copy.
    assert not hasattr(TT, "_download_audio")
    assert not hasattr(TT, "_share_id")
