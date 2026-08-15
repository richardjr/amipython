"""Orchestrate the transpilation pipeline: load modules → validate → typecheck → emit."""

import os

from amipython.emit import emit
from amipython.errors import AmipythonError
from amipython.modules import decode_lineno, load_program
from amipython.typecheck import typecheck
from amipython.validate import validate


def transpile(source: str, filename: str = "<string>") -> str:
    """Transpile Python source to C89 code.

    `filename` is the main file; `from <mod> import ...` of sibling `.py`
    files is resolved relative to it and spliced into one unit.
    Returns the generated C source code string.
    Raises ParseError, ValidationError, TypeCheckError or EmitError on failure —
    for multi-module programs the message carries `file:line`.
    """
    tree = load_program(source, filename)
    try:
        errors = validate(tree)
        if errors:
            raise errors[0]

        info = typecheck(tree)
        # Pass source directory so emitter can resolve relative asset paths
        source_dir = os.path.dirname(os.path.abspath(filename)) if filename != "<string>" else None
        return emit(tree, info, source_dir=source_dir)
    except AmipythonError as e:
        fname, line = decode_lineno(tree, e.lineno)
        if fname is None:
            raise
        raise e.with_location(fname, line) from None
