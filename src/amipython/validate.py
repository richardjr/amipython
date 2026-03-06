"""Validate that an AST only uses the supported Python subset."""

import ast

from amipython.engine import ALL_ENGINE_NAMES, OBJECT_TYPES
from amipython.errors import ValidationError

# AST node types allowed in Phase 1
ALLOWED_NODES = frozenset({
    # Module structure
    ast.Module,
    ast.ImportFrom,
    # Statements
    ast.FunctionDef,
    ast.Return,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.Expr,
    ast.If,
    ast.While,
    ast.For,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Global,
    # Expressions
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Call,
    ast.Constant,
    ast.Name,
    ast.Attribute,
    # Expression contexts
    ast.Load,
    ast.Store,
    ast.Del,
    # Operators
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    # Boolean operators
    ast.And,
    ast.Or,
    # Unary operators
    ast.Not,
    ast.USub,
    ast.UAdd,
    # Comparison operators
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    # Function arguments
    ast.arguments,
    ast.arg,
    # Import / keyword support
    ast.keyword,
    ast.alias,
})

# Built-in functions allowed in Phase 1
ALLOWED_BUILTINS = frozenset({
    "print",
    "range",
    "int",
    "float",
    "abs",
})


class Validator(ast.NodeVisitor):
    """Walk the AST and reject unsupported constructs."""

    def __init__(self):
        self.errors: list[ValidationError] = []

    def _reject(self, node: ast.AST, message: str):
        lineno = getattr(node, "lineno", None)
        self.errors.append(ValidationError(message, lineno=lineno))

    def generic_visit(self, node: ast.AST):
        if type(node) not in ALLOWED_NODES:
            self._reject(node, f"unsupported syntax: {type(node).__name__}")
            return
        super().generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for decorators
        if node.decorator_list:
            self._reject(node, "decorators are not supported")
        # Check for default arguments
        if node.args.defaults or node.args.kw_defaults:
            self._reject(node, "default arguments are not supported")
        # Check for *args, **kwargs
        if node.args.vararg:
            self._reject(node, "*args is not supported")
        if node.args.kwarg:
            self._reject(node, "**kwargs is not supported")
        if node.args.kwonlyargs:
            self._reject(node, "keyword-only arguments are not supported")
        # Visit children
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        # Only allow `for x in range(...)`
        if not (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        ):
            self._reject(node, "for loops must use range()")
        if node.orelse:
            self._reject(node, "for/else is not supported")
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        if node.orelse:
            self._reject(node, "while/else is not supported")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module != "amiga":
            self._reject(node, "only 'from amiga import ...' is supported")
            return
        for alias in node.names:
            if alias.name not in ALL_ENGINE_NAMES:
                self._reject(node, f"unknown engine import: '{alias.name}'")
            if alias.asname is not None:
                self._reject(node, "import aliases are not supported")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Allow keyword arguments for engine constructor calls
        if node.keywords:
            is_engine_constructor = (
                isinstance(node.func, ast.Name) and node.func.id in OBJECT_TYPES
            )
            if not is_engine_constructor:
                self._reject(node, "keyword arguments are not supported")
        if node.starargs if hasattr(node, "starargs") else False:
            self._reject(node, "star arguments are not supported")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Only single-target assignments
        if len(node.targets) > 1:
            self._reject(node, "multiple assignment targets are not supported")
        # No tuple unpacking
        if isinstance(node.targets[0], ast.Tuple):
            self._reject(node, "tuple unpacking is not supported")
        self.generic_visit(node)


def validate(tree: ast.Module) -> list[ValidationError]:
    """Validate an AST tree. Returns a list of errors (empty if valid)."""
    validator = Validator()
    validator.visit(tree)
    return validator.errors
