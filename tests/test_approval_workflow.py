import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import execute_approved_action
from app.db.models import Base, PendingAction, Task


def test_approval_workflow_creates_high_priority_task():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()

    action = PendingAction(
        id="test-action",
        action_type="create_high_priority_task",
        payload_json=json.dumps({"title": "Escalate ticket 102", "description": "Urgent escalation", "source_ticket_id": 102}),
        reason="High priority requires approval.",
        status="pending",
    )
    db.add(action)
    db.commit()

    result = execute_approved_action(action, db)
    assert result["task"]["priority"] == "high"
    assert db.query(Task).count() == 1
    db.close()
