"""ADF (Amiga Disk File) creation for distributing games on real Amiga hardware.

Creates bootable 880KB FFS floppy images using xdftool from amitools.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from amipython.errors import BuildError

ADF_SIZE = 901_120  # 880KB = 80 cyl * 2 heads * 11 sectors * 512 bytes
ADF_USABLE = 850_000  # approximate usable space after filesystem overhead


def _find_xdftool() -> str:
    path = shutil.which("xdftool")
    if path is None:
        raise BuildError(
            "xdftool not found. Install amitools:\n"
            '  pip install "git+https://github.com/cnvogelg/amitools.git@main#egg=amitools"'
        )
    return path


def create_adf(
    binary: Path,
    output: Path,
    label: str | None = None,
    bootable: bool = True,
) -> Path:
    """Create an ADF floppy image containing the compiled game binary.

    Args:
        binary: Path to the compiled Amiga Hunk executable.
        output: Path for the output .adf file.
        label: Volume label (default: binary stem).
        bootable: If True, write a standard AmigaDOS boot block.

    Returns:
        Path to the created ADF file.
    """
    binary = binary.resolve()

    if not binary.exists():
        raise BuildError(f"Binary not found: {binary}")

    size = binary.stat().st_size
    if size > ADF_USABLE:
        raise BuildError(
            f"Binary too large for ADF: {size:,} bytes "
            f"(max ~{ADF_USABLE:,} bytes)"
        )

    if label is None:
        label = binary.stem.replace(" ", "_")[:30]

    xdftool = _find_xdftool()
    binary_name = binary.name

    # Remove existing ADF — xdftool refuses to overwrite
    if output.exists():
        output.unlink()

    # Create a temporary startup-sequence
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="startup_", delete=False
    ) as f:
        f.write(f"C:{binary_name}\n")
        startup_path = Path(f.name)

    try:
        # Build xdftool command chain
        # format + optional boot + dirs + files
        chain = [
            xdftool, str(output),
            "create",  # create blank ADF
            "+", "format", label, "ffs",
        ]
        if bootable:
            chain += ["+", "boot", "install"]
        chain += [
            "+", "makedir", "S",
            "+", "makedir", "C",
            "+", "write", str(startup_path), "S/Startup-Sequence",
            "+", "write", str(binary), f"C/{binary_name}",
        ]

        result = subprocess.run(
            chain, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise BuildError(
                f"xdftool failed:\n{result.stderr.strip() or result.stdout.strip()}"
            )

        if not output.exists():
            raise BuildError(f"ADF not created: {output}")

        return output
    finally:
        startup_path.unlink(missing_ok=True)
