"""Two-pass type checker for the amipython transpiler.

Pass 1: Collect function signatures and global variable declarations.
Pass 2: Walk function bodies and module-level code, inferring expression types.
"""

import ast

from amipython.engine import BUILTINS, MODULE_TYPES, OBJECT_TYPES
from amipython.errors import TypeCheckError
from amipython.types import (
    ANNOTATION_MAP,
    ENGINE_TYPE_MAP,
    AmipyType,
    FunctionInfo,
    TypeInfo,
    VariableInfo,
)


def typecheck(tree: ast.Module) -> TypeInfo:
    """Type-check an AST and return a TypeInfo side-table."""
    info = TypeInfo()
    _pass1(tree, info)
    _pass2(tree, info)
    return info


def _resolve_annotation(node: ast.expr, lineno: int | None = None) -> AmipyType:
    """Resolve a type annotation AST node to an AmipyType."""
    if isinstance(node, ast.Name) and node.id in ANNOTATION_MAP:
        return ANNOTATION_MAP[node.id]
    raise TypeCheckError(
        f"unsupported type annotation: {ast.dump(node)}", lineno=lineno
    )


def _pass1(tree: ast.Module, info: TypeInfo):
    """Collect function signatures, global annotated assignments, and engine imports."""
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            _collect_import(node, info)
        elif isinstance(node, ast.FunctionDef):
            _collect_function(node, info)
        elif isinstance(node, ast.AnnAssign):
            _collect_global_annotated(node, info)
        elif isinstance(node, ast.Assign):
            # Will be typed in pass 2
            pass


def _collect_import(node: ast.ImportFrom, info: TypeInfo):
    """Register engine imports from 'from amiga import ...'."""
    for alias in node.names:
        name = alias.name
        info.engine_imports.add(name)
        if name in MODULE_TYPES:
            info.engine_modules.add(name)
            info.globals[name] = VariableInfo(name, AmipyType.MODULE)


def _collect_function(node: ast.FunctionDef, info: TypeInfo):
    """Collect a function's signature."""
    params = []
    for arg in node.args.args:
        if arg.annotation is None:
            raise TypeCheckError(
                f"parameter '{arg.arg}' must have a type annotation",
                lineno=node.lineno,
            )
        param_type = _resolve_annotation(arg.annotation, lineno=node.lineno)
        params.append(VariableInfo(arg.arg, param_type))

    return_type = AmipyType.VOID
    if node.returns is not None:
        return_type = _resolve_annotation(node.returns, lineno=node.lineno)

    info.functions[node.name] = FunctionInfo(node.name, params, return_type)
    info.locals[node.name] = {}


def _collect_global_annotated(node: ast.AnnAssign, info: TypeInfo):
    """Collect a global annotated assignment like `x: int = 42`."""
    if not isinstance(node.target, ast.Name):
        raise TypeCheckError(
            "only simple variable annotations are supported", lineno=node.lineno
        )
    var_type = _resolve_annotation(node.annotation, lineno=node.lineno)
    info.globals[node.target.id] = VariableInfo(node.target.id, var_type)


