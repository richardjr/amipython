"""Cross-compilation tests — compile with vbcc/ACE in Docker, verify Amiga binary."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from amipython.docker import has_docker, has_ace_image
from amipython.pipeline import transpile

HEADER_DIR = Path(__file__).parent.parent / "src" / "amipython" / "c_runtime"

# Amiga Hunk executable magic bytes
HUNK_MAGIC = b'\x00\x00\x03\xf3'

pytestmark = pytest.mark.docker


def _has_vbcc_image():
    if not has_docker():
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", "walkero/docker4amigavbcc:latest-m68k"],
        capture_output=True,
    )
    return result.returncode == 0


skip_no_docker = pytest.mark.skipif(
    not has_docker(), reason="Docker not available"
)
skip_no_vbcc = pytest.mark.skipif(
    not _has_vbcc_image(), reason="vbcc Docker image not pulled"
)
skip_no_ace = pytest.mark.skipif(
    not has_ace_image(), reason="ACE Docker image not built (run: amipython build-ace-image)"
)


def _cross_compile_and_check(source: str, name: str = "test") -> Path:
    """Transpile, cross-compile, and verify Hunk magic. Returns binary path."""
    from amipython.docker import cross_compile

    c_code = transpile(source)
    tmpdir = tempfile.mkdtemp()
    tmppath = Path(tmpdir)

    c_file = tmppath / f"{name}.c"
    c_file.write_text(c_code)

    # Copy all runtime files
    for fname in ["amipython.h", "amipython_engine.h", "amipython_engine_amiga.c",
                   "CMakeLists.txt"]:
        src = HEADER_DIR / fname
        if src.exists():
            shutil.copy2(src, tmppath / fname)

    output = tmppath / name
    result = cross_compile(c_file, output, HEADER_DIR)

    assert result.exists(), "binary not produced"

    with open(result, "rb") as f:
        magic = f.read(4)
    assert magic == HUNK_MAGIC, (
        f"expected Amiga Hunk magic 0x000003F3, got {magic.hex()}"
    )
    return result


@skip_no_docker
@skip_no_vbcc
class TestCrossCompileVbcc:
    def test_hello_produces_hunk(self):
        """Cross-compile hello.py with vbcc and verify Amiga Hunk binary."""
        _cross_compile_and_check('''
x: int = 42
print("Hello, Amiga!")
print("x =", x)
''', "hello")


@skip_no_docker
@skip_no_ace
class TestCrossCompileACE:
    def test_display1_produces_hunk(self):
        """Cross-compile display1 example with ACE engine."""
        _cross_compile_and_check('''
from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=8)
bm = Bitmap(320, 256, bitplanes=8)

for i in range(256):
    palette.aga(i, i, i, i)

for i in range(255, 0, -1):
    bm.circle_filled(160, 128, i // 2, i)

display.show(bm)
wait_mouse()
''', "display1")
