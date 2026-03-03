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
    def test_class_def(self):
        errors = _validate("class Foo:\n    pass")
        assert len(errors) == 1
        assert "unsupported syntax" in str(errors[0])

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

    def test_for_without_range(self):
        errors = _validate("for i in x:\n    pass")
        assert len(errors) >= 1
        assert "range()" in str(errors[0])

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
