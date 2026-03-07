"""Validate that an AST only uses the supported Python subset."""

import ast

from amipython.engine import ALL_ENGINE_NAMES, OBJECT_TYPES
from amipython.errors import ValidationError

# AST node types allowed
ALLOWED_NODES = frozenset({
    # Module structure
    ast.Module,
    ast.ImportFrom,
    # Statements
    ast.FunctionDef,
    ast.ClassDef,
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
    ast.Subscript,
    ast.List,
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
    # Lambda (used in run(until=lambda: ...))
    ast.Lambda,
})

# Built-in functions allowed
ALLOWED_BUILTINS = frozenset({
    "print",
    "range",
    "int",
    "float",
    "abs",
    "len",
})


class Validator(ast.NodeVisitor):
    """Walk the AST and reject unsupported constructs."""

    def __init__(self):
        self.errors: list[ValidationError] = []
        self.struct_names: set[str] = set()
        self.has_dataclass_import: bool = False

    def _reject(self, node: ast.AST, message: str):
        lineno = getattr(node, "lineno", None)
        self.errors.append(ValidationError(message, lineno=lineno))

    def generic_visit(self, node: ast.AST):
        if type(node) not in ALLOWED_NODES:
            self._reject(node, f"unsupported syntax: {type(node).__name__}")
            return
        super().generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Must have exactly one decorator: @dataclass
        if len(node.decorator_list) != 1:
            self._reject(node, "classes must have exactly @dataclass decorator")
            return
        dec = node.decorator_list[0]
        if not (isinstance(dec, ast.Name) and dec.id == "dataclass"):
            self._reject(node, "classes must use @dataclass decorator")
            return
        if not self.has_dataclass_import:
            self._reject(node, "@dataclass requires: from dataclasses import dataclass")
            return
        # No bases
        if node.bases:
            self._reject(node, "class inheritance is not supported")
            return
        # Body must contain only annotated assignments (field declarations)
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                if not isinstance(item.target, ast.Name):
                    self._reject(item, "only simple field annotations are supported")
            elif isinstance(item, ast.Pass):
                pass
            else:
                self._reject(item, "dataclass body must contain only field declarations")
        self.struct_names.add(node.name)
        # Visit children for node type checking
        self.generic_visit(node)

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
        # Allow `for x in range(...)` or `for x in list_var`
        is_range = (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        )
        is_name = isinstance(node.iter, ast.Name)
        if not is_range and not is_name:
            self._reject(node, "for loops must use range() or iterate over a list variable")
        if node.orelse:
            self._reject(node, "for/else is not supported")
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        if node.orelse:
            self._reject(node, "while/else is not supported")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "dataclasses":
            for alias in node.names:
                if alias.name != "dataclass":
                    self._reject(node, "only 'dataclass' can be imported from dataclasses")
                if alias.asname is not None:
                    self._reject(node, "import aliases are not supported")
            self.has_dataclass_import = True
            return
        if node.module != "amiga":
            self._reject(node, "only 'from amiga import ...' and 'from dataclasses import dataclass' are supported")
            return
        for alias in node.names:
            if alias.name not in ALL_ENGINE_NAMES:
                self._reject(node, f"unknown engine import: '{alias.name}'")
            if alias.asname is not None:
                self._reject(node, "import aliases are not supported")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Allow keyword arguments for engine constructors, run(), and struct constructors
        if node.keywords:
            is_engine_constructor = (
                isinstance(node.func, ast.Name) and node.func.id in OBJECT_TYPES
            )
            is_run_call = (
                isinstance(node.func, ast.Name) and node.func.id == "run"
            )
            is_struct_constructor = (
                isinstance(node.func, ast.Name) and node.func.id in self.struct_names
            )
            # Also allow kwargs on method/module calls (e.g. sprite.show(x, y, channel=0))
            is_method_call = isinstance(node.func, ast.Attribute)
            if not (is_engine_constructor or is_run_call or is_struct_constructor or is_method_call):
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
