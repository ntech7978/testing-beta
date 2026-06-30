"""Regression tests for ``messaging/transcription.py`` (the shared audio core).

These guard the exact failures we already hit in production:

* whisper-1 was used against a key that only allows
  ``openai/openai/gpt-4o-transcribe`` (issues #1, #3) — so we assert the model id
  the request actually sends.
* ``mimetypes.guess_extension("audio/wav")`` returns ``None`` and mislabeled
  WAVs — so we assert the content-type fallback map is used.
* non-speech audio returned empty/punctuation junk — so we assert it raises.

All tests are network-free: ``requests.post`` and the gateway config are mocked.

Run:  pytest tests/test_transcription.py
"""

import importlib

import pytest

from messaging import transcription as T


class _FakeResp:
    """Minimal stand-in for a ``requests.Response``."""

    def __init__(self, *, ok=True, status_code=200, payload=None, text=""):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


@pytest.fixture
def captured_post(monkeypatch):
    """Patch transcribe_bytes' network deps; return a dict capturing the POST.

    The returned dict has a ``response`` slot the test sets before calling, and
    records ``url`` / ``data`` / ``files`` from the intercepted ``requests.post``.
    """
    box = {"response": _FakeResp(payload={"text": "hello world"}), "data": None}

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        box["url"] = url
        box["headers"] = headers
        box["files"] = files
        box["data"] = data
        return box["response"]

    monkeypatch.setattr(T.requests, "post", fake_post)
    monkeypatch.setattr(T, "get_config", lambda: {"api_key": "test-key"})
    monkeypatch.setattr(T, "api_url", lambda path: f"http://test{path}")
    return box


# --------------------------------------------------------------------------- #
# audio_ext
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "source,content_type,expected",
    [
        ("https://x/clip.wav", "application/octet-stream", ".wav"),
        ("https://x/clip.webm", "application/octet-stream", ".webm"),
        ("https://files.slack.com/clip.mp3?t=1", "audio/mpeg", ".mp3"),
    ],
)
def test_audio_ext_url_suffix_wins(source, content_type, expected):
    assert T.audio_ext(source, content_type) == expected


def test_audio_ext_ct_map_for_wav():
    # mimetypes.guess_extension("audio/wav") is None on many systems; the
    # explicit map must still resolve it (the bug that mislabeled WAVs as .m4a).
    assert T.audio_ext("https://x/voicenote", "audio/wav") == ".wav"


def test_audio_ext_fallback_m4a():
    assert T.audio_ext("https://x/voicenote", "application/unknown") == ".m4a"


# --------------------------------------------------------------------------- #
# model id
# --------------------------------------------------------------------------- #
def test_default_model_is_gpt4o_transcribe():
    assert T.TRANSCRIBE_MODEL == "openai/openai/gpt-4o-transcribe"


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("NINJA_TRANSCRIBE_MODEL", "openai/openai/custom-asr")
    reloaded = importlib.reload(T)
    try:
        assert reloaded.TRANSCRIBE_MODEL == "openai/openai/custom-asr"
    finally:
        # Restore the module's default for the rest of the suite.
        monkeypatch.delenv("NINJA_TRANSCRIBE_MODEL", raising=False)
        importlib.reload(T)


# --------------------------------------------------------------------------- #
# transcribe_bytes
# --------------------------------------------------------------------------- #
def test_transcribe_bytes_sends_correct_model(captured_post):
    # This is the core regression guard: never whisper-1 again.
    out = T.transcribe_bytes(b"\x00\x01", "audio.wav", "audio/wav")
    assert out == "hello world"
    assert captured_post["data"]["model"] == "openai/openai/gpt-4o-transcribe"
    assert captured_post["data"]["model"] != "whisper-1"
    # filename + content type are forwarded for container detection
    assert captured_post["files"]["file"][0] == "audio.wav"


def test_transcribe_bytes_raises_on_http_error(captured_post):
    captured_post["response"] = _FakeResp(
        ok=False, status_code=401, text="key_model_access_denied"
    )
    with pytest.raises(RuntimeError, match="Transcription failed"):
        T.transcribe_bytes(b"x", "audio.wav", "audio/wav")


@pytest.mark.parametrize("junk", ["", "   ", '"""', "--", ".", "\n"])
def test_transcribe_bytes_no_intelligible_speech(captured_post, junk):
    captured_post["response"] = _FakeResp(payload={"text": junk})
    with pytest.raises(RuntimeError, match="no intelligible speech"):
        T.transcribe_bytes(b"x", "audio.wav", "audio/wav")


def test_transcribe_bytes_accepts_real_text(captured_post):
    captured_post["response"] = _FakeResp(payload={"text": "Meeting at 3pm."})
    assert T.transcribe_bytes(b"x", "audio.wav", "audio/wav") == "Meeting at 3pm."
