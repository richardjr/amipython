"""Multi-module programs — splice sibling modules into one translation unit.

A program may be split across several files in the same directory:

    game/main.py       from mapgen import gen_floor, MAP_W
    game/mapgen.py     from state import G   (may itself import siblings)
    game/state.py

`from <mod> import a, b` (or `*`) where `<mod>.py` sits beside the importing
file is a *local import*. The Python preview needs nothing special (real
imports). For transpilation every local module is parsed once, its body is
spliced ahead of the importing module in dependency order, and the local
import statements are dropped — the C output is a single unit with one
namespace. Rules enforced here:

- top-level names (functions, classes, globals) must be unique across all
  modules;
- a module may not rebind a name it imported (`global X` in a function or a
  module-level assignment) — Python would silently create a module-local
  copy while the C would share one variable. Shared mutable scalars go in a
  `@dataclass` state object instead;
- imported names must exist at the top level of the target module;
- no aliases (`as`), no plain `import mod`, no circular imports.

Each module's AST is line-shifted by LINE_STRIDE * index (main = 0) so a
downstream error's `lineno` can be decoded back to (file, line) — see
`decode_lineno`.
"""

from __future__ import annotations

import ast
from pathlib import Path

from amipython.errors import ParseError, ValidationError
from amipython.parse import parse

# Line-number stride between spliced modules. Main module is index 0 so
# single-file programs are unaffected.
LINE_STRIDE = 1_000_000

_STD_IMPORTS = ("amiga", "dataclasses")


class ProgramModule:
    """One source file of a multi-module program."""

    def __init__(self, name: str, path: Path | None, tree: ast.Module, index: int):
        self.name = name
        self.path = path
        self.tree = tree
        self.index = index
        self.imports: dict[str, list[str]] = {}   # module -> imported names (["*"] for star)
        self.imported_names: set[str] = set()
        self.defined_names: set[str] = set()

    @property
    def display_name(self) -> str:
        return str(self.path) if self.path is not None else self.name


