"""Asset conversion — PNG/IFF to ACE .bm planar bitmap format.

Converts indexed-color images to ACE's native bitmap format for loading
on Amiga hardware. The .bm format is raw planar data with a 9-byte header,
loaded instantly by ACE's bitmapCreateFromPath().

ACE .bm format:
    width(2) + height(2) + depth(1) + version(1) + flags(1) + pad(2)
    followed by non-interleaved bitplane data (plane0 complete, plane1, etc.)
"""

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class AssetInfo:
    """Metadata about a converted asset."""
    bm_path: Path
    mask_path: Path | None
    palette: list[tuple[int, int, int]]  # OCS 4-bit (r, g, b) each 0-15
    width: int
    height: int
    depth: int  # bitplanes


def _chunky_to_planar(pixels: list[list[int]], width: int, height: int, depth: int) -> bytes:
    """Convert chunky pixel data to non-interleaved planar format.

    Args:
        pixels: 2D array [y][x] of palette indices.
        width: Image width (must be multiple of 16 for word alignment).
        height: Image height.
        depth: Number of bitplanes.

    Returns:
        Bytes of planar data: plane0 complete, then plane1, etc.
    """
    # Word-align width
    aligned_width = (width + 15) & ~15
    bytes_per_row = aligned_width // 8
    planes = []
    for plane in range(depth):
        plane_data = bytearray()
        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width:
                        pixel = pixels[y][x]
                    else:
                        pixel = 0
                    if pixel & (1 << plane):
                        byte |= (0x80 >> bit)
                plane_data.append(byte)
        planes.append(bytes(plane_data))
    return b"".join(planes)


def _generate_mask(pixels: list[list[int]], width: int, height: int) -> bytes:
    """Generate a 1-bitplane mask where color 0 = transparent (0), others = opaque (1)."""
    aligned_width = (width + 15) & ~15
    bytes_per_row = aligned_width // 8
    mask_data = bytearray()
    for y in range(height):
        for x_byte in range(bytes_per_row):
            byte = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < width:
                    pixel = pixels[y][x]
                else:
                    pixel = 0
                if pixel != 0:
                    byte |= (0x80 >> bit)
            mask_data.append(byte)
    return bytes(mask_data)


def _write_bm(path: Path, width: int, height: int, depth: int, planar_data: bytes) -> None:
    """Write ACE .bm file: 9-byte header + planar data."""
    aligned_width = (width + 15) & ~15
    header = struct.pack(">HHBBBxx", aligned_width, height, depth, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + planar_data)


def _extract_palette_ocs(image: Image.Image) -> list[tuple[int, int, int]]:
    """Extract palette as OCS 4-bit values (each component 0-15)."""
    raw_palette = image.getpalette()
    if raw_palette is None:
        return [(0, 0, 0)]
    # raw_palette is flat [r0, g0, b0, r1, g1, b1, ...]
    n_colors = len(raw_palette) // 3
    palette = []
    for i in range(n_colors):
        r = raw_palette[i * 3] >> 4
        g = raw_palette[i * 3 + 1] >> 4
        b = raw_palette[i * 3 + 2] >> 4
        palette.append((r, g, b))
    return palette


def _depth_for_colors(n_colors: int) -> int:
    """Return the number of bitplanes needed for n_colors."""
    if n_colors <= 2:
        return 1
    if n_colors <= 4:
        return 2
    if n_colors <= 8:
        return 3
    if n_colors <= 16:
        return 4
    return 5  # max 32 colors for OCS


def convert_image(source: Path, output_dir: Path) -> AssetInfo:
    """Convert a PNG or IFF image to ACE .bm format.

    Args:
        source: Path to PNG or IFF ILBM file.
        output_dir: Directory for output .bm files.

    Returns:
        AssetInfo with paths to generated files and metadata.
    """
    image = Image.open(source)

    # Convert to indexed if needed
    if image.mode != "P":
        image = image.convert("P", colors=32)

    palette = _extract_palette_ocs(image)
    width, height = image.size

    # Count actual colors used
    pixel_data = list(image.tobytes())
    max_color = max(pixel_data) if pixel_data else 0
    n_colors = max_color + 1
    depth = _depth_for_colors(n_colors)

    # Trim palette to actual depth
    max_palette = 1 << depth
    palette = palette[:max_palette]

    # Build 2D pixel array
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(pixel_data[y * width + x])
        pixels.append(row)

    # Convert to planar
    planar_data = _chunky_to_planar(pixels, width, height, depth)

    # Write .bm file
    stem = source.stem
    bm_path = output_dir / f"{stem}.bm"
    _write_bm(bm_path, width, height, depth, planar_data)

    # Generate mask (1-bitplane .bm where color 0 = transparent)
    has_transparent = 0 in pixel_data
    mask_path = None
    if has_transparent:
        mask_data = _generate_mask(pixels, width, height)
        mask_path = output_dir / f"{stem}_mask.bm"
        _write_bm(mask_path, width, height, 1, mask_data)

    return AssetInfo(
        bm_path=bm_path,
        mask_path=mask_path,
        palette=palette,
        width=width,
        height=height,
        depth=depth,
    )


def convert_image_to_bytes(source_path: str) -> dict | None:
    """Convert a PNG/IFF to planar byte data for embedding in C.

    Returns dict with 'data' (bytes), 'width', 'height', 'depth',
    or None on failure.
    """
    try:
        image = Image.open(source_path)
    except Exception:
        return None

    if image.mode != "P":
        image = image.convert("P", colors=32)

    width, height = image.size

    pixel_data = list(image.tobytes())
    max_color = max(pixel_data) if pixel_data else 0
    n_colors = max_color + 1
    depth = _depth_for_colors(n_colors)

    # Word-align width for blitter
    aligned_width = (width + 15) & ~15

    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append(pixel_data[y * width + x])
        pixels.append(row)

    planar_data = _chunky_to_planar(pixels, aligned_width, height, depth)

    return {
        "data": planar_data,
        "width": aligned_width,
        "height": height,
        "depth": depth,
    }


def collect_asset_paths(c_content: str) -> list[str]:
    """Extract .bm asset paths referenced in generated C code.

    Scans for amipython_shape_load/amipython_bitmap_load calls and
    extracts the path string argument.
    """
    pattern = r'amipython_(?:shape|bitmap)_load\(&\w+,\s*"([^"]+)"\)'
    return re.findall(pattern, c_content)
