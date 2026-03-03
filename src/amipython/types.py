"""Type system for the amipython transpiler."""

from dataclasses import dataclass, field
from enum import Enum, auto


class AmipyType(Enum):
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    STR = auto()
    VOID = auto()


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
}

# printf format specifiers for each type
FORMAT_MAP: dict[AmipyType, str] = {
    AmipyType.INT: "%ld",
    AmipyType.FLOAT: "%f",
    AmipyType.BOOL: "%d",
    AmipyType.STR: "%s",
}


@dataclass
class VariableInfo:
    name: str
    type: AmipyType


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
