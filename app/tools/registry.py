from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approval_reason: str | None = None
    action_type: str | None = None
    action_payload: dict[str, Any] | None = None


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]
    requires_approval_for: list[str]

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        ...


class ToolRegistry:
    """Simple registry that exposes only explicitly registered tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool is not registered or allowed: {name}")
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "requires_approval_for": tool.requires_approval_for,
            }
            for tool in self._tools.values()
        ]


def create_default_registry() -> ToolRegistry:
    from app.tools.calculator import CalculatorTool
    from app.tools.customer_lookup import CustomerLookupTool
    from app.tools.email_draft import EmailDraftTool
    from app.tools.knowledge_search import KnowledgeSearchTool
    from app.tools.task_creator import TaskCreationTool
    from app.tools.ticket_summary import TicketSummaryTool

    registry = ToolRegistry()
    registry.register(KnowledgeSearchTool())
    registry.register(TicketSummaryTool())
    registry.register(CalculatorTool())
    registry.register(EmailDraftTool())
    registry.register(TaskCreationTool())
    registry.register(CustomerLookupTool())
    return registry
