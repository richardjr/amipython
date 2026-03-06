"""Tests for engine types, imports, and code generation."""

import ast

import pytest

from amipython.errors import TypeCheckError, ValidationError
from amipython.parse import parse
from amipython.pipeline import transpile
from amipython.typecheck import typecheck
from amipython.types import AmipyType
from amipython.validate import validate


def _validate(source: str):
    tree = ast.parse(source)
    return validate(tree)


def _typecheck(source: str):
    tree = parse(source)
    return typecheck(tree)


def _emit(source: str) -> str:
    return transpile(source)


class TestValidateImports:
    def test_from_amiga_import_accepted(self):
        assert _validate("from amiga import Display") == []

    def test_from_amiga_import_multiple(self):
        assert _validate("from amiga import Display, Bitmap, palette, wait_mouse") == []

    def test_from_other_module_rejected(self):
        errors = _validate("from os import path")
        assert len(errors) >= 1
        assert "only 'from amiga import" in str(errors[0])

    def test_unknown_engine_import_rejected(self):
        errors = _validate("from amiga import FooBar")
        assert len(errors) >= 1
        assert "unknown engine import" in str(errors[0])

    def test_import_alias_rejected(self):
        errors = _validate("from amiga import Display as D")
        assert len(errors) >= 1
        assert "aliases" in str(errors[0])

    def test_kwargs_accepted_for_engine_constructor(self):
        assert _validate("from amiga import Display\ndisplay = Display(320, 256, bitplanes=8)") == []

    def test_kwargs_still_rejected_for_regular_calls(self):
        errors = _validate("print(end='\\n')")
        assert len(errors) >= 1


class TestTypecheckEngine:
    def test_display_constructor_type(self):
        info = _typecheck("from amiga import Display\nd = Display(320, 256, bitplanes=5)")
        assert info.globals["d"].type == AmipyType.DISPLAY

    def test_bitmap_constructor_type(self):
        info = _typecheck("from amiga import Bitmap\nbm = Bitmap(320, 256)")
        assert info.globals["bm"].type == AmipyType.BITMAP

    def test_constructor_default_kwargs(self):
        # bitplanes defaults to 5
        info = _typecheck("from amiga import Display\nd = Display(320, 256)")
        assert info.globals["d"].type == AmipyType.DISPLAY

    def test_constructor_wrong_args(self):
        with pytest.raises(TypeCheckError, match="expects 2 positional"):
            _typecheck("from amiga import Display\nd = Display(320)")

    def test_constructor_unknown_kwarg(self):
        with pytest.raises(TypeCheckError, match="unknown keyword"):
            _typecheck("from amiga import Display\nd = Display(320, 256, foo=1)")

    def test_builtin_type(self):
        info = _typecheck("from amiga import wait_mouse\nwait_mouse()")
        # wait_mouse returns VOID, no variable assigned

    def test_module_function_call(self):
        info = _typecheck("from amiga import palette\npalette.aga(0, 0, 0, 0)")

    def test_method_call_type(self):
        info = _typecheck(
            "from amiga import Display, Bitmap\n"
            "d = Display(320, 256)\n"
            "bm = Bitmap(320, 256)\n"
            "d.show(bm)"
        )

    def test_unknown_method_rejected(self):
        with pytest.raises(TypeCheckError, match="has no method"):
            _typecheck("from amiga import Display\nd = Display(320, 256)\nd.foo()")

    def test_unknown_module_function_rejected(self):
        with pytest.raises(TypeCheckError, match="has no function"):
            _typecheck("from amiga import palette\npalette.foo()")

    def test_constructor_without_import_rejected(self):
        with pytest.raises(TypeCheckError, match="unknown function"):
            _typecheck("d = Display(320, 256)")


class TestEmitEngine:
    def test_display_init(self):
        c = _emit("from amiga import Display\nd = Display(320, 256, bitplanes=8)")
        assert "AmipyDisplay d;" in c
        assert "amipython_display_init(&d, 320, 256, 8);" in c

    def test_display_init_default_kwargs(self):
        c = _emit("from amiga import Display\nd = Display(320, 256)")
        assert "amipython_display_init(&d, 320, 256, 5);" in c

    def test_bitmap_method_call(self):
        c = _emit("from amiga import Bitmap\nbm = Bitmap(320, 256)\nbm.clear()")
        assert "amipython_bitmap_clear(&bm);" in c

    def test_module_function_call(self):
        c = _emit("from amiga import palette\npalette.aga(0, 255, 0, 0)")
        assert "amipython_palette_aga(0, 255, 0, 0);" in c

    def test_builtin_call(self):
        c = _emit("from amiga import wait_mouse\nwait_mouse()")
        assert "amipython_wait_mouse();" in c

    def test_engine_header_included(self):
        c = _emit("from amiga import Display\nd = Display(320, 256)")
        assert '#include "amipython_engine.h"' in c

    def test_no_engine_header_without_imports(self):
        c = _emit("x = 42")
        assert "amipython_engine.h" not in c

    def test_method_with_engine_object_arg(self):
        c = _emit(
            "from amiga import Display, Bitmap\n"
            "d = Display(320, 256)\n"
            "bm = Bitmap(320, 256)\n"
            "d.show(bm)"
        )
        assert "amipython_display_show(&d, &bm);" in c

    def test_no_module_variable_declaration(self):
        c = _emit("from amiga import palette\npalette.aga(0, 0, 0, 0)")
        # palette should NOT appear as a C variable declaration
        lines = c.split("\n")
        decl_lines = [l for l in lines if l.strip().endswith(";") and "palette" in l
                      and "amipython_palette" not in l]
        assert decl_lines == []
