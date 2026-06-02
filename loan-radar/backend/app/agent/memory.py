from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.agent import AgentConversation

logger = logging.getLogger(__name__)


class ConversationMessage:
    __slots__ = ("role", "content", "tool_calls", "metadata")

    def __init__(
        self,
        *,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def to_openai_message(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.role == "assistant" and self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg


class ConversationBufferMemory:
    def __init__(
        self,
        *,
        max_messages: int = 40,
        max_context_messages: int = 20,
    ) -> None:
        self._max_messages = max_messages
        self._max_context_messages = max_context_messages
        self._messages: list[ConversationMessage] = []

    @property
    def messages(self) -> list[ConversationMessage]:
        return list(self._messages)

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def add_user_message(self, content: str, **metadata: Any) -> None:
        self._messages.append(
            ConversationMessage(role="user", content=content, metadata=metadata if metadata else None)
        )
        self._trim()

    def add_assistant_message(
        self,
        content: str,
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        **metadata: Any,
    ) -> None:
        self._messages.append(
            ConversationMessage(
                role="assistant",
                content=content,
                tool_calls=tool_calls,
                metadata=metadata if metadata else None,
            )
        )
        self._trim()

    def add_tool_result(
        self,
        *,
        tool_name: str,
        observation: str,
        success: bool = True,
    ) -> None:
        self._messages.append(
            ConversationMessage(
                role="tool",
                content=observation,
                metadata={"tool_name": tool_name, "success": success},
            )
        )
        self._trim()

    def get_context_messages(self) -> list[dict[str, Any]]:
        if not self._messages:
            return []

        context = self._messages[-self._max_context_messages :]
        return [m.to_openai_message() for m in context]

    def get_context_text(self, *, include_tool_results: bool = True) -> str:
        if not self._messages:
            return ""

        context = self._messages[-self._max_context_messages :]
        parts: list[str] = []

        for msg in context:
            if msg.role == "user":
                parts.append(f"用户: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"助手: {msg.content}")
                if include_tool_results and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name", tc.get("action", "unknown"))
                        args = tc.get("args", tc.get("action_input", {}))
                        parts.append(f"  调用工具: {name}({json.dumps(args, ensure_ascii=False)})")
            elif msg.role == "tool":
                if include_tool_results:
                    tool_name = msg.metadata.get("tool_name", "unknown")
                    status = "成功" if msg.metadata.get("success", True) else "失败"
                    parts.append(f"  工具结果({tool_name}, {status}): {msg.content[:500]}")

        return "\n".join(parts)

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        if len(self._messages) > self._max_messages:
            keep = self._max_messages
            self._messages = self._messages[-keep:]

    @classmethod
    def load_from_db(
        cls,
        *,
        db: Session,
        thread_id: str,
        user_id: int,
        max_messages: int = 40,
        max_context_messages: int = 20,
    ) -> ConversationBufferMemory:
        memory = cls(
            max_messages=max_messages,
            max_context_messages=max_context_messages,
        )

        rows = db.scalars(
            select(AgentConversation)
            .where(
                AgentConversation.thread_id == thread_id,
                AgentConversation.user_id == user_id,
            )
            .order_by(AgentConversation.id.asc())
        ).all()

        for row in rows:
            memory._messages.append(
                ConversationMessage(
                    role=row.role,
                    content=row.content,
                    tool_calls=row.tool_calls,
                    metadata=row.metadata_,
                )
            )

        return memory

    def save_to_db(
        self,
        *,
        db: Session,
        thread_id: str,
        user_id: int,
        only_new: bool = True,
    ) -> int:
        if only_new:
            existing_count = db.scalar(
                select(AgentConversation.id)
                .where(
                    AgentConversation.thread_id == thread_id,
                    AgentConversation.user_id == user_id,
                )
                .order_by(AgentConversation.id.desc())
                .limit(1)
            )
            start_idx = 0
            if existing_count is not None:
                rows = db.scalars(
                    select(AgentConversation.id)
                    .where(
                        AgentConversation.thread_id == thread_id,
                        AgentConversation.user_id == user_id,
                    )
                    .order_by(AgentConversation.id.asc())
                ).all()
                start_idx = len(rows)
        else:
            start_idx = 0

        saved = 0
        for msg in self._messages[start_idx:]:
            row = AgentConversation(
                user_id=user_id,
                thread_id=thread_id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls if msg.tool_calls else None,
                metadata_=msg.metadata if msg.metadata else None,
            )
            db.add(row)
            saved += 1

        if saved > 0:
            db.flush()

        return saved

    @staticmethod
    def delete_thread(*, db: Session, thread_id: str, user_id: int) -> int:
        result = db.execute(
            delete(AgentConversation).where(
                AgentConversation.thread_id == thread_id,
                AgentConversation.user_id == user_id,
            )
        )
        db.flush()
        return result.rowcount

    @staticmethod
    def list_threads(*, db: Session, user_id: int, limit: int = 20) -> list[dict[str, Any]]:
        from sqlalchemy import func

        subq = (
            select(
                AgentConversation.thread_id,
                func.max(AgentConversation.created_at).label("last_active"),
                func.count(AgentConversation.id).label("message_count"),
            )
            .where(AgentConversation.user_id == user_id)
            .group_by(AgentConversation.thread_id)
            .order_by(func.max(AgentConversation.created_at).desc())
            .limit(limit)
            .subquery()
        )

        rows = db.execute(select(subq)).all()

        threads = []
        for row in rows:
            first_msg = db.scalar(
                select(AgentConversation.content)
                .where(
                    AgentConversation.thread_id == row.thread_id,
                    AgentConversation.user_id == user_id,
                    AgentConversation.role == "user",
                )
                .order_by(AgentConversation.id.asc())
                .limit(1)
            )

            threads.append({
                "thread_id": row.thread_id,
                "last_active": row.last_active.isoformat() if row.last_active else None,
                "message_count": row.message_count,
                "preview": (first_msg or "")[:100],
            })

        return threads
