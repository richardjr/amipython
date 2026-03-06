# Blitz Basic to amipython

amipython's API is designed to cover the same game development capabilities as Blitz Basic's "blitz mode", but with Pythonic syntax that any Python developer can read immediately.

## Game Loop Model

Blitz Basic uses an explicit `While`/`Wend` loop with manual `VWait` and buffer swapping. amipython abstracts this into a `run()` function that handles frame timing, double-buffer swaps, and blit queue management automatically.

```python
# amipython game loop — the engine calls update() every frame
def update():
    # game logic here — drawing, movement, input
    pass

run(update, until=joy.button(0))
```

The transpiler generates the C equivalent: a `while` loop with `VWait`, `DisplayBitMap` swap, `UnQueue`/`QBlit`, wrapping the user's update function.

## API Modules

| Module | Purpose | Blitz Equivalent |
|---|---|---|
| `Display` | Screen setup, double buffering, display modes | `BitMap`, `InitCopList`, `CreateDisplay`, `DisplayBitMap` |
| `DualPlayfield` | Dual playfield with independent scroll | `InitCopList` with $36 flag, dual `DisplayBitMap` |
| `Bitmap` | Offscreen drawing surface | `BitMap`, `Use BitMap` |
| `Shape` | Loadable/grabbable graphic objects | `LoadShape`, `GetaShape`, `MidHandle` |
| `Sprite` | Hardware sprites | `GetaSprite`, `ShowSprite`, `InFront` |
| `Tilemap` | Scrolling tile maps with automatic column replacement | Manual tile loop + `QWrap` + `DisplayBitMap` offset |
| `BlitQueue` | Automatic erase/draw cycle for bobs | `Queue`, `QBlit`, `UnQueue` |
| `palette` | Colour management (OCS/ECS) | `RGB`, `PalRGB`, `AGAPalRGB` |
| `copper` | Per-scanline colour changes, raw copper | `ColSplit`, `DisplayRGB`, `CustomCop` |
| `collision` | Hardware sprite/playfield collision | `SetColl`, `DoColl`, `PColl` |
| `joy` | Joystick input | `Joyx`, `Joyy`, `Joyb` |
| `mouse` | Mouse position and buttons | `Mouse On`, `MouseX`, `MouseY`, `MouseArea` |
| `key` | Keyboard input | `BlitzKeys On`, `RawStatus`, `Inkey$` |
| `sound` | Paula audio playback | Audio commands |
| `math` | Fast trig tables, wrap, clamp | `QWrap`, `QLimit`, sin/cos lookup |

---

## Side-by-Side Examples

### 1. Display Setup + Drawing

**Blitz Basic** (`display1.ab3`):
```basic
BitMap 0,320,256,5
For i=0 To 31:RGB i,i*2,i*2,i*2:Next
InitCopList 0,44,256,$13005,8,256,0
BLITZ
CreateDisplay 0
DisplayBitMap 0,0:DisplayPalette 0,0
For i=31 To 1 Step -1:Circlef 160,128,i*4,i:Next
MouseWait
End
```

**amipython**:
```python
from amiga import Display, Bitmap, palette, wait_mouse

display = Display(320, 256, bitplanes=5)
bm = Bitmap(320, 256, bitplanes=5)

for i in range(32):
    palette.aga(i, i * 8, i * 8, i * 8)

for i in range(31, 0, -1):
    bm.circle_filled(160, 128, i * 4, i)

display.show(bm)
wait_mouse()
```

---

### 2. Sprite Movement

**Blitz Basic** (`sprites_simple_example.ab3`):
```basic
BitMap 0,320,DispHeight,2
Boxf 0,0,63,63,1
Boxf 8,8,55,55,2
Boxf 16,16,47,47,3
GetaShape 0,0,0,64,64
GetaSprite 0,0
Free Shape 0
BLITZ
Cls
Slice 0,44,2
Show 0
For k = 0 To 1
  RGB k*4+17,15,15,0
  RGB k*4+18,15,8,0
  RGB k*4+19,15,4,0
Next k
For k = 0 To 319
  VWait
  ShowSprite 0,k,100,0
Next k
MouseWait
End
```

