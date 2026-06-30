"""Slack messaging adapter."""

__all__ = ["SlackInterface"]


def __getattr__(name):
    # Lazy import (PEP 562): keep `from messaging.slack import SlackInterface`
    # working without dragging the full interface stack into leaf-module imports
    # like `messaging.slack.transcribe`.
    if name == "SlackInterface":
        from messaging.slack.interface import SlackInterface

        return SlackInterface
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
