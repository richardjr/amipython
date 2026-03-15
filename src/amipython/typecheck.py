"""Two-pass type checker for the amipython transpiler.

Pass 1: Collect function signatures and global variable declarations.
Pass 2: Walk function bodies and module-level code, inferring expression types.
"""

import ast

from amipython.engine import BUILTINS, MODULE_TYPES, OBJECT_TYPES, EngineStaticMethod
from amipython.errors import TypeCheckError
from amipython.types import (
    ANNOTATION_MAP,
    ENGINE_TYPE_MAP,
    AmipyType,
    FunctionInfo,
    StructField,
    StructInfo,
    TypeInfo,
    VariableInfo,
)


def typecheck(tree: ast.Module) -> TypeInfo:
    """Type-check an AST and return a TypeInfo side-table."""
    info = TypeInfo()
    _pass1(tree, info)
    _pass2(tree, info)
    return info


def _resolve_annotation(
    node: ast.expr,
    lineno: int | None = None,
    structs: dict[str, StructInfo] | None = None,
) -> tuple[AmipyType, str | None, AmipyType | None, str | None]:
    """Resolve a type annotation AST node.

    Returns (type, struct_name, list_element_type, list_element_struct).
    """
    if isinstance(node, ast.Name):
        if node.id in ANNOTATION_MAP:
            return ANNOTATION_MAP[node.id], None, None, None
        if node.id in ENGINE_TYPE_MAP:
            return ENGINE_TYPE_MAP[node.id], None, None, None
        if structs and node.id in structs:
            return AmipyType.STRUCT, node.id, None, None
    if isinstance(node, ast.Subscript):
        # list[T]
        if isinstance(node.value, ast.Name) and node.value.id == "list":
            elem_type, elem_struct, _, _ = _resolve_annotation(
                node.slice, lineno=lineno, structs=structs
            )
            return AmipyType.LIST, None, elem_type, elem_struct
    raise TypeCheckError(
        f"unsupported type annotation: {ast.dump(node)}", lineno=lineno
    )


def _pass1(tree: ast.Module, info: TypeInfo):
    """Collect structs, function signatures, global annotated assignments, and engine imports."""
    # First pass: collect struct definitions so they can be used in annotations
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            _collect_struct(node, info)
    # Second pass: everything else
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


def _collect_struct(node: ast.ClassDef, info: TypeInfo):
    """Collect a @dataclass class as a struct definition."""
    fields = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            field_type, struct_name, _, _ = _resolve_annotation(
                item.annotation, lineno=item.lineno, structs=info.structs
            )
            if field_type not in (AmipyType.INT, AmipyType.FLOAT, AmipyType.BOOL):
                raise TypeCheckError(
                    f"struct field '{item.target.id}' must be int, float, or bool",
                    lineno=item.lineno,
                )
            default = None
            if item.value is not None:
                if isinstance(item.value, ast.Constant):
                    default = item.value.value
                else:
                    raise TypeCheckError(
                        f"struct field default must be a literal",
                        lineno=item.lineno,
                    )
            fields.append(StructField(item.target.id, field_type, default))
    info.structs[node.name] = StructInfo(node.name, fields)


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
        param_type, struct_name, _, _ = _resolve_annotation(
            arg.annotation, lineno=node.lineno, structs=info.structs
        )
        params.append(VariableInfo(arg.arg, param_type, struct_name=struct_name))

    return_type = AmipyType.VOID
    if node.returns is not None:
        return_type, _, _, _ = _resolve_annotation(
            node.returns, lineno=node.lineno, structs=info.structs
        )

    info.functions[node.name] = FunctionInfo(node.name, params, return_type)
    info.locals[node.name] = {}


