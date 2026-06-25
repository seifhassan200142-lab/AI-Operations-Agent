from app.agent.policy import ApprovalPolicy
from app.tools.registry import ToolResult


def test_sensitive_action_detection():
    policy = ApprovalPolicy()
    assert policy.is_sensitive_action("create_high_priority_task") is True
    assert policy.is_sensitive_action("customer_record_access") is True
    assert policy.is_sensitive_action("unknown") is False


def test_policy_uses_tool_result_flag():
    policy = ApprovalPolicy()
    result = ToolResult(True, "Needs approval", requires_approval=True)
    assert policy.should_require_approval(result) is True
