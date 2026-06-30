"""Microsoft Teams messaging adapter (stub — not yet implemented)."""

__all__ = ["TeamsInterface"]


def __getattr__(name):
    # Lazy import (PEP 562): keep `from messaging.teams import TeamsInterface`
    # working without dragging the full interface stack (httpx, monitor_service)
    # into leaf-module imports like `messaging.teams.transcribe`.
    if name == "TeamsInterface":
        from messaging.teams.interface import TeamsInterface

        return TeamsInterface
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
