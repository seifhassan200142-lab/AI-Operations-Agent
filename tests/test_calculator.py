from app.tools.calculator import CalculatorTool


def test_calculator_allows_basic_arithmetic():
    tool = CalculatorTool()
    result = tool.execute({"expression": "2 + 3 * 4"}, db=None)  # type: ignore[arg-type]
    assert result.success is True
    assert result.data["result"] == 14


def test_calculator_rejects_unsafe_calls():
    tool = CalculatorTool()
    result = tool.execute({"expression": "__import__('os').system('echo hacked')"}, db=None)  # type: ignore[arg-type]
    assert result.success is False


def test_calculator_rejects_large_exponents():
    tool = CalculatorTool()
    result = tool.execute({"expression": "2 ** 100"}, db=None)  # type: ignore[arg-type]
    assert result.success is False
