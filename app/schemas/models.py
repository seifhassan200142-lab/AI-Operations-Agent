from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=100)


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result_summary: str
    requires_approval: bool = False
    action_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    reasoning_summary: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    pending_action_ids: list[str] = Field(default_factory=list)


class ToolInfo(BaseModel):
    name: str
    description: str
    requires_approval_for: list[str] = Field(default_factory=list)
    parameters: dict[str, Any]


class PendingActionOut(BaseModel):
    id: str
    action_type: str
    payload: dict[str, Any]
    reason: str
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime
    resolved_at: datetime | None = None
    result: dict[str, Any] | None = None


class ApprovalResponse(BaseModel):
    action_id: str
    status: Literal["approved", "rejected"]
    message: str
    result: dict[str, Any] | None = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    category: str
    status: str
    customer_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    priority: str
    status: str
    source_ticket_id: int | None
    requires_approval: bool
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    service: str
