from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import SupportTicket
from app.tools.registry import ToolResult


class TicketSummaryTool:
    name = "ticket_summary"
    description = "Summarize open support tickets by priority and category from SQLite."
    requires_approval_for: list[str] = []
    parameters = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Ticket status to summarize.", "default": "open"},
        },
    }

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        status = str(arguments.get("status", "open")).strip().lower() or "open"
        tickets = db.query(SupportTicket).filter(SupportTicket.status == status).all()
        by_priority = Counter(ticket.priority for ticket in tickets)
        by_category = Counter(ticket.category for ticket in tickets)
        category_priority: dict[str, Counter[str]] = defaultdict(Counter)
        for ticket in tickets:
            category_priority[ticket.category][ticket.priority] += 1

        ticket_rows = [
            {
                "id": ticket.id,
                "title": ticket.title,
                "priority": ticket.priority,
                "category": ticket.category,
                "status": ticket.status,
            }
            for ticket in tickets
        ]
        return ToolResult(
            True,
            f"Found {len(tickets)} {status} tickets.",
            {
                "status": status,
                "total": len(tickets),
                "by_priority": dict(by_priority),
                "by_category": dict(by_category),
                "category_priority": {key: dict(value) for key, value in category_priority.items()},
                "tickets": ticket_rows,
            },
        )
