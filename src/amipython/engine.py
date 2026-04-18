"""Engine type registry for amipython — defines known Amiga engine objects, modules, and builtins."""

from dataclasses import dataclass, field
from amipython.types import AmipyType


@dataclass
class EngineParam:
    name: str
    type: AmipyType


@dataclass
class EngineMethod:
    name: str
    c_name: str
    params: list[EngineParam]
    return_type: AmipyType
    keywords: dict[str, tuple[AmipyType, object]] = field(default_factory=dict)


@dataclass
class EngineConstructor:
    positional: list[EngineParam]
    keywords: dict[str, tuple[AmipyType, object]]  # name -> (type, default)


@dataclass
class EngineObjectType:
    python_name: str
    c_type: str
    c_init: str
    constructor: EngineConstructor | None
    methods: dict[str, EngineMethod]
    static_methods: dict[str, EngineStaticMethod] = field(default_factory=dict)


@dataclass
class EngineModuleType:
    python_name: str
    functions: dict[str, EngineMethod]
    properties: dict[str, EngineProperty] = field(default_factory=dict)


@dataclass
class EngineStaticMethod:
    name: str
    c_name: str
    params: list[EngineParam]
    return_type: AmipyType
    keywords: dict[str, tuple[AmipyType, object]] = field(default_factory=dict)


@dataclass
class EngineProperty:
    name: str
    type: AmipyType
    c_getter: str


@dataclass
class EngineBuiltin:
    python_name: str
    c_name: str
    params: list[EngineParam]
    return_type: AmipyType


# --- Registry ---

