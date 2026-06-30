"""Smoke test: the real channel interface modules import cleanly under test.

This guards the #15 fix: with ``NINJA_TEST_MODE=1`` (set by conftest.py and in
CI), importing the real interfaces must not blow up on import-time side effects
like ``messaging/slack/interface.py``'s ``/workspace/logs`` mkdir. Complements
``test_lazy_channel_imports.py`` (which proves leaf imports stay light) by
proving the heavy path still works on demand.
"""

import importlib

import pytest

INTERFACES = [
    ("messaging.teams.interface", "TeamsInterface"),
    ("messaging.slack.interface", "SlackInterface"),
    ("messaging.whatsapp.interface", "WhatsAppInterface"),
]


@pytest.mark.parametrize("module_path,class_name", INTERFACES)
def test_real_interface_imports(module_path, class_name):
    mod = importlib.import_module(module_path)
    assert hasattr(mod, class_name), f"{module_path} should expose {class_name}"


def test_ninja_test_mode_is_set():
    # conftest.py guarantees this for every test run (local + CI).
    import os

    assert os.environ.get("NINJA_TEST_MODE") == "1"
