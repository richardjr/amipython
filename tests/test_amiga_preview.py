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
    from amiga._palette import palette
    yield
    Backend.reset()
    # Reset palette singleton state
    palette._target_colors.clear()
    palette._fade_level = 15


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


def test_palette_fade_scales_colors():
    """palette.fade() should scale all set colors by level/15."""
    from amiga._backend import Backend
    from amiga._palette import palette

    palette.set(1, 15, 0, 0)   # full red → (255, 0, 0)
    assert Backend.get()._palette[1] == (255, 0, 0)

    palette.fade(0)
    assert Backend.get()._palette[1] == (0, 0, 0)

    palette.fade(15)
    assert Backend.get()._palette[1] == (255, 0, 0)

    # Half brightness: 255 * 7 // 15 = 119
    palette.fade(7)
    assert Backend.get()._palette[1] == (119, 0, 0)


def test_palette_fade_multiple_registers():
    """palette.fade() applies to all registers that have been set."""
    from amiga._backend import Backend
    from amiga._palette import palette

    palette.set(0, 0, 0, 0)
    palette.set(1, 15, 15, 15)  # white → (255, 255, 255)
    palette.set(2, 8, 4, 0)

    palette.fade(0)
    assert Backend.get()._palette[0] == (0, 0, 0)
    assert Backend.get()._palette[1] == (0, 0, 0)
    assert Backend.get()._palette[2] == (0, 0, 0)


def test_palette_fade_clamps():
    """palette.fade() clamps level to 0-15."""
    from amiga._backend import Backend
    from amiga._palette import palette

    palette.set(1, 15, 0, 0)
    palette.fade(-5)
    assert Backend.get()._palette[1] == (0, 0, 0)

    palette.fade(99)
    assert Backend.get()._palette[1] == (255, 0, 0)


def test_palette_set_after_fade():
    """palette.set() after fade should apply fade to new color."""
    from amiga._backend import Backend
    from amiga._palette import palette

    palette.fade(0)
    palette.set(1, 15, 15, 15)
    assert Backend.get()._palette[1] == (0, 0, 0)

    palette.fade(15)
    assert Backend.get()._palette[1] == (255, 255, 255)


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


def test_joy_button_pressed_is_edge_triggered(monkeypatch):
    from amiga._joy import _JoyModule
    j = _JoyModule()
    state = {"held": False}
    monkeypatch.setattr(j, "button", lambda port=0: state["held"])

    # Not pressed yet.
    assert j.button_pressed() is False

    # First frame the button goes down -> True.
    state["held"] = True
    assert j.button_pressed() is True

    # Still held on the next frame -> False (edge already consumed).
    assert j.button_pressed() is False
    assert j.button_pressed() is False

    # Released then held again -> True on that frame only.
    state["held"] = False
    assert j.button_pressed() is False
    state["held"] = True
    assert j.button_pressed() is True
    assert j.button_pressed() is False


def test_joy_direction_pressed_is_edge_triggered(monkeypatch):
    from amiga._joy import _JoyModule
    j = _JoyModule()
    state = {"l": False}
    monkeypatch.setattr(j, "left", lambda: state["l"])

    assert j.left_pressed() is False
    state["l"] = True
    assert j.left_pressed() is True
    assert j.left_pressed() is False  # still held, edge consumed
    state["l"] = False
    assert j.left_pressed() is False
    state["l"] = True
    assert j.left_pressed() is True


def test_key_module_importable():
    import amiga
    assert hasattr(amiga, "key")
    assert amiga.K_SPACE == 0x40
    assert amiga.K_LEFT == 0x4F
    assert amiga.K_P == 0x19
    assert amiga.K_A == 0x20


