"""amifish — fishing game using hardware sprites.

Walk left/right at the top of the screen with joy.left/right. Press fire to
drop a hook straight down — it descends until something touches it. Fish
score; electric eels cost a life. 3 lives → game over.

Scenes: TITLE → PLAY → GAMEOVER → TITLE.
Top-5 scoreboard is in-memory only — no persistence (resets on quit).

Engine surface exercised:
    - Hardware sprites: 8 channels (boat, hook, 6 fish/eel slots).
    - Sprite.overlaps(other) for hook-vs-fish AABB catch detection.
    - rnd(lo, hi) for fish spawn depth + speed.
    - Bitmap.load + Sprite.grab pipeline for sprite-sheet assets.
"""

from dataclasses import dataclass
from amiga import Display, Bitmap, Shape, Sprite, palette, copper, Color, run, rnd
from amiga import joy, key, int_to_str
from amiga import K_ESC

# --- Geometry ---
WATERLINE_Y: int = 40
BOAT_Y: int = 28          # boat sprite top — hull straddles the waterline
HOOK_REST_Y: int = -32    # hidden off-screen when not cast
HOOK_X_OFFSET: int = 5    # hook x relative to boat x (rod-tip alignment)
PLAYER_X_MIN: int = 4
PLAYER_X_MAX: int = 300
SEABED_Y: int = 175
LINE_X_OFFSET: int = 8    # line column inside the hook sprite
ROD_TIP_X: int = 13       # rod-tip column inside the boat sprite
ROD_TIP_Y_LOCAL: int = 3  # rod-tip row inside the boat sprite

HOOK_DROP_SPEED: int = 1
HOOK_RETRACT_SPEED: int = 3
PLAYER_WALK_SPEED: int = 2

LIVES_START: int = 3
FLASH_FRAMES: int = 24
SPAWN_INTERVAL: int = 28

# --- Sprite cells (16x128 sheet, 8 cells of 16x16) ---
CELL_BOAT: int = 0
CELL_HOOK: int = 1
CELL_FISH_S: int = 2
CELL_FISH_M: int = 3
CELL_FISH_L: int = 4
CELL_FISH_R: int = 5
CELL_EEL: int = 6

# --- Fish kinds (also used as score-table indices) ---
KIND_SMALL: int = 0
KIND_MEDIUM: int = 1
KIND_LARGE: int = 2
KIND_RARE: int = 3
KIND_EEL: int = 4

# --- Hook state machine ---
HOOK_REST: int = 0
HOOK_DROPPING: int = 1
HOOK_RETRACTING: int = 2

# --- Scenes ---
SCENE_TITLE: int = 0
SCENE_PLAY: int = 1
SCENE_GAMEOVER: int = 2

# --- Slot count and per-slot kind layout ---
# 6 fish slots map 1:1 onto hardware-sprite channels 2..7.
# Two small-fish slots so the screen feels populated; the rest are unique.
FISH_SLOTS: int = 6


# --- Display setup ---
display = Display(320, 200, bitplanes=4)
screen = Bitmap(320, 200, bitplanes=4)

display.show(screen)

# --- Asset loading order matters here ---
#
# 1. Bitmap.load applies the PNG palette to playfield regs 0..15. The sprite
#    sheet's PNG palette is laid out so its lower-2-bits-per-channel-pair
#    encoding is correct for hardware sprites (see generate_assets.py).
# 2. Sprite.grab takes a snapshot of the sprite source — on Amiga it copies
#    the lower 2 bitplanes into a 2BPP interleaved sprite bitmap; on pygame
#    it copies the subsurface with its current palette.
# 3. We then overwrite the playfield palette with the screen colours we want
#    (sky/sea/wave/UI). The grabbed sprite surfaces keep their own copy of
#    the original sprite palette in pygame; the Amiga path uses sprite
#    palette regs 17..31 set explicitly below.
sprites_bm = Bitmap.load("data/sprites.png")

boat_spr = Sprite.grab(sprites_bm, 0, CELL_BOAT * 16, 16, 16)
hook_spr = Sprite.grab(sprites_bm, 0, CELL_HOOK * 16, 16, 16)

