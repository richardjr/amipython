"""Error types for the amipython transpiler."""


class AmipythonError(Exception):
    """Base error for all amipython errors."""

    def __init__(self, message: str, lineno: int | None = None):
        self.lineno = lineno
        if lineno is not None:
            message = f"line {lineno}: {message}"
        super().__init__(message)


class ParseError(AmipythonError):
    """Error during parsing."""


class ValidationError(AmipythonError):
    """Error when unsupported Python features are used."""


class TypeCheckError(AmipythonError):
    """Error during type checking."""


class EmitError(AmipythonError):
    """Error during C code generation."""


class BuildError(AmipythonError):
    """Error during compilation."""
