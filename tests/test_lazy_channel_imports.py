"""Tests for lazy channel-package imports (issue #13).

Importing a leaf utility (e.g. ``messaging.teams.transcribe``) must NOT pull in
the channel's full interface stack (interface -> services.monitor_service ->
httpx -> ...). The package's ``<Chan>Interface`` export stays available lazily
via PEP 562 ``__getattr__``.

Network-free: only checks import behavior, no I/O.
"""

import importlib
import sys

import pytest

CHANNELS = [
    ("messaging.teams", "messaging.teams.transcribe", "messaging.teams.interface", "TeamsInterface"),
    ("messaging.slack", "messaging.slack.transcribe", "messaging.slack.interface", "SlackInterface"),
    (
        "messaging.whatsapp",
        "messaging.whatsapp.transcribe",
        "messaging.whatsapp.interface",
        "WhatsAppInterface",
    ),
]


@pytest.mark.parametrize("pkg,leaf,interface_mod,_iface", CHANNELS)
def test_leaf_import_does_not_load_interface(pkg, leaf, interface_mod, _iface):
    # Drop any previously-imported copies so we observe a clean import.
    for mod in [m for m in sys.modules if m.startswith(pkg)]:
        del sys.modules[mod]

    importlib.import_module(leaf)

    assert leaf in sys.modules, f"{leaf} should import"
    assert (
        interface_mod not in sys.modules
    ), f"importing {leaf} must not eagerly load {interface_mod}"


@pytest.mark.parametrize("pkg,_leaf,interface_mod,iface", CHANNELS)
def test_interface_export_still_resolves_lazily(pkg, _leaf, interface_mod, iface):
    package = importlib.import_module(pkg)
    # Accessing the export triggers __getattr__, which imports the interface.
    obj = getattr(package, iface)
    assert obj.__name__ == iface
    assert interface_mod in sys.modules


@pytest.mark.parametrize("pkg", [c[0] for c in CHANNELS])
def test_unknown_attribute_raises(pkg):
    package = importlib.import_module(pkg)
    with pytest.raises(AttributeError):
        package.DoesNotExist
