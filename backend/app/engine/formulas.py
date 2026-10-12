"""
Safe formula evaluator for device-quantity expressions such as "500 + (NPM3 % 35)".

Only a tiny arithmetic subset is allowed (+, -, *, /, %, parentheses, integers,
and the case variables). No attribute access, calls, or builtins -> safe against
arbitrary code execution from a TA-authored case expression.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}


def eval_quantity(expr: str, variables: Dict[str, int]) -> int:
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, variables: Dict[str, int]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ValueError(f"Unknown variable: {node.id}")
    if isinstance(node, ast.BinOp):
        op = _ALLOWED_BINOPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Disallowed operator: {type(node.op).__name__}")
        return op(_eval_node(node.left, variables), _eval_node(node.right, variables))
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval_node(node.operand, variables)
        if isinstance(node.op, ast.UAdd):
            return _eval_node(node.operand, variables)
        raise ValueError("Disallowed unary operator")
    if isinstance(node, ast.Paren):
        return _eval_node(node.value, variables)
    raise ValueError(f"Disallowed expression node: {type(node).__name__}")
