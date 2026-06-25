from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Customer
from app.tools.registry import ToolResult


SENSITIVE_MASK = "[REDACTED - approval required]"


def redact_customer(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "name": customer.name,
        "company": customer.company,
        "account_tier": customer.account_tier,
        "email": SENSITIVE_MASK,
        "phone": SENSITIVE_MASK,
        "notes": SENSITIVE_MASK,
    }


class CustomerLookupTool:
    name = "customer_lookup"
    description = "Look up sample customers from SQLite. Sensitive fields are redacted unless approved."
    requires_approval_for = ["customer_record_access"]
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Customer name, company, or customer id."},
        },
        "required": ["query"],
    }

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolResult(False, "Customer lookup query is required.")

        if query.isdigit():
            customers = db.query(Customer).filter(Customer.id == int(query)).all()
        else:
            pattern = f"%{query}%"
            customers = (
                db.query(Customer)
                .filter(or_(Customer.name.ilike(pattern), Customer.company.ilike(pattern)))
                .limit(5)
                .all()
            )

        redacted_matches = [redact_customer(customer) for customer in customers]
        return ToolResult(
            True,
            "Customer lookup found matches. Sensitive fields are redacted until approval.",
            {"matches": redacted_matches, "count": len(redacted_matches)},
            requires_approval=True if redacted_matches else False,
            approval_reason="Customer records contain personal contact details and account notes.",
            action_type="customer_record_access" if redacted_matches else None,
            action_payload={"customer_ids": [customer.id for customer in customers], "query": query} if redacted_matches else None,
        )