**amipython**:
```python
from amiga import Display, Bitmap, Sprite, palette

display = Display(320, 256, bitplanes=2)
bm = Bitmap(320, 256, bitplanes=2)

bm.box_filled(0, 0, 63, 63, 1)
bm.box_filled(8, 8, 55, 55, 2)
bm.box_filled(16, 16, 47, 47, 3)
player = Sprite.grab(bm, 0, 0, 64, 64)

for k in range(2):
    palette.set(k * 4 + 17, 15, 15, 0)
    palette.set(k * 4 + 18, 15, 8, 0)
    palette.set(k * 4 + 19, 15, 4, 0)

bm.clear()
display.show(bm)

for k in range(320):
    vwait()
    player.show(k, 100, channel=0)

wait_mouse()
```

---

### 3. Double-Buffered Bob Animation

**Blitz Basic** (`doublebuffer.ab3`):
```basic
NEWTYPE.ball
  x.q : y : xs : ys
End NEWTYPE
Dim List balls.ball(10)
LoadShape 0,"data/ball",0

; ... populate balls list ...

BLITZ
BitMap 0,320,200,3 : BitMap 1,320,200,3
Queue 0,50 : Queue 1,50
InitCopList 0,44,200,3,8,8,0
DisplayPalette 0,0 : DisplayBitMap 0,0 : CreateDisplay 0

While Joyb(0)=0
  ResetList balls()
  VWait
  DisplayBitMap 0,db : db=1-db : Use BitMap db
  UnQueue db
  While NextItem(balls())
    balls()\x + balls()\xs
    balls()\y + balls()\ys
    If balls()\x<10 OR balls()\x>290 Then balls()\xs = -balls()\xs
    If balls()\y<10 OR balls()\y>170 Then balls()\ys = -balls()\ys
    QBlit db,0,balls()\x,balls()\y
  Wend
Wend
End
```

**amipython**:
```python
from amiga import Display, Shape, joy, rnd

class Ball:
    x: float
    y: float
    xs: float
    ys: float

display = Display(320, 200, bitplanes=3, double_buffer=True)
ball_shape = Shape.load("data/ball")
balls: list[Ball] = []

for i in range(10):
    balls.append(Ball(
        x=rnd(280) + 10, y=rnd(160) + 10,
        xs=(rnd() - 0.5) * 8, ys=(rnd() - 0.5) * 8
    ))

def update():
    for b in balls:
        b.x += b.xs
        b.y += b.ys
        if b.x < 10 or b.x > 290:
            b.xs = -b.xs
        if b.y < 10 or b.y > 170:
            b.ys = -b.ys
        display.blit(ball_shape, b.x, b.y)

run(update, until=joy.button(0))
```

The `run()` function handles VWait, double-buffer swap, and QBlit/UnQueue automatically. The user just writes movement logic and draw calls.

---

### 4. Tile Map Scrolling

**Blitz Basic** (`scrolling.ab3`):
```basic
BitMap 0,256,12,1
LoadBitMap 0,"Data/scrollmap"
Dim m(255,63)
For x=0 To 255
  For y=0 To 11
    m(x,y)=Point(x,y)
  Next:Next
LoadShape 0,"Data/block",0

; ... tile blitting statement ...

BitMap 0,384,192,3
; ... fill initial tiles ...

a=.5 : f=.25

While Joyb(1)=0 AND RawStatus($45)=0
  VWait
  DisplayBitMap 0,0,sx,sy
  If Joyx(1)=-1 Then xs-a : If xs<-16 Then xs=-16
  If Joyx(1)=1  Then xs+a : If xs>16 Then xs=16
  ; ... replace edge tile columns with QWrap ...
  mx = QWrap(mx+xs, 0, 4096)
  sx = QWrap(sx+xs, 16, 368)
Wend
End
```

