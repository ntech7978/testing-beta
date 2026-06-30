# Tests

Unit tests for Ninja. **Runner: `pytest`.**

```bash
# from the repo root
python -m pytest                     # whole suite
python -m pytest tests/test_transcription.py -v
```

## Conventions

- **Network-free & deterministic.** No real HTTP, no credentials, no live
  gateway. Mock `requests` (and `get_config` / `api_url`) so tests run anywhere,
  including CI. See `tests/test_transcription.py` for the pattern.
- **One file per module under test**, named `test_<module>.py`.
- Tests import modules by their package path (e.g.
  `from messaging import transcription`) — run from the repo root so imports
  resolve.

## What's covered

| File | Guards |
|------|--------|
| `test_transcription.py` | Shared transcription core (`messaging/transcription.py`): model id is `openai/openai/gpt-4o-transcribe` (never whisper-1 again — issues #1/#3), `audio_ext` content-type fallback (the `audio/wav`→`.m4a` mislabel bug), and no-intelligible-speech handling. |
