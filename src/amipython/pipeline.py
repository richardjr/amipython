"""Orchestrate the transpilation pipeline: parse → validate → typecheck → emit."""

from amipython.emit import emit
from amipython.errors import ValidationError
from amipython.parse import parse
from amipython.typecheck import typecheck
from amipython.validate import validate


def transpile(source: str, filename: str = "<string>") -> str:
    """Transpile Python source to C89 code.

    Returns the generated C source code string.
    Raises ParseError, ValidationError, or TypeCheckError on failure.
    """
    tree = parse(source, filename=filename)

    errors = validate(tree)
    if errors:
        raise errors[0]

    info = typecheck(tree)
    # Pass source directory so emitter can resolve relative asset paths
    import os
    source_dir = os.path.dirname(os.path.abspath(filename)) if filename != "<string>" else None
    return emit(tree, info, source_dir=source_dir)
