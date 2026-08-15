"""Multi-module programs — sibling `from <mod> import ...` splicing."""

import textwrap

import pytest

from amipython.errors import TypeCheckError, ValidationError
from amipython.pipeline import transpile


def _write(tmp_path, files: dict[str, str]):
    for name, src in files.items():
        (tmp_path / name).write_text(textwrap.dedent(src))
    main = tmp_path / "main.py"
    return main.read_text(), str(main)


STATE = """
    from dataclasses import dataclass

    MAP_W: int = 8
    MAP_H: int = 4

    @dataclass
    class Game:
        turn: int = 0
        hp: int = 10

    G = Game()
    grid: list[int] = [0] * (MAP_W * MAP_H)
"""

MAPGEN = """
    from amiga import rnd
    from state import G, grid, MAP_W, MAP_H

    def gen_floor():
        for i in range(MAP_W * MAP_H):
            grid[i] = rnd(3)
        G.turn = 0

    def count_walls() -> int:
        n: int = 0
        for i in range(len(grid)):
            if grid[i] == 2:
                n += 1
        return n
"""

MAIN = """
    from amiga import Display, Bitmap, run, joy
    from state import G, grid
    from mapgen import gen_floor, count_walls

    display = Display(320, 256, bitplanes=5)
    bm = Bitmap(320, 256, bitplanes=5)
    gen_floor()
    G.hp -= 1
    bm.print_at(8, 8, "WALLS", count_walls(), "HP", G.hp)
    display.show(bm)

    def update():
        G.turn += 1

    run(update, until=lambda: joy.button(0))
"""


class TestSplice:
    def test_three_modules_transpile(self, tmp_path):
        src, fn = _write(tmp_path, {"state.py": STATE, "mapgen.py": MAPGEN, "main.py": MAIN})
        c = transpile(src, fn)
        # dependency order: state, mapgen, main — one namespace
        assert c.index("Game G;") < c.index("void gen_floor(void) {") < c.index("int main(void)")
        assert "grid_items[i] = amipython_rnd(3);" in c
        assert "G.hp -= 1;" in c
        assert "count_walls()" in c
        # module top-level statements run in main() before the main file's
        assert c.index("G.turn = 0;\n    G.hp = 10;") < c.index("gen_floor();")
        # local imports are dropped, engine imports kept
        assert "state" not in c.split("int main")[0].replace("amipython_engine", "")

    def test_star_import(self, tmp_path):
        src, fn = _write(tmp_path, {
            "consts.py": "W: int = 5\nH: int = 3\n",
            "main.py": "from consts import *\ncells: list[int] = [0] * (W * H)\nprint(len(cells))\n",
        })
        c = transpile(src, fn)
        assert "for (_fi = 0; _fi < 15; _fi++) cells_items[_fi] = 0;" in c

    def test_transitive_import(self, tmp_path):
        src, fn = _write(tmp_path, {
            "a.py": "A: int = 1\n",
            "b.py": "from a import A\ndef fb() -> int:\n    return A + 1\n",
            "main.py": "from b import fb\nprint(fb())\n",
        })
        c = transpile(src, fn)
        assert "LONG A;" in c and "return (A + 1);" in c

    def test_single_file_unchanged(self, tmp_path):
        src, fn = _write(tmp_path, {"main.py": "x: int = 1\nprint(x)\n"})
        assert "amipython_print_long(x);" in transpile(src, fn)


