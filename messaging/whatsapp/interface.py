"""
WhatsApp messaging adapter.

Status: stub — implement when WhatsApp Business API credentials are available.

CLI usage (mirrors slack/interface.py):
    python messaging/whatsapp/interface.py say "Hello!"
    python messaging/whatsapp/interface.py read
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from messaging.base import MessagingInterface


class WhatsAppInterface(MessagingInterface):
    """Stub WhatsApp adapter. Raises NotImplementedError on all calls."""

    def say(
        self,
        message: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None,
        username: Optional[str] = None,
        icon_emoji: Optional[str] = None,
        icon_url: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError("WhatsApp adapter is not yet implemented.")

    def get_history(
        self,
        channel: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("WhatsApp adapter is not yet implemented.")

    def collect_pending(
        self,
        msg: Dict[str, Any],
        agent_mentions: List[str],
        seen_messages: set,
        agent_data: dict,
        pending_messages: list,
    ) -> None:
        raise NotImplementedError("WhatsApp adapter is not yet implemented.")

    def post_welcome_if_needed(self, agent: dict, welcome_text: str) -> bool:
        raise NotImplementedError("WhatsApp adapter is not yet implemented.")

    def check_messaging_health(self) -> Dict[str, Any]:
        raise NotImplementedError("WhatsApp adapter is not yet implemented.")