class _TypeChecker(ast.NodeVisitor):
    """Pass 2: Walk code bodies, infer expression types, check consistency."""

    def __init__(self, info: TypeInfo):
        self.info = info
        # Current function name (None = module level)
        self.current_function: str | None = None
        # Set of names declared global in current function
        self.global_names: set[str] = set()

    def _set_type(self, node: ast.expr, t: AmipyType):
        self.info.expr_types[id(node)] = t

    def _get_var(self, name: str, lineno: int | None = None) -> VariableInfo | None:
        """Look up a variable in current scope."""
        if self.current_function and name not in self.global_names:
            local = self.info.locals.get(self.current_function, {})
            if name in local:
                return local[name]
        if name in self.info.globals:
            return self.info.globals[name]
        return None

    def _set_var(self, name: str, var_type: AmipyType, lineno: int | None = None):
        """Set a variable's type in the current scope."""
        if self.current_function and name not in self.global_names:
            local = self.info.locals.setdefault(self.current_function, {})
            if name in local:
                if local[name].type != var_type:
                    raise TypeCheckError(
                        f"cannot reassign '{name}' from {local[name].type.name} "
                        f"to {var_type.name}",
                        lineno=lineno,
                    )
            else:
                local[name] = VariableInfo(name, var_type)
        else:
            if name in self.info.globals:
                if self.info.globals[name].type != var_type:
                    raise TypeCheckError(
                        f"cannot reassign '{name}' from "
                        f"{self.info.globals[name].type.name} to {var_type.name}",
                        lineno=lineno,
                    )
            else:
                self.info.globals[name] = VariableInfo(name, var_type)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_func = self.current_function
        old_globals = self.global_names
        self.current_function = node.name
        self.global_names = set()

        # Add parameters as locals
        func_info = self.info.functions[node.name]
        for param in func_info.params:
            self.info.locals[node.name][param.name] = param

        for stmt in node.body:
            self.visit(stmt)

        self.current_function = old_func
        self.global_names = old_globals

    def visit_ImportFrom(self, node: ast.ImportFrom):
        pass  # Already handled in pass 1

    def visit_Global(self, node: ast.Global):
        for name in node.names:
            self.global_names.add(name)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not isinstance(node.target, ast.Name):
            return
        var_type = _resolve_annotation(node.annotation, lineno=node.lineno)
        if node.value is not None:
            val_type = self._infer(node.value)
            if val_type != var_type and not _can_promote(val_type, var_type):
                raise TypeCheckError(
                    f"type mismatch: annotated as {var_type.name} but "
                    f"assigned {val_type.name}",
                    lineno=node.lineno,
                )
        self._set_var(node.target.id, var_type, lineno=node.lineno)

    def visit_Assign(self, node: ast.Assign):
        val_type = self._infer(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._set_var(target.id, val_type, lineno=node.lineno)

    def visit_AugAssign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Name):
            var = self._get_var(node.target.id, lineno=node.lineno)
            if var is None:
                raise TypeCheckError(
                    f"variable '{node.target.id}' used before assignment",
                    lineno=node.lineno,
                )
            val_type = self._infer(node.value)
            result_type = _arithmetic_result(var.type, val_type, node.op)
            if result_type != var.type and not _can_promote(result_type, var.type):
                raise TypeCheckError(
                    f"augmented assignment changes type of '{node.target.id}' "
                    f"from {var.type.name} to {result_type.name}",
                    lineno=node.lineno,
                )

    def visit_Expr(self, node: ast.Expr):
        self._infer(node.value)

    def visit_Return(self, node: ast.Return):
        if self.current_function is None:
            raise TypeCheckError("return outside function", lineno=node.lineno)
        func = self.info.functions[self.current_function]
        if node.value is None:
            if func.return_type != AmipyType.VOID:
                raise TypeCheckError(
                    f"function '{self.current_function}' must return "
                    f"{func.return_type.name}",
                    lineno=node.lineno,
                )
        else:
            val_type = self._infer(node.value)
            if val_type != func.return_type and not _can_promote(
                val_type, func.return_type
            ):
                raise TypeCheckError(
                    f"function '{self.current_function}' returns "
                    f"{func.return_type.name} but got {val_type.name}",
                    lineno=node.lineno,
                )

    def visit_If(self, node: ast.If):
        self._infer(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_While(self, node: ast.While):
        self._infer(node.test)
        for stmt in node.body:
            self.visit(stmt)

    def visit_For(self, node: ast.For):
        # for i in range(...) — i is always int
        if isinstance(node.target, ast.Name):
            self._set_var(node.target.id, AmipyType.INT, lineno=node.lineno)
        # Type-check range arguments
        if isinstance(node.iter, ast.Call):
            for arg in node.iter.args:
                self._infer(arg)
        for stmt in node.body:
            self.visit(stmt)

    def _infer(self, node: ast.expr) -> AmipyType:
        """Infer and record the type of an expression."""
        t = self._infer_inner(node)
        self._set_type(node, t)
        return t

    def _infer_inner(self, node: ast.expr) -> AmipyType:
        if isinstance(node, ast.Constant):
            return _literal_type(node)

        if isinstance(node, ast.Name):
            var = self._get_var(node.id, lineno=node.lineno)
            if var is None:
                # Could be a builtin function name used as value
                raise TypeCheckError(
                    f"variable '{node.id}' used before assignment",
                    lineno=node.lineno,
                )
            return var.type

        if isinstance(node, ast.BinOp):
            left = self._infer(node.left)
            right = self._infer(node.right)
            return _arithmetic_result(left, right, node.op)

        if isinstance(node, ast.UnaryOp):
            operand = self._infer(node.operand)
            if isinstance(node.op, ast.Not):
                return AmipyType.BOOL
            return operand

        if isinstance(node, ast.BoolOp):
            for val in node.values:
                self._infer(val)
            return AmipyType.BOOL

        if isinstance(node, ast.Compare):
            self._infer(node.left)
            for comp in node.comparators:
                self._infer(comp)
            return AmipyType.BOOL

        if isinstance(node, ast.Call):
            return self._infer_call(node)

        if isinstance(node, ast.Attribute):
            return self._infer_attribute(node)

        raise TypeCheckError(
            f"cannot infer type of {type(node).__name__}",
            lineno=getattr(node, "lineno", None),
        )

    def _infer_call(self, node: ast.Call) -> AmipyType:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            # Built-in functions
            if name == "print":
                for arg in node.args:
                    self._infer(arg)
                return AmipyType.VOID
            if name == "range":
                for arg in node.args:
                    self._infer(arg)
                return AmipyType.INT  # range itself isn't stored
            if name == "int":
                for arg in node.args:
                    self._infer(arg)
                return AmipyType.INT
            if name == "float":
                for arg in node.args:
                    self._infer(arg)
                return AmipyType.FLOAT
            if name == "abs":
                if len(node.args) == 1:
                    return self._infer(node.args[0])
                raise TypeCheckError("abs() takes exactly 1 argument",
                                     lineno=node.lineno)
            # Engine constructor: Display(...), Bitmap(...)
            if name in OBJECT_TYPES and name in self.info.engine_imports:
                return self._infer_engine_constructor(node, name)
            # Engine builtin: wait_mouse(), vwait()
            if name in BUILTINS and name in self.info.engine_imports:
                builtin = BUILTINS[name]
                if len(node.args) != len(builtin.params):
                    raise TypeCheckError(
                        f"'{name}()' expects {len(builtin.params)} arguments, "
                        f"got {len(node.args)}",
                        lineno=node.lineno,
                    )
                for arg in node.args:
                    self._infer(arg)
                return builtin.return_type
            # User-defined function
            if name in self.info.functions:
                func = self.info.functions[name]
                if len(node.args) != len(func.params):
                    raise TypeCheckError(
                        f"function '{name}' expects {len(func.params)} arguments, "
                        f"got {len(node.args)}",
                        lineno=node.lineno,
                    )
                for arg, param in zip(node.args, func.params):
                    arg_type = self._infer(arg)
                    if arg_type != param.type and not _can_promote(
                        arg_type, param.type
                    ):
                        raise TypeCheckError(
                            f"argument type mismatch for '{param.name}': "
                            f"expected {param.type.name}, got {arg_type.name}",
                            lineno=node.lineno,
                        )
                return func.return_type
            raise TypeCheckError(
                f"unknown function '{name}'", lineno=node.lineno
            )
        if isinstance(node.func, ast.Attribute):
            return self._infer_method_call(node)
        raise TypeCheckError(
            "only simple function calls are supported", lineno=node.lineno
        )

    def _infer_engine_constructor(self, node: ast.Call, name: str) -> AmipyType:
        obj_type = OBJECT_TYPES[name]
        ctor = obj_type.constructor
        expected_pos = len(ctor.positional)
        if len(node.args) != expected_pos:
            raise TypeCheckError(
                f"'{name}()' expects {expected_pos} positional arguments, "
                f"got {len(node.args)}",
                lineno=node.lineno,
            )
        for arg, param in zip(node.args, ctor.positional):
            arg_type = self._infer(arg)
            if arg_type != param.type and not _can_promote(arg_type, param.type):
                raise TypeCheckError(
                    f"argument type mismatch for '{param.name}': "
                    f"expected {param.type.name}, got {arg_type.name}",
                    lineno=node.lineno,
                )
        for kw in node.keywords:
            if kw.arg not in ctor.keywords:
                raise TypeCheckError(
                    f"unknown keyword argument '{kw.arg}' for {name}()",
                    lineno=node.lineno,
                )
            kw_type, _ = ctor.keywords[kw.arg]
            val_type = self._infer(kw.value)
            if val_type != kw_type and not _can_promote(val_type, kw_type):
                raise TypeCheckError(
                    f"keyword argument '{kw.arg}' type mismatch: "
                    f"expected {kw_type.name}, got {val_type.name}",
                    lineno=node.lineno,
                )
        return ENGINE_TYPE_MAP[name]

    def _infer_method_call(self, node: ast.Call) -> AmipyType:
        attr = node.func
        if not isinstance(attr.value, ast.Name):
            raise TypeCheckError(
                "only simple method calls are supported", lineno=node.lineno
            )
        obj_name = attr.value.id
        method_name = attr.attr

        # Module function call: palette.aga(...)
        if obj_name in self.info.engine_modules:
            mod = MODULE_TYPES[obj_name]
            if method_name not in mod.functions:
                raise TypeCheckError(
                    f"'{obj_name}' has no function '{method_name}'",
                    lineno=node.lineno,
                )
            func = mod.functions[method_name]
            if len(node.args) != len(func.params):
                raise TypeCheckError(
                    f"'{obj_name}.{method_name}()' expects {len(func.params)} "
                    f"arguments, got {len(node.args)}",
                    lineno=node.lineno,
                )
            for arg in node.args:
                self._infer(arg)
            return func.return_type

        # Object method call: bm.circle_filled(...)
        var = self._get_var(obj_name, lineno=node.lineno)
        if var is None:
            raise TypeCheckError(
                f"variable '{obj_name}' used before assignment",
                lineno=node.lineno,
            )
        # Find the engine object type for this variable's type
        obj_type_info = None
        for ot in OBJECT_TYPES.values():
            if ENGINE_TYPE_MAP.get(ot.python_name) == var.type:
                obj_type_info = ot
                break
        if obj_type_info is None:
            raise TypeCheckError(
                f"'{obj_name}' is not an engine object", lineno=node.lineno
            )
        if method_name not in obj_type_info.methods:
            raise TypeCheckError(
                f"'{obj_type_info.python_name}' has no method '{method_name}'",
                lineno=node.lineno,
            )
        method = obj_type_info.methods[method_name]
        if len(node.args) != len(method.params):
            raise TypeCheckError(
                f"'{obj_name}.{method_name}()' expects {len(method.params)} "
                f"arguments, got {len(node.args)}",
                lineno=node.lineno,
            )
        for arg in node.args:
            self._infer(arg)
        return method.return_type

    def _infer_attribute(self, node: ast.Attribute) -> AmipyType:
        """Infer type for attribute access (non-call)."""
        raise TypeCheckError(
            "attribute access is only supported in method calls",
            lineno=node.lineno,
        )


def _literal_type(node: ast.Constant) -> AmipyType:
    """Determine the type of a literal constant."""
    if isinstance(node.value, bool):
        return AmipyType.BOOL
    if isinstance(node.value, int):
        return AmipyType.INT
    if isinstance(node.value, float):
        return AmipyType.FLOAT
    if isinstance(node.value, str):
        return AmipyType.STR
    raise TypeCheckError(
        f"unsupported literal type: {type(node.value).__name__}",
        lineno=node.lineno,
    )


def _can_promote(from_type: AmipyType, to_type: AmipyType) -> bool:
    """Check if from_type can be implicitly promoted to to_type."""
    # int can promote to float
    if from_type == AmipyType.INT and to_type == AmipyType.FLOAT:
        return True
    # bool can promote to int
    if from_type == AmipyType.BOOL and to_type == AmipyType.INT:
        return True
    return False


def _arithmetic_result(
    left: AmipyType, right: AmipyType, op: ast.operator
) -> AmipyType:
    """Determine result type of an arithmetic operation."""
    # Division always yields float
    if isinstance(op, ast.Div):
        return AmipyType.FLOAT
    # Floor division always yields int
    if isinstance(op, ast.FloorDiv):
        return AmipyType.INT
    # String concatenation
    if isinstance(op, ast.Add) and left == AmipyType.STR and right == AmipyType.STR:
        return AmipyType.STR
    # If either operand is float, result is float
    if left == AmipyType.FLOAT or right == AmipyType.FLOAT:
        return AmipyType.FLOAT
    # Int arithmetic stays int
    if left == AmipyType.INT and right == AmipyType.INT:
        return AmipyType.INT
    # Bool in arithmetic promotes to int
    if left in (AmipyType.INT, AmipyType.BOOL) and right in (
        AmipyType.INT,
        AmipyType.BOOL,
    ):
        return AmipyType.INT
    raise TypeCheckError(f"unsupported operation between {left.name} and {right.name}")


def _pass2(tree: ast.Module, info: TypeInfo):
    """Walk all code, infer types, check consistency."""
    checker = _TypeChecker(info)
    for node in tree.body:
        checker.visit(node)
