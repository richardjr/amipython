"""CLI for the amipython transpiler."""

import sys
from pathlib import Path

import click

from amipython.errors import AmipythonError


def _convert_assets(c_code: str, source_dir: Path, work_dir: Path):
    """Find asset references in C code and convert source images to .bm format.

    Returns list of (relative_path, absolute_path) tuples for converted assets.
    """
    from amipython.assets import collect_asset_paths, convert_image

    bm_paths = collect_asset_paths(c_code)
    asset_files = []
    for bm_rel in bm_paths:
        # Find source image: replace .bm with .png or .iff
        bm_rel_path = Path(bm_rel)
        for ext in (".png", ".iff"):
            source_img = source_dir / bm_rel_path.with_suffix(ext)
            if source_img.exists():
                output_subdir = work_dir / bm_rel_path.parent
                info = convert_image(source_img, output_subdir)
                asset_files.append((bm_rel, info.bm_path))
                if info.mask_path:
                    mask_rel = str(bm_rel_path.with_name(bm_rel_path.stem + "_mask.bm"))
                    asset_files.append((mask_rel, info.mask_path))
                break
    return asset_files


@click.group()
def main():
    """amipython — Python-to-Amiga game development toolchain."""


_OUT_OPTION = click.option(
    "--out", type=click.Path(file_okay=False, path_type=Path), default=None,
    help="Directory for generated C, headers, converted assets, binary and "
         "ADF (default: beside the source file). Created if missing.")


def _resolve_out(source: Path, out: Path | None, output: Path | None,
                 suffix: str) -> tuple[Path, Path]:
    """Return (c_file, output_path) for a build.

    With --out DIR everything lands in DIR; otherwise beside the source.
    `suffix` is the default output's suffix ("" = binary, ".adf")."""
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        c_file = out / source.with_suffix(".c").name
        default_output = out / source.with_suffix(suffix).name
    else:
        c_file = source.with_suffix(".c")
        default_output = source.with_suffix(suffix)
    return c_file, (output if output is not None else default_output)


def _transpile_or_exit(source: Path) -> str:
    from amipython.pipeline import transpile as do_transpile
    try:
        return do_transpile(source.read_text(), filename=str(source))
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _build(source: Path, c_file: Path, output: Path):
    """Transpile, stage runtime + assets beside `c_file`, cross-compile.

    Returns (binary_path, asset_files)."""
    from amipython.docker import cross_compile

    c_code = _transpile_or_exit(source)
    c_file.write_text(c_code)
    _copy_runtime(c_file.parent, c_code)
    asset_files = _convert_assets(c_code, source.parent, c_file.parent)
    try:
        binary = cross_compile(c_file, output, _header_dir())
    except AmipythonError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"Built {binary}")
    return binary, asset_files


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output .c file path (default: same name with .c extension)")
@_OUT_OPTION
def transpile(source: Path, output: Path | None, out: Path | None):
    """Transpile a Python file to C89."""
    _, output = _resolve_out(source, out, output, ".c")
    c_code = _transpile_or_exit(source)
    # Copy runtime files alongside the output
    _copy_runtime(output.parent, c_code)
    output.write_text(c_code)
    click.echo(f"Wrote {output}")


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), default=None,
              help="Output binary path (default: source stem without extension)")
@_OUT_OPTION
def build(source: Path, output: Path | None, out: Path | None):
    """Transpile and cross-compile to an Amiga binary."""
    c_file, output = _resolve_out(source, out, output, "")
    _build(source, c_file, output)


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
@_OUT_OPTION
@click.option("--no-build", is_flag=True, help="Skip build, package existing binary")
@click.option("--no-boot", is_flag=True, help="Create data-only disk (not bootable)")
@click.option("--label", type=str, default=None, help="Volume label (default: source stem)")
@click.option("--run", is_flag=True, help="Launch ADF in Amiberry after creation")
def adf(source: Path, output: Path | None, out: Path | None, no_build: bool,
        no_boot: bool, label: str | None, run: bool):
    """Build and package into a bootable ADF floppy image."""
    from amipython.adf import create_adf

    c_file, binary = _resolve_out(source, out, None, "")
    _, output = _resolve_out(source, out, output, ".adf")

    if not no_build:
        binary, asset_files = _build(source, c_file, binary)
    elif not binary.exists():
        click.echo(f"Error: binary not found: {binary}", err=True)
        sys.exit(1)
    else:
        asset_files = []

    try:
        result = create_adf(binary, output, label=label, bootable=not no_boot,
                            asset_files=asset_files)
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
@_OUT_OPTION
@click.option("--no-build", is_flag=True, help="Skip build, run existing binary")
def run(source: Path, output: Path | None, out: Path | None, no_build: bool):
    """Build and run in Amiberry."""
    from amipython.amiberry import launch_amiberry

    c_file, output = _resolve_out(source, out, output, "")

    if not no_build:
        output, _ = _build(source, c_file, output)
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
