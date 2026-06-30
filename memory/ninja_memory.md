# Ninja Memory

## Session Log
- **2026-06-30** — Worked issue #1: Teams `transcribe.py` was broken. Three root
  causes fixed (PR #2, merged): SharePoint path URLs 401'd on direct GET →
  Graph `/shares` fallback; `whisper-1` unreachable by gateway key → use
  `openai/openai/gpt-4o-transcribe`; `mimetypes.guess_extension("audio/wav")`
  returns `None` and mislabeled WAVs → robust `_audio_ext()`. Verified
  end-to-end on the real SharePoint WAV. Reflect phase: extracted the download
  logic into reusable `tools/graph_fetch.py` (CLI + API), registered in
  `tools/README.md`.

## Technical Decisions
- **Attachment downloads**: always go through `tools/graph_fetch.py` — direct
  GET works only for pre-authenticated `downloadUrl` links; SharePoint *path*
  URLs need Graph `/shares/{u!base64url}/driveItem/content`.
- **Transcription model**: gateway key is scoped; `openai/openai/gpt-4o-transcribe`
  (doubled prefix) is the working id. `whisper-1` / un-prefixed names → 401.

## Pending Items
- **Issue #3** (filed) — Slack `transcribe.py:70` has the same `whisper-1` bug →
  401. Its download uses a Slack bot token (not Graph), so only the model needs
  fixing. Suggested a shared `transcribe_bytes()` helper to stop drift.
- **Issue #4** (filed) — WhatsApp `transcribe.py` is an unimplemented stub.
- **Toolkit idea** (captured in #3): extract one shared transcription helper
  (owns model id `openai/openai/gpt-4o-transcribe` + `/v1/audio/transcriptions`
  endpoint) so Teams/Slack/WhatsApp can't diverge again. Build it when #3 is
  worked, not before.
