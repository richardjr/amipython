"""Tests for the asset converter (PNG/IFF → ACE .bm format)."""

import struct
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from amipython.assets import (
    AssetInfo,
    collect_asset_paths,
    convert_image,
    _chunky_to_planar,
    _generate_mask,
)


def _make_indexed_png(path: Path, width: int, height: int, colors: int = 4,
                      fill: int = 0) -> Path:
    """Create a test indexed PNG image."""
    img = Image.new("P", (width, height), fill)
    palette = [0] * 768
    for i in range(colors):
        palette[i * 3] = i * 60  # R
        palette[i * 3 + 1] = i * 40  # G
        palette[i * 3 + 2] = i * 80  # B
    img.putpalette(palette)
    img.save(str(path))
    return path


class TestChunkyToPlanar:
    def test_single_plane(self):
        """8 pixels, 1 bitplane: pixel values 0 or 1."""
        pixels = [[1, 0, 1, 0, 1, 0, 1, 0,  0, 0, 0, 0, 0, 0, 0, 0]]
        result = _chunky_to_planar(pixels, 16, 1, 1)
        # Plane 0: 10101010 00000000 = 0xAA 0x00
        assert result == bytes([0xAA, 0x00])

    def test_two_planes(self):
        """Pixel value 3 (binary 11) sets bits in both planes."""
        pixels = [[3, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0]]
        result = _chunky_to_planar(pixels, 16, 1, 2)
        # Plane 0: bit 0 of 3 = 1 → 0x80, 0x00
        # Plane 1: bit 1 of 3 = 1 → 0x80, 0x00
        assert result == bytes([0x80, 0x00, 0x80, 0x00])

    def test_word_alignment(self):
        """Width not multiple of 16 should be padded."""
        pixels = [[1] * 8]
        result = _chunky_to_planar(pixels, 8, 1, 1)
        # Aligned to 16 pixels: 0xFF 0x00
        assert result == bytes([0xFF, 0x00])


class TestGenerateMask:
    def test_all_transparent(self):
        pixels = [[0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0]]
        mask = _generate_mask(pixels, 16, 1)
        assert mask == bytes([0x00, 0x00])

    def test_all_opaque(self):
        pixels = [[1, 1, 1, 1, 1, 1, 1, 1,  1, 1, 1, 1, 1, 1, 1, 1]]
        mask = _generate_mask(pixels, 16, 1)
        assert mask == bytes([0xFF, 0xFF])

    def test_mixed(self):
        pixels = [[0, 1, 0, 1, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0]]
        mask = _generate_mask(pixels, 16, 1)
        assert mask == bytes([0x50, 0x00])


class TestConvertImage:
    def test_basic_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            png_path = _make_indexed_png(tmppath / "test.png", 16, 16, colors=4, fill=1)
            info = convert_image(png_path, tmppath / "out")
            assert info.bm_path.exists()
            assert info.width == 16
            assert info.height == 16
            assert info.depth >= 1
            # Check .bm header
            data = info.bm_path.read_bytes()
            w, h, depth, ver, flags = struct.unpack(">HHBBBxx", data[:9])
            assert w == 16
            assert h == 16
            assert depth == info.depth

    def test_mask_generated_when_transparent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create image with color 0 pixels (transparent)
            img = Image.new("P", (16, 16), 0)
            palette = [0] * 768
            palette[3] = 255  # color 1 = red
            img.putpalette(palette)
            pixels = img.load()
            # Draw some non-zero pixels
            for x in range(4, 12):
                for y in range(4, 12):
                    pixels[x, y] = 1
            img.save(str(tmppath / "ball.png"))
            info = convert_image(tmppath / "ball.png", tmppath / "out")
            assert info.mask_path is not None
            assert info.mask_path.exists()

    def test_palette_ocs_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            img = Image.new("P", (16, 16), 1)
            palette = [0] * 768
            # Color 1: RGB(255, 128, 0) → OCS (15, 8, 0)
            palette[3] = 255
            palette[4] = 128
            palette[5] = 0
            img.putpalette(palette)
            img.save(str(tmppath / "test.png"))
            info = convert_image(tmppath / "test.png", tmppath / "out")
            assert info.palette[1] == (15, 8, 0)


class TestCollectAssetPaths:
    def test_finds_shape_load(self):
        c_code = 'amipython_shape_load(&ball, "data/ball.bm");'
        paths = collect_asset_paths(c_code)
        assert paths == ["data/ball.bm"]

    def test_finds_bitmap_load(self):
        c_code = 'amipython_bitmap_load(&bg, "levels/bg.bm");'
        paths = collect_asset_paths(c_code)
        assert paths == ["levels/bg.bm"]

    def test_finds_multiple(self):
        c_code = (
            'amipython_shape_load(&s1, "data/a.bm");\n'
            'amipython_bitmap_load(&b1, "data/b.bm");'
        )
        paths = collect_asset_paths(c_code)
        assert set(paths) == {"data/a.bm", "data/b.bm"}

    def test_no_matches(self):
        c_code = 'amipython_shape_grab(&s, &bm, 0, 0, 16, 16);'
        paths = collect_asset_paths(c_code)
        assert paths == []
