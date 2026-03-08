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
}

ALL_ENGINE_NAMES = set(OBJECT_TYPES) | set(MODULE_TYPES) | set(BUILTINS) | {"run", "sin_table", "cos_table"}
