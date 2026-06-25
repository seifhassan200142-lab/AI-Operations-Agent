from app.tools.registry import create_default_registry


def test_default_registry_contains_required_tools():
    registry = create_default_registry()
    expected = {
        "knowledge_search",
        "ticket_summary",
        "calculator",
        "email_draft",
        "task_creator",
        "customer_lookup",
    }
    assert expected.issubset(set(registry.names()))
