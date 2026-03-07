"""CLI for the amipython transpiler."""

import sys
from pathlib import Path

import click

from amipython.errors import AmipythonError


@click.group()
def main():
    """amipython — Python-to-Amiga game development toolchain."""


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output .c file path (default: same name with .c extension)")
def transpile(source: Path, output: Path | None):
    """Transpile a Python file to C89."""
    from amipython.pipeline import transpile as do_transpile

    if output is None:
        output = source.with_suffix(".c")

    try:
        code = source.read_text()
        c_code = do_transpile(code, filename=str(source))
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Copy runtime files alongside the output
    _copy_runtime(output.parent, c_code)

    output.write_text(c_code)
    click.echo(f"Wrote {output}")


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output binary path (default: source stem without extension)")
def build(source: Path, output: Path | None):
    """Transpile and cross-compile to an Amiga binary."""
    from amipython.docker import cross_compile
    from amipython.pipeline import transpile as do_transpile

    if output is None:
        output = source.with_suffix("")

    try:
        code = source.read_text()
        c_code = do_transpile(code, filename=str(source))
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    c_file = source.with_suffix(".c")
    c_file.write_text(c_code)

    header_dir = _header_dir()
    _copy_runtime(c_file.parent, c_code)

    try:
        result = cross_compile(c_file, output, header_dir)
        click.echo(f"Built {result}")
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("build-ace-image")
def build_ace_image():
    """Build the Docker image with GCC + ACE engine (required for engine builds)."""
    from amipython.docker import build_ace_image as do_build, has_ace_image

    if has_ace_image():
        click.echo("ACE Docker image already exists. Rebuilding...")

    click.echo("Building ACE Docker image (this may take a few minutes)...")
    try:
        do_build()
        click.echo("ACE Docker image built successfully.")
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output .adf file path (default: source stem with .adf extension)")
@click.option("--no-build", is_flag=True, help="Skip build, package existing binary")
@click.option("--no-boot", is_flag=True, help="Create data-only disk (not bootable)")
@click.option("--label", type=str, default=None, help="Volume label (default: source stem)")
@click.option("--run", is_flag=True, help="Launch ADF in Amiberry after creation")
def adf(source: Path, output: Path | None, no_build: bool, no_boot: bool, label: str | None, run: bool):
    """Build and package into a bootable ADF floppy image."""
    from amipython.adf import create_adf

    binary = source.with_suffix("")

    if not no_build:
        from amipython.docker import cross_compile
        from amipython.pipeline import transpile as do_transpile

        try:
            code = source.read_text()
            c_code = do_transpile(code, filename=str(source))
        except AmipythonError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        c_file = source.with_suffix(".c")
        c_file.write_text(c_code)

        header_dir = _header_dir()
        _copy_runtime(c_file.parent, c_code)

        try:
            binary = cross_compile(c_file, binary, header_dir)
            click.echo(f"Built {binary}")
        except AmipythonError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    elif not binary.exists():
        click.echo(f"Error: binary not found: {binary}", err=True)
        sys.exit(1)

    if output is None:
        output = source.with_suffix(".adf")

    try:
        result = create_adf(binary, output, label=label, bootable=not no_boot)
        click.echo(f"Created {result} ({result.stat().st_size:,} bytes)")
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if run:
        from amipython.amiberry import launch_amiberry_adf
        try:
            launch_amiberry_adf(result)
        except AmipythonError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output binary path (default: source stem without extension)")
@click.option("--no-build", is_flag=True, help="Skip build, run existing binary")
def run(source: Path, output: Path | None, no_build: bool):
    """Build and run in Amiberry."""
    from amipython.amiberry import launch_amiberry

    if output is None:
        output = source.with_suffix("")

    if not no_build:
        from amipython.docker import cross_compile
        from amipython.pipeline import transpile as do_transpile

        try:
            code = source.read_text()
            c_code = do_transpile(code, filename=str(source))
        except AmipythonError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

        c_file = source.with_suffix(".c")
        c_file.write_text(c_code)

        header_dir = _header_dir()
        _copy_runtime(c_file.parent, c_code)

        try:
            output = cross_compile(c_file, output, header_dir)
            click.echo(f"Built {output}")
        except AmipythonError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    elif not output.exists():
        click.echo(f"Error: binary not found: {output}", err=True)
        sys.exit(1)

    try:
        launch_amiberry(output)
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _header_dir() -> Path:
    """Return the path to the c_runtime directory."""
    return Path(__file__).parent / "c_runtime"


def _copy_runtime(dest_dir: Path, c_code: str):
    """Copy runtime headers (and host stubs if needed) to dest_dir."""
    import shutil
    runtime_dir = _header_dir()
    for name in ["amipython.h"]:
        src = runtime_dir / name
        dst = dest_dir / name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    if '#include "amipython_engine.h"' in c_code:
        for name in ["amipython_engine.h", "amipython_engine_host.c"]:
            src = runtime_dir / name
            dst = dest_dir / name
            if src.exists() and src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