# Per-slot sprites — each slot has a fixed kind so we don't need to swap
# sprite bitmaps mid-game. Slot index = channel - 2.
slot0_spr = Sprite.grab(sprites_bm, 0, CELL_FISH_S * 16, 16, 16)
slot1_spr = Sprite.grab(sprites_bm, 0, CELL_FISH_S * 16, 16, 16)
slot2_spr = Sprite.grab(sprites_bm, 0, CELL_FISH_M * 16, 16, 16)
slot3_spr = Sprite.grab(sprites_bm, 0, CELL_FISH_L * 16, 16, 16)
slot4_spr = Sprite.grab(sprites_bm, 0, CELL_FISH_R * 16, 16, 16)
slot5_spr = Sprite.grab(sprites_bm, 0, CELL_EEL   * 16, 16, 16)

# --- Screen playfield palette (regs 0..15) — overrides what Bitmap.load wrote ---
palette.set(0,  0,  0,  0)     # transparent / sky-deep
palette.set(1,  1,  2,  6)     # deep night blue (sky)
palette.set(2,  3,  6,  12)    # mid sea blue
palette.set(3,  8,  12, 14)    # light blue / wave highlight
palette.set(4,  15, 14, 4)     # yellow (logo, HUD highlights)
palette.set(5,  8,  4,  1)     # brown (logo shadow)
palette.set(6,  15, 11, 7)     # tan
palette.set(7,  15, 3,  2)     # red (life-flash)
palette.set(8,  15, 15, 15)    # white (HUD text)
palette.set(9,  15, 9,  2)     # orange
palette.set(10, 12, 6,  1)
palette.set(11, 4,  12, 4)
palette.set(12, 1,  6,  1)
palette.set(13, 15, 6,  12)
palette.set(14, 8,  2,  14)
palette.set(15, 15, 15, 4)

# --- Hardware-sprite palette (regs 17..31) ---
# Channels 0/1 (boat + hook): yellow / brown / white
palette.set(17, 15, 14, 4)     # yellow — boat hull
palette.set(18, 8,  4,  1)     # brown  — boat trim, mast, rod
palette.set(19, 15, 15, 15)    # white  — angler, hook line
# Channels 2/3 (small fish a + b): orange / dark orange / off-white
palette.set(21, 15, 9,  2)
palette.set(22, 12, 6,  1)
palette.set(23, 14, 14, 14)
# Channels 4/5 (medium + large fish): green / dark green / pale green
palette.set(25, 4,  12, 4)
palette.set(26, 1,  6,  1)
palette.set(27, 13, 14, 13)
# Channels 6/7 (rare + eel): violet / bright yellow / pale pink
palette.set(29, 10, 3,  14)
palette.set(30, 15, 14, 4)
palette.set(31, 15, 13, 13)

logo = Shape.load("data/logo.png")

# --- Copper sky → sea gradient ---
# We fill the playfield with colour 1 every frame and let the copper rewrite
# what colour 1 *means* per scanline. Pure init-time setup; no per-frame cost.
# The bands are coarse (every 4 scanlines above the waterline, every 8 below)
# so the table stays well under the 320-entry buffer in the C runtime.
for y in range(0, WATERLINE_Y, 4):
    # Sky: deep blue at the top brightening toward the waterline.
    sky_t: int = (y * 6) // WATERLINE_Y
    copper.color_at(scanline=y, register=1,
                    color=Color(0, 1 + sky_t, 5 + sky_t))
# Snap to a bright water-surface highlight at the waterline itself.
copper.color_at(scanline=WATERLINE_Y, register=1, color=Color(7, 12, 14))
for y in range(WATERLINE_Y + 4, 200, 6):
    # Sea: cyan-blue at the surface fading toward near-black at the seabed.
    depth: int = y - WATERLINE_Y
    span: int = 200 - WATERLINE_Y
    fade: int = (depth * 12) // span
    sea_g: int = 8 - fade
    if sea_g < 1:
        sea_g = 1
    sea_b: int = 14 - fade
    if sea_b < 3:
        sea_b = 3
    copper.color_at(scanline=y, register=1,
                    color=Color(0, sea_g, sea_b))


