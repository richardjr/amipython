"""Tests for the Python-native amiga preview module."""

import os
import pytest

# Use dummy video driver for headless testing
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(autouse=True)
def reset_backend():
    """Reset the backend singleton between tests."""
    from amiga._backend import Backend
    yield
    Backend.reset()


def test_import_all():
    from amiga import Display, Bitmap, palette, wait_mouse, vwait
    assert Display is not None
    assert Bitmap is not None
    assert palette is not None
    assert wait_mouse is not None
    assert vwait is not None


def test_palette_aga_downscale():
    """palette.aga() should downscale 8-bit to OCS 4-bit then expand back."""
    from amiga._backend import Backend
    from amiga._palette import palette

    # 255 >> 4 = 15, 15 * 17 = 255
    palette.aga(1, 255, 0, 0)
    assert Backend.get()._palette[1] == (255, 0, 0)

    # 128 >> 4 = 8, 8 * 17 = 136
    palette.aga(2, 128, 128, 128)
    assert Backend.get()._palette[2] == (136, 136, 136)

    # 16 >> 4 = 1, 1 * 17 = 17
    palette.aga(3, 16, 32, 48)
    r = (16 >> 4) & 0xF  # 1
    g = (32 >> 4) & 0xF  # 2
    b = (48 >> 4) & 0xF  # 3
    assert Backend.get()._palette[3] == (r * 17, g * 17, b * 17)


def test_palette_set_ocs():
    """palette.set() takes OCS 4-bit values (0-15)."""
    from amiga._backend import Backend
    from amiga._palette import palette

    palette.set(1, 15, 0, 0)
    assert Backend.get()._palette[1] == (255, 0, 0)

    palette.set(2, 8, 8, 8)
    assert Backend.get()._palette[2] == (136, 136, 136)

    palette.set(3, 0, 0, 0)
    assert Backend.get()._palette[3] == (0, 0, 0)


def test_palette_out_of_range():
    """Out-of-range registers should be silently ignored."""
    from amiga._palette import palette

    palette.aga(-1, 255, 0, 0)  # should not crash
    palette.aga(256, 255, 0, 0)  # should not crash
    palette.set(-1, 15, 0, 0)
    palette.set(256, 15, 0, 0)


def test_bitmap_creation():
    """Bitmap creates an 8-bit indexed surface."""
    from amiga._bitmap import Bitmap

    bm = Bitmap(320, 256, bitplanes=5)
    assert bm.width == 320
    assert bm.height == 256
    assert bm.bitplanes == 5
    assert bm._surface.get_bitsize() == 8


def test_bitmap_plot():
    """plot() sets a pixel to the given colour index."""
    from amiga._bitmap import Bitmap

    bm = Bitmap(320, 256, bitplanes=5)
    bm.plot(10, 20, 5)
    assert bm._surface.get_at_mapped((10, 20)) == 5


def test_bitmap_plot_bounds():
    """plot() out of bounds should not crash."""
    from amiga._bitmap import Bitmap

    bm = Bitmap(320, 256, bitplanes=5)
    bm.plot(-1, 0, 1)
    bm.plot(0, -1, 1)
    bm.plot(320, 0, 1)
    bm.plot(0, 256, 1)


def test_bitmap_clear():
    """clear() fills with colour index 0."""
    from amiga._bitmap import Bitmap

    bm = Bitmap(320, 256, bitplanes=5)
    bm.plot(10, 10, 5)
    bm.clear()
    assert bm._surface.get_at_mapped((10, 10)) == 0


def test_bitmap_circle_filled():
    """circle_filled() draws pixels with the given colour index."""
    from amiga._bitmap import Bitmap

    bm = Bitmap(320, 256, bitplanes=5)
    bm.circle_filled(160, 128, 10, 3)
    # Center pixel should be colour 3
    assert bm._surface.get_at_mapped((160, 128)) == 3
    # A point far away should still be 0
    assert bm._surface.get_at_mapped((0, 0)) == 0


def test_display_creation():
    """Display stores dimensions without creating a window."""
    from amiga._display import Display
    from amiga._backend import Backend

    d = Display(320, 256, bitplanes=5)
    assert d.width == 320
    assert d.height == 256
    # Window should NOT be created yet
    assert not Backend.get()._initialized


def test_display_show_initializes():
    """display.show() should initialize the backend."""
    from amiga._display import Display
    from amiga._bitmap import Bitmap
    from amiga._backend import Backend

    d = Display(320, 256, bitplanes=5)
    bm = Bitmap(320, 256, bitplanes=5)
    d.show(bm)
    assert Backend.get()._initialized


def test_palette_before_display():
    """Palette set before display.show() should still work."""
    from amiga._display import Display
    from amiga._bitmap import Bitmap
    from amiga._palette import palette
    from amiga._backend import Backend

    palette.aga(1, 255, 0, 0)
    assert Backend.get()._palette[1] == (255, 0, 0)

    d = Display(320, 256, bitplanes=5)
    bm = Bitmap(320, 256, bitplanes=5)
    bm.circle_filled(160, 128, 20, 1)
    d.show(bm)

    # Palette should still be correct
    assert Backend.get()._palette[1] == (255, 0, 0)


def test_music_module_import():
    from amiga import music
    assert music is not None


def test_music_load_sets_path(tmp_path):
    """music.load() should resolve the path relative to the caller."""
    from amiga._music import _MusicModule
    m = _MusicModule()
    # Create a dummy file so the path exists
    mod_file = tmp_path / "song.mod"
    mod_file.write_bytes(b"\x00" * 16)
    # Simulate load from a script in tmp_path
    m._loaded_path = str(mod_file)
    assert m._loaded_path.endswith("song.mod")


def test_music_volume_before_init():
    """music.volume() should not crash if mixer not initialized."""
    from amiga._music import _MusicModule
    m = _MusicModule()
    m.volume(48)  # should not raise


def test_music_stop_before_init():
    """music.stop() should not crash if mixer not initialized."""
    from amiga._music import _MusicModule
    m = _MusicModule()
    m.stop()  # should not raise