**amipython**:
```python
from amiga import Display, Tilemap, joy, key

display = Display(320, 192, bitplanes=3)
tilemap = Tilemap.load("data/scrollmap", tile_shape="data/block")

accel = 0.5
friction = 0.25
speed_x = 0.0

def update():
    global speed_x

    if joy.left(1) or key.held(key.LEFT):
        speed_x -= accel
        speed_x = max(speed_x, -16.0)
    elif joy.right(1) or key.held(key.RIGHT):
        speed_x += accel
        speed_x = min(speed_x, 16.0)
    else:
        speed_x *= (1.0 - friction)

    tilemap.scroll(speed_x, 0)

run(update, until=lambda: joy.button(1) or key.pressed(key.ESC))
```

The `Tilemap` object handles the oversized bitmap, QWrap column replacement, and hardware scroll offset internally.

---

### 5. Smooth Hardware Scrolling

**Blitz Basic** (`smoothscrolling.ab3`):
```basic
BLITZ
BitMap 0,640,400,3
For k=1 To 1000
  Plot Rnd(640),Rnd(400),Rnd(7)+1
Next
InitCopList 0,44,200,$13,8,8,0
CreateDisplay 0
Mouse On
While Joyb(0)=0
  VWait
  DisplayBitMap 0,0,MouseX,MouseY
Wend
End
```

**amipython**:
```python
from amiga import Display, Bitmap, mouse, joy, rnd

display = Display(320, 200, bitplanes=3)
bm = Bitmap(640, 400, bitplanes=3)

for k in range(1000):
    bm.plot(rnd(640), rnd(400), rnd(7) + 1)

def update():
    display.scroll_to(mouse.x, mouse.y)

display.show(bm)
run(update, until=joy.button(0))
```

---

### 6. Momentum Scroller with Wrap

**Blitz Basic** (`scroller.ab3`):
```basic
BLITZ
Mouse On
BitMap 0,640,512,3
For i=0 To 150
  Circlef Rnd(320-32)+16,Rnd(256-32)+16,Rnd(16),Rnd(8)
Next
Scroll 0,0,320,256,320,0
Scroll 0,0,640,256,0,256
InitCopList 0,$13
CreateDisplay 0
While Joyb(0)=0
  VWait
  DisplayBitMap 0,db,x,y
  xa=QLimit(xa+MouseXSpeed,-20,20)
  ya=QLimit(ya+MouseYSpeed,-20,20)
  x=QWrap(x+xa,0,320)
  y=QWrap(y+ya,0,256)
Wend
End
```

**amipython**:
```python
from amiga import Display, Bitmap, mouse, joy, rnd, wrap, clamp

display = Display(320, 256, bitplanes=3)
bm = Bitmap(640, 512, bitplanes=3)

for i in range(150):
    bm.circle_filled(rnd(288) + 16, rnd(224) + 16, rnd(16), rnd(8))

# duplicate quadrants for seamless wrapping
bm.copy_region(0, 0, 320, 256, 320, 0)
bm.copy_region(0, 0, 640, 256, 0, 256)

display.show(bm)
x = 0.0
y = 0.0
xa = 0.0
ya = 0.0

def update():
    global x, y, xa, ya
    xa = clamp(xa + mouse.x_speed, -20, 20)
    ya = clamp(ya + mouse.y_speed, -20, 20)
    x = wrap(x + xa, 0, 320)
    y = wrap(y + ya, 0, 256)
    display.scroll_to(int(x), int(y))

run(update, until=joy.button(0))
```

---

### 7. Copper Colour Splits

**Blitz Basic** (`lineswithcopsplit.ab3`):
```basic
BLITZ
BitMap 0,320,270,1
Slice 0,34,320,270,$FFFA,1,8,2,320,320
RGB 0,0,0,15 : RGB 1,15,15,0
For i=1 To 7
  ColSplit 0,0,0,8+i,i*5+160
Next
CustomCop co$,190+34
Show 0
```

