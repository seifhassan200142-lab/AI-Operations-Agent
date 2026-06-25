from app.schemas.models import ChatResponse, ToolCallRecord


def test_chat_response_schema():
    response = ChatResponse(
        answer="Done",
        reasoning_summary="The agent used one tool.",
        tool_calls=[ToolCallRecord(tool_name="calculator", arguments={"expression": "2+2"}, result_summary="ok")],
    )
    assert response.answer == "Done"
    assert response.tool_calls[0].tool_name == "calculator"
