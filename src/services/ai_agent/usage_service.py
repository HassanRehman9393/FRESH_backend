"""Assistant usage tracking and enforcement helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.core.config import get_settings
from src.core.supabase_client import admin_supabase


class AssistantUsageService:
    """Track daily AI Assistant usage and enforce per-role limits."""

    def __init__(self, db=None):
        self.db = db or admin_supabase
        self.settings = get_settings()

    def get_daily_limit_for_role(self, role: str | None) -> int:
        normalized_role = (role or "farmer").strip().lower()

        if normalized_role == "admin":
            return self.settings.ai_assistant_admin_daily_message_limit
        if normalized_role == "government":
            return self.settings.ai_assistant_government_daily_message_limit
        if normalized_role == "exporter":
            return self.settings.ai_assistant_exporter_daily_message_limit
        return self.settings.ai_assistant_daily_message_limit

    def _get_day_window(self) -> tuple[datetime, datetime]:
        window_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=1)
        return window_start, window_end

    async def get_usage_summary(self, user_id: str, role: str | None = None) -> Dict[str, Any]:
        """Return the current daily usage summary for a user."""
        window_start, window_end = self._get_day_window()
        daily_limit = self.get_daily_limit_for_role(role)

        if daily_limit <= 0:
            daily_limit = 0

        conversation_response = self.db.table("ai_conversations").select("id").eq(
            "user_id", user_id
        ).execute()
        conversation_ids: List[str] = [row["id"] for row in (conversation_response.data or []) if row.get("id")]

        used_messages = 0
        if conversation_ids:
            message_response = self.db.table("ai_messages").select("id").eq(
                "role", "user"
            ).in_("conversation_id", conversation_ids).gte(
                "created_at", window_start.isoformat()
            ).lt(
                "created_at", window_end.isoformat()
            ).execute()
            used_messages = len(message_response.data or [])

        remaining_messages = max(daily_limit - used_messages, 0)
        allowed = used_messages < daily_limit

        return {
            "role": (role or "farmer").strip().lower() or "farmer",
            "daily_message_limit": daily_limit,
            "used_messages": used_messages,
            "remaining_messages": remaining_messages,
            "allowed": allowed,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "reset_at": window_end.isoformat(),
        }

    async def is_allowed(self, user_id: str, role: str | None = None) -> Dict[str, Any]:
        """Return usage details and whether the user can send another message."""
        return await self.get_usage_summary(user_id=user_id, role=role)

    @staticmethod
    def retry_after_seconds() -> int:
        """How long until the next UTC day begins."""
        now = datetime.utcnow()
        next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return max(int((next_day - now).total_seconds()), 0)
