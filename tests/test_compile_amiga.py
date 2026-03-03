"""Cross-compilation tests — compile with vbcc in Docker, verify Amiga binary."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from amipython.docker import has_docker
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


@skip_no_docker
@skip_no_vbcc
class TestCrossCompile:
    def test_hello_produces_hunk(self):
        """Cross-compile hello.py and verify it produces an Amiga Hunk binary."""
        from amipython.docker import cross_compile

        source = '''
x: int = 42
print("Hello, Amiga!")
print("x =", x)
'''
        c_code = transpile(source)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            c_file = tmppath / "hello.c"
            c_file.write_text(c_code)

            shutil.copy2(HEADER_DIR / "amipython.h", tmppath / "amipython.h")

            output = tmppath / "hello"
            result = cross_compile(c_file, output, HEADER_DIR)

            assert result.exists(), "binary not produced"

            # Check Amiga Hunk magic bytes
            with open(result, "rb") as f:
                magic = f.read(4)
            assert magic == HUNK_MAGIC, (
                f"expected Amiga Hunk magic 0x000003F3, got {magic.hex()}"
            )
