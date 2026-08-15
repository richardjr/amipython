"""Error types for the amipython transpiler."""


class AmipythonError(Exception):
    """Base error for all amipython errors."""

    def __init__(self, message: str, lineno: int | None = None,
                 filename: str | None = None):
        self.message = message
        self.lineno = lineno
        self.filename = filename
        if lineno is not None and filename is not None:
            message = f"{filename}:{lineno}: {message}"
        elif lineno is not None:
            message = f"line {lineno}: {message}"
        super().__init__(message)

    def with_location(self, filename: str | None, lineno: int | None):
        """Same error, re-formatted with a resolved (file, line) location."""
        return type(self)(self.message, lineno=lineno, filename=filename)


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