def _collect_global_annotated(node: ast.AnnAssign, info: TypeInfo):
    """Collect a global annotated assignment like `x: int = 42`."""
    if not isinstance(node.target, ast.Name):
        raise TypeCheckError(
            "only simple variable annotations are supported", lineno=node.lineno
        )
    var_type, struct_name, elem_type, elem_struct = _resolve_annotation(
        node.annotation, lineno=node.lineno, structs=info.structs
    )
    info.globals[node.target.id] = VariableInfo(
        node.target.id, var_type,
        struct_name=struct_name,
        list_element_type=elem_type,
        list_element_struct=elem_struct,
    )


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

    def _set_var(
        self, name: str, var_type: AmipyType, lineno: int | None = None,
        struct_name: str | None = None,
        list_element_type: AmipyType | None = None,
        list_element_struct: str | None = None,
        is_ref: bool = False,
    ):
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
                local[name] = VariableInfo(
                    name, var_type,
                    struct_name=struct_name,
                    list_element_type=list_element_type,
                    list_element_struct=list_element_struct,
                    is_ref=is_ref,
                )
        else:
            if name in self.info.globals:
                if self.info.globals[name].type != var_type:
                    raise TypeCheckError(
                        f"cannot reassign '{name}' from "
                        f"{self.info.globals[name].type.name} to {var_type.name}",
                        lineno=lineno,
                    )
            else:
                self.info.globals[name] = VariableInfo(
                    name, var_type,
                    struct_name=struct_name,
                    list_element_type=list_element_type,
                    list_element_struct=list_element_struct,
                    is_ref=is_ref,
                )

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
        pass  # Already handled in pass 1 (amiga imports and dataclasses)

    def visit_Global(self, node: ast.Global):
        for name in node.names:
            self.global_names.add(name)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not isinstance(node.target, ast.Name):
            return
        var_type, struct_name, elem_type, elem_struct = _resolve_annotation(
            node.annotation, lineno=node.lineno, structs=self.info.structs
        )
        if node.value is not None:
            val_type = self._infer(node.value)
            if var_type == AmipyType.LIST:
                # Allow `[]` empty list literal
                if not (isinstance(node.value, ast.List) and len(node.value.elts) == 0):
                    if val_type != var_type:
                        raise TypeCheckError(
                            f"type mismatch: annotated as {var_type.name} but "
                            f"assigned {val_type.name}",
                            lineno=node.lineno,
                        )
            elif val_type != var_type and not _can_promote(val_type, var_type):
                raise TypeCheckError(
                    f"type mismatch: annotated as {var_type.name} but "
                    f"assigned {val_type.name}",
                    lineno=node.lineno,
                )
        self._set_var(
            node.target.id, var_type, lineno=node.lineno,
            struct_name=struct_name,
            list_element_type=elem_type,
            list_element_struct=elem_struct,
        )

    def visit_Assign(self, node: ast.Assign):
        val_type = self._infer(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Struct constructor assignment
                if (isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id in self.info.structs):
                    struct_name = node.value.func.id
                    self._set_var(
                        target.id, AmipyType.STRUCT, lineno=node.lineno,
                        struct_name=struct_name,
                    )
                # Trig table assignment: var = sin_table(n) / cos_table(n, scale)
                elif (isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id in ("sin_table", "cos_table")
                        and val_type == AmipyType.LIST):
                    capacity = 64
                    init_values = None
                    func_name = node.value.func.id
                    args = node.value.args
                    # Determine if scaled (2 args) or unscaled (1 arg)
                    has_scale = (len(args) == 2
                                 and isinstance(args[1], ast.Constant)
                                 and isinstance(args[1].value, int))
                    elem_type = AmipyType.INT if has_scale else AmipyType.FLOAT
                    if (args
                            and isinstance(args[0], ast.Constant)
                            and isinstance(args[0].value, int)):
                        import math
                        capacity = args[0].value
                        n = capacity
                        if has_scale:
                            scale = args[1].value
                            if func_name == "sin_table":
                                init_values = [int(math.sin(2.0 * math.pi * i / n) * scale) for i in range(n)]
                            else:
                                init_values = [int(math.cos(2.0 * math.pi * i / n) * scale) for i in range(n)]
                        else:
                            if func_name == "sin_table":
                                init_values = [math.sin(2.0 * math.pi * i / n) for i in range(n)]
                            else:
                                init_values = [math.cos(2.0 * math.pi * i / n) for i in range(n)]
                    self._set_var(
                        target.id, AmipyType.LIST, lineno=node.lineno,
                        list_element_type=elem_type,
                    )
                    # Update capacity and init values on the variable after creation
                    var = self._get_var(target.id)
                    if var:
                        var.list_capacity = capacity
                        var.list_init_values = init_values
                else:
                    self._set_var(target.id, val_type, lineno=node.lineno)
            elif isinstance(target, ast.Attribute):
                self._check_field_assign(target, val_type, node.lineno)

    def visit_AugAssign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Attribute):
            field_type = self._resolve_field_type(node.target)
            val_type = self._infer(node.value)
            result_type = _arithmetic_result(field_type, val_type, node.op)
            if result_type != field_type and not _can_promote(result_type, field_type):
                raise TypeCheckError(
                    f"augmented assignment changes field type "
                    f"from {field_type.name} to {result_type.name}",
                    lineno=node.lineno,
                )
            return
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
        if isinstance(node.iter, ast.Name):
            # for item in list_var
            list_var = self._get_var(node.iter.id, lineno=node.lineno)
            if list_var is None:
                raise TypeCheckError(
                    f"variable '{node.iter.id}' used before assignment",
                    lineno=node.lineno,
                )
            if list_var.type != AmipyType.LIST:
                raise TypeCheckError(
                    f"cannot iterate over non-list variable '{node.iter.id}'",
                    lineno=node.lineno,
                )
            if isinstance(node.target, ast.Name):
                elem_type = list_var.list_element_type
                elem_struct = list_var.list_element_struct
                self._set_var(
                    node.target.id, elem_type, lineno=node.lineno,
                    struct_name=elem_struct,
                    is_ref=True,  # loop var is a pointer for mutation
                )
        else:
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

        if isinstance(node, ast.Subscript):
            return self._infer_subscript(node)

        if isinstance(node, ast.List):
            # Empty list literal — type comes from annotation context
            if len(node.elts) == 0:
                return AmipyType.LIST
            raise TypeCheckError(
                "only empty list literals are supported (use .append())",
                lineno=getattr(node, "lineno", None),
            )

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
            if name == "len":
                if len(node.args) != 1:
                    raise TypeCheckError("len() takes exactly 1 argument",
                                         lineno=node.lineno)
                arg_type = self._infer(node.args[0])
                if arg_type != AmipyType.LIST:
                    raise TypeCheckError("len() argument must be a list",
                                         lineno=node.lineno)
                return AmipyType.INT
            # Struct constructor: Ball(x=10, y=20)
            if name in self.info.structs:
                return self._infer_struct_constructor(node, name)
            # Engine constructor: Display(...), Bitmap(...)
            if name in OBJECT_TYPES and name in self.info.engine_imports:
                return self._infer_engine_constructor(node, name)
            # run(update, until=expr) — special game loop builtin
            if name == "run" and name in self.info.engine_imports:
                return self._infer_run_call(node)
            # Trig table builtins: sin_table(n), cos_table(n, scale) -> list
            if name in ("sin_table", "cos_table") and name in self.info.engine_imports:
                if len(node.args) not in (1, 2):
                    raise TypeCheckError(
                        f"'{name}()' expects 1 or 2 arguments", lineno=node.lineno
                    )
                for arg in node.args:
                    self._infer(arg)
                return AmipyType.LIST
            # Engine builtin: wait_mouse(), vwait(), rnd()
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

    def _infer_run_call(self, node: ast.Call) -> AmipyType:
        """Type-check run(update_fn, until=lambda: expr)."""
        if len(node.args) != 1:
            raise TypeCheckError(
                "run() expects exactly 1 positional argument (update function)",
                lineno=node.lineno,
            )
        # First arg must be a function name
        func_arg = node.args[0]
        if not isinstance(func_arg, ast.Name):
            raise TypeCheckError(
                "run() first argument must be a function name",
                lineno=node.lineno,
            )
        if func_arg.id not in self.info.functions:
            raise TypeCheckError(
                f"run() argument '{func_arg.id}' is not a defined function",
                lineno=node.lineno,
            )
        # Mark the func_arg as VOID so _infer doesn't complain
        self._set_type(func_arg, AmipyType.VOID)
        # Check until= keyword
        has_until = False
        for kw in node.keywords:
            if kw.arg == "until":
                if not isinstance(kw.value, ast.Lambda):
                    raise TypeCheckError(
                        "run(until=...) must use a lambda: "
                        "run(update, until=lambda: expr)",
                        lineno=node.lineno,
                    )
                # Type-check the lambda body expression
                self._infer(kw.value.body)
                has_until = True
            else:
                raise TypeCheckError(
                    f"run() got unexpected keyword argument '{kw.arg}'",
                    lineno=node.lineno,
                )
        if not has_until:
            raise TypeCheckError(
                "run() requires 'until=' keyword argument",
                lineno=node.lineno,
            )
        return AmipyType.VOID

    def _infer_struct_constructor(self, node: ast.Call, name: str) -> AmipyType:
        """Type-check a struct constructor call like Ball(x=10, y=20)."""
        struct = self.info.structs[name]
        if node.args:
            raise TypeCheckError(
                f"struct '{name}' constructor only accepts keyword arguments",
                lineno=node.lineno,
            )
        provided = set()
        for kw in node.keywords:
            if kw.arg is None:
                raise TypeCheckError(
                    f"**kwargs not supported in struct constructor",
                    lineno=node.lineno,
                )
            field = None
            for f in struct.fields:
                if f.name == kw.arg:
                    field = f
                    break
            if field is None:
                raise TypeCheckError(
                    f"struct '{name}' has no field '{kw.arg}'",
                    lineno=node.lineno,
                )
            val_type = self._infer(kw.value)
            if val_type != field.type and not _can_promote(val_type, field.type):
                raise TypeCheckError(
                    f"field '{kw.arg}' type mismatch: expected {field.type.name}, "
                    f"got {val_type.name}",
                    lineno=node.lineno,
                )
            provided.add(kw.arg)
        # Check all required fields (those without defaults) are provided
        for field in struct.fields:
            if field.name not in provided and field.default is None:
                raise TypeCheckError(
                    f"struct '{name}' missing required field '{field.name}'",
                    lineno=node.lineno,
                )
        self.info.expr_struct_names[id(node)] = name
        return AmipyType.STRUCT

    def _infer_method_call(self, node: ast.Call) -> AmipyType:
        attr = node.func
        if not isinstance(attr.value, ast.Name):
            raise TypeCheckError(
                "only simple method calls are supported", lineno=node.lineno
            )
        obj_name = attr.value.id
        method_name = attr.attr

        # List method call: balls.append(...), balls.remove(...)
        var = self._get_var(obj_name, lineno=node.lineno)
        if var and var.type == AmipyType.LIST:
            return self._infer_list_method(node, var, method_name)

        # Static method call: Shape.grab(...)
        if obj_name in OBJECT_TYPES and obj_name in self.info.engine_imports:
            return self._infer_static_method_call(node, obj_name, method_name)

        # Module function call: palette.aga(...)
        if obj_name in self.info.engine_modules:
            mod = MODULE_TYPES[obj_name]
            if method_name not in mod.functions:
                raise TypeCheckError(
                    f"'{obj_name}' has no function '{method_name}'",
                    lineno=node.lineno,
                )
            func = mod.functions[method_name]
            self._check_method_args(node, func, f"{obj_name}.{method_name}")
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
        self._check_method_args(node, method, f"{obj_name}.{method_name}")
        return method.return_type

    def _check_method_args(self, node: ast.Call, method, label: str):
        """Validate positional + keyword args for an EngineMethod."""
        n_positional = len(method.params)
        if len(node.args) != n_positional:
            raise TypeCheckError(
                f"'{label}()' expects {n_positional} positional "
                f"arguments, got {len(node.args)}",
                lineno=node.lineno,
            )
        for arg in node.args:
            self._infer(arg)
        if method.keywords:
            for kw in node.keywords:
                if kw.arg not in method.keywords:
                    raise TypeCheckError(
                        f"'{label}()' got unexpected keyword argument '{kw.arg}'",
                        lineno=node.lineno,
                    )
                self._infer(kw.value)

    def _infer_list_method(
        self, node: ast.Call, list_var: VariableInfo, method_name: str
    ) -> AmipyType:
        """Type-check list method calls."""
        if method_name == "append":
            if len(node.args) != 1:
                raise TypeCheckError(
                    "list.append() takes exactly 1 argument",
                    lineno=node.lineno,
                )
            arg_type = self._infer(node.args[0])
            if list_var.list_element_type == AmipyType.STRUCT:
                if arg_type != AmipyType.STRUCT:
                    raise TypeCheckError(
                        f"list.append() type mismatch: expected struct, got {arg_type.name}",
                        lineno=node.lineno,
                    )
                # Check struct name matches
                arg_struct = self.info.expr_struct_names.get(id(node.args[0]))
                if arg_struct != list_var.list_element_struct:
                    raise TypeCheckError(
                        f"list.append() struct type mismatch: expected {list_var.list_element_struct}, "
                        f"got {arg_struct}",
                        lineno=node.lineno,
                    )
            elif arg_type != list_var.list_element_type and not _can_promote(
                arg_type, list_var.list_element_type
            ):
                raise TypeCheckError(
                    f"list.append() type mismatch: expected {list_var.list_element_type.name}, "
                    f"got {arg_type.name}",
                    lineno=node.lineno,
                )
            return AmipyType.VOID
        if method_name == "remove":
            if len(node.args) != 1:
                raise TypeCheckError(
                    "list.remove() takes exactly 1 argument",
                    lineno=node.lineno,
                )
            self._infer(node.args[0])
            return AmipyType.VOID
        raise TypeCheckError(
            f"list has no method '{method_name}'", lineno=node.lineno
        )

    def _infer_static_method_call(
        self, node: ast.Call, class_name: str, method_name: str
    ) -> AmipyType:
        obj_type = OBJECT_TYPES[class_name]
        if method_name not in obj_type.static_methods:
            raise TypeCheckError(
                f"'{class_name}' has no static method '{method_name}'",
                lineno=node.lineno,
            )
        static = obj_type.static_methods[method_name]
        if len(node.args) != len(static.params):
            raise TypeCheckError(
                f"'{class_name}.{method_name}()' expects {len(static.params)} "
                f"arguments, got {len(node.args)}",
                lineno=node.lineno,
            )
        for arg in node.args:
            self._infer(arg)
        # Validate keyword arguments if the static method supports them
        if hasattr(static, 'keywords') and static.keywords:
            for kw in node.keywords:
                if kw.arg not in static.keywords:
                    raise TypeCheckError(
                        f"'{class_name}.{method_name}()' got unexpected keyword "
                        f"argument '{kw.arg}'",
                        lineno=node.lineno,
                    )
                self._infer(kw.value)
        return static.return_type

    def _infer_attribute(self, node: ast.Attribute) -> AmipyType:
        """Infer type for attribute access (struct fields or module properties)."""
        if isinstance(node.value, ast.Name):
            name = node.value.id
            var = self._get_var(name, lineno=node.lineno)
            if var and var.type == AmipyType.STRUCT and var.struct_name:
                return self._resolve_field_type(node)
            # Module property access (e.g. mouse.x, mouse.y)
            if name in self.info.engine_modules:
                from amipython.engine import MODULE_TYPES
                mod = MODULE_TYPES[name]
                if node.attr in mod.properties:
                    return mod.properties[node.attr].type
                raise TypeCheckError(
                    f"module '{name}' has no property '{node.attr}'",
                    lineno=node.lineno,
                )
        # Attribute on subscript: eq[i].level — list[Struct][idx].field
        if isinstance(node.value, ast.Subscript):
            elem_type = self._infer_subscript(node.value)
            if elem_type == AmipyType.STRUCT:
                # Find struct name from list var
                if isinstance(node.value.value, ast.Name):
                    list_var = self._get_var(node.value.value.id, lineno=node.lineno)
                    if list_var and list_var.list_element_struct:
                        struct = self.info.structs.get(list_var.list_element_struct)
                        if struct:
                            for f in struct.fields:
                                if f.name == node.attr:
                                    return f.type
                raise TypeCheckError(
                    f"cannot resolve field '{node.attr}' on subscript expression",
                    lineno=node.lineno,
                )
        raise TypeCheckError(
            "attribute access is only supported on struct fields, module properties, and method calls",
            lineno=node.lineno,
        )

    def _infer_subscript(self, node: ast.Subscript) -> AmipyType:
        """Infer type for subscript access (list[idx])."""
        if isinstance(node.value, ast.Name):
            var = self._get_var(node.value.id, lineno=node.lineno)
            if var and var.type == AmipyType.LIST:
                self._infer(node.slice)
                elem_type = var.list_element_type or AmipyType.INT
                return elem_type
        raise TypeCheckError(
            "subscript access is only supported on list variables",
            lineno=node.lineno,
        )

    def _resolve_field_type(self, node: ast.Attribute) -> AmipyType:
        """Resolve a struct field's type from an attribute node."""
        if not isinstance(node.value, ast.Name):
            raise TypeCheckError(
                "only simple field access is supported", lineno=node.lineno
            )
        var = self._get_var(node.value.id, lineno=node.lineno)
        if var is None:
            raise TypeCheckError(
                f"variable '{node.value.id}' used before assignment",
                lineno=node.lineno,
            )
        if var.type != AmipyType.STRUCT or not var.struct_name:
            raise TypeCheckError(
                f"'{node.value.id}' is not a struct", lineno=node.lineno
            )
        struct = self.info.structs.get(var.struct_name)
        if struct is None:
            raise TypeCheckError(
                f"unknown struct '{var.struct_name}'", lineno=node.lineno
            )
        for field in struct.fields:
            if field.name == node.attr:
                return field.type
        raise TypeCheckError(
            f"struct '{var.struct_name}' has no field '{node.attr}'",
            lineno=node.lineno,
        )

    def _check_field_assign(self, target: ast.Attribute, val_type: AmipyType, lineno: int | None):
        """Type-check assignment to a struct field."""
        field_type = self._resolve_field_type(target)
        if val_type != field_type and not _can_promote(val_type, field_type):
            raise TypeCheckError(
                f"field type mismatch: expected {field_type.name}, got {val_type.name}",
                lineno=lineno,
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
        if isinstance(node, ast.ClassDef):
            continue  # Handled in pass 1
        checker.visit(node)
