from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Task
from app.tools.registry import ToolResult


class TaskCreationTool:
    name = "task_creator"
    description = "Create operational tasks in SQLite. High-priority tasks require human approval."
    requires_approval_for = ["high_priority_task"]
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            "source_ticket_id": {"type": "integer"},
        },
        "required": ["title", "priority"],
    }

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        title = str(arguments.get("title", "")).strip()
        description = str(arguments.get("description", "")).strip()
        priority = str(arguments.get("priority", "medium")).strip().lower()
        source_ticket_id = arguments.get("source_ticket_id")

        if not title:
            return ToolResult(False, "Task title is required.")
        if priority not in {"low", "medium", "high"}:
            return ToolResult(False, "Priority must be low, medium, or high.")

        payload = {
            "title": title,
            "description": description,
            "priority": priority,
            "source_ticket_id": int(source_ticket_id) if source_ticket_id is not None else None,
        }

        if priority == "high":
            return ToolResult(
                True,
                "High-priority task requires approval before it is created.",
                {"task_preview": payload},
                requires_approval=True,
                approval_reason="High-priority tasks may trigger urgent operational work and require human approval.",
                action_type="create_high_priority_task",
                action_payload=payload,
            )

        task = Task(**payload, status="open", requires_approval=False, approved=True)
        db.add(task)
        db.commit()
        db.refresh(task)
        return ToolResult(True, "Task created.", {"task": {"id": task.id, **payload, "status": task.status}})
