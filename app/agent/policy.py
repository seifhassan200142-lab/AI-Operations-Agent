from typing import Any


SENSITIVE_ACTION_TYPES = {
    "create_high_priority_task": "High-priority operational tasks require human approval.",
    "external_email_draft": "External email drafts require human review before use.",
    "customer_record_access": "Customer records include personal data and require approval.",
}


class ApprovalPolicy:
    """Central policy for sensitive action checks."""

    def is_sensitive_action(self, action_type: str | None) -> bool:
        return bool(action_type and action_type in SENSITIVE_ACTION_TYPES)

    def reason_for(self, action_type: str | None) -> str:
        if not action_type:
            return "No approval required."
        return SENSITIVE_ACTION_TYPES.get(action_type, "This action requires approval by policy.")

    def should_require_approval(self, tool_result: Any) -> bool:
        return bool(tool_result.requires_approval or self.is_sensitive_action(tool_result.action_type))
