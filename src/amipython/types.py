"""Type system for the amipython transpiler."""

from dataclasses import dataclass, field
from enum import Enum, auto


class AmipyType(Enum):
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    STR = auto()
    VOID = auto()
    DISPLAY = auto()
    BITMAP = auto()
    SHAPE = auto()
    SPRITE = auto()
    TILEMAP = auto()
    MODULE = auto()  # engine module (palette, copper, etc.)
    STRUCT = auto()
    LIST = auto()


# Map Python type annotation names to AmipyType
ANNOTATION_MAP: dict[str, AmipyType] = {
    "int": AmipyType.INT,
    "float": AmipyType.FLOAT,
    "bool": AmipyType.BOOL,
    "str": AmipyType.STR,
}

# Map AmipyType to C type strings
C_TYPE_MAP: dict[AmipyType, str] = {
    AmipyType.INT: "LONG",
    AmipyType.FLOAT: "float",
    AmipyType.BOOL: "BOOL",
    AmipyType.STR: "const char *",
    AmipyType.VOID: "void",
    AmipyType.DISPLAY: "AmipyDisplay",
    AmipyType.BITMAP: "AmipyBitmap",
    AmipyType.SHAPE: "AmipyShape",
    AmipyType.SPRITE: "AmipySprite",
    AmipyType.TILEMAP: "AmipyTilemap",
}

# Map engine Python type names to AmipyType
ENGINE_TYPE_MAP: dict[str, AmipyType] = {
    "Display": AmipyType.DISPLAY,
    "Bitmap": AmipyType.BITMAP,
    "Shape": AmipyType.SHAPE,
    "Sprite": AmipyType.SPRITE,
    "Tilemap": AmipyType.TILEMAP,
}

# printf format specifiers for each type
FORMAT_MAP: dict[AmipyType, str] = {
    AmipyType.INT: "%ld",
    AmipyType.FLOAT: "%f",
    AmipyType.BOOL: "%d",
    AmipyType.STR: "%s",
}


@dataclass
class StructField:
    name: str
    type: AmipyType
    default: object | None = None  # None = required


@dataclass
class StructInfo:
    name: str
    fields: list[StructField]


@dataclass
class VariableInfo:
    name: str
    type: AmipyType
    struct_name: str | None = None  # when type == STRUCT, identifies which struct
    list_element_type: AmipyType | None = None  # when type == LIST
    list_element_struct: str | None = None  # when LIST of STRUCT
    is_ref: bool = False  # True for loop vars over lists (emitted as pointers)
    list_capacity: int = 64  # max elements for list arrays
    list_init_values: list | None = None  # pre-computed values for trig tables


@dataclass
class FunctionInfo:
    name: str
    params: list[VariableInfo]
    return_type: AmipyType


@dataclass
class TypeInfo:
    """Side-table storing type information collected during type checking."""
    # Global variables
    globals: dict[str, VariableInfo] = field(default_factory=dict)
    # Function signatures
    functions: dict[str, FunctionInfo] = field(default_factory=dict)
    # Per-function local variables: function_name -> {var_name -> VariableInfo}
    locals: dict[str, dict[str, VariableInfo]] = field(default_factory=dict)
    # Expression types: ast node id -> AmipyType
    expr_types: dict[int, AmipyType] = field(default_factory=dict)
    # Imported engine names (from amiga import Display, palette, etc.)
    engine_imports: set[str] = field(default_factory=set)
    # Module variables: names that are engine modules (palette, copper, etc.)
    engine_modules: set[str] = field(default_factory=set)
    # User-defined structs (@dataclass classes)
    structs: dict[str, StructInfo] = field(default_factory=dict)
    # Expression struct names: ast node id -> struct name (for STRUCT-typed exprs)
    expr_struct_names: dict[int, str] = field(default_factory=dict)
    # Expression list element info: ast node id -> (element_type, element_struct)
    expr_list_info: dict[int, tuple[AmipyType, str | None]] = field(default_factory=dict)