# --- Fish state ---
@dataclass
class Fish:
    x: int
    y: int
    vx: int
    alive: bool


fishes: list[Fish] = []
for i in range(FISH_SLOTS):
    fishes.append(Fish(x=-32, y=120, vx=0, alive=False))


# --- Game state ---
scene: int = SCENE_TITLE
last_scene: int = -1
quit_flag: bool = False

player_x: int = 152
hook_x: int = 0
hook_y: int = HOOK_REST_Y
hook_state: int = HOOK_REST
caught_slot: int = -1

score: int = 0
lives: int = LIVES_START
flash_timer: int = 0
spawn_timer: int = 0

prev_score: int = -1
prev_lives: int = -1
need_line_erase: bool = False
prev_line_x: int = 0
prev_line_y_bottom: int = 0

# --- In-memory top-5 scoreboard (no storage) ---
top_scores: list[int] = []
for i in range(5):
    top_scores.append(0)

gameover_committed: bool = False


# ================================================================
# Helpers
# ================================================================

def slot_kind(slot: int) -> int:
    """Each slot has a fixed fish kind so its sprite never changes."""
    if slot == 0:
        return KIND_SMALL
    if slot == 1:
        return KIND_SMALL
    if slot == 2:
        return KIND_MEDIUM
    if slot == 3:
        return KIND_LARGE
    if slot == 4:
        return KIND_RARE
    return KIND_EEL


def score_for_kind(kind: int) -> int:
    if kind == KIND_SMALL:
        return 10
    if kind == KIND_MEDIUM:
        return 25
    if kind == KIND_LARGE:
        return 50
    if kind == KIND_RARE:
        return 100
    return 0   # eels never score


def show_slot(slot: int, x: int, y: int):
    """Position one slot's sprite on its hardware channel."""
    ch: int = slot + 2
    if slot == 0:
        slot0_spr.show(x, y, channel=ch)
    elif slot == 1:
        slot1_spr.show(x, y, channel=ch)
    elif slot == 2:
        slot2_spr.show(x, y, channel=ch)
    elif slot == 3:
        slot3_spr.show(x, y, channel=ch)
    elif slot == 4:
        slot4_spr.show(x, y, channel=ch)
    else:
        slot5_spr.show(x, y, channel=ch)


def slot_overlaps_hook(slot: int) -> bool:
    if slot == 0:
        return hook_spr.overlaps(slot0_spr)
    if slot == 1:
        return hook_spr.overlaps(slot1_spr)
    if slot == 2:
        return hook_spr.overlaps(slot2_spr)
    if slot == 3:
        return hook_spr.overlaps(slot3_spr)
    if slot == 4:
        return hook_spr.overlaps(slot4_spr)
    return hook_spr.overlaps(slot5_spr)


def spawn_fish_in_first_dead_slot():
    spawned: bool = False
    for f in fishes:
        if not spawned and not f.alive:
            # Swim left-to-right or right-to-left, randomised speed.
            if rnd(2) == 0:
                f.x = -16
                f.vx = rnd(1, 4)
            else:
                f.x = 320
                f.vx = -rnd(1, 4)
            f.y = rnd(WATERLINE_Y + 16, SEABED_Y - 8)
            f.alive = True
            spawned = True


def reset_play_state():
    global score, lives, hook_state, hook_y, player_x, flash_timer
    global spawn_timer, prev_score, prev_lives, gameover_committed
    global need_line_erase, caught_slot
    score = 0
    lives = LIVES_START
    hook_state = HOOK_REST
    hook_y = HOOK_REST_Y
    player_x = 152
    flash_timer = 0
    spawn_timer = 0
    prev_score = -1
    prev_lives = -1
    gameover_committed = False
    need_line_erase = False
    caught_slot = -1
    for f in fishes:
        f.alive = False
        f.x = -32
    # Park every slot's sprite off-screen so previous-game ghosts don't
    # render before the first show() call hits.
    for i in range(FISH_SLOTS):
        show_slot(i, -32, -32)