**amipython**:
```python
from amiga import Display, Bitmap, palette, copper, Color

display = Display(320, 270, bitplanes=1)
bm = Bitmap(320, 270, bitplanes=1)

palette.set(0, 0, 0, 15)
palette.set(1, 15, 15, 0)

for i in range(1, 8):
    copper.color_at(scanline=i * 5 + 160, register=0, color=Color(0, 0, 8 + i))

# raw copper for advanced effects
copper.raw(scanline=224, instructions=[
    (copper.BPLMOD1, -122),
    (copper.BPLMOD2, -122),
])

display.show(bm)
```

---

### 8. Sprite Collision Detection

**Blitz Basic** (`sprites_Collision.ab3`):
```basic
NoCli
BitMap 0,320,200,4
Boxf 0,0,7,7,1
GetaShape 0,0,0,8,8
GetaSprite 0,0
Cls
BLITZ
Slice 0,44,320,200,$fff8,4,8,32,320,320
Show 0
For k = 1 To 100
  Plot Rnd(320),Rnd(200),Rnd(14)+1
Next
Circlef 160,100,40,15
SetColl 15,4
Mouse On : Pointer 0,0
While Joyb(0) = 0
  VWait
  DoColl
  Locate 0,0
  If PColl(0) Then Print "BANG!" Else Print "     "
Wend
End
```

**amipython**:
```python
from amiga import Display, Bitmap, Sprite, collision, mouse, joy, rnd

display = Display(320, 200, bitplanes=4)
bm = Bitmap(320, 200, bitplanes=4)

bm.box_filled(0, 0, 7, 7, 1)
player = Sprite.grab(bm, 0, 0, 8, 8)
bm.clear()

for k in range(100):
    bm.plot(rnd(320), rnd(200), rnd(14) + 1)

bm.circle_filled(160, 100, 40, 15)
collision.register(color=15, mask=4)

display.show(bm)
mouse.set_pointer(player)

def update():
    collision.check()
    if player.collided():
        bm.print_at(0, 0, "BANG!")
    else:
        bm.print_at(0, 0, "     ")

run(update, until=joy.button(0))
```

---

### 9. Dual Playfield Parallax

**Blitz Basic** (`dualpf.ab3`):
```basic
BLITZ
BitMap 0,640,512,3
For i=0 To 255
  Line Rnd(640),Rnd(512),Rnd(640),Rnd(512),Rnd(7)
Next
BitMap 1,640,512,3
For i=0 To 255
  Circlef Rnd(640),Rnd(512),Rnd(15),Rnd(7)
Next
InitCopList 0,$36
CreateDisplay 0
While Joyb(0) = 0
  VWait
  x1=160+Sin(r)*160 : y1=128+Cos(r)*128
  x2=160-Sin(r)*160 : y2=128-Cos(r)*128
  DisplayBitMap 0,1,x1,y1,0,x2,y2
  r + .05
Wend
End
```

**amipython**:
```python
from amiga import DualPlayfield, Bitmap, joy, sin, cos, rnd

fg = Bitmap(640, 512, bitplanes=3)
bg = Bitmap(640, 512, bitplanes=3)

for i in range(256):
    fg.line(rnd(640), rnd(512), rnd(640), rnd(512), rnd(7))

for i in range(256):
    bg.circle_filled(rnd(640), rnd(512), rnd(15), rnd(7))

display = DualPlayfield(fg, bg)
r = 0.0

def update():
    global r
    display.scroll_fg(160 + sin(r) * 160, 128 + cos(r) * 128)
    display.scroll_bg(160 - sin(r) * 160, 128 - cos(r) * 128)
    r += 0.05

run(update, until=joy.button(0))
```

---

### 10. Starfield with Entity Management

