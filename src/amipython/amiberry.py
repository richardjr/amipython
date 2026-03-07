"""Amiberry integration for running Amiga binaries."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from amipython.errors import BuildError

# Default paths
_KICKSTART_ROM = Path.home() / "Emulation" / "ROMs" / "Kickstart v3.1 rev 40.68 (1993)(Commodore)(A1200).rom"

# Minimal boot directory (ships with amipython, has S/Startup-Sequence)
_BOOT_DIR = Path(__file__).parent.parent.parent / "amiberry_boot"


def _find_amiberry() -> str:
    path = shutil.which("amiberry")
    if path is None:
        raise BuildError(
            "Amiberry is not installed or not in PATH.\n"
            "Install from: https://github.com/BlitterStudio/amiberry"
        )
    return path


def _generate_uae(binary_dir: Path, binary_name: str, boot_dir: Path) -> str:
    """Generate a .uae config that boots from minimal drive and runs the game."""
    return f"""\
config_description=amipython auto-run
config_hardware=true
config_host=true
config_version=7.1.1
use_gui=no
use_debugger=false
kickstart_rom_file={_KICKSTART_ROM}
kickstart_ext_rom_file=
pcmcia_mb_rom_file=:ENABLED
ide_mb_rom_file=:ENABLED
flash_file=
cart_file=
rtc_file=
kickshifter=false
floppy_volume=0
floppy0=
floppy1=
floppy2=
floppy3=
nr_floppies=0
floppy_speed=100
sound_output=exact
sound_channels=stereo
sound_frequency=44100
sound_interpol=anti
sound_filter=emulated
sound_filter_type=enhanced
sound_volume=0
cachesize=0
joyport0=mouse
joyport0autofire=none
joyportfriendlyname0=System mouse
joyportname0=MOUSE0
joyport1=none
joyport1autofire=none
bsdsocket_emu=false
gfx_display=0
gfx_framerate=1
gfx_width=720
gfx_height=568
gfx_width_windowed=720
gfx_height_windowed=568
gfx_backbuffers=2
gfx_lores=false
gfx_resolution=hires
gfx_linemode=double2
gfx_fullscreen_amiga=false
gfx_colour_mode=32bit
gfx_api=sdl2
gfx_api_options=hardware
immediate_blits=false
waiting_blits=automatic
multithreaded_drawing=true
ntsc=false
chipset=aga
collision_level=playfields
chipset_compatible=A1200
rtc=MSM6242B
cia_overlay=false
ksmirror_a8=true
pcmcia=true
ide=a600/a1200
fastmem_size=0
mbresmem_size=128
z3mem_size=0
bogomem_size=0
chipmem_size=16
cpu_speed=real
cpu_type=68020
cpu_model=68020
cpu_compatible=true
cpu_24bit_addressing=false
fpu_strict=false
debug_mem=false
kbd_lang=us
filesystem2=rw,DH0:System:{boot_dir},0
uaehf0=dir,rw,DH0:System:{boot_dir},0
filesystem2=ro,DH1:Run:{binary_dir},-128
uaehf1=dir,ro,DH1:Run:{binary_dir},-128
input.config=0
input.mouse_speed=100
input.autofire_speed=600
"""


def _generate_uae_adf(adf_path: Path) -> str:
    """Generate a .uae config that boots from an ADF floppy image."""
    return f"""\
config_description=amipython ADF boot
config_hardware=true
config_host=true
config_version=7.1.1
use_gui=no
use_debugger=false
kickstart_rom_file={_KICKSTART_ROM}
kickstart_ext_rom_file=
pcmcia_mb_rom_file=:ENABLED
ide_mb_rom_file=:ENABLED
flash_file=
cart_file=
rtc_file=
kickshifter=false
floppy_volume=0
floppy0={adf_path}
floppy1=
floppy2=
floppy3=
nr_floppies=1
floppy_speed=800
sound_output=exact
sound_channels=stereo
sound_frequency=44100
sound_interpol=anti
sound_filter=emulated
sound_filter_type=enhanced
sound_volume=0
cachesize=0
joyport0=mouse
joyport0autofire=none
joyportfriendlyname0=System mouse
joyportname0=MOUSE0
joyport1=none
joyport1autofire=none
bsdsocket_emu=false
gfx_display=0
gfx_framerate=1
gfx_width=720
gfx_height=568
gfx_width_windowed=720
gfx_height_windowed=568
gfx_backbuffers=2
gfx_lores=false
gfx_resolution=hires
gfx_linemode=double2
gfx_fullscreen_amiga=false
gfx_colour_mode=32bit
gfx_api=sdl2
gfx_api_options=hardware
immediate_blits=false
waiting_blits=automatic
multithreaded_drawing=true
ntsc=false
chipset=aga
collision_level=playfields
chipset_compatible=A1200
rtc=MSM6242B
cia_overlay=false
ksmirror_a8=true
pcmcia=true
ide=a600/a1200
fastmem_size=0
mbresmem_size=128
z3mem_size=0
bogomem_size=0
chipmem_size=16
cpu_speed=real
cpu_type=68020
cpu_model=68020
cpu_compatible=true
cpu_24bit_addressing=false
fpu_strict=false
debug_mem=false
kbd_lang=us
input.config=0
input.mouse_speed=100
input.autofire_speed=600
"""


def _launch(uae_content: str) -> None:
    """Write a temp .uae config and launch Amiberry."""
    amiberry = _find_amiberry()

    if not _KICKSTART_ROM.exists():
        raise BuildError(
            f"Kickstart ROM not found: {_KICKSTART_ROM}\n"
            "A real Kickstart 3.1 ROM is required."
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".uae", prefix="amipython_", delete=False
    ) as f:
        f.write(uae_content)
        uae_path = f.name

    try:
        cmd = [amiberry, "-G", "-f", uae_path]
        subprocess.run(cmd)
    except FileNotFoundError:
        raise BuildError("Amiberry is not installed or not in PATH")
    finally:
        Path(uae_path).unlink(missing_ok=True)


def launch_amiberry(binary: Path) -> None:
    """Launch a compiled Amiga binary in Amiberry.

    Uses a minimal boot drive (no Workbench) with KS 3.1.
    The binary's directory is mounted as Run: and the startup-sequence
    runs it directly.
    """
    binary = binary.resolve()

    if not binary.exists():
        raise BuildError(f"Binary not found: {binary}")

    if not _BOOT_DIR.exists():
        raise BuildError(f"Boot directory not found: {_BOOT_DIR}")

    binary_dir = binary.parent
    binary_name = binary.name

    # Write startup-sequence that runs this specific binary
    startup = _BOOT_DIR / "S" / "Startup-Sequence"
    startup.write_text(f"Run:{binary_name}\n")

    uae_content = _generate_uae(binary_dir, binary_name, _BOOT_DIR)
    _launch(uae_content)


def launch_amiberry_adf(adf_path: Path) -> None:
    """Launch Amiberry booting from an ADF floppy image.

    Uses KS 3.1 ROM with the ADF as DF0:. The ADF must contain
    S/Startup-Sequence that runs the game.
    """
    adf_path = adf_path.resolve()

    if not adf_path.exists():
        raise BuildError(f"ADF not found: {adf_path}")

    uae_content = _generate_uae_adf(adf_path)
    _launch(uae_content)
