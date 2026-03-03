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

    # Copy amipython.h alongside the output
    _copy_header(output.parent)

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
    _copy_header(c_file.parent)

    try:
        result = cross_compile(c_file, output, header_dir)
        click.echo(f"Built {result}")
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _header_dir() -> Path:
    """Return the path to the c_runtime directory."""
    return Path(__file__).parent / "c_runtime"


def _copy_header(dest_dir: Path):
    """Copy amipython.h to dest_dir if not already there."""
    import shutil
    src = _header_dir() / "amipython.h"
    dst = dest_dir / "amipython.h"
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
