"""Golden file tests — transpile fixtures and compare against expected C output."""

from pathlib import Path

import pytest

from amipython.pipeline import transpile

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_NAMES = ["hello", "arithmetic", "functions", "control_flow", "display1"]


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_golden_file(name: str):
    py_file = FIXTURES_DIR / f"{name}.py"
    c_file = FIXTURES_DIR / f"{name}.c"

    source = py_file.read_text()
    expected = c_file.read_text()
    actual = transpile(source, filename=str(py_file))

    assert actual == expected, (
        f"Generated C for {name}.py doesn't match {name}.c.\n"
        f"--- expected ---\n{expected}\n"
        f"--- actual ---\n{actual}"
    )


def test_music_load_missing_file_is_transpile_error():
    # The Amiga runtime cannot load a MOD from disk, so a music.load that
    # can't be embedded at transpile time must fail loudly, not fall back
    # to a call that is a silent no-op on hardware.
    import pytest
    from amipython.errors import EmitError
    with pytest.raises(EmitError, match="could not embed"):
        transpile(
            "from amiga import Display, music\n"
            'music.load("data/definitely_missing.mod")\n'
        )


def test_sfx_load_missing_file_is_transpile_error():
    import pytest
    from amipython.errors import EmitError
    with pytest.raises(EmitError, match="could not embed"):
        transpile(
            "from amiga import Display, sfx\n"
            'sfx.load(0, "data/definitely_missing.wav")\n'
        )