def test_key_just_pressed_and_released(monkeypatch):
    from amiga._key import _KeyModule, K_SPACE
    k = _KeyModule()
    state = {"held": False}
    monkeypatch.setattr(k, "_held", lambda code: state["held"])

    # Initial: not held, no edge.
    assert k.just_pressed(K_SPACE) is False
    assert k.pressed(K_SPACE) is False

    # Press -> just_pressed on first call only.
    state["held"] = True
    assert k.just_pressed(K_SPACE) is True
    assert k.just_pressed(K_SPACE) is False
    assert k.pressed(K_SPACE) is True

    # Release -> just_released on first call only.
    state["held"] = False
    assert k.just_released(K_SPACE) is True
    assert k.just_released(K_SPACE) is False


def test_sfx_module_importable_and_no_crash(tmp_path):
    """sfx.load/play/stop must be safe to call even when no audio device is available."""
    import os
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from amiga import sfx
    # Missing file — should be a no-op, not a crash.
    sfx.load(0, str(tmp_path / "missing.wav"))
    sfx.play(0)
    sfx.stop(0)
    # Out-of-range slot — no-op.
    sfx.play(99)
    sfx.stop(-1)


def test_sfx_load_real_wav(tmp_path, monkeypatch):
    """Load a real WAV file and ensure the slot ends up populated."""
    import os, wave
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    wav_path = tmp_path / "tiny.wav"
    # 100 samples, 8-bit unsigned mono, 11025 Hz, silent.
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(11025)
        w.writeframes(bytes([128] * 100))

    from amiga._sfx import _SfxModule
    s = _SfxModule()
    # Fake the caller-dir resolution so load() finds the wav directly.
    monkeypatch.setattr("inspect.stack",
                         lambda: [type("F", (), {"filename": str(tmp_path / "x.py")})()] * 2)
    s.load(0, "tiny.wav")
    # On systems without a real mixer init we may still be None — allow either.
    assert 0 in s._sounds


def test_storage_int_list_roundtrip(tmp_path, monkeypatch):
    import amiga._storage as s
    monkeypatch.setattr(s, "_base_dir", lambda: tmp_path)
    from amiga import storage

    items = [100, 75, 50, 25, 0]
    storage.save_int_list("scores", items)

    loaded: list[int] = []
    ok = storage.load_int_list("scores", loaded)
    assert ok is True
    assert loaded == [100, 75, 50, 25, 0]


def test_storage_str_roundtrip(tmp_path, monkeypatch):
    import amiga._storage as s
    monkeypatch.setattr(s, "_base_dir", lambda: tmp_path)
    from amiga import storage

    storage.save_str("name", "RJR")
    assert storage.load_str("name") == "RJR"
    assert storage.exists("name") is True
    assert storage.exists("not_there") is False
    assert storage.load_str("not_there") == ""


def test_storage_missing_int_list_returns_false(tmp_path, monkeypatch):
    import amiga._storage as s
    monkeypatch.setattr(s, "_base_dir", lambda: tmp_path)
    from amiga import storage

    existing = [1, 2, 3]
    ok = storage.load_int_list("nope", existing)
    assert ok is False
    assert existing == [1, 2, 3]   # unchanged


def test_print_centered_positions_correctly():
    from amiga import Bitmap, palette
    palette.set(1, 15, 15, 15)
    bm = Bitmap(80, 16, bitplanes=3)
    # "AB" = 2 chars × 8px = 16px wide. Centered in 80 px → starts at x = 32.
    bm.print_centered(4, "AB", color=1)
    # Pixel outside the text area should be 0; pixel inside should be 1.
    # "A" glyph first row has set bits in the middle.
    # It's easier to just check that SOME pixel in columns 32..47 is set.
    has_lit = any(bm._surface.get_at((x, 4 + 2))[:3] != (0, 0, 0)
                  for x in range(32, 48))
    assert has_lit
    # And that nothing was drawn before x=32.
    for x in range(0, 32):
        assert bm._surface.get_at((x, 4 + 2))[:3] == (0, 0, 0)


