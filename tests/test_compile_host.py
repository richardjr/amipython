"""Host compilation tests — transpile, compile with gcc, run, check output."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from amipython.pipeline import transpile

HEADER_DIR = Path(__file__).parent.parent / "src" / "amipython" / "c_runtime"


def _has_gcc():
    return shutil.which("gcc") is not None


pytestmark = pytest.mark.skipif(not _has_gcc(), reason="gcc not available")


def _compile_and_run(source: str) -> str:
    """Transpile Python source, compile with gcc, run, return stdout."""
    c_code = transpile(source)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Write C file
        c_file = tmppath / "test.c"
        c_file.write_text(c_code)

        # Copy headers
        shutil.copy2(HEADER_DIR / "amipython.h", tmppath / "amipython.h")

        # Build source file list
        source_files = [str(c_file)]

        # If engine is used, copy engine headers and host stubs
        if '#include "amipython_engine.h"' in c_code:
            shutil.copy2(HEADER_DIR / "amipython_engine.h",
                         tmppath / "amipython_engine.h")
            shutil.copy2(HEADER_DIR / "amipython_engine_host.c",
                         tmppath / "amipython_engine_host.c")
            source_files.append(str(tmppath / "amipython_engine_host.c"))

        # Compile
        binary = tmppath / "test"
        result = subprocess.run(
            ["gcc", "-std=c89", "-pedantic", "-Wall", "-Werror",
             "-o", str(binary), *source_files, "-lm"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"gcc compilation failed:\n{result.stderr}"
        )

        # Run
        result = subprocess.run(
            [str(binary)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"binary exited with code {result.returncode}:\n{result.stderr}"
        )
        return result.stdout


class TestHelloWorld:
    def test_hello(self):
        output = _compile_and_run('''
x: int = 42
name: str = "Amiga"

def square(n: int) -> int:
    return n * n

print("Hello,", name)
print("square(x) =", square(x))
''')
        assert "Hello, Amiga" in output
        assert "square(x) = 1764" in output


class TestArithmetic:
    def test_basic_ops(self):
        output = _compile_and_run('''
a: int = 10
b: int = 3
print("add =", a + b)
print("sub =", a - b)
print("mul =", a * b)
print("floordiv =", a // b)
print("mod =", a % b)
print("pow =", a ** b)
''')
        assert "add = 13" in output
        assert "sub = 7" in output
        assert "mul = 30" in output
        assert "floordiv = 3" in output
        assert "mod = 1" in output
        assert "pow = 1000" in output

    def test_negative_floordiv(self):
        """Python floor division rounds toward -infinity."""
        output = _compile_and_run('''
x = -7 // 2
print("result =", x)
''')
        assert "result = -4" in output

    def test_negative_mod(self):
        """Python modulo result has same sign as divisor."""
        output = _compile_and_run('''
x = -7 % 3
print("result =", x)
''')
        assert "result = 2" in output


class TestControlFlow:
    def test_for_range(self):
        output = _compile_and_run('''
for i in range(5):
    print(i)
''')
        lines = output.strip().split("\n")
        assert [l.strip() for l in lines] == ["0", "1", "2", "3", "4"]

    def test_while_break(self):
        output = _compile_and_run('''
count: int = 0
while True:
    count = count + 1
    if count >= 3:
        break
print("count =", count)
''')
        assert "count = 3" in output


class TestFunctions:
    def test_recursive_function(self):
        output = _compile_and_run('''
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print("5! =", factorial(5))
''')
        assert "5! = 120" in output

    def test_global_mutation(self):
        output = _compile_and_run('''
counter: int = 0

def increment() -> int:
    global counter
    counter = counter + 1
    return counter

print(increment())
print(increment())
print(increment())
''')
        lines = output.strip().split("\n")
        assert [l.strip() for l in lines] == ["1", "2", "3"]


class TestEngine:
    def test_display_init(self):
        output = _compile_and_run('''
from amiga import Display
d = Display(320, 256, bitplanes=8)
''')
        assert "[display] init 320x256 8bp" in output

    def test_bitmap_methods(self):
        output = _compile_and_run('''
from amiga import Bitmap
bm = Bitmap(320, 256)
bm.plot(10, 20, 3)
bm.clear()
''')
        assert "[bitmap] init 320x256 5bp" in output
        assert "[bitmap] plot 10,20 color=3" in output
        assert "[bitmap] clear 320x256" in output

    def test_palette_module(self):
        output = _compile_and_run('''
from amiga import palette
palette.aga(0, 255, 128, 64)
''')
        assert "[palette] aga 0 r=255 g=128 b=64" in output

    def test_wait_mouse(self):
        output = _compile_and_run('''
from amiga import wait_mouse
wait_mouse()
''')
        assert "[input] wait_mouse" in output

    def test_display_show_bitmap(self):
        output = _compile_and_run('''
from amiga import Display, Bitmap
d = Display(320, 256)
bm = Bitmap(320, 256)
d.show(bm)
''')
        assert "[display] show 320x256 on 320x256" in output

    def test_shape_grab(self):
        output = _compile_and_run('''
from amiga import Bitmap, Shape
bm = Bitmap(16, 16, bitplanes=3)
bm.circle_filled(8, 8, 7, 1)
ball = Shape.grab(bm, 0, 0, 16, 16)
''')
        assert "[bitmap] init 16x16 3bp" in output
        assert "[shape] grab 16x16 from 16x16 at 0,0" in output

    def test_display_blit(self):
        output = _compile_and_run('''
from amiga import Display, Bitmap, Shape
d = Display(320, 200, bitplanes=3)
bm = Bitmap(16, 16, bitplanes=3)
bm.circle_filled(8, 8, 7, 1)
ball = Shape.grab(bm, 0, 0, 16, 16)
d.blit(ball, 100, 50)
''')
        assert "[display] blit 16x16 at 100,50" in output

    def test_rnd(self):
        output = _compile_and_run('''
from amiga import rnd
x = rnd(100)
''')
        assert "[rnd] 100" in output

    def test_joy_button(self):
        output = _compile_and_run('''
from amiga import joy
x = joy.button(0)
''')
        assert "[input] joy_button port=0" in output

    def test_run_game_loop(self):
        output = _compile_and_run('''
from amiga import run, joy
count: int = 0

def update():
    global count
    count = count + 1

run(update, until=lambda: joy.button(0))
print("iterations =", count)
''')
        # joy.button returns TRUE after 3 calls, so loop runs 3 times
        assert "iterations = 3" in output

    def test_bouncing_ball(self):
        output = _compile_and_run('''
from amiga import Display, Bitmap, Shape, palette, run, joy, vwait

display = Display(320, 200, bitplanes=3)
bm = Bitmap(320, 200, bitplanes=3)

palette.set(1, 15, 0, 0)
bm.circle_filled(8, 8, 7, 1)
ball = Shape.grab(bm, 0, 0, 16, 16)
bm.clear()

x: float = 160.0
y: float = 100.0
xs: float = 3.0
ys: float = 2.0

display.show(bm)

def update():
    global x, y, xs, ys
    x = x + xs
    y = y + ys
    if x < 10.0 or x > 290.0:
        xs = -xs
    if y < 10.0 or y > 170.0:
        ys = -ys
    bm.clear()
    display.blit(ball, int(x), int(y))

run(update, until=lambda: joy.button(0))
''')
        assert "[display] init 320x200 3bp" in output
        assert "[shape] grab 16x16 from 320x200 at 0,0" in output
        assert "[display] show 320x200 on 320x200" in output
        # The loop runs 3 times before joy.button returns TRUE
        assert output.count("[input] vwait") == 3

class TestStruct:
    def test_struct_basic(self):
        output = _compile_and_run('''
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

p = Point(x=10, y=20)
print("x =", p.x)
print("y =", p.y)
''')
        assert "x = 10" in output
        assert "y = 20" in output

    def test_struct_field_mutation(self):
        output = _compile_and_run('''
from dataclasses import dataclass

@dataclass
class Ball:
    x: float
    y: float

b = Ball(x=1.0, y=2.0)
b.x += 0.5
b.y = b.y * 2.0
print("x =", b.x)
print("y =", b.y)
''')
        assert "x = 1.5" in output
        assert "y = 4.0" in output

    def test_struct_with_defaults(self):
        output = _compile_and_run('''
from dataclasses import dataclass

@dataclass
class Star:
    angle: int
    speed: float = 1.0

s = Star(angle=45)
print("angle =", s.angle)
print("speed =", s.speed)
''')
        assert "angle = 45" in output
        assert "speed = 1.0" in output


class TestList:
    def test_list_of_int(self):
        output = _compile_and_run('''
nums: list[int] = []
for i in range(5):
    nums.append(i * 10)
print("len =", len(nums))
for n in nums:
    print(n)
''')
        assert "len = 5" in output
        lines = output.strip().split("\n")
        assert "0" in lines[1].strip()
        assert "40" in lines[5].strip()

    def test_list_of_struct(self):
        output = _compile_and_run('''
from dataclasses import dataclass

@dataclass
class Ball:
    x: float
    y: float

balls: list[Ball] = []
balls.append(Ball(x=10.0, y=20.0))
balls.append(Ball(x=30.0, y=40.0))

print("count =", len(balls))
for b in balls:
    print("x =", b.x)
''')
        assert "count = 2" in output
        assert "x = 10.0" in output
        assert "x = 30.0" in output

    def test_list_struct_mutation(self):
        output = _compile_and_run('''
from dataclasses import dataclass

@dataclass
class Ball:
    x: float

balls: list[Ball] = []
balls.append(Ball(x=1.0))
balls.append(Ball(x=2.0))

for b in balls:
    b.x += 10.0

for b in balls:
    print(b.x)
''')
        lines = output.strip().split("\n")
        assert "11.0" in lines[0].strip()
        assert "12.0" in lines[1].strip()


class TestEngine:
    def test_display1_example(self):
        output = _compile_and_run('''
from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=8)
bm = Bitmap(320, 256, bitplanes=8)

for i in range(256):
    palette.aga(i, i, i, i)

for i in range(255, 0, -1):
    bm.circle_filled(160, 128, i // 2, i)

display.show(bm)
wait_mouse()
''')
        assert "[display] init 320x256 8bp" in output
        assert "[bitmap] init 320x256 8bp" in output
        assert "[palette] aga 0 r=0 g=0 b=0" in output
        assert "[palette] aga 255 r=255 g=255 b=255" in output
        assert "[bitmap] circle_filled 160,128 r=127 color=255" in output
        assert "[bitmap] circle_filled 160,128 r=0 color=1" in output
        assert "[display] show 320x256 on 320x256" in output
        assert "[input] wait_mouse" in output