def commit_high_score(final_score: int):
    inserted: bool = False
    for i in range(5):
        if not inserted and final_score > top_scores[i]:
            j: int = 4
            while j > i:
                top_scores[j] = top_scores[j - 1]
                j = j - 1
            top_scores[i] = final_score
            inserted = True


def draw_backdrop():
    """Fill the whole screen with colour 1 — the copper rewrites that
    register per scanline so we get the sky→sea gradient for free, with
    one box_filled instead of three boxes/lines."""
    screen.box_filled(0, 0, 319, 199, 1)
    # Waterline ripple highlight in white (colour 8) — copper doesn't touch
    # register 8 so this stays the same colour at the waterline.
    screen.line(0, WATERLINE_Y, 319, WATERLINE_Y, 8)


def draw_seabed():
    screen.line(0, SEABED_Y + 8, 319, SEABED_Y + 8, 5)


# ================================================================
# Scene: TITLE
# ================================================================

def enter_title():
    draw_backdrop()
    draw_seabed()
    # Logo near the top, centred-ish (width = 60 px = 7 letters * 8 + 4)
    display.blit(logo, 130, 12)
    screen.print_centered(60, "HIGH SCORES", color=8)
    for i in range(5):
        screen.print_at(96, 76 + i * 10, int_to_str(i + 1, 1), ".", color=3)
        screen.print_right(224, 76 + i * 10,
                           int_to_str(top_scores[i], 6), color=8)
    screen.print_centered(150, "PRESS FIRE TO START", color=8)
    screen.print_centered(170, "ESC TO QUIT", color=3)
    # Hide all gameplay sprites off-screen.
    boat_spr.show(-32, -32, channel=0)
    hook_spr.show(-32, -32, channel=1)
    for i in range(FISH_SLOTS):
        show_slot(i, -32, -32)


def update_title():
    global scene, quit_flag
    if joy.button_pressed(0):
        scene = SCENE_PLAY
    if key.just_pressed(K_ESC):
        quit_flag = True


# ================================================================
# Scene: PLAY
# ================================================================

def enter_play():
    reset_play_state()
    draw_backdrop()
    draw_seabed()


