"""Golden file tests — transpile fixtures and compare against expected C output."""

from pathlib import Path

import pytest

from amipython.pipeline import transpile

FIXTURES_DIR = Path(__file__).parent / "fixtures"

FIXTURE_NAMES = ["hello", "arithmetic", "functions", "control_flow"]


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
