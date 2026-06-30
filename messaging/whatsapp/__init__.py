"""WhatsApp messaging adapter (stub — not yet implemented)."""

__all__ = ["WhatsAppInterface"]


def __getattr__(name):
    # Lazy import (PEP 562): keep `from messaging.whatsapp import WhatsAppInterface`
    # working without dragging the full interface stack into leaf-module imports
    # like `messaging.whatsapp.transcribe`.
    if name == "WhatsAppInterface":
        from messaging.whatsapp.interface import WhatsAppInterface

        return WhatsAppInterface
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