def _top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def _locally_bound_names(tree: ast.Module) -> set[str]:
    """Names bound anywhere inside the module (function params, locals, loop
    variables, ...) — these legitimately shadow other modules' globals."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _local_module_path(source_dir: Path | None, module: str) -> Path | None:
    if source_dir is None or "." in module:
        return None
    candidate = source_dir / f"{module}.py"
    return candidate if candidate.is_file() else None


def load_program(source: str, filename: str) -> ast.Module:
    """Parse `source` (the main file) and splice in any local modules it
    imports, transitively. Returns a single ast.Module.

    Single-file programs come back as-is (parsed, unshifted)."""
    main_path = Path(filename) if filename != "<string>" else None
    source_dir = main_path.parent if main_path is not None else None

    main_tree = parse(source, filename=filename)
    modules: dict[str, ProgramModule] = {}
    order: list[ProgramModule] = []          # post-order (dependencies first)
    visiting: list[str] = []

    def _load(name: str, tree: ast.Module, path: Path | None) -> ProgramModule:
        mod = ProgramModule(name, path, tree, index=len(modules))
        modules[name] = mod
        visiting.append(name)
        for node in tree.body:
            if isinstance(node, ast.Import):
                raise ValidationError(
                    f"plain 'import' is not supported — use "
                    f"'from {node.names[0].name} import ...'",
                    lineno=node.lineno, filename=mod.display_name,
                )
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module in _STD_IMPORTS and node.level == 0:
                continue
            target = node.module or ""
            if node.level != 0:
                raise ValidationError(
                    f"relative imports are not supported — use "
                    f"'from {target or '<module>'} import ...' (sibling file)",
                    lineno=node.lineno, filename=mod.display_name,
                )
            dep_path = _local_module_path(source_dir, target)
            if dep_path is None:
                if source_dir is None:
                    hint = " (local modules need a real source path)"
                else:
                    hint = f" (no {source_dir / (target + '.py')})"
                raise ValidationError(
                    f"unknown module '{target}'{hint} — only "
                    f"'from amiga import ...', 'from dataclasses import dataclass' "
                    f"and sibling modules are supported",
                    lineno=node.lineno, filename=mod.display_name,
                )
            names = []
            for alias in node.names:
                if alias.asname is not None:
                    raise ValidationError(
                        "import aliases are not supported",
                        lineno=node.lineno, filename=mod.display_name,
                    )
                names.append(alias.name)
            mod.imports.setdefault(target, []).extend(names)
            if target in visiting:
                cycle = " -> ".join(visiting[visiting.index(target):] + [target])
                raise ValidationError(
                    f"circular import: {cycle}",
                    lineno=node.lineno, filename=mod.display_name,
                )
            if target not in modules:
                try:
                    dep_source = dep_path.read_text()
                except OSError as e:
                    raise ParseError(f"cannot read module {dep_path}: {e}") from e
                try:
                    dep_tree = parse(dep_source, filename=str(dep_path))
                except ParseError as e:
                    raise e.with_location(str(dep_path), e.lineno) from None
                _load(target, dep_tree, dep_path)
        visiting.pop()
        mod.defined_names = _top_level_names(tree)
        order.append(mod)
        return mod

    _load(main_path.stem if main_path is not None else "<main>", main_tree, main_path)

    if len(modules) == 1:
        return main_tree                      # single file — nothing to do

    # --- cross-module checks -------------------------------------------------
    for mod in order:
        for target, names in mod.imports.items():
            dep = modules[target]
            for name in names:
                if name == "*":
                    mod.imported_names |= dep.defined_names
                    continue
                if name not in dep.defined_names:
                    raise ValidationError(
                        f"cannot import '{name}' from '{target}' — not defined "
                        f"at the top level of {dep.display_name}",
                        filename=mod.display_name,
                    )
                mod.imported_names.add(name)
        rebound = mod.imported_names & mod.defined_names
        if rebound:
            raise ValidationError(
                f"'{sorted(rebound)[0]}' is imported and also assigned at "
                f"module level — a module may not rebind an imported name",
                filename=mod.display_name,
            )
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    if name in mod.imported_names:
                        raise ValidationError(
                            f"'global {name}' rebinds a name imported from "
                            f"another module — Python would make a module-local "
                            f"copy while the C shares one variable. Keep shared "
                            f"mutable scalars in a @dataclass state object "
                            f"(e.g. G.{name}) instead",
                            lineno=node.lineno, filename=mod.display_name,
                        )
    owner: dict[str, ProgramModule] = {}
    for mod in order:
        for name in mod.defined_names:
            if name in owner:
                raise ValidationError(
                    f"'{name}' is defined in both {owner[name].display_name} and "
                    f"{mod.display_name} — top-level names must be unique across "
                    f"all modules (the C output is a single namespace)",
                )
            owner[name] = mod
    # A module may only use another module's top-level names if it imported
    # them. The spliced C would compile regardless (one namespace) but Python
    # raises NameError when that code path runs — catch it at transpile time.
    for mod in order:
        local_names = _locally_bound_names(mod.tree)
        for node in ast.walk(mod.tree):
            if not (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)):
                continue
            name = node.id
            if name in mod.defined_names or name in mod.imported_names or name in local_names:
                continue
            other = owner.get(name)
            if other is not None and other is not mod:
                raise ValidationError(
                    f"'{name}' is used but not imported — add "
                    f"'from {other.name} import {name}'",
                    lineno=node.lineno, filename=mod.display_name,
                )

    # --- splice ---------------------------------------------------------------
    body: list[ast.stmt] = []
    for mod in order:
        if mod.index:
            ast.increment_lineno(mod.tree, LINE_STRIDE * mod.index)
        for node in mod.tree.body:
            if isinstance(node, ast.ImportFrom) and not (
                node.module in _STD_IMPORTS and node.level == 0
            ):
                continue                      # local import — spliced instead
            body.append(node)
    merged = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(merged)
    merged._amipy_modules = [m.display_name for m in sorted(modules.values(), key=lambda m: m.index)]  # type: ignore[attr-defined]
    return merged


def decode_lineno(tree: ast.Module, lineno: int | None) -> tuple[str | None, int | None]:
    """Map a (possibly shifted) line number back to (file, line)."""
    names = getattr(tree, "_amipy_modules", None)
    if lineno is None or not names:
        return None, lineno
    idx, line = divmod(lineno, LINE_STRIDE)
    if idx >= len(names):
        return None, lineno
    return names[idx], line
