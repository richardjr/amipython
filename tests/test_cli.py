"""CLI path handling — default outputs beside the source, `--out DIR` otherwise."""

from click.testing import CliRunner

from amipython.cli import main


def test_transpile_default_writes_beside_source(tmp_path):
    src = tmp_path / "game.py"
    src.write_text("x: int = 1\nprint(x)\n")
    result = CliRunner().invoke(main, ["transpile", str(src)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "game.c").exists()
    assert (tmp_path / "amipython.h").exists()


def test_transpile_out_dir(tmp_path):
    src = tmp_path / "game.py"
    src.write_text("from amiga import Display\nd = Display(320, 200)\n")
    out = tmp_path / "build"
    result = CliRunner().invoke(main, ["transpile", "--out", str(out), str(src)])
    assert result.exit_code == 0, result.output
    assert (out / "game.c").exists()
    assert (out / "amipython_engine.h").exists()
    assert not (tmp_path / "game.c").exists()


def test_transpile_reports_module_errors(tmp_path):
    (tmp_path / "lib.py").write_text("def f():\n    y: int = 'no'\n")
    src = tmp_path / "game.py"
    src.write_text("from lib import f\nf()\n")
    result = CliRunner().invoke(main, ["transpile", str(src)])
    assert result.exit_code == 1
    assert "lib.py:2:" in result.output


def test_run_no_build_looks_in_out_dir(tmp_path):
    src = tmp_path / "game.py"
    src.write_text("x: int = 1\n")
    result = CliRunner().invoke(main, ["run", "--no-build", "--out", str(tmp_path / "build"), str(src)])
    assert result.exit_code == 1
    assert "binary not found" in result.output
    assert str(tmp_path / "build" / "game") in result.output


def test_adf_no_build_looks_in_out_dir(tmp_path):
    src = tmp_path / "game.py"
    src.write_text("x: int = 1\n")
    result = CliRunner().invoke(main, ["adf", "--no-build", "--out", str(tmp_path / "build"), str(src)])
    assert result.exit_code == 1
    assert str(tmp_path / "build" / "game") in result.output