OBJECT_TYPES: dict[str, EngineObjectType] = {
    "Display": EngineObjectType(
        python_name="Display",
        c_type="AmipyDisplay",
        c_init="amipython_display_init",
        constructor=EngineConstructor(
            positional=[
                EngineParam("width", AmipyType.INT),
                EngineParam("height", AmipyType.INT),
            ],
            keywords={"bitplanes": (AmipyType.INT, 5)},
        ),
        methods={
            "show": EngineMethod(
                name="show",
                c_name="amipython_display_show",
                params=[EngineParam("bm", AmipyType.BITMAP)],
                return_type=AmipyType.VOID,
            ),
            "blit": EngineMethod(
                name="blit",
                c_name="amipython_display_blit",
                params=[
                    EngineParam("shape", AmipyType.SHAPE),
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "sprites_behind": EngineMethod(
                name="sprites_behind",
                c_name="amipython_display_sprites_behind",
                params=[],
                return_type=AmipyType.VOID,
                keywords={"from_channel": (AmipyType.INT, 4)},
            ),
        },
    ),
    "Bitmap": EngineObjectType(
        python_name="Bitmap",
        c_type="AmipyBitmap",
        c_init="amipython_bitmap_init",
        constructor=EngineConstructor(
            positional=[
                EngineParam("width", AmipyType.INT),
                EngineParam("height", AmipyType.INT),
            ],
            keywords={"bitplanes": (AmipyType.INT, 5)},
        ),
        methods={
            "circle_filled": EngineMethod(
                name="circle_filled",
                c_name="amipython_bitmap_circle_filled",
                params=[
                    EngineParam("cx", AmipyType.INT),
                    EngineParam("cy", AmipyType.INT),
                    EngineParam("r", AmipyType.INT),
                    EngineParam("color", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "box_filled": EngineMethod(
                name="box_filled",
                c_name="amipython_bitmap_box_filled",
                params=[
                    EngineParam("x1", AmipyType.INT),
                    EngineParam("y1", AmipyType.INT),
                    EngineParam("x2", AmipyType.INT),
                    EngineParam("y2", AmipyType.INT),
                    EngineParam("color", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "clear": EngineMethod(
                name="clear",
                c_name="amipython_bitmap_clear",
                params=[],
                return_type=AmipyType.VOID,
            ),
            "plot": EngineMethod(
                name="plot",
                c_name="amipython_bitmap_plot",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                    EngineParam("color", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "line": EngineMethod(
                name="line",
                c_name="amipython_bitmap_line",
                params=[
                    EngineParam("x1", AmipyType.INT),
                    EngineParam("y1", AmipyType.INT),
                    EngineParam("x2", AmipyType.INT),
                    EngineParam("y2", AmipyType.INT),
                    EngineParam("color", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "print_at": EngineMethod(
                name="print_at",
                c_name="amipython_bitmap_print_at",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                    EngineParam("text", AmipyType.STR),
                ],
                return_type=AmipyType.VOID,
                keywords={"color": (AmipyType.INT, 1)},
            ),
        },
        static_methods={
            "load": EngineStaticMethod(
                name="load",
                c_name="amipython_bitmap_load",
                params=[EngineParam("path", AmipyType.STR)],
                return_type=AmipyType.BITMAP,
            ),
        },
    ),
    "Shape": EngineObjectType(
        python_name="Shape",
        c_type="AmipyShape",
        c_init=None,  # No direct constructor — use Shape.grab()
        constructor=None,
        methods={},
        static_methods={
            "grab": EngineStaticMethod(
                name="grab",
                c_name="amipython_shape_grab",
                params=[
                    EngineParam("bm", AmipyType.BITMAP),
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                    EngineParam("w", AmipyType.INT),
                    EngineParam("h", AmipyType.INT),
                ],
                return_type=AmipyType.SHAPE,
            ),
            "load": EngineStaticMethod(
                name="load",
                c_name="amipython_shape_load",
                params=[EngineParam("path", AmipyType.STR)],
                return_type=AmipyType.SHAPE,
            ),
        },
    ),
    "Sprite": EngineObjectType(
        python_name="Sprite",
        c_type="AmipySprite",
        c_init=None,  # No direct constructor — use Sprite.grab()
        constructor=None,
        methods={
            "show": EngineMethod(
                name="show",
                c_name="amipython_sprite_show",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
                keywords={"channel": (AmipyType.INT, 0)},
            ),
            "collided": EngineMethod(
                name="collided",
                c_name="amipython_sprite_collided",
                params=[],
                return_type=AmipyType.BOOL,
            ),
        },
        static_methods={
            "grab": EngineStaticMethod(
                name="grab",
                c_name="amipython_sprite_grab",
                params=[
                    EngineParam("bm", AmipyType.BITMAP),
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                    EngineParam("w", AmipyType.INT),
                    EngineParam("h", AmipyType.INT),
                ],
                return_type=AmipyType.SPRITE,
            ),
        },
    ),
    "Tilemap": EngineObjectType(
        python_name="Tilemap",
        c_type="AmipyTilemap",
        c_init="amipython_tilemap_init",
        constructor=EngineConstructor(
            positional=[
                EngineParam("tileset_path", AmipyType.STR),
                EngineParam("width", AmipyType.INT),
                EngineParam("height", AmipyType.INT),
            ],
            keywords={
                "bitplanes": (AmipyType.INT, 3),
                "tile_size": (AmipyType.INT, 16),
                "map_w": (AmipyType.INT, 20),
                "map_h": (AmipyType.INT, 20),
            },
        ),
        methods={
            "show": EngineMethod(
                name="show",
                c_name="amipython_tilemap_show",
                params=[],
                return_type=AmipyType.VOID,
            ),
            "camera": EngineMethod(
                name="camera",
                c_name="amipython_tilemap_camera",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "scroll": EngineMethod(
                name="scroll",
                c_name="amipython_tilemap_scroll",
                params=[
                    EngineParam("dx", AmipyType.INT),
                    EngineParam("dy", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "set_tile": EngineMethod(
                name="set_tile",
                c_name="amipython_tilemap_set_tile",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                    EngineParam("tile", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "get_tile": EngineMethod(
                name="get_tile",
                c_name="amipython_tilemap_get_tile",
                params=[
                    EngineParam("x", AmipyType.INT),
                    EngineParam("y", AmipyType.INT),
                ],
                return_type=AmipyType.INT,
            ),
            "is_blocking": EngineMethod(
                name="is_blocking",
                c_name="amipython_tilemap_is_blocking",
                params=[
                    EngineParam("pixel_x", AmipyType.INT),
                    EngineParam("pixel_y", AmipyType.INT),
                ],
                return_type=AmipyType.BOOL,
            ),
            "draw_shape": EngineMethod(
                name="draw_shape",
                c_name="amipython_tilemap_draw_shape",
                params=[
                    EngineParam("shape", AmipyType.SHAPE),
                    EngineParam("world_x", AmipyType.INT),
                    EngineParam("world_y", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
        },
        static_methods={
            "load_tiled": EngineStaticMethod(
                name="load_tiled",
                c_name="amipython_tilemap_init",
                params=[
                    EngineParam("json_path", AmipyType.STR),
                    EngineParam("width", AmipyType.INT),
                    EngineParam("height", AmipyType.INT),
                ],
                return_type=AmipyType.TILEMAP,
                keywords={
                    "bitplanes": (AmipyType.INT, 3),
                },
            ),
        },
    ),
}

MODULE_TYPES: dict[str, EngineModuleType] = {
    "palette": EngineModuleType(
        python_name="palette",
        functions={
            "aga": EngineMethod(
                name="aga",
                c_name="amipython_palette_aga",
                params=[
                    EngineParam("reg", AmipyType.INT),
                    EngineParam("r", AmipyType.INT),
                    EngineParam("g", AmipyType.INT),
                    EngineParam("b", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "set": EngineMethod(
                name="set",
                c_name="amipython_palette_set",
                params=[
                    EngineParam("reg", AmipyType.INT),
                    EngineParam("r", AmipyType.INT),
                    EngineParam("g", AmipyType.INT),
                    EngineParam("b", AmipyType.INT),
                ],
                return_type=AmipyType.VOID,
            ),
            "fade": EngineMethod(
                name="fade",
                c_name="amipython_palette_fade",
                params=[EngineParam("level", AmipyType.INT)],
                return_type=AmipyType.VOID,
            ),
        },
    ),
    "mouse": EngineModuleType(
        python_name="mouse",
        functions={
            "set_pointer": EngineMethod(
                name="set_pointer",
                c_name="amipython_mouse_set_pointer",
                params=[EngineParam("sprite", AmipyType.SPRITE)],
                return_type=AmipyType.VOID,
            ),
        },
        properties={
            "x": EngineProperty(
                name="x",
                type=AmipyType.INT,
                c_getter="amipython_mouse_x",
            ),
            "y": EngineProperty(
                name="y",
                type=AmipyType.INT,
                c_getter="amipython_mouse_y",
            ),
        },
    ),
    "joy": EngineModuleType(
        python_name="joy",
        functions={
            "button": EngineMethod(
                name="button",
                c_name="amipython_joy_button",
                params=[EngineParam("port", AmipyType.INT)],
                return_type=AmipyType.BOOL,
            ),
            "button_pressed": EngineMethod(
                name="button_pressed",
                c_name="amipython_joy_button_pressed",
                params=[EngineParam("port", AmipyType.INT)],
                return_type=AmipyType.BOOL,
            ),
            "left": EngineMethod(
                name="left",
                c_name="amipython_joy_left",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "left_pressed": EngineMethod(
                name="left_pressed",
                c_name="amipython_joy_left_pressed",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "right": EngineMethod(
                name="right",
                c_name="amipython_joy_right",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "right_pressed": EngineMethod(
                name="right_pressed",
                c_name="amipython_joy_right_pressed",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "up": EngineMethod(
                name="up",
                c_name="amipython_joy_up",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "up_pressed": EngineMethod(
                name="up_pressed",
                c_name="amipython_joy_up_pressed",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "down": EngineMethod(
                name="down",
                c_name="amipython_joy_down",
                params=[],
                return_type=AmipyType.BOOL,
            ),
            "down_pressed": EngineMethod(
                name="down_pressed",
                c_name="amipython_joy_down_pressed",
                params=[],
                return_type=AmipyType.BOOL,
            ),
        },
    ),
    "music": EngineModuleType(
        python_name="music",
        functions={
            "load": EngineMethod(
                name="load",
                c_name="amipython_music_load",
                params=[EngineParam("path", AmipyType.STR)],
                return_type=AmipyType.VOID,
            ),
            "play": EngineMethod(
                name="play",
                c_name="amipython_music_play",
                params=[],
                return_type=AmipyType.VOID,
            ),
            "stop": EngineMethod(
                name="stop",
                c_name="amipython_music_stop",
                params=[],
                return_type=AmipyType.VOID,
            ),
            "volume": EngineMethod(
                name="volume",
                c_name="amipython_music_volume",
                params=[EngineParam("vol", AmipyType.INT)],
                return_type=AmipyType.VOID,
            ),
        },
    ),
    "key": EngineModuleType(
        python_name="key",
        functions={
            "pressed": EngineMethod(
                name="pressed",
                c_name="amipython_key_pressed",
                params=[EngineParam("code", AmipyType.INT)],
                return_type=AmipyType.BOOL,
            ),
            "just_pressed": EngineMethod(
                name="just_pressed",
                c_name="amipython_key_just_pressed",
                params=[EngineParam("code", AmipyType.INT)],
                return_type=AmipyType.BOOL,
            ),
            "just_released": EngineMethod(
                name="just_released",
                c_name="amipython_key_just_released",
                params=[EngineParam("code", AmipyType.INT)],
                return_type=AmipyType.BOOL,
            ),
        },
    ),
    "sfx": EngineModuleType(
        python_name="sfx",
        functions={
            "load": EngineMethod(
                name="load",
                c_name="amipython_sfx_load",
                params=[
                    EngineParam("slot", AmipyType.INT),
                    EngineParam("path", AmipyType.STR),
                ],
                return_type=AmipyType.VOID,
            ),
            "play": EngineMethod(
                name="play",
                c_name="amipython_sfx_play",
                params=[EngineParam("slot", AmipyType.INT)],
                return_type=AmipyType.VOID,
                keywords={
                    "channel": (AmipyType.INT, 2),
                    "volume": (AmipyType.INT, 64),
                },
            ),
            "stop": EngineMethod(
                name="stop",
                c_name="amipython_sfx_stop",
                params=[EngineParam("slot", AmipyType.INT)],
                return_type=AmipyType.VOID,
            ),
        },
    ),
    "storage": EngineModuleType(
        python_name="storage",
        functions={
            "save_int_list": EngineMethod(
                name="save_int_list",
                c_name="amipython_storage_save_int_list",
                params=[
                    EngineParam("name", AmipyType.STR),
                    EngineParam("items", AmipyType.LIST),
                ],
                return_type=AmipyType.VOID,
            ),
            "load_int_list": EngineMethod(
                name="load_int_list",
                c_name="amipython_storage_load_int_list",
                params=[
                    EngineParam("name", AmipyType.STR),
                    EngineParam("items", AmipyType.LIST),
                ],
                return_type=AmipyType.BOOL,
            ),
            "save_str": EngineMethod(
                name="save_str",
                c_name="amipython_storage_save_str",
                params=[
                    EngineParam("name", AmipyType.STR),
                    EngineParam("value", AmipyType.STR),
                ],
                return_type=AmipyType.VOID,
            ),
            "load_str": EngineMethod(
                name="load_str",
                c_name="amipython_storage_load_str",
                params=[EngineParam("name", AmipyType.STR)],
                return_type=AmipyType.STR,
            ),
            "exists": EngineMethod(
                name="exists",
                c_name="amipython_storage_exists",
                params=[EngineParam("name", AmipyType.STR)],
                return_type=AmipyType.BOOL,
            ),
        },
    ),
    "collision": EngineModuleType(
        python_name="collision",
        functions={
            "register": EngineMethod(
                name="register",
                c_name="amipython_collision_register",
                params=[],
                return_type=AmipyType.VOID,
                keywords={
                    "color": (AmipyType.INT, None),
                    "mask": (AmipyType.INT, None),
                },
            ),
            "check": EngineMethod(
                name="check",
                c_name="amipython_collision_check",
                params=[],
                return_type=AmipyType.VOID,
            ),
        },
    ),
}

# Keyboard key-name constants — Amiga raw-key codes. Names that user code
# imports from `amiga`, like `K_LEFT`, `K_SPACE`. Values are ACE KEY_* codes.
KEY_CONSTANTS: dict[str, int] = {
    # Letters
    "K_A": 0x20, "K_B": 0x35, "K_C": 0x33, "K_D": 0x22, "K_E": 0x12,
    "K_F": 0x23, "K_G": 0x24, "K_H": 0x25, "K_I": 0x17, "K_J": 0x26,
    "K_K": 0x27, "K_L": 0x28, "K_M": 0x37, "K_N": 0x36, "K_O": 0x18,
    "K_P": 0x19, "K_Q": 0x10, "K_R": 0x13, "K_S": 0x21, "K_T": 0x14,
    "K_U": 0x16, "K_V": 0x34, "K_W": 0x11, "K_X": 0x32, "K_Y": 0x15,
    "K_Z": 0x31,
    # Digits (row 1..9,0)
    "K_1": 0x01, "K_2": 0x02, "K_3": 0x03, "K_4": 0x04, "K_5": 0x05,
    "K_6": 0x06, "K_7": 0x07, "K_8": 0x08, "K_9": 0x09, "K_0": 0x0A,
    # Navigation / special
    "K_LEFT": 0x4F, "K_RIGHT": 0x4E, "K_UP": 0x4C, "K_DOWN": 0x4D,
    "K_SPACE": 0x40, "K_RETURN": 0x44, "K_ESC": 0x45,
}


BUILTINS: dict[str, EngineBuiltin] = {
    "wait_mouse": EngineBuiltin(
        python_name="wait_mouse",
        c_name="amipython_wait_mouse",
        params=[],
        return_type=AmipyType.VOID,
    ),
    "vwait": EngineBuiltin(
        python_name="vwait",
        c_name="amipython_vwait",
        params=[EngineParam("n", AmipyType.INT)],
        return_type=AmipyType.VOID,
    ),
    "rnd": EngineBuiltin(
        python_name="rnd",
        c_name="amipython_rnd",
        params=[EngineParam("n", AmipyType.INT)],
        return_type=AmipyType.INT,
    ),
    "int_to_str": EngineBuiltin(
        python_name="int_to_str",
        c_name="amipython_int_to_str",
        params=[
            EngineParam("n", AmipyType.INT),
            EngineParam("width", AmipyType.INT),
        ],
        return_type=AmipyType.STR,
    ),
}

ALL_ENGINE_NAMES = (set(OBJECT_TYPES) | set(MODULE_TYPES) | set(BUILTINS)
                    | set(KEY_CONSTANTS)
                    | {"run", "sin_table", "cos_table"})
