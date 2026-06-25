from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class MemoryMessage:
    role: str
    content: str


class ConversationMemory:
    """Short-term in-process memory for the last N messages per session.

    This is intentionally not long-term memory. It resets when the process restarts.
    """

    def __init__(self, window_size: int = 8) -> None:
        self.window_size = window_size
        self._messages: dict[str, deque[MemoryMessage]] = defaultdict(lambda: deque(maxlen=self.window_size))

    def add(self, session_id: str, role: str, content: str) -> None:
        self._messages[session_id].append(MemoryMessage(role=role, content=content))

    def get(self, session_id: str) -> list[MemoryMessage]:
        return list(self._messages[session_id])

    def as_text(self, session_id: str) -> str:
        messages = self.get(session_id)
        if not messages:
            return "No previous messages in short-term memory."
        return "\n".join(f"{message.role}: {message.content}" for message in messages)

    def clear(self, session_id: str) -> None:
        self._messages.pop(session_id, None)
