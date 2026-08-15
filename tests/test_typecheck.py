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

    def test_list_subscript_assign_ok(self):
        _typecheck('nums: list[int] = []\nnums.append(1)\nnums[0] = 42\n')

    def test_list_subscript_assign_wrong_type(self):
        with pytest.raises(TypeCheckError):
            _typecheck('nums: list[int] = []\nnums.append(1)\nnums[0] = 1.5\n')

    def test_list_subscript_assign_non_list(self):
        with pytest.raises(TypeCheckError):
            _typecheck('x: int = 5\nx[0] = 1\n')

    def test_list_subscript_assign_non_int_index(self):
        with pytest.raises(TypeCheckError):
            _typecheck('nums: list[int] = []\nnums.append(1)\nnums[1.5] = 42\n')


class TestEngineCallErrors:
    def test_missing_required_kwarg_rejected(self):
        with pytest.raises(TypeCheckError, match="missing required keyword"):
            _typecheck(
                "from amiga import Display, copper, Color\n"
                "copper.color_at(color=Color(15, 0, 0))\n"
            )

    def test_all_required_kwargs_accepted(self):
        _typecheck(
            "from amiga import Display, copper, Color\n"
            "copper.color_at(scanline=10, register=0, color=Color(15, 0, 0))\n"
        )

    def test_direct_shape_construction_rejected(self):
        with pytest.raises(TypeCheckError, match="cannot be constructed directly"):
            _typecheck("from amiga import Display, Shape\ns = Shape()\n")

    def test_direct_sprite_construction_rejected(self):
        with pytest.raises(TypeCheckError, match="cannot be constructed directly"):
            _typecheck("from amiga import Display, Sprite\ns = Sprite()\n")

    def test_list_parameter_rejected(self):
        with pytest.raises(TypeCheckError, match="list parameters are not supported"):
            _typecheck("def f(xs: list[int]) -> int:\n    return 0\n")

    def test_none_return_annotation_accepted(self):
        info = _typecheck("def f() -> None:\n    pass\n")
        assert info.functions["f"].return_type == AmipyType.VOID


class TestByRefParams:
    def test_struct_param_is_ref(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n"
            "def hurt(m: Merc, n: int):\n    m.hp -= n\n"
        )
        info = _typecheck(src)
        params = info.functions["hurt"].params
        assert params[0].is_ref is True
        assert params[0].struct_name == "Merc"
        assert params[1].is_ref is False

    def test_engine_param_is_ref(self):
        src = (
            "from amiga import Bitmap\n"
            "def clear(bm: Bitmap):\n    bm.clear()\n"
        )
        info = _typecheck(src)
        assert info.functions["clear"].params[0].is_ref is True

    def test_struct_arg_wrong_struct_rejected(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n"
            "@dataclass\nclass Crate:\n    loot: int\n"
            "def hurt(m: Merc):\n    m.hp -= 1\n"
            "c = Crate(loot=1)\nhurt(c)\n"
        )
        with pytest.raises(TypeCheckError, match="expected struct Merc"):
            _typecheck(src)

    def test_struct_arg_from_list_element_ok(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n"
            "def hurt(m: Merc):\n    m.hp -= 1\n"
            "mercs: list[Merc] = []\nmercs.append(Merc(hp=5))\nhurt(mercs[0])\n"
            "def tick():\n    for m in mercs:\n        hurt(m)\n"
        )
        _typecheck(src)  # should not raise

    def test_struct_arg_must_be_addressable(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n"
            "def hurt(m: Merc):\n    m.hp -= 1\n"
            "hurt(Merc(hp=5))\n"
        )
        with pytest.raises(TypeCheckError, match="by reference"):
            _typecheck(src)


class TestSizedListLiteral:
    def test_capacity_from_literal(self):
        info = _typecheck("grid: list[int] = [0] * 1280\n")
        var = info.globals["grid"]
        assert var.type == AmipyType.LIST
        assert var.list_element_type == AmipyType.INT
        assert var.list_capacity == 1280

    def test_capacity_from_module_constants(self):
        info = _typecheck("W: int = 40\nH: int = 32\ngrid: list[bool] = [False] * (W * H)\n")
        assert info.const_ints == {"W": 40, "H": 32}
        assert info.globals["grid"].list_capacity == 1280
        assert info.globals["grid"].list_element_type == AmipyType.BOOL

    def test_unannotated_infers_element_type(self):
        info = _typecheck('names = [""] * 64\nweights = [1.5] * 8\n')
        assert info.globals["names"].list_element_type == AmipyType.STR
        assert info.globals["weights"].list_element_type == AmipyType.FLOAT
        # capacity never shrinks below the default
        assert info.globals["names"].list_capacity == 256

    def test_rebound_constant_is_not_a_size(self):
        # W is assigned twice, so it is not a compile-time constant
        with pytest.raises(TypeCheckError):
            _typecheck("W: int = 40\nW = 50\ngrid: list[int] = [0] * W\n")

    def test_element_type_mismatch(self):
        with pytest.raises(TypeCheckError, match="does not match"):
            _typecheck('grid: list[int] = ["x"] * 4\n')

    def test_struct_sized_literal_rejected(self):
        src = STRUCT_PREAMBLE + "@dataclass\nclass B:\n    x: int\nbs: list[B] = [0] * 4\n"
        with pytest.raises(TypeCheckError):
            _typecheck(src)

    def test_local_sized_list(self):
        info = _typecheck("def f():\n    tmp: list[int] = [0] * 300\n    tmp[5] = 1\n")
        assert info.locals["f"]["tmp"].list_capacity == 300


class TestStructConstDefaults:
    def test_int_field_default_from_module_constant(self):
        src = STRUCT_PREAMBLE + (
            "MAX_HP: int = 20\n"
            "@dataclass\nclass Merc:\n    hp: int = MAX_HP\n    lives: int = -1\n    x: int = MAX_HP // 2\n"
            "m = Merc()\n"
        )
        info = _typecheck(src)
        fields = {f.name: f.default for f in info.structs["Merc"].fields}
        assert fields == {"hp": 20, "lives": -1, "x": 10}

    def test_non_constant_default_rejected(self):
        src = STRUCT_PREAMBLE + (
            "hp0: int = 20\nhp0 = 30\n"
            "@dataclass\nclass Merc:\n    hp: int = hp0\n"
        )
        with pytest.raises(TypeCheckError, match="module-level int constant"):
            _typecheck(src)


class TestListElementFieldAssign:
    def test_assign_and_augassign_to_list_element_field(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n    alive: bool = True\n"
            "mercs: list[Merc] = []\nmercs.append(Merc(hp=5))\n"
            "mercs[0].hp = 7\nmercs[0].hp -= 2\nmercs[0].alive = False\n"
        )
        _typecheck(src)  # should not raise

    def test_wrong_type_rejected(self):
        src = STRUCT_PREAMBLE + (
            "@dataclass\nclass Merc:\n    hp: int\n"
            "mercs: list[Merc] = []\nmercs.append(Merc(hp=5))\nmercs[0].hp = 1.5\n"
        )
        with pytest.raises(TypeCheckError, match="field type mismatch"):
            _typecheck(src)
