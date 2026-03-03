"""Tests for the type checker."""

import pytest

from amipython.errors import TypeCheckError
from amipython.parse import parse
from amipython.typecheck import typecheck
from amipython.types import AmipyType


def _typecheck(source: str):
    tree = parse(source)
    return typecheck(tree)


class TestLiteralInference:
    def test_int_literal(self):
        info = _typecheck("x = 42")
        assert info.globals["x"].type == AmipyType.INT

    def test_float_literal(self):
        info = _typecheck("x = 3.14")
        assert info.globals["x"].type == AmipyType.FLOAT

    def test_bool_literal(self):
        info = _typecheck("x = True")
        assert info.globals["x"].type == AmipyType.BOOL

    def test_str_literal(self):
        info = _typecheck('x = "hello"')
        assert info.globals["x"].type == AmipyType.STR


class TestAnnotations:
    def test_annotated_int(self):
        info = _typecheck("x: int = 1")
        assert info.globals["x"].type == AmipyType.INT

    def test_annotated_float(self):
        info = _typecheck("x: float = 1.0")
        assert info.globals["x"].type == AmipyType.FLOAT

    def test_annotation_mismatch(self):
        with pytest.raises(TypeCheckError, match="type mismatch"):
            _typecheck('x: int = "hello"')

    def test_int_to_float_promotion(self):
        # int can promote to float in annotation
        info = _typecheck("x: float = 1")
        assert info.globals["x"].type == AmipyType.FLOAT


class TestArithmetic:
    def test_int_plus_int(self):
        info = _typecheck("x = 1 + 2")
        assert info.globals["x"].type == AmipyType.INT

    def test_int_plus_float(self):
        info = _typecheck("x = 1 + 2.0")
        assert info.globals["x"].type == AmipyType.FLOAT

    def test_division_always_float(self):
        info = _typecheck("x = 10 / 3")
        assert info.globals["x"].type == AmipyType.FLOAT

    def test_floor_division_always_int(self):
        info = _typecheck("x = 10 // 3")
        assert info.globals["x"].type == AmipyType.INT

    def test_modulo(self):
        info = _typecheck("x = 10 % 3")
        assert info.globals["x"].type == AmipyType.INT

    def test_power(self):
        info = _typecheck("x = 2 ** 3")
        assert info.globals["x"].type == AmipyType.INT


class TestComparisons:
    def test_comparison_is_bool(self):
        info = _typecheck("x = 1\ny = x > 0")
        assert info.globals["y"].type == AmipyType.BOOL

    def test_bool_ops(self):
        info = _typecheck("x = True and False")
        assert info.globals["x"].type == AmipyType.BOOL


class TestFunctions:
    def test_function_return_type(self):
        info = _typecheck("def f(x: int) -> int:\n    return x")
        assert info.functions["f"].return_type == AmipyType.INT
        assert info.functions["f"].params[0].type == AmipyType.INT

    def test_missing_param_annotation(self):
        with pytest.raises(TypeCheckError, match="type annotation"):
            _typecheck("def f(x):\n    return x")

    def test_call_return_type(self):
        info = _typecheck(
            "def f(x: int) -> int:\n    return x\ny = f(1)"
        )
        assert info.globals["y"].type == AmipyType.INT

    def test_wrong_arg_count(self):
        with pytest.raises(TypeCheckError, match="expects 1 arguments"):
            _typecheck("def f(x: int) -> int:\n    return x\ny = f(1, 2)")

    def test_wrong_arg_type(self):
        with pytest.raises(TypeCheckError, match="argument type mismatch"):
            _typecheck('def f(x: int) -> int:\n    return x\ny = f("hello")')


class TestTypeConsistency:
    def test_reassign_same_type(self):
        # Should not raise
        info = _typecheck("x = 1\nx = 2")
        assert info.globals["x"].type == AmipyType.INT

    def test_reassign_different_type(self):
        with pytest.raises(TypeCheckError, match="cannot reassign"):
            _typecheck('x = 1\nx = "hello"')

    def test_use_before_assignment(self):
        with pytest.raises(TypeCheckError, match="used before assignment"):
            _typecheck("y = x")


class TestGlobal:
    def test_global_access(self):
        info = _typecheck(
            "x: int = 0\ndef inc() -> int:\n    global x\n    x = x + 1\n    return x"
        )
        assert info.globals["x"].type == AmipyType.INT

    def test_local_shadows_global(self):
        info = _typecheck(
            "x: int = 0\ndef f() -> float:\n    x = 1.5\n    return x"
        )
        assert info.globals["x"].type == AmipyType.INT
        assert info.locals["f"]["x"].type == AmipyType.FLOAT


class TestForRange:
    def test_range_var_is_int(self):
        info = _typecheck("for i in range(10):\n    pass")
        assert info.globals["i"].type == AmipyType.INT