**Blitz Basic** (`starfield.ab3`):
```basic
NEWTYPE.star
  angle.w : dist.q : speed : acc
  sx.w : sy
End NEWTYPE
Dim List stars.star(128)
USEPATH stars()
Dim qsin.q(1023), qcos.q(1023)
For i = 0 To 1023
  qsin(i) = Sin(i * Pi / 512)
  qcos(i) = Cos(i * Pi / 512)
Next i
BLITZ
; ... display setup ...
While Joyb(O)=O
  mx = MouseX
  ResetList stars()
  While NextItem(stars())
    Plot \sx, \sy, 0
    \speed + \acc
    \dist + \speed
    \sx = 160 + qcos((\angle + mx) & 1023) * \dist
    \sy = 128 + qsin((\angle + mx) & 1023) * \dist
    If \sx<0 OR \sx>319 OR \sy<0 OR \sy>256
      KillItem stars()
    Else
      Plot \sx, \sy, \dist / 20
    EndIf
  Wend
  If AddItem(stars())
    \dist=0 : \speed=0 : \acc=Rnd(1)/32 : \angle=Rnd(1024)
  EndIf
Wend
End
```

**amipython**:
```python
from amiga import Display, Bitmap, mouse, joy, rnd, sin_table, cos_table

class Star:
    angle: int
    dist: float = 0.0
    speed: float = 0.0
    acc: float = 0.0
    sx: int = 160
    sy: int = 128

display = Display(320, 256, bitplanes=3)
bm = Bitmap(320, 256, bitplanes=3)
display.show(bm)

stars: list[Star] = []
qsin = sin_table(1024)
qcos = cos_table(1024)

def update():
    mx = mouse.x

    for star in stars[:]:
        bm.plot(star.sx, star.sy, 0)          # erase
        star.speed += star.acc
        star.dist += star.speed
        star.sx = 160 + int(qcos[(star.angle + mx) & 1023] * star.dist)
        star.sy = 128 + int(qsin[(star.angle + mx) & 1023] * star.dist)

        if star.sx < 0 or star.sx > 319 or star.sy < 0 or star.sy > 256:
            stars.remove(star)
        else:
            bm.plot(star.sx, star.sy, int(star.dist / 20))

    if len(stars) < 128:
        stars.append(Star(angle=rnd(1024), acc=rnd() / 32))

run(update, until=joy.button(0))
```

---

### 11. Mouse + Keyboard Input

**Blitz Basic** (`mouseOfTwo.ab3` + `blitzIO_RawStatus.ab3`):
```basic
Mouse On
MouseArea 0,0,160-8,199,0
MouseArea 160,0,319,199,1
Repeat
  VWait
  NPrint "X = ",MouseX," " : NPrint "Y = ",MouseY(0)," "
  NPrint "JoyX = ", Joyx(0)," " : NPrint "JoyY = ", Joyy(0)," "
Until Joyb(0) OR Joyb(1)

; Keyboard:
BlitzKeys On
While Joyb(0) = 0
  VWait
  If RawStatus(80) Then NPrint "Down" Else NPrint "Up  "
Wend
```

**amipython**:
```python
from amiga import Display, Bitmap, mouse, joy, key

display = Display(320, 200, bitplanes=2)
bm = Bitmap(320, 200, bitplanes=2)
display.show(bm)

mouse.set_area(0, 0, 152, 199, port=0)
mouse.set_area(160, 0, 319, 199, port=1)

def update():
    bm.print_at(0, 0, f"X = {mouse.x}  ")
    bm.print_at(0, 1, f"Y = {mouse.y}  ")
    bm.print_at(0, 2, f"JoyX = {joy.x(0)}  ")
    bm.print_at(0, 3, f"JoyY = {joy.y(0)}  ")

    if key.held(key.F1):
        bm.print_at(0, 5, "Down")
    else:
        bm.print_at(0, 5, "Up  ")

run(update, until=lambda: joy.button(0) or joy.button(1))
```

---

### 12. Sprite Priority (Z-ordering)

**Blitz Basic** (`sprites_InFront.ab3`):
```basic
; ... create sprite ...
BLITZ
Cls
Slice 0,44,2 : Show 0
Circlef 0,160,100,90,3
Circlef 0,160,100,80,0
InFront 4
For k = 0 To 319
  VWait
  ShowSprite 0,k,20,0      ; in front of bitmap
  ShowSprite 0,k,120,4     ; behind bitmap
Next
MouseWait
```