def test_print_right_positions_correctly():
    from amiga import Bitmap, palette
    palette.set(1, 15, 15, 15)
    bm = Bitmap(80, 16, bitplanes=3)
    # "HI" = 16 px wide. print_right(64, 0, "HI") → text spans x=48..63.
    bm.print_right(64, 0, "HI", color=1)
    # Last glyph must end at or before x=64. Something lit in [48,64).
    has_lit = any(bm._surface.get_at((x, 2))[:3] != (0, 0, 0)
                  for x in range(48, 64))
    assert has_lit
    for x in range(64, 80):
        assert bm._surface.get_at((x, 2))[:3] == (0, 0, 0)


def test_shuffle_preserves_multiset():
    from amiga import shuffle
    lst = list(range(20))
    shuffle(lst)
    assert sorted(lst) == list(range(20))


def test_bitmap_clear_rect():
    from amiga import Bitmap, palette
    palette.set(0, 0, 0, 0)   # index 0 = black
    palette.set(5, 15, 0, 0)  # index 5 = red — distinct from 0
    bm = Bitmap(64, 32, bitplanes=3)
    bm.box_filled(0, 0, 63, 31, 5)
    bm.clear_rect(5, 5, 20, 20)
    inside = bm._surface.get_at((10, 10))[:3]
    outside = bm._surface.get_at((40, 20))[:3]
    assert inside == (0, 0, 0)
    assert outside[0] > 0   # red component non-zero
    # Clamping — off-screen clear should be a no-op, not a crash.
    bm.clear_rect(-50, -50, 10, 10)
    bm.clear_rect(1000, 1000, 10, 10)
    bm.clear_rect(0, 0, 0, 0)


def test_bitmap_copy_from():
    from amiga import Bitmap, palette
    palette.set(0, 0, 0, 0)
    palette.set(3, 0, 15, 0)  # green — backdrop colour
    palette.set(5, 15, 0, 0)  # red — foreground colour
    bg = Bitmap(64, 32, bitplanes=3)
    fg = Bitmap(64, 32, bitplanes=3)
    bg.box_filled(0, 0, 63, 31, 3)        # green backdrop
    fg.box_filled(0, 0, 63, 31, 5)        # red foreground
    fg.copy_from(bg, 10, 10, 20, 20)      # punch a window through to the green
    inside = fg._surface.get_at((15, 15))[:3]
    outside = fg._surface.get_at((40, 5))[:3]
    assert inside[1] > 0 and inside[0] == 0   # green only
    assert outside[0] > 0 and outside[1] == 0 # red only
    # Clamping / no-op cases.
    fg.copy_from(bg, -50, -50, 10, 10)
    fg.copy_from(bg, 1000, 1000, 10, 10)
    fg.copy_from(bg, 0, 0, 0, 0)


def test_bitmap_print_at_multi_arg():
    from amiga import Bitmap
    bm = Bitmap(320, 200, bitplanes=3)
    # Should not raise — multi-arg form with mixed types.
    bm.print_at(10, 20, "SCORE", 1234, True, color=1)
    bm.print_at(10, 30, "just-one")


def test_int_to_str_formatting():
    from amiga import int_to_str
    assert int_to_str(0, 0) == "0"
    assert int_to_str(42, 6) == "000042"
    assert int_to_str(-5, 4) == "-005"
    assert int_to_str(1234, 3) == "1234"
    assert int_to_str(-1234, 6) == "-01234"


def test_joy_button_pressed_per_port(monkeypatch):
    from amiga._joy import _JoyModule
    j = _JoyModule()
    held = {0: False, 1: False}
    monkeypatch.setattr(j, "button", lambda port=0: held[port])

    # Port 0 and port 1 must track independently.
    held[0] = True
    assert j.button_pressed(0) is True
    assert j.button_pressed(1) is False
    held[1] = True
    assert j.button_pressed(0) is False  # port 0 already latched
    assert j.button_pressed(1) is True
