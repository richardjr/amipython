"""Tests for the AST validator."""

import ast

import pytest

from amipython.validate import validate


def _validate(source: str):
    tree = ast.parse(source)
    return validate(tree)


class TestAcceptsValid:
    def test_simple_assignment(self):
        assert _validate("x = 1") == []

    def test_annotated_assignment(self):
        assert _validate("x: int = 1") == []

    def test_function_def(self):
        assert _validate("def f(x: int) -> int:\n    return x") == []

    def test_if_elif_else(self):
        assert _validate("x = 1\nif x > 0:\n    pass\nelif x == 0:\n    pass\nelse:\n    pass") == []

    def test_while_loop(self):
        assert _validate("x = 1\nwhile x > 0:\n    x = x - 1") == []

    def test_for_range(self):
        assert _validate("for i in range(10):\n    pass") == []

    def test_print_call(self):
        assert _validate('print("hello")') == []

    def test_break_continue(self):
        assert _validate("for i in range(10):\n    if i == 5:\n        break\n    continue") == []

    def test_global_statement(self):
        assert _validate("x = 1\ndef f() -> int:\n    global x\n    return x") == []

    def test_arithmetic(self):
        assert _validate("x = 1 + 2 * 3 - 4 // 5 % 6 ** 7") == []

    def test_comparisons(self):
        assert _validate("x = 1\ny = x > 0 and x < 10") == []

    def test_boolean_ops(self):
        assert _validate("x = True and False or not True") == []

    def test_unary_ops(self):
        assert _validate("x = -1\ny = +x\nz = not True") == []

    def test_augmented_assign(self):
        assert _validate("x = 1\nx += 2") == []


class TestRejectsInvalid:
    def test_class_def_no_decorator(self):
        errors = _validate("class Foo:\n    pass")
        assert len(errors) == 1
        assert "dataclass" in str(errors[0])

    def test_decorator(self):
        errors = _validate("@dec\ndef f():\n    pass")
        assert len(errors) >= 1
        assert "decorator" in str(errors[0])

    def test_list_comprehension(self):
        errors = _validate("x = [i for i in range(10)]")
        assert len(errors) >= 1

    def test_import(self):
        errors = _validate("import os")
        assert len(errors) >= 1

    def test_for_with_function_call(self):
        """for i in some_func(): not allowed (only range() and names)."""
        errors = _validate("for i in foo():\n    pass")
        assert len(errors) >= 1
        assert "range()" in str(errors[0]) or "list" in str(errors[0])

    def test_default_args(self):
        errors = _validate("def f(x: int = 1):\n    pass")
        assert len(errors) >= 1
        assert "default" in str(errors[0])

    def test_star_args(self):
        errors = _validate("def f(*args):\n    pass")
        assert len(errors) >= 1

    def test_kwargs(self):
        errors = _validate("def f(**kwargs):\n    pass")
        assert len(errors) >= 1

    def test_tuple_unpacking(self):
        errors = _validate("a, b = 1, 2")
        assert len(errors) >= 1

    def test_multiple_targets(self):
        errors = _validate("a = b = 1")
        assert len(errors) >= 1

    def test_while_else(self):
        errors = _validate("while True:\n    pass\nelse:\n    pass")
        assert len(errors) >= 1

    def test_for_else(self):
        errors = _validate("for i in range(10):\n    pass\nelse:\n    pass")
        assert len(errors) >= 1

    def test_keyword_args_in_call(self):
        errors = _validate("print(end='\\n')")
        assert len(errors) >= 1


DATACLASS_IMPORT = "from dataclasses import dataclass\n"


class TestDataclass:
    def test_accepts_dataclass(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Ball:\n    x: float\n    y: float\n"
        assert _validate(src) == []

    def test_accepts_dataclass_with_defaults(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Star:\n    x: int\n    speed: float = 1.0\n"
        assert _validate(src) == []

    def test_rejects_class_without_dataclass_import(self):
        errors = _validate("@dataclass\nclass Ball:\n    x: float\n")
        assert len(errors) >= 1
        assert "requires" in str(errors[0])

    def test_rejects_class_with_methods(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Ball:\n    x: float\n    def move(self):\n        pass\n"
        errors = _validate(src)
        assert len(errors) >= 1
        assert "field declarations" in str(errors[0])

    def test_rejects_class_with_inheritance(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Ball(Base):\n    x: float\n"
        errors = _validate(src)
        assert len(errors) >= 1
        assert "inheritance" in str(errors[0])

    def test_rejects_wrong_decorator(self):
        src = DATACLASS_IMPORT + "@property\nclass Ball:\n    x: float\n"
        errors = _validate(src)
        assert len(errors) >= 1
        assert "dataclass" in str(errors[0])

    def test_accepts_struct_constructor_kwargs(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Ball:\n    x: float\n    y: float\nb = Ball(x=1.0, y=2.0)\n"
        assert _validate(src) == []

    def test_accepts_for_in_name(self):
        assert _validate("for i in items:\n    pass") == []

    def test_accepts_empty_list(self):
        src = DATACLASS_IMPORT + "@dataclass\nclass Ball:\n    x: float\nballs: list[Ball] = []\n"
        assert _validate(src) == []

    def test_accepts_len(self):
        assert _validate("x = len(items)") == []

    def test_accepts_dataclasses_import(self):
        assert _validate("from dataclasses import dataclass") == []

    def test_rejects_wrong_dataclasses_import(self):
        errors = _validate("from dataclasses import field")
        assert len(errors) >= 1
