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
- **Transcription core is shared**: `messaging/transcription.py` owns the model
  id + endpoint + no-speech handling via `transcribe_bytes(content, filename,
  content_type)` and `audio_ext(source, content_type)`. Teams + Slack both route
  through it (PR #5). Each channel only does its own download. WhatsApp (#4)
  should reuse it too — do NOT re-hardcode the model.

## Pending Items (work queue — one issue per cycle)
- **Issue #4** — WhatsApp `transcribe.py` is an unimplemented stub. Implement
  using `messaging/transcription.py` + (likely) `tools/graph_fetch.py`-style
  download; do NOT re-hardcode the model. **Blocks on creds for live e2e** (no
  whatsapp config in settings) — code + mocked tests, then block if only live
  verification remains. **Heads-up:** any test that imports a `messaging.<chan>`
  package triggers that package's `__init__` (e.g. `messaging/teams/__init__`
  imports the full interface → httpx); CI now installs `infra/requirements.txt`
  so that resolves, but keep tests' own logic network-free.

## Testing & CI
- **Runner: `pytest`** (network-free; mock `requests`/`httpx`/`get_config`/
  `api_url`). `python -m pytest` from repo root. Convention in `tests/README.md`.
  Suites: `tests/test_transcription.py` (16), `tests/test_teams_transcribe.py` (3).
- **CI is live** (`.github/workflows/test.yml`, issue #10 / PR #11): runs pytest
  on push to main + every PR. Installs `infra/requirements.txt` (PR #12) — a
  hand-picked `pytest requests` was NOT enough because importing a channel
  module drags in its package `__init__` deps (httpx etc.). #9 was a concurrent
  duplicate of #10 and is CLOSED.

## Environment facts
- `~/.agent_settings.json` has only `teams` + `default_agent` — **no whatsapp /
  slack creds**. So #4 (WhatsApp) can be coded but not verified e2e until creds
  exist; annotated on the issue. Slack transcribe (#3) likewise unverifiable e2e.

## Resolved this session
- #1 (Teams transcribe, PR #2), #3 (Slack transcribe + shared helper, PR #5),
  #7 (transcription regression tests, PR #8), #10 (CI, PR #11),
  #6 (Teams download → graph_fetch de-dup, PR #12).
- Built `tools/graph_fetch.py`, `messaging/transcription.py`, `tests/` suite, CI.

## What to try next
- Prefer fixing duplication at the root (shared helper) over copy-paste — paid
  off in #3. Watch for the same pattern in the WhatsApp work (#4).
- New code paths should ship with a network-free pytest now that the convention
  exists.
