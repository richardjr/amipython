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


@dataclass
class EngineConstructor:
    positional: list[EngineParam]
    keywords: dict[str, tuple[AmipyType, object]]  # name -> (type, default)


@dataclass
class EngineObjectType:
    python_name: str
    c_type: str
    c_init: str
    constructor: EngineConstructor
    methods: dict[str, EngineMethod]


@dataclass
class EngineModuleType:
    python_name: str
    functions: dict[str, EngineMethod]


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
        params=[],
        return_type=AmipyType.VOID,
    ),
}

ALL_ENGINE_NAMES = set(OBJECT_TYPES) | set(MODULE_TYPES) | set(BUILTINS)
