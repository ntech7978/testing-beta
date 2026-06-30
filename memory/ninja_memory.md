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
- Slack/WhatsApp `transcribe.py` variants likely share the same two bugs
  (whisper-1 + direct-GET download). Not in scope for issue #1 — file a follow-up
  if those channels are used. Could also refactor them onto `graph_fetch.py`.
