"""Docker-based cross-compilation with vbcc."""

import shutil
import subprocess
from pathlib import Path

from amipython.errors import BuildError

VBCC_IMAGE = "walkero/docker4amigavbcc:latest-m68k"

VBCC_COMPILE_CMD = [
    "vc", "+aos68k",
    "-DAMIGA",
    "-I/opt/sdk/NDK_3.9/Include/include_h",
    "-L/opt/sdk/NDK_3.9/Include/linker_libs",
    "-lamiga",
]


def has_docker() -> bool:
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def cross_compile(
    c_file: Path,
    output: Path,
    header_dir: Path,
) -> Path:
    """Cross-compile a C file to an Amiga binary using vbcc in Docker.

    Args:
        c_file: Path to the .c file.
        output: Path for the output binary.
        header_dir: Path to directory containing amipython.h.

    Returns:
        Path to the output binary.
    """
    if not has_docker():
        raise BuildError("Docker is not installed or not in PATH")

    work_dir = c_file.parent.resolve()
    c_name = c_file.name
    out_name = output.name

    # Copy amipython.h into the work directory if needed
    header_src = header_dir / "amipython.h"
    header_dst = work_dir / "amipython.h"
    if header_src.resolve() != header_dst.resolve():
        shutil.copy2(header_src, header_dst)

    # Check if the C file uses floats — if so, link IEEE math library
    compile_cmd = list(VBCC_COMPILE_CMD)
    c_content = c_file.read_text()
    if "AMIPYTHON_USE_FLOAT" in c_content:
        compile_cmd.append("-lmieee")

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/opt/code",
        "-w", "/opt/code",
        VBCC_IMAGE,
        *compile_cmd,
        "-o", out_name,
        c_name,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise BuildError("cross-compilation timed out (120s)")
    except FileNotFoundError:
        raise BuildError("Docker is not installed or not in PATH")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise BuildError(f"vbcc compilation failed:\n{stderr}")

    output_path = work_dir / out_name
    if not output_path.exists():
        raise BuildError(f"expected output file not found: {output_path}")

    return output_path