class TestErrors:
    def test_typecheck_error_reports_module_and_line(self, tmp_path):
        src, fn = _write(tmp_path, {
            "state.py": STATE,
            "mapgen.py": MAPGEN + "\n    def bad():\n        x: int = \"s\"\n",
            "main.py": MAIN,
        })
        with pytest.raises(TypeCheckError) as ei:
            transpile(src, fn)
        assert str(ei.value).startswith(str(tmp_path / "mapgen.py") + ":18:")
        assert ei.value.filename.endswith("mapgen.py")
        assert ei.value.lineno == 18

    def test_error_in_main_reports_main(self, tmp_path):
        src, fn = _write(tmp_path, {
            "state.py": STATE,
            "main.py": "from state import G\nG.hp = 1.5\n",
        })
        with pytest.raises(TypeCheckError) as ei:
            transpile(src, fn)
        assert ei.value.filename.endswith("main.py")
        assert ei.value.lineno == 2

    def test_duplicate_top_level_name(self, tmp_path):
        src, fn = _write(tmp_path, {
            "a.py": "def f():\n    pass\nA: int = 1\n",
            "b.py": "def f():\n    pass\nB: int = 2\n",
            "main.py": "from a import A\nfrom b import B\nprint(A + B)\n",
        })
        with pytest.raises(ValidationError, match="defined in both"):
            transpile(src, fn)

    def test_import_then_redefine_rejected(self, tmp_path):
        src, fn = _write(tmp_path, {
            "a.py": "def f():\n    pass\n",
            "main.py": "from a import f\ndef f():\n    pass\n",
        })
        with pytest.raises(ValidationError, match="may not rebind"):
            transpile(src, fn)

    def test_global_rebind_of_import_rejected(self, tmp_path):
        src, fn = _write(tmp_path, {
            "state.py": "hp: int = 10\n",
            "main.py": "from state import hp\ndef hit():\n    global hp\n    hp -= 1\nhit()\n",
        })
        with pytest.raises(ValidationError, match="rebinds a name imported") as ei:
            transpile(src, fn)
        assert ei.value.lineno == 3

    def test_module_level_rebind_of_import_rejected(self, tmp_path):
        src, fn = _write(tmp_path, {
            "state.py": "hp: int = 10\n",
            "main.py": "from state import hp\nhp = 5\n",
        })
        with pytest.raises(ValidationError, match="may not rebind"):
            transpile(src, fn)

    def test_missing_name(self, tmp_path):
        src, fn = _write(tmp_path, {
            "a.py": "x: int = 1\n",
            "main.py": "from a import y\n",
        })
        with pytest.raises(ValidationError, match="cannot import 'y'"):
            transpile(src, fn)

    def test_unknown_module(self, tmp_path):
        src, fn = _write(tmp_path, {"main.py": "from nowhere import x\n"})
        with pytest.raises(ValidationError, match="unknown module 'nowhere'"):
            transpile(src, fn)

    def test_circular_import(self, tmp_path):
        src, fn = _write(tmp_path, {
            "a.py": "from b import B\nA: int = 1\n",
            "b.py": "from a import A\nB: int = 2\n",
            "main.py": "from a import A\n",
        })
        with pytest.raises(ValidationError, match="circular import"):
            transpile(src, fn)

    def test_plain_import_and_alias_rejected(self, tmp_path):
        src, fn = _write(tmp_path, {"a.py": "x: int = 1\n", "main.py": "import a\n"})
        with pytest.raises(ValidationError, match="plain 'import'"):
            transpile(src, fn)
        src, fn = _write(tmp_path, {"a.py": "x: int = 1\n", "main.py": "from a import x as y\n"})
        with pytest.raises(ValidationError, match="aliases"):
            transpile(src, fn)

    def test_local_import_needs_real_path(self):
        with pytest.raises(ValidationError, match="unknown module"):
            transpile("from a import x\n")


def test_used_but_not_imported_name_is_rejected(tmp_path):
    src, fn = _write(tmp_path, {
        "tables.py": "LIMIT: int = 5\nOTHER: int = 1\n",
        "main.py": "from tables import OTHER\nprint(LIMIT)\n",
    })
    with pytest.raises(ValidationError, match="'LIMIT' is used but not imported") as ei:
        transpile(src, fn)
    assert ei.value.filename.endswith("main.py") and ei.value.lineno == 2


def test_local_shadowing_is_not_flagged(tmp_path):
    src, fn = _write(tmp_path, {
        "tables.py": "dist: int = 5\n",
        "main.py": "def f(dist: int) -> int:\n    total: int = dist\n    return total\nprint(f(2))\n",
    })
    transpile(src, fn)   # `dist` is a parameter here — fine
