from typing import Any

from sqlalchemy.orm import Session

from app.tools.registry import ToolResult


class EmailDraftTool:
    name = "email_draft"
    description = "Generate an external email draft. Drafts always require human approval and are never sent."
    requires_approval_for = ["external_email_draft"]
    parameters = {
        "type": "object",
        "properties": {
            "recipient_name": {"type": "string"},
            "recipient_email": {"type": "string"},
            "subject": {"type": "string"},
            "purpose": {"type": "string"},
            "tone": {"type": "string", "default": "professional"},
        },
        "required": ["recipient_name", "subject", "purpose"],
    }

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        recipient_name = str(arguments.get("recipient_name", "Customer")).strip() or "Customer"
        recipient_email = str(arguments.get("recipient_email", "")).strip()
        subject = str(arguments.get("subject", "Operational update")).strip() or "Operational update"
        purpose = str(arguments.get("purpose", "Provide an operational update.")).strip()
        tone = str(arguments.get("tone", "professional")).strip() or "professional"

        body = (
            f"Hi {recipient_name},\n\n"
            f"I wanted to share a quick update regarding your request. {purpose}\n\n"
            "Our operations team is reviewing the next steps and will keep you informed as soon as there is a confirmed update.\n\n"
            "Best regards,\n"
            "Operations Team"
        )
        draft = {
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
            "subject": subject,
            "body": body,
            "tone": tone,
            "status": "draft_requires_human_approval",
        }
        return ToolResult(
            True,
            "Email draft prepared and routed to human approval. It was not sent.",
            {"draft_preview": {"subject": subject, "recipient_name": recipient_name}},
            requires_approval=True,
            approval_reason="External email drafts can affect customers and must be reviewed before use.",
            action_type="external_email_draft",
            action_payload=draft,
        )