**amipython**:
```python
from amiga import Display, Bitmap, Sprite

display = Display(320, 256, bitplanes=2)
bm = Bitmap(320, 256, bitplanes=2)
# ... create sprite ...

bm.circle_filled(160, 100, 90, 3)
bm.circle_filled(160, 100, 80, 0)

display.show(bm)
display.sprites_behind(from_channel=4)    # channels 4-7 behind bitmap

for k in range(320):
    vwait()
    player.show(k, 20, channel=0)         # in front
    player.show(k, 120, channel=4)        # behind

wait_mouse()
```

---

## Blitz Feature Coverage

Complete mapping of Blitz Basic blitz-mode capabilities to amipython API.

### Display System
| Blitz | amipython | Notes |
|---|---|---|
| `BLITZ` / `AMIGA` | Automatic | Transpiler handles mode switch |
| `BitMap id,w,h,depth` | `Bitmap(w, h, bitplanes=depth)` | Named objects not numbered slots |
| `Use BitMap id` | Automatic via `display` | Double buffer managed by `run()` |
| `InitCopList`, `CreateDisplay` | `Display(w, h, ...)` | Single constructor |
| `DisplayBitMap id,bm,x,y` | `display.scroll_to(x, y)` | |
| `DisplayPalette` | Automatic | |
| `DisplayAdjust` | `Display(overscan=True)` | |
| Dual playfield (`$36` flag) | `DualPlayfield(fg, bg)` | |
| `ShowF` / `ShowB` | Automatic via `DualPlayfield` | |

### Palette & Copper
| Blitz | amipython | Notes |
|---|---|---|
| `RGB reg,r,g,b` | `palette.set(reg, r, g, b)` | OCS/ECS 4-bit per channel (0-15) |
| `AGAPalRGB pal,reg,r,g,b` | `palette.aga(reg, r, g, b)` | 8-bit per channel (0-255), downscaled to OCS 12-bit |
| `ColSplit` | `copper.color_at(scanline, reg, color)` | |
| `DisplayRGB` | `copper.gradient(reg, start, end, colors)` | |
| `CustomCop` | `copper.raw(scanline, instructions)` | |

### Drawing Primitives
| Blitz | amipython | Notes |
|---|---|---|
| `Plot x,y,col` | `bm.plot(x, y, col)` | |
| `Point(x,y)` | `bm.read_pixel(x, y)` | |
| `Line x1,y1,x2,y2,col` | `bm.line(x1, y1, x2, y2, col)` | |
| `Box` / `Boxf` | `bm.box()` / `bm.box_filled()` | |
| `Circle` / `Circlef` | `bm.circle()` / `bm.circle_filled()` | |
| `Poly` / `Polyf` | `bm.polygon()` / `bm.polygon_filled()` | |
| `Cls` | `bm.clear()` | |
| `Scroll` / `BlockScroll` | `bm.copy_region()` | |
| `CopyBitMap` | `bm.copy_to(other)` | |

### Shapes & Blitting
| Blitz | amipython | Notes |
|---|---|---|
| `LoadShape id,file$` | `Shape.load(path)` | |
| `GetaShape id,x,y,w,h` | `Shape.grab(bm, x, y, w, h)` | |
| `MidHandle id` | `shape.set_origin("center")` | |
| `Free Shape id` | Automatic (scope-based) | |
| `Blit shape,x,y` | `display.blit(shape, x, y)` | |
| `BlitMode CookieMode` | `display.blit(shape, x, y, mode=COOKIE)` | Default mode |
| `BlitMode EraseMode` | Automatic via `run()` | UnQueue handles erase |
| `Queue` / `QBlit` / `UnQueue` | Automatic via `run()` | |