def update_play():
    global player_x, hook_x, hook_y, hook_state, caught_slot
    global score, lives, scene, flash_timer, spawn_timer
    global prev_score, prev_lives
    global need_line_erase, prev_line_x, prev_line_y_bottom

    # --- Spawning ---
    spawn_timer = spawn_timer + 1
    if spawn_timer >= SPAWN_INTERVAL:
        spawn_timer = 0
        spawn_fish_in_first_dead_slot()

    # --- Player movement (only when hook is at rest) ---
    if hook_state == HOOK_REST:
        if joy.left():
            player_x = player_x - PLAYER_WALK_SPEED
            if player_x < PLAYER_X_MIN:
                player_x = PLAYER_X_MIN
        if joy.right():
            player_x = player_x + PLAYER_WALK_SPEED
            if player_x > PLAYER_X_MAX:
                player_x = PLAYER_X_MAX
        if joy.button_pressed(0):
            # Cast — lock hook column to current rod-tip x
            hook_x = player_x + HOOK_X_OFFSET
            hook_y = WATERLINE_Y - 8
            hook_state = HOOK_DROPPING

    # --- Hook state machine ---
    if hook_state == HOOK_DROPPING:
        hook_y = hook_y + HOOK_DROP_SPEED
        if hook_y >= SEABED_Y:
            hook_y = SEABED_Y
            hook_state = HOOK_RETRACTING
            caught_slot = -1
    elif hook_state == HOOK_RETRACTING:
        hook_y = hook_y - HOOK_RETRACT_SPEED
        if hook_y <= WATERLINE_Y - 8:
            # Apply the catch (or non-catch) effects
            if caught_slot >= 0:
                kind: int = slot_kind(caught_slot)
                if kind == KIND_EEL:
                    lives = lives - 1
                    flash_timer = FLASH_FRAMES
                    if lives <= 0:
                        scene = SCENE_GAMEOVER
                else:
                    score = score + score_for_kind(kind)
                caught_slot = -1
            hook_state = HOOK_REST
            hook_y = HOOK_REST_Y

    # --- Update fish positions (reference iter so mutations persist) ---
    for f in fishes:
        if f.alive:
            f.x = f.x + f.vx
            if f.vx > 0 and f.x > 320:
                f.alive = False
            if f.vx < 0 and f.x < -16:
                f.alive = False

    # --- Show all sprites this frame ---
    boat_spr.show(player_x, BOAT_Y, channel=0)
    if hook_state == HOOK_REST:
        hook_spr.show(-32, -32, channel=1)
    else:
        hook_spr.show(hook_x, hook_y, channel=1)

    show_idx: int = 0
    for f2 in fishes:
        if f2.alive:
            show_slot(show_idx, f2.x, f2.y)
        else:
            show_slot(show_idx, -32, -32)
        show_idx = show_idx + 1

    # --- Hook-vs-fish overlap (only while dropping) ---
    if hook_state == HOOK_DROPPING:
        check_idx: int = 0
        for f3 in fishes:
            if f3.alive and caught_slot < 0 and slot_overlaps_hook(check_idx):
                caught_slot = check_idx
                f3.alive = False
                hook_state = HOOK_RETRACTING
            check_idx = check_idx + 1

    # --- Erase old fishing line, draw new ---
    if need_line_erase:
        # Erase by drawing in colour 1 — same register the copper varies
        # for the sky/sea gradient, so the erase tracks the gradient.
        screen.line(prev_line_x, WATERLINE_Y + 1,
                    prev_line_x, prev_line_y_bottom, 1)
        need_line_erase = False
    if hook_state != HOOK_REST:
        line_x: int = hook_x + LINE_X_OFFSET
        line_bottom: int = hook_y + 10
        screen.line(line_x, WATERLINE_Y + 1, line_x, line_bottom, 8)
        prev_line_x = line_x
        prev_line_y_bottom = line_bottom
        need_line_erase = True

    # --- Lose-a-life palette flash on register 7 (player shirt + eel zap) ---
    if flash_timer > 0:
        flash_timer = flash_timer - 1
        if (flash_timer // 4) % 2 == 0:
            palette.set(7, 15, 15, 4)   # bright yellow
        else:
            palette.set(7, 15, 3, 2)    # red back
        if flash_timer == 0:
            palette.set(7, 15, 3, 2)

    # --- HUD (only repaint when values change) ---
    if score != prev_score:
        screen.clear_rect(220, 4, 96, 8)
        screen.print_right(316, 4, "SCORE", int_to_str(score, 6), color=8)
        prev_score = score
    if lives != prev_lives:
        screen.clear_rect(4, 4, 80, 8)
        screen.print_at(4, 4, "LIVES", int_to_str(lives, 1), color=8)
        prev_lives = lives

    if key.just_pressed(K_ESC):
        scene = SCENE_GAMEOVER


# ================================================================
# Scene: GAMEOVER
# ================================================================

def enter_gameover():
    global gameover_committed
    if not gameover_committed:
        commit_high_score(score)
        gameover_committed = True
    draw_backdrop()
    screen.print_centered(56, "GAME OVER", color=7)
    screen.print_centered(80, "FINAL", int_to_str(score, 6), color=8)
    screen.print_centered(140, "PRESS FIRE TO RETRY", color=8)
    # Park sprites
    boat_spr.show(-32, -32, channel=0)
    hook_spr.show(-32, -32, channel=1)
    for i in range(FISH_SLOTS):
        show_slot(i, -32, -32)


def update_gameover():
    global scene
    if joy.button_pressed(0):
        scene = SCENE_TITLE


# ================================================================
# Main loop
# ================================================================

def update():
    global last_scene
    if scene != last_scene:
        last_scene = scene
        if scene == SCENE_TITLE:
            enter_title()
        elif scene == SCENE_PLAY:
            enter_play()
        else:
            enter_gameover()

    if scene == SCENE_TITLE:
        update_title()
    elif scene == SCENE_PLAY:
        update_play()
    else:
        update_gameover()


run(update, until=lambda: quit_flag)
