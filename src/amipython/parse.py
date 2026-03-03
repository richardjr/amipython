"""Parse Python source into an AST."""

import ast

from amipython.errors import ParseError


def parse(source: str, filename: str = "<string>") -> ast.Module:
    """Parse Python source code and return an AST module node."""
    try:
        return ast.parse(source, filename=filename)
    except SyntaxError as e:
        raise ParseError(str(e), lineno=e.lineno) from e
