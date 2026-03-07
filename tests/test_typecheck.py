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


STRUCT_PREAMBLE = "from dataclasses import dataclass\n"


class TestStruct:
    def test_struct_definition(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    y: float\n"
        info = _typecheck(src)
        assert "Ball" in info.structs
        assert len(info.structs["Ball"].fields) == 2
        assert info.structs["Ball"].fields[0].name == "x"
        assert info.structs["Ball"].fields[0].type == AmipyType.FLOAT

    def test_struct_constructor(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    y: float\nb = Ball(x=1.0, y=2.0)\n"
        info = _typecheck(src)
        assert info.globals["b"].type == AmipyType.STRUCT
        assert info.globals["b"].struct_name == "Ball"

    def test_struct_field_access(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    y: float\nb = Ball(x=1.0, y=2.0)\nv = b.x\n"
        info = _typecheck(src)
        assert info.globals["v"].type == AmipyType.FLOAT

    def test_struct_field_assign(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    y: float\nb = Ball(x=1.0, y=2.0)\nb.x = 3.0\n"
        _typecheck(src)  # should not raise

    def test_struct_field_aug_assign(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\nb = Ball(x=1.0)\nb.x += 0.5\n"
        _typecheck(src)  # should not raise

    def test_struct_missing_required_field(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    y: float\nb = Ball(x=1.0)\n"
        with pytest.raises(TypeCheckError, match="missing required field 'y'"):
            _typecheck(src)

    def test_struct_unknown_field(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\nb = Ball(x=1.0, z=2.0)\n"
        with pytest.raises(TypeCheckError, match="no field 'z'"):
            _typecheck(src)

    def test_struct_field_type_mismatch(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: int\nb = Ball(x=1.0)\n"
        with pytest.raises(TypeCheckError):
            _typecheck(src)

    def test_struct_default_field(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\n    speed: float = 1.0\nb = Ball(x=1.0)\n"
        _typecheck(src)  # speed uses default, should not raise

    def test_struct_bad_field_access(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\nb = Ball(x=1.0)\nv = b.z\n"
        with pytest.raises(TypeCheckError, match="no field 'z'"):
            _typecheck(src)


class TestList:
    def test_list_declaration(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\nballs: list[Ball] = []\n"
        info = _typecheck(src)
        assert info.globals["balls"].type == AmipyType.LIST
        assert info.globals["balls"].list_element_type == AmipyType.STRUCT
        assert info.globals["balls"].list_element_struct == "Ball"

    def test_list_of_int(self):
        src = "nums: list[int] = []\n"
        info = _typecheck(src)
        assert info.globals["nums"].type == AmipyType.LIST
        assert info.globals["nums"].list_element_type == AmipyType.INT

    def test_list_append(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass Ball:\n    x: float\nballs: list[Ball] = []\nballs.append(Ball(x=1.0))\n"
        _typecheck(src)  # should not raise

    def test_list_len(self):
        src = "nums: list[int] = []\nn = len(nums)\n"
        info = _typecheck(src)
        assert info.globals["n"].type == AmipyType.INT

    def test_for_in_list(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Ball:\n    x: float\nballs: list[Ball] = []\n"
            "def update():\n    for b in balls:\n        b.x += 1.0\n"
        )
        info = _typecheck(src)
        assert info.locals["update"]["b"].type == AmipyType.STRUCT
        assert info.locals["update"]["b"].is_ref is True

    def test_list_iterate_non_list(self):
        src = "x: int = 5\nfor i in x:\n    pass\n"
        with pytest.raises(TypeCheckError, match="non-list"):
            _typecheck(src)
