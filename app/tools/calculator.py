import ast
import operator
from typing import Any

from sqlalchemy.orm import Session

from app.tools.registry import ToolResult


class CalculatorTool:
    name = "calculator"
    description = "Safely evaluate basic arithmetic expressions without using eval."
    requires_approval_for: list[str] = []
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression using numbers, +, -, *, /, //, %, **, and parentheses.",
            }
        },
        "required": ["expression"],
    }

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def execute(self, arguments: dict[str, Any], db: Session) -> ToolResult:
        expression = str(arguments.get("expression", "")).strip()
        if not expression:
            return ToolResult(False, "Expression is required.")
        if len(expression) > 200:
            return ToolResult(False, "Expression is too long.")
        try:
            tree = ast.parse(expression, mode="eval")
            result = self._eval_node(tree.body)
        except ZeroDivisionError:
            return ToolResult(False, "Division by zero is not allowed.")
        except Exception as exc:  # noqa: BLE001 - return safe error to user
            return ToolResult(False, f"Unsafe or invalid arithmetic expression: {exc}")

        if abs(float(result)) > 1_000_000_000:
            return ToolResult(False, "Result is too large for this demo calculator.")
        return ToolResult(True, "Calculation completed.", {"expression": expression, "result": result})

    def _eval_node(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise ValueError("operator is not allowed")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Pow) and abs(float(right)) > 10:
                raise ValueError("exponent is too large")
            return self._operators[op_type](left, right)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise ValueError("unary operator is not allowed")
            return self._operators[op_type](self._eval_node(node.operand))
        raise ValueError(f"node type is not allowed: {type(node).__name__}")
