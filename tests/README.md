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
- **`NINJA_TEST_MODE=1`** is set automatically by the root `conftest.py` before
  any module is imported (CI also sets it at the job level). Some modules guard
  import-time side effects on it — e.g. `messaging/slack/interface.py` skips its
  `/workspace/logs` mkdir — so importing real interface modules is safe under
  test, on any machine. Don't unset it during a test run.

## What's covered

| File | Guards |
|------|--------|
| `test_transcription.py` | Shared transcription core (`messaging/transcription.py`): model id is `openai/openai/gpt-4o-transcribe` (never whisper-1 again — issues #1/#3), `audio_ext` content-type fallback (the `audio/wav`→`.m4a` mislabel bug), and no-intelligible-speech handling. |
| `test_teams_transcribe.py` | Teams downloads via `tools.graph_fetch.fetch_bytes` (issue #6); private download helpers stay gone. |
| `test_lazy_channel_imports.py` | Leaf utility imports don't drag in the channel interface stack (issue #13); lazy `__getattr__` export still resolves. |
| `test_interface_imports.py` | Real channel interface modules import cleanly under `NINJA_TEST_MODE=1` (issue #15). |
