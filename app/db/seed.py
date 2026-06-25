from sqlalchemy.orm import Session

from app.db.database import SessionLocal, init_db
from app.db.models import Customer, SupportTicket, Task


CUSTOMERS = [
    {
        "name": "Maya Johnson",
        "company": "Northstar Retail",
        "email": "maya.johnson@northstar.example",
        "phone": "+1-202-555-0145",
        "account_tier": "Enterprise",
        "notes": "Prefers email updates for operational incidents.",
    },
    {
        "name": "Omar Khaled",
        "company": "Delta Logistics",
        "email": "omar.khaled@delta.example",
        "phone": "+20-100-555-0122",
        "account_tier": "Business",
        "notes": "Escalate delivery delays to operations manager.",
    },
    {
        "name": "Emma Chen",
        "company": "GreenBox Foods",
        "email": "emma.chen@greenbox.example",
        "phone": "+44-20-5555-0117",
        "account_tier": "Starter",
        "notes": "Requires invoices before shipment release.",
    },
]

TICKETS = [
    {
        "id": 101,
        "title": "Delayed shipment for enterprise order",
        "description": "Customer reports a delayed shipment for order NS-8831. Carrier scan has not updated for 24 hours.",
        "priority": "high",
        "category": "shipping",
        "status": "open",
        "customer_id": 1,
    },
    {
        "id": 102,
        "title": "Billing address mismatch",
        "description": "Invoice contains the old billing address. Customer requested correction before payment.",
        "priority": "medium",
        "category": "billing",
        "status": "open",
        "customer_id": 2,
    },
    {
        "id": 103,
        "title": "Refund request outside normal window",
        "description": "Customer asks whether a refund is possible after 35 days because the item arrived damaged.",
        "priority": "high",
        "category": "refund",
        "status": "open",
        "customer_id": 3,
    },
    {
        "id": 104,
        "title": "Feature request for weekly export",
        "description": "Customer requested a scheduled CSV export of open orders every Monday morning.",
        "priority": "low",
        "category": "product",
        "status": "open",
        "customer_id": 2,
    },
    {
        "id": 105,
        "title": "Resolved login issue",
        "description": "Password reset email was blocked by spam rules and is now resolved.",
        "priority": "medium",
        "category": "account",
        "status": "closed",
        "customer_id": 1,
    },
]

TASKS = [
    {
        "title": "Review damaged shipment refund exception",
        "description": "Check evidence for ticket 103 and decide whether manager approval is required.",
        "priority": "medium",
        "status": "open",
        "source_ticket_id": 103,
        "requires_approval": False,
        "approved": True,
    },
    {
        "title": "Update billing address for Delta Logistics",
        "description": "Confirm the latest billing details before regenerating the invoice.",
        "priority": "low",
        "status": "open",
        "source_ticket_id": 102,
        "requires_approval": False,
        "approved": True,
    },
]


def seed_database(db: Session) -> None:
    """Insert sample data only when the database is empty."""
    if db.query(Customer).count() == 0:
        db.add_all(Customer(**customer) for customer in CUSTOMERS)
        db.commit()

    if db.query(SupportTicket).count() == 0:
        db.add_all(SupportTicket(**ticket) for ticket in TICKETS)
        db.commit()

    if db.query(Task).count() == 0:
        db.add_all(Task(**task) for task in TASKS)
        db.commit()


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
        print("Database initialized and seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
