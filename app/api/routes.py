from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.memory import ConversationMemory
from app.agent.orchestrator import AgentOrchestrator
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import ActionLog, Customer, PendingAction, SupportTicket, Task
from app.schemas.models import (
    ApprovalResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    PendingActionOut,
    TaskOut,
    TicketOut,
    ToolInfo,
)
from app.tools.customer_lookup import redact_customer
from app.tools.registry import create_default_registry

router = APIRouter()
settings = get_settings()
registry = create_default_registry()
memory = ConversationMemory(window_size=settings.memory_window)
orchestrator = AgentOrchestrator(registry=registry, memory=memory, max_steps=settings.max_agent_steps)


def _json_loads(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    value = json.loads(text)
    return value if isinstance(value, dict) else {"value": value}


def _pending_to_schema(action: PendingAction) -> PendingActionOut:
    return PendingActionOut(
        id=action.id,
        action_type=action.action_type,
        payload=_json_loads(action.payload_json) or {},
        reason=action.reason,
        status=action.status,  # type: ignore[arg-type]
        created_at=action.created_at,
        resolved_at=action.resolved_at,
        result=_json_loads(action.result_json),
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return orchestrator.run(request.message, request.session_id, db)


@router.get("/api/pending-actions", response_model=list[PendingActionOut])
def pending_actions(db: Session = Depends(get_db)) -> list[PendingActionOut]:
    actions = db.query(PendingAction).order_by(PendingAction.created_at.desc()).all()
    return [_pending_to_schema(action) for action in actions]


@router.post("/api/approve/{action_id}", response_model=ApprovalResponse)
def approve_action(action_id: str, db: Session = Depends(get_db)) -> ApprovalResponse:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    if action.status != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action.status}.")

    result = execute_approved_action(action, db)
    action.status = "approved"
    action.resolved_at = datetime.now(timezone.utc)
    action.result_json = json.dumps(result)
    db.add(ActionLog(action_type=action.action_type, action_id=action.id, status="approved", message="Action approved."))
    db.commit()
    return ApprovalResponse(action_id=action.id, status="approved", message="Action approved.", result=result)


@router.post("/api/reject/{action_id}", response_model=ApprovalResponse)
def reject_action(action_id: str, db: Session = Depends(get_db)) -> ApprovalResponse:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    if action.status != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action.status}.")

    action.status = "rejected"
    action.resolved_at = datetime.now(timezone.utc)
    action.result_json = json.dumps({"message": "The action was rejected and not executed."})
    db.add(ActionLog(action_type=action.action_type, action_id=action.id, status="rejected", message="Action rejected."))
    db.commit()
    return ApprovalResponse(
        action_id=action.id,
        status="rejected",
        message="Action rejected. No sensitive operation was executed.",
        result={"message": "The action was rejected and not executed."},
    )


@router.get("/api/tools", response_model=list[ToolInfo])
def tools() -> list[ToolInfo]:
    return [ToolInfo(**tool) for tool in registry.describe()]


@router.get("/api/tickets", response_model=list[TicketOut])
def tickets(db: Session = Depends(get_db)) -> list[TicketOut]:
    return db.query(SupportTicket).order_by(SupportTicket.id.asc()).all()


@router.get("/api/tasks", response_model=list[TaskOut])
def tasks(db: Session = Depends(get_db)) -> list[TaskOut]:
    return db.query(Task).order_by(Task.created_at.desc()).all()


def execute_approved_action(action: PendingAction, db: Session) -> dict[str, Any]:
    payload = _json_loads(action.payload_json) or {}

    if action.action_type == "create_high_priority_task":
        task = Task(
            title=str(payload["title"]),
            description=str(payload.get("description", "")),
            priority="high",
            status="open",
            source_ticket_id=payload.get("source_ticket_id"),
            requires_approval=True,
            approved=True,
        )
        db.add(task)
        db.flush()
        return {"task": {"id": task.id, "title": task.title, "priority": task.priority, "status": task.status}}

    if action.action_type == "external_email_draft":
        # This demo approves the draft for human use. It still does not send email.
        return {"approved_email_draft": payload, "sent": False}

    if action.action_type == "customer_record_access":
        ids = payload.get("customer_ids", [])
        customers = db.query(Customer).filter(Customer.id.in_(ids)).all() if ids else []
        return {
            "customers": [
                {
                    "id": customer.id,
                    "name": customer.name,
                    "company": customer.company,
                    "account_tier": customer.account_tier,
                    "email": customer.email,
                    "phone": customer.phone,
                    "notes": customer.notes,
                }
                for customer in customers
            ],
            "redacted_preview": [redact_customer(customer) for customer in customers],
        }

    raise HTTPException(status_code=400, detail=f"Unsupported action type: {action.action_type}")