### Hardware Sprites
| Blitz | amipython | Notes |
|---|---|---|
| `GetaSprite id,shape` | `Sprite.grab(bm, x, y, w, h)` | |
| `ShowSprite shape,x,y,ch` | `sprite.show(x, y, channel=ch)` | |
| `DisplaySprite` | `sprite.show()` via copperlist | |
| `InFront ch` | `display.sprites_behind(from_channel=ch)` | |
| `InFrontF` / `InFrontB` | `display.fg_sprites_behind()` etc. | |
| `Pointer shape,ch,port` | `mouse.set_pointer(sprite)` | |
| `SpriteMode 2` | `Sprite.set_width(64)` | |

### Collision Detection
| Blitz | amipython | Notes |
|---|---|---|
| `SetColl colour,mask` | `collision.register(color, mask)` | |
| `DoColl` | `collision.check()` | |
| `PColl(channel)` | `sprite.collided()` | |

### Input
| Blitz | amipython | Notes |
|---|---|---|
| `Joyx(port)` / `Joyy(port)` | `joy.x(port)` / `joy.y(port)` | Returns -1, 0, 1 |
| `Joyb(port)` | `joy.button(port)` | |
| `Mouse On` | Automatic | |
| `MouseX` / `MouseY` | `mouse.x` / `mouse.y` | |
| `MouseX(port)` | `mouse.x_port(port)` | |
| `MouseXSpeed` | `mouse.x_speed` | |
| `MouseArea x1,y1,x2,y2` | `mouse.set_area(x1, y1, x2, y2)` | |
| `MouseWait` | `wait_mouse()` | |
| `BlitzKeys On` | Automatic | |
| `RawStatus(scancode)` | `key.held(key.F1)` | Named constants |
| `Inkey$` | `key.char()` | |

### Timing
| Blitz | amipython | Notes |
|---|---|---|
| `VWait` | `vwait()` | Manual; `run()` handles it automatically |
| `VWait n` | `vwait(n)` | Wait n frames |

### Data Structures
| Blitz | amipython | Notes |
|---|---|---|
| `NEWTYPE.name` | `class Name:` with annotations | Compiles to C struct |
| `Dim array(size)` | `values: list[int] = [0] * size` | Fixed-size array |
| `Dim List name.type(max)` | `items: list[Type] = []` | Dynamic list |
| `USEPATH` / `\field` | Standard `obj.field` | |
| `AddItem` / `KillItem` | `list.append()` / `list.remove()` | |
| `ResetList` / `NextItem` | `for item in list:` | |

### Math & Utility
| Blitz | amipython | Notes |
|---|---|---|
| `QWrap(val, min, max)` | `wrap(val, min, max)` | Modular wrap |
| `QLimit(val, min, max)` | `clamp(val, min, max)` | Clamp to range |
| `Rnd(n)` | `rnd(n)` | Random integer |
| `Rnd` (no args) | `rnd()` | Random 0.0-1.0 |
| `Sin` / `Cos` | `sin()` / `cos()` | Standard trig |
| Lookup table pattern | `sin_table(size)` / `cos_table(size)` | Pre-computed |
| `Abs` / `Sgn` / `Int` | `abs()` / `sgn()` / `int()` | |
| `LSL` / `LSR` | `<<` / `>>` | Python operators |

### Text Output
| Blitz | amipython | Notes |
|---|---|---|
| `BitMapOutput id` | Draw on any `Bitmap` | |
| `Locate col,row` | Part of `bm.print_at(x, y, text)` | |
| `Print` / `NPrint` | `bm.print_at(x, y, text)` | |

### Not Supported (by design)
| Blitz | Reason |
|---|---|
| Inline 68k assembly | Use C escape hatch for advanced users |
| `Gosub` / `Goto` | Use functions instead |
| `Macro` / `!macro` | Use functions instead |
| `SetInt` / `ClrInt` | Interrupts handled by engine internally |
| `Screen` / `Window` (Intuition) | Games use blitz-mode display only |
| Serial/ARexx | Out of scope for game engine |
