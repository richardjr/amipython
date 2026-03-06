"""Docker-based cross-compilation for Amiga targets.

Two build paths:
- vbcc: Simple programs (no engine/display). Fast, small binaries.
- GCC+ACE: Engine programs (display, sprites, etc.). Requires ACE game engine.
"""

import shutil
import subprocess
from pathlib import Path

from amipython.errors import BuildError

VBCC_IMAGE = "walkero/docker4amigavbcc:latest-m68k"
ACE_IMAGE = "amipython-ace"

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


def has_ace_image() -> bool:
    """Check if the amipython-ace Docker image is built."""
    if not has_docker():
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", ACE_IMAGE],
        capture_output=True,
    )
    return result.returncode == 0


def build_ace_image() -> None:
    """Build the amipython-ace Docker image from docker/Dockerfile.ace."""
    dockerfile = Path(__file__).parent.parent.parent / "docker" / "Dockerfile.ace"
    if not dockerfile.exists():
        raise BuildError(
            f"Dockerfile not found: {dockerfile}\n"
            "Run from the amipython project root."
        )
    cmd = [
        "docker", "build",
        "-t", ACE_IMAGE,
        "-f", str(dockerfile),
        str(dockerfile.parent),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise BuildError(f"Failed to build ACE Docker image:\n{result.stderr}")


def _needs_engine(c_content: str) -> bool:
    """Check if the C code uses engine features."""
    return '#include "amipython_engine.h"' in c_content


def _copy_runtime(work_dir: Path, header_dir: Path, c_content: str):
    """Copy all needed runtime files into the work directory."""
    for name in ["amipython.h", "amipython_engine.h", "amipython_engine_amiga.c",
                  "CMakeLists.txt"]:
        src = header_dir / name
        dst = work_dir / name
        if src.exists() and src.resolve() != dst.resolve():
            shutil.copy2(src, dst)


def cross_compile(
    c_file: Path,
    output: Path,
    header_dir: Path,
) -> Path:
    """Cross-compile a C file to an Amiga binary.

    Automatically selects vbcc (non-engine) or GCC+ACE (engine) build path.
    """
    if not has_docker():
        raise BuildError("Docker is not installed or not in PATH")

    c_content = c_file.read_text()

    if _needs_engine(c_content):
        return _cross_compile_ace(c_file, output, header_dir, c_content)
    return _cross_compile_vbcc(c_file, output, header_dir, c_content)


def _cross_compile_vbcc(
    c_file: Path,
    output: Path,
    header_dir: Path,
    c_content: str,
) -> Path:
    """Cross-compile with vbcc (non-engine programs)."""
    work_dir = c_file.parent.resolve()
    c_name = c_file.name
    out_name = output.name

    _copy_runtime(work_dir, header_dir, c_content)

    compile_cmd = list(VBCC_COMPILE_CMD)
    if "AMIPYTHON_USE_FLOAT" in c_content:
        compile_cmd.append("-lmieee")

    source_files = [c_name]

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/opt/code",
        "-w", "/opt/code",
        VBCC_IMAGE,
        *compile_cmd,
        "-o", out_name,
        *source_files,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise BuildError("cross-compilation timed out (120s)")
    except FileNotFoundError:
        raise BuildError("Docker is not installed or not in PATH")

    if result.returncode != 0:
        raise BuildError(f"vbcc compilation failed:\n{result.stderr.strip()}")

    output_path = work_dir / out_name
    if not output_path.exists():
        raise BuildError(f"expected output file not found: {output_path}")
    return output_path


def _cross_compile_ace(
    c_file: Path,
    output: Path,
    header_dir: Path,
    c_content: str,
) -> Path:
    """Cross-compile with GCC+ACE (engine programs)."""
    if not has_ace_image():
        raise BuildError(
            f"ACE Docker image '{ACE_IMAGE}' not found.\n"
            "Build it with: amipython build-ace-image"
        )

    work_dir = c_file.parent.resolve()
    c_name = c_file.name
    out_name = output.name

    _copy_runtime(work_dir, header_dir, c_content)

    # Rename the generated .c to game.c for CMake
    game_c = work_dir / "game.c"
    if c_file.resolve() != game_c.resolve():
        shutil.copy2(c_file, game_c)

    # CMake configure + build inside Docker
    cmake_configure = (
        f"mkdir -p /opt/code/build && cd /opt/code/build && "
        f"cmake /opt/code "
        f"-DCMAKE_TOOLCHAIN_FILE=$CMAKE_TOOLCHAINS_DIR/m68k-amigaos.cmake "
        f"-DM68K_CPU=68000 "
        f"-DM68K_FPU=soft "
        f"-DGAME_OUTPUT_NAME={out_name} "
        f"-DCMAKE_BUILD_TYPE=Release && "
        f"make -j$(nproc) && "
        f"cp /opt/code/build/{out_name} /opt/code/{out_name}"
    )

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{work_dir}:/opt/code",
        ACE_IMAGE,
        "bash", "-c", cmake_configure,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise BuildError("ACE cross-compilation timed out (300s)")
    except FileNotFoundError:
        raise BuildError("Docker is not installed or not in PATH")

    if result.returncode != 0:
        raise BuildError(f"ACE compilation failed:\n{result.stderr.strip()}")

    output_path = work_dir / out_name
    if not output_path.exists():
        raise BuildError(f"expected output file not found: {output_path}")

    # Clean up build directory
    build_dir = work_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    return output_path
