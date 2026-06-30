"""Pytest session setup.

Set ``NINJA_TEST_MODE=1`` before any test module (and therefore any application
module) is imported. Several modules guard import-time side effects on this flag
— e.g. ``messaging/slack/interface.py`` skips creating ``/workspace/logs`` at
import. pytest imports this conftest before collecting test files, so the flag is
in place in time. CI also sets it at the job level; ``setdefault`` keeps any
externally-provided value.
"""

import os

os.environ.setdefault("NINJA_TEST_MODE", "1")
