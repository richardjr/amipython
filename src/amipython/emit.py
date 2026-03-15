"""C89 code emitter for the amipython transpiler."""

import ast
import math
import re

from amipython.engine import BUILTINS, MODULE_TYPES, OBJECT_TYPES
from amipython.errors import EmitError
from amipython.types import (
    C_TYPE_MAP,
    ENGINE_TYPE_MAP,
    FORMAT_MAP,
    AmipyType,
    TypeInfo,
    VariableInfo,
)


def _rewrite_asset_path(c_str: str) -> str:
    """Rewrite .png/.iff path to .bm for asset loading in C code.

    Input is a C string literal like '"data/ball.png"'.
    Returns '"data/ball.bm"'.
    """
    return re.sub(r'\.(?:png|iff)"$', '.bm"', c_str)


# Map AmipyType to the amipython_print_* function name
_PRINT_FN_MAP: dict[AmipyType, str] = {
    AmipyType.INT: "amipython_print_long",
    AmipyType.FLOAT: "amipython_print_float",
    AmipyType.BOOL: "amipython_print_bool",
    AmipyType.STR: "amipython_print_str",
}


def emit(tree: ast.Module, info: TypeInfo, source_dir: str | None = None) -> str:
    """Emit C89 code from a type-checked AST."""
    emitter = _Emitter(info, source_dir=source_dir)
    return emitter.emit_module(tree)


class _Emitter:
    def __init__(self, info: TypeInfo, source_dir: str | None = None):
        self.info = info
        self.indent = 0
        self.lines: list[str] = []
        self.source_dir = source_dir  # directory of the .py source file
        self._embedded_counter = 0  # counter for unique embedded data names
        self._embedded_decls: list[str] = []  # top-level embedded data arrays

    def _embed_shape(self, path_literal: str, var_name: str) -> str | None:
        """Convert a PNG/IFF at transpile time and return embedded load call.

        Returns a C statement like:
            amipython_shape_load_embedded(&var, s_assetData0, 192, 56, 3);

        The planar data array is added to self._embedded_decls for emission
        before main(). Returns None if the image can't be found/converted.
        """
        if not self.source_dir:
            return None
        # Strip quotes from C string literal: '"data/logo.png"' -> 'data/logo.png'
        rel_path = path_literal.strip('"')
        # Try original extension, then swap .bm back to .png/.iff
        import os
        for ext in [None, ".png", ".iff"]:
            if ext is None:
                full = os.path.join(self.source_dir, rel_path)
            else:
                base = os.path.splitext(rel_path)[0]
                full = os.path.join(self.source_dir, base + ext)
            if os.path.exists(full):
                break
        else:
            return None

        from amipython.assets import convert_image_to_bytes
        info = convert_image_to_bytes(full)
        if info is None:
            return None

        data_name = f"s_assetData{self._embedded_counter}"
        self._embedded_counter += 1

        # Build C array declaration
        lines = [f"static const UBYTE {data_name}[] = {{"]
        data = info["data"]
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_vals = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"    {hex_vals},")
        lines.append("};")
        self._embedded_decls.append("\n".join(lines))

        w = info["width"]
        h = info["height"]
        bp = info["depth"]
        return f'amipython_shape_load_embedded(&{var_name}, {data_name}, {w}, {h}, {bp});'

    def _embed_bitmap(self, path_literal: str, var_name: str) -> str | None:
        """Convert a PNG/IFF at transpile time and return embedded bitmap load call.

        Returns a C statement like:
            amipython_bitmap_load_embedded(&var, s_assetData0, 144, 32, 3);

        Same as _embed_shape but for Bitmap objects.
        """
        if not self.source_dir:
            return None
        rel_path = path_literal.strip('"')
        import os
        for ext in [None, ".png", ".iff"]:
            if ext is None:
                full = os.path.join(self.source_dir, rel_path)
            else:
                base = os.path.splitext(rel_path)[0]
                full = os.path.join(self.source_dir, base + ext)
            if os.path.exists(full):
                break
        else:
            return None

        from amipython.assets import convert_image_to_bytes
        info = convert_image_to_bytes(full)
        if info is None:
            return None

        data_name = f"s_assetData{self._embedded_counter}"
        self._embedded_counter += 1

        lines = [f"static const UBYTE {data_name}[] = {{"]
        data = info["data"]
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_vals = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"    {hex_vals},")
        lines.append("};")
        self._embedded_decls.append("\n".join(lines))

        w = info["width"]
        h = info["height"]
        bp = info["depth"]
        return f'amipython_bitmap_load_embedded(&{var_name}, {data_name}, {w}, {h}, {bp});'

    def _embed_tileset(self, path_literal: str) -> dict | None:
        """Convert a tileset PNG at transpile time and return embedded data info.

        Returns dict with data_name, width, height, depth for the C init call.
        The planar data array is added to self._embedded_decls.
        """
        if not self.source_dir:
            return None
        rel_path = path_literal.strip('"')
        import os
        for ext in [None, ".png", ".iff"]:
            if ext is None:
                full = os.path.join(self.source_dir, rel_path)
            else:
                base = os.path.splitext(rel_path)[0]
                full = os.path.join(self.source_dir, base + ext)
            if os.path.exists(full):
                break
        else:
            return None

        from amipython.assets import convert_image_to_bytes
        info = convert_image_to_bytes(full)
        if info is None:
            return None

        data_name = f"s_assetData{self._embedded_counter}"
        self._embedded_counter += 1

        lines = [f"static const UBYTE {data_name}[] = {{"]
        data = info["data"]
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_vals = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"    {hex_vals},")
        lines.append("};")
        self._embedded_decls.append("\n".join(lines))

        return {
            "data_name": data_name,
            "width": info["width"],
            "height": info["height"],
            "depth": info["depth"],
        }

    def _emit_tilemap_load_tiled(self, var_name: str, call: ast.Call):
        """Emit Tilemap.load_tiled() — parse Tiled JSON at transpile time.

        Reads the JSON, embeds the tileset PNG, emits map data as set_tile
        calls, and sets up blocking flags.
        """
        import json as json_mod
        import os

        json_path_str = self._emit_arg(call.args[0]).strip('"')
        width_str = self._emit_arg(call.args[1])
        height_str = self._emit_arg(call.args[2])

        # Resolve keyword args
        kw_provided = {kw.arg: self._emit_arg(kw.value) for kw in call.keywords}
        bitplanes_str = kw_provided.get("bitplanes", "3")

        # Read JSON file relative to source directory
        if not self.source_dir:
            raise EmitError("cannot resolve Tiled JSON path", lineno=call.lineno)
        full_json = os.path.join(self.source_dir, json_path_str)
        if not os.path.exists(full_json):
            raise EmitError(
                f"Tiled JSON not found: {full_json}", lineno=call.lineno)

        with open(full_json) as f:
            tiled = json_mod.load(f)

        map_w = tiled["width"]
        map_h = tiled["height"]
        tile_size = tiled["tilewidth"]

        # Find tileset and embed its image
        ts_info = tiled["tilesets"][0]
        firstgid = ts_info["firstgid"]
        tileset_image = ts_info["image"]
        json_dir = os.path.dirname(full_json)
        tileset_full = os.path.join(json_dir, tileset_image)

        tileset_info = self._embed_tileset(f'"{tileset_full}"')
        if tileset_info is None:
            raise EmitError(
                f"cannot embed tileset: {tileset_full}", lineno=call.lineno)

        # Extract blocking tile IDs
        blocking_ids = set()
        if "tiles" in ts_info:
            for tile_info in ts_info["tiles"]:
                tile_id = tile_info["id"]
                for prop in tile_info.get("properties", []):
                    if prop["name"] == "blocking" and prop.get("value", False):
                        blocking_ids.add(tile_id)

        # Emit blocking flags array as embedded data
        tile_count = ts_info.get("tilecount", 0)
        if tile_count > 0 and blocking_ids:
            flags_name = f"s_blockingFlags{self._embedded_counter}"
            self._embedded_counter += 1
            flags = [1 if i in blocking_ids else 0 for i in range(tile_count)]
            flags_hex = ", ".join(str(f) for f in flags)
            self._embedded_decls.append(
                f"static const UBYTE {flags_name}[] = {{ {flags_hex} }};")
        else:
            flags_name = "NULL"
            tile_count = 0

        # Emit tilemap init call with embedded tileset data
        self._line(
            f"amipython_tilemap_init(&{var_name}, "
            f"{tileset_info['data_name']}, "
            f"{tileset_info['width']}, {tileset_info['height']}, "
            f"{tileset_info['depth']}, "
            f"{width_str}, {height_str}, {bitplanes_str}, "
            f"{tile_size}, {map_w}, {map_h});"
        )

        # Set blocking flags
        if flags_name != "NULL":
            self._line(
                f"amipython_tilemap_set_blocking(&{var_name}, "
                f"{flags_name}, {tile_count});"
            )

        # Emit tile data from the first tile layer
        for layer in tiled["layers"]:
            if layer["type"] == "tilelayer":
                layer_data = layer["data"]
                for i, gid in enumerate(layer_data):
                    if gid > 0:
                        tile_idx = gid - firstgid
                        x = i % map_w
                        y = i // map_w
                        if tile_idx != 0:  # skip floor (tile 0) — it's the default
                            self._line(
                                f"amipython_tilemap_set_tile("
                                f"&{var_name}, {x}, {y}, {tile_idx});"
                            )
                break

    def _embed_music(self, path_literal: str) -> str | None:
        """Embed a MOD file at transpile time and return the load call.

        Returns a C statement like:
            amipython_music_load_embedded(s_modData0, 12345UL);

        The raw byte array is added to self._embedded_decls for emission
        before main(). Returns None if the file can't be found.
        """
        if not self.source_dir:
            return None
        import os
        rel_path = path_literal.strip('"')
        full = os.path.join(self.source_dir, rel_path)
        if not os.path.exists(full):
            return None

        with open(full, "rb") as f:
            data = f.read()

        data_name = f"s_modData{self._embedded_counter}"
        size_name = f"s_modSize{self._embedded_counter}"
        self._embedded_counter += 1

        lines = [f"static const UBYTE {data_name}[] = {{"]
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            hex_vals = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"    {hex_vals},")
        lines.append("};")
        lines.append(f"static const ULONG {size_name} = {len(data)}UL;")
        self._embedded_decls.append("\n".join(lines))

        return f"amipython_music_load_embedded({data_name}, {size_name});"

    def _line(self, text: str = ""):
        if text:
            self.lines.append("    " * self.indent + text)
        else:
            self.lines.append("")

    def _type_str(self, t: AmipyType) -> str:
        return C_TYPE_MAP[t]

    def _var_decl(self, t: AmipyType, name: str) -> str:
        """Format a variable declaration, handling pointer types correctly."""
        c_type = C_TYPE_MAP[t]
        if c_type.endswith("*"):
            return f"{c_type}{name}"
        return f"{c_type} {name}"

    def _format_spec(self, t: AmipyType) -> str:
        return FORMAT_MAP[t]

    def _expr_type(self, node: ast.expr) -> AmipyType:
        t = self.info.expr_types.get(id(node))
        if t is None:
            raise EmitError(
                f"no type info for expression",
                lineno=getattr(node, "lineno", None),
            )
        return t

    def _uses_float(self) -> bool:
        """Check if the program uses any float types."""
        for var in self.info.globals.values():
            if var.type == AmipyType.FLOAT:
                return True
        for func in self.info.functions.values():
            if func.return_type == AmipyType.FLOAT:
                return True
            for param in func.params:
                if param.type == AmipyType.FLOAT:
                    return True
        for locals_dict in self.info.locals.values():
            for var in locals_dict.values():
                if var.type == AmipyType.FLOAT:
                    return True
        for t in self.info.expr_types.values():
            if t == AmipyType.FLOAT:
                return True
        for struct in self.info.structs.values():
            for field in struct.fields:
                if field.type == AmipyType.FLOAT:
                    return True
        return False

    def emit_module(self, tree: ast.Module) -> str:
        self.lines = []
        self._line("/* Generated by amipython */")
        if self._uses_float():
            self._line("#define AMIPYTHON_USE_FLOAT")
        self._line('#include "amipython.h"')
        if self.info.engine_imports:
            self._line('#include "amipython_engine.h"')
        self._line()

        # Emit struct typedefs
        if self.info.structs:
            for struct in self.info.structs.values():
                self._emit_struct_typedef(struct)
            self._line()

        # Collect function declarations (forward declarations)
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        for func_node in functions:
            self._emit_forward_decl(func_node)

        if functions:
            self._line()

        # Emit global variable declarations
        self._emit_global_declarations(tree)

        # Emit function definitions
        for func_node in functions:
            self._emit_function(func_node)

        # Emit main — this may generate embedded data arrays
        self._emit_main(tree)

        # Insert embedded asset data arrays before function definitions
        if self._embedded_decls:
            # Find the insertion point: after global declarations, before functions
            insert_idx = 0
            for i, line in enumerate(self.lines):
                if line.startswith("void ") or line.startswith("int main("):
                    insert_idx = i
                    break
            embedded_lines = []
            for decl in self._embedded_decls:
                embedded_lines.extend(decl.split("\n"))
                embedded_lines.append("")
            for j, el in enumerate(embedded_lines):
                self.lines.insert(insert_idx + j, el)

        return "\n".join(self.lines) + "\n"

    def _emit_struct_typedef(self, struct):
        """Emit a C struct typedef from a StructInfo."""
        self._line(f"typedef struct {{")
        self.indent += 1
        for field in struct.fields:
            self._line(f"{self._var_decl(field.type, field.name)};")
        self.indent -= 1
        self._line(f"}} {struct.name};")
        self._line()

    def _emit_forward_decl(self, node: ast.FunctionDef):
        func = self.info.functions[node.name]
        params = ", ".join(
            self._var_decl(p.type, p.name) for p in func.params
        )
        if not params:
            params = "void"
        self._line(f"{self._type_str(func.return_type)} {node.name}({params});")

    def _emit_global_declarations(self, tree: ast.Module):
        """Emit global variable declarations."""
        declared = set()
        for name, var in self.info.globals.items():
            if var.type == AmipyType.MODULE:
                continue  # modules aren't C variables
            if var.type == AmipyType.STRUCT and var.struct_name:
                if var.is_ref:
                    self._line(f"{var.struct_name} *{name};")
                else:
                    self._line(f"{var.struct_name} {name};")
            elif var.type == AmipyType.LIST:
                self._emit_list_decl(name, var)
            else:
                self._line(f"{self._var_decl(var.type, name)};")
            declared.add(name)
        if declared:
            self._line()

    def _emit_list_decl(self, name: str, var: VariableInfo):
        """Emit parallel-variable declarations for a list."""
        if var.list_element_type == AmipyType.STRUCT and var.list_element_struct:
            elem_c = var.list_element_struct
        else:
            elem_c = C_TYPE_MAP.get(var.list_element_type, "LONG")
        capacity = var.list_capacity
        if var.list_init_values is not None:
            # Pre-computed values — emit as initialized array
            self._line(f"{elem_c} {name}_items[{capacity}] = {{")
            self.indent += 1
            chunk_size = 8
            values = var.list_init_values
            is_float = var.list_element_type == AmipyType.FLOAT
            for i in range(0, len(values), chunk_size):
                chunk = values[i:i + chunk_size]
                if is_float:
                    line = ", ".join(f"{v:.8f}f" for v in chunk)
                else:
                    line = ", ".join(str(v) for v in chunk)
                if i + chunk_size < len(values):
                    line += ","
                self._line(line)
            self.indent -= 1
            self._line("};")
            self._line(f"LONG {name}_count = {len(values)};")
        else:
            self._line(f"{elem_c} {name}_items[{capacity}];")
            self._line(f"LONG {name}_count = 0;")

    def _emit_var_decl_for_local(self, name: str, var: VariableInfo):
        """Emit a local variable declaration, handling structs, lists, and refs."""
        if var.type == AmipyType.STRUCT and var.struct_name:
            if var.is_ref:
                self._line(f"{var.struct_name} *{name};")
            else:
                self._line(f"{var.struct_name} {name};")
        elif var.type == AmipyType.LIST:
            self._emit_list_decl(name, var)
        elif var.is_ref and self._is_engine_object_type(var.type):
            c_type = C_TYPE_MAP[var.type]
            self._line(f"{c_type} *{name};")
        else:
            self._line(f"{self._var_decl(var.type, name)};")

    def _emit_function(self, node: ast.FunctionDef):
        func = self.info.functions[node.name]
        params = ", ".join(
            self._var_decl(p.type, p.name) for p in func.params
        )
        if not params:
            params = "void"
        self._line(f"{self._type_str(func.return_type)} {node.name}({params}) {{")
        self.indent += 1

        # Declare local variables at top of scope (C89)
        locals_dict = self.info.locals.get(node.name, {})
        param_names = {p.name for p in func.params}
        local_vars = {
            k: v for k, v in locals_dict.items() if k not in param_names
        }
        # Also need index vars for list iteration
        for_idx_vars = set()
        self._collect_for_idx_vars(node.body, for_idx_vars)
        for var_name, var_info in local_vars.items():
            self._emit_var_decl_for_local(var_name, var_info)
        for idx_var in sorted(for_idx_vars):
            if idx_var not in local_vars and idx_var not in param_names:
                self._line(f"LONG {idx_var};")
        if local_vars or for_idx_vars:
            self._line()

        # Emit function body (skip Global statements)
        for stmt in node.body:
            if not isinstance(stmt, ast.Global):
                self._emit_stmt(stmt)

        self.indent -= 1
        self._line("}")
        self._line()

    def _collect_for_idx_vars(self, stmts: list, out: set):
        """Collect _idx variable names needed for list iteration loops."""
        for stmt in stmts:
            if isinstance(stmt, ast.For) and isinstance(stmt.iter, ast.Name):
                # for x in list_var -> x_idx
                list_var = self._get_var_info(stmt.iter.id)
                if list_var and list_var.type == AmipyType.LIST:
                    if isinstance(stmt.target, ast.Name):
                        out.add(f"{stmt.target.id}_idx")
                self._collect_for_idx_vars(stmt.body, out)
            elif isinstance(stmt, ast.If):
                self._collect_for_idx_vars(stmt.body, out)
                self._collect_for_idx_vars(stmt.orelse, out)
            elif isinstance(stmt, ast.While):
                self._collect_for_idx_vars(stmt.body, out)

    def _emit_main(self, tree: ast.Module):
        """Emit the main function from module-level statements."""
        has_engine = bool(self.info.engine_imports)
        # Collect module-level statements (non-function-defs, non-imports, non-classes)
        stmts = [n for n in tree.body
                 if not isinstance(n, (ast.FunctionDef, ast.ImportFrom, ast.ClassDef))]
        if not stmts:
            self._line("int main(void) {")
            self.indent += 1
            if has_engine:
                self._line("amipython_engine_create();")
                self._line("amipython_engine_destroy();")
            self._line("return 0;")
            self.indent -= 1
            self._line("}")
            return

        self._line("int main(void) {")
        self.indent += 1

        # Declare index vars needed for list iteration at main scope
        for_idx_vars = set()
        self._collect_for_idx_vars(stmts, for_idx_vars)
        for idx_var in sorted(for_idx_vars):
            self._line(f"LONG {idx_var};")
        if for_idx_vars:
            self._line()

        if has_engine:
            self._line("amipython_engine_create();")

        for stmt in stmts:
            self._emit_stmt(stmt)

        if has_engine:
            self._line("amipython_engine_destroy();")
        self._line("return 0;")
        self.indent -= 1
        self._line("}")

    def _emit_stmt(self, node: ast.stmt):
        if isinstance(node, ast.Assign):
            self._emit_assign(node)
        elif isinstance(node, ast.AnnAssign):
            self._emit_ann_assign(node)
        elif isinstance(node, ast.AugAssign):
            self._emit_aug_assign(node)
        elif isinstance(node, ast.Expr):
            self._emit_expr_stmt(node)
        elif isinstance(node, ast.If):
            self._emit_if(node)
        elif isinstance(node, ast.While):
            self._emit_while(node)
        elif isinstance(node, ast.For):
            self._emit_for(node)
        elif isinstance(node, ast.Return):
            self._emit_return(node)
        elif isinstance(node, ast.Break):
            self._line("break;")
        elif isinstance(node, ast.Continue):
            self._line("continue;")
        elif isinstance(node, ast.Pass):
            pass  # No C output needed
        elif isinstance(node, ast.Global):
            pass  # Handled by type checker
        elif isinstance(node, ast.ImportFrom):
            pass  # Handled at module level
        else:
            raise EmitError(
                f"unsupported statement: {type(node).__name__}",
                lineno=getattr(node, "lineno", None),
            )

    def _emit_assign(self, node: ast.Assign):
        target = node.targets[0]
        if isinstance(target, ast.Name):
            # Engine constructor: display = Display(320, 256, bitplanes=8)
            if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in OBJECT_TYPES
                    and node.value.func.id in self.info.engine_imports):
                self._emit_engine_init(target.id, node.value)
                return
            # Static method returning engine type: ball = Shape.grab(bm, ...)
            if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and isinstance(node.value.func.value, ast.Name)
                    and node.value.func.value.id in OBJECT_TYPES
                    and node.value.func.value.id in self.info.engine_imports):
                class_name = node.value.func.value.id
                method_name = node.value.func.attr
                obj_type = OBJECT_TYPES[class_name]
                if method_name in obj_type.static_methods:
                    static = obj_type.static_methods[method_name]
                    # Tilemap.load_tiled — parse JSON at transpile time
                    if method_name == "load_tiled" and class_name == "Tilemap":
                        self._emit_tilemap_load_tiled(
                            target.id, node.value)
                        return
                    args_strs = [self._emit_arg(a) for a in node.value.args]
                    if method_name == "load" and class_name == "Shape" and args_strs:
                        # Try embedded approach (convert PNG at transpile time)
                        embedded = self._embed_shape(args_strs[0], target.id)
                        if embedded:
                            self._line(embedded)
                            return
                        args_strs = [_rewrite_asset_path(s) for s in args_strs]
                    elif method_name == "load" and class_name == "Bitmap" and args_strs:
                        # Try embedded approach for Bitmap.load too
                        embedded = self._embed_bitmap(args_strs[0], target.id)
                        if embedded:
                            self._line(embedded)
                            return
                        args_strs = [_rewrite_asset_path(s) for s in args_strs]
                    elif method_name == "load":
                        args_strs = [_rewrite_asset_path(s) for s in args_strs]
                    # Resolve keyword args for static methods
                    if hasattr(static, 'keywords') and static.keywords:
                        kw_provided = {kw.arg: self._emit_arg(kw.value)
                                       for kw in node.value.keywords}
                        for kw_name, (kw_type, kw_default) in static.keywords.items():
                            if kw_name in kw_provided:
                                args_strs.append(kw_provided[kw_name])
                            elif kw_default is not None:
                                args_strs.append(str(kw_default))
                    args = ", ".join(args_strs)
                    if args:
                        self._line(f"{static.c_name}(&{target.id}, {args});")
                    else:
                        self._line(f"{static.c_name}(&{target.id});")
                    return
            # Struct constructor: ball = Ball(x=10, y=20)
            if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in self.info.structs):
                self._emit_struct_init(target.id, node.value)
                return
            # Trig table: orbit_x = cos_table(720)
            # Values pre-computed at transpile time — array already initialized at declaration
            if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in ("sin_table", "cos_table")):
                var = self._get_var_info(target.id)
                if var and var.list_init_values is not None:
                    # Already initialized at declaration — nothing to emit
                    pass
                else:
                    # Fallback to runtime call for non-literal args
                    func_name = node.value.func.id
                    c_name = f"amipython_{func_name}"
                    arg = self._emit_expr(node.value.args[0])
                    self._line(f"{c_name}({target.id}_items, {arg});")
                    self._line(f"{target.id}_count = {arg};")
                return
            val = self._emit_expr(node.value)
            self._line(f"{target.id} = {val};")
        elif isinstance(target, ast.Attribute):
            # Field assignment: ball.x = 10
            val = self._emit_expr(node.value)
            obj_expr = self._emit_field_target(target)
            self._line(f"{obj_expr} = {val};")

    def _emit_ann_assign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.value is not None:
            # Skip empty list literal — declaration handles it
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                # Reset count to 0 (already initialized in declaration)
                var = self._get_var_info(node.target.id)
                if var and var.type == AmipyType.LIST:
                    self._line(f"{node.target.id}_count = 0;")
                return
            val = self._emit_expr(node.value)
            self._line(f"{node.target.id} = {val};")

    def _emit_aug_assign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Attribute):
            target = self._emit_field_target(node.target)
            op = self._binop_symbol(node.op)
            val = self._emit_expr(node.value)
            self._line(f"{target} {op}= {val};")
            return
        if isinstance(node.target, ast.Name):
            target = node.target.id
            op = self._binop_symbol(node.op)
            # For special operators, expand to full assignment
            if isinstance(node.op, (ast.FloorDiv, ast.Pow, ast.Mod)):
                var = self._get_var_info(node.target.id)
                left_expr = target
                right_expr = self._emit_expr(node.value)
                val = self._emit_binop_call(
                    node.op, left_expr, right_expr,
                    var.type if var else AmipyType.INT,
                    self._expr_type(node.value)
                )
                self._line(f"{target} = {val};")
            elif isinstance(node.op, ast.Div):
                right_expr = self._emit_expr(node.value)
                self._line(f"{target} = (float)({target}) / (float)({right_expr});")
            else:
                val = self._emit_expr(node.value)
                self._line(f"{target} {op}= {val};")

    def _emit_expr_stmt(self, node: ast.Expr):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name):
                if call.func.id == "print":
                    self._emit_print(call)
                    return
                # run(update, until=expr) — game loop
                if (call.func.id == "run"
                        and "run" in self.info.engine_imports):
                    self._emit_run(call)
                    return
                # Engine builtin: wait_mouse(), vwait(), rnd()
                if (call.func.id in BUILTINS
                        and call.func.id in self.info.engine_imports):
                    builtin = BUILTINS[call.func.id]
                    args = ", ".join(self._emit_expr(a) for a in call.args)
                    self._line(f"{builtin.c_name}({args});")
                    return
            # Method call: bm.circle_filled(...), palette.aga(...), balls.append(...)
            if isinstance(call.func, ast.Attribute):
                # Check if it's a list method
                if isinstance(call.func.value, ast.Name):
                    list_var = self._get_var_info(call.func.value.id)
                    if list_var and list_var.type == AmipyType.LIST:
                        self._emit_list_method_stmt(call, list_var)
                        return
                self._emit_method_call_stmt(call)
                return
        # General expression statement
        val = self._emit_expr(node.value)
        self._line(f"{val};")

    def _emit_print(self, node: ast.Call):
        """Emit print() using amipython_print_* helpers."""
        if not node.args:
            self._line("amipython_print_newline();")
            return

        for i, arg in enumerate(node.args):
            if i > 0:
                self._line("amipython_print_space();")
            arg_type = self._expr_type(arg)
            val = self._emit_expr(arg)
            print_fn = _PRINT_FN_MAP.get(arg_type)
            if print_fn:
                self._line(f"{print_fn}({val});")
            else:
                self._line(f"amipython_print_str({val});")
        self._line("amipython_print_newline();")

    def _emit_struct_init(self, var_name: str, call: ast.Call):
        """Emit struct constructor as field-by-field assignment."""
        struct_name = call.func.id
        struct = self.info.structs[struct_name]
        # Check if target is a ref (pointer from list iteration)
        var = self._get_var_info(var_name)
        accessor = "->" if (var and var.is_ref) else "."

        # Build map of provided kwargs
        provided = {}
        for kw in call.keywords:
            provided[kw.arg] = self._emit_expr(kw.value)
        # Emit assignments for all fields (provided + defaults)
        for field in struct.fields:
            if field.name in provided:
                self._line(f"{var_name}{accessor}{field.name} = {provided[field.name]};")
            elif field.default is not None:
                default_val = self._format_default(field.default, field.type)
                self._line(f"{var_name}{accessor}{field.name} = {default_val};")

    def _format_default(self, value, field_type: AmipyType) -> str:
        """Format a default value for a struct field."""
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, float):
            return f"{value!r}f"
        return str(value)

    def _emit_field_target(self, node: ast.Attribute) -> str:
        """Emit a field access target, using -> for refs and . for values.

        Module properties (e.g. mouse.x) emit as C getter function calls.
        Supports subscript targets: eq[i].level -> eq_items[i].level
        """
        if isinstance(node.value, ast.Subscript):
            # e.g. eq[i].level -> eq_items[i].level
            sub = self._emit_subscript(node.value)
            return f"{sub}.{node.attr}"
        if not isinstance(node.value, ast.Name):
            raise EmitError("unsupported field target", lineno=node.lineno)
        name = node.value.id
        # Module property access — emit as getter function call
        if name in self.info.engine_modules:
            mod = MODULE_TYPES[name]
            if node.attr in mod.properties:
                return f"{mod.properties[node.attr].c_getter}()"
        var = self._get_var_info(name)
        accessor = "->" if (var and var.is_ref) else "."
        return f"{name}{accessor}{node.attr}"

    def _emit_subscript(self, node: ast.Subscript) -> str:
        """Emit list subscript access: list_var[idx] -> list_var_items[idx]."""
        if isinstance(node.value, ast.Name):
            idx = self._emit_expr(node.slice)
            return f"{node.value.id}_items[{idx}]"
        raise EmitError("unsupported subscript target", lineno=node.lineno)

    def _emit_engine_init(self, var_name: str, call: ast.Call):
        """Emit engine constructor as init call: amipython_display_init(&d, ...)."""
        type_name = call.func.id
        obj_type = OBJECT_TYPES[type_name]
        ctor = obj_type.constructor

        # Build arg list: positional args + keyword args (fill defaults)
        args = [self._emit_expr(a) for a in call.args]
        # Tilemap constructor: first arg is tileset path — embed tileset data
        if type_name == "Tilemap" and args:
            tileset_info = self._embed_tileset(args[0])
            if tileset_info:
                # Replace path arg with: data_ptr, ts_w, ts_h, ts_bp
                args[0:1] = [tileset_info["data_name"],
                             str(tileset_info["width"]),
                             str(tileset_info["height"]),
                             str(tileset_info["depth"])]
            else:
                args[0] = _rewrite_asset_path(args[0])
        kw_provided = {kw.arg: self._emit_expr(kw.value) for kw in call.keywords}
        for kw_name, (kw_type, kw_default) in ctor.keywords.items():
            if kw_name in kw_provided:
                args.append(kw_provided[kw_name])
            else:
                args.append(str(kw_default))

        all_args = f"&{var_name}, " + ", ".join(args) if args else f"&{var_name}"
        self._line(f"{obj_type.c_init}({all_args});")

    def _resolve_method_kwargs(self, call: ast.Call, method) -> list[str]:
        """Resolve positional + keyword args for an EngineMethod, return full arg list."""
        args_strs = [self._emit_arg(a) for a in call.args]
        if method.keywords:
            kw_provided = {kw.arg: self._emit_arg(kw.value) for kw in call.keywords}
            for kw_name, (kw_type, kw_default) in method.keywords.items():
                if kw_name in kw_provided:
                    args_strs.append(kw_provided[kw_name])
                elif kw_default is not None:
                    args_strs.append(str(kw_default))
                # else: required kwarg — type checker ensures it's provided
        return args_strs

    def _emit_method_call_stmt(self, call: ast.Call):
        """Emit method/module function call as statement."""
        attr = call.func
        if not isinstance(attr.value, ast.Name):
            raise EmitError("unsupported method call", lineno=call.lineno)

        obj_name = attr.value.id
        method_name = attr.attr

        # Static method: Shape.grab(...)
        if (obj_name in OBJECT_TYPES
                and obj_name in self.info.engine_imports
                and method_name in OBJECT_TYPES[obj_name].static_methods):
            static = OBJECT_TYPES[obj_name].static_methods[method_name]
            args_strs = [self._emit_arg(a) for a in call.args]
            if method_name == "load":
                args_strs = [_rewrite_asset_path(s) for s in args_strs]
            args = ", ".join(args_strs)
            self._line(f"{static.c_name}({args});")
            return

        # Module function: palette.aga(...), collision.register(color=15, mask=4)
        if obj_name in self.info.engine_modules:
            mod = MODULE_TYPES[obj_name]
            func = mod.functions[method_name]
            # Intercept music.load() — embed MOD at transpile time
            if obj_name == "music" and method_name == "load" and call.args:
                path_str = self._emit_arg(call.args[0])
                embedded = self._embed_music(path_str)
                if embedded:
                    self._line(embedded)
                    return
            args_strs = self._resolve_method_kwargs(call, func)
            args = ", ".join(args_strs)
            self._line(f"{func.c_name}({args});")
            return

        # Object method: bm.circle_filled(...), sprite.show(x, y, channel=0)
        var = self._get_var_info(obj_name)
        if var is None:
            raise EmitError(f"unknown variable '{obj_name}'", lineno=call.lineno)

        obj_type_info = None
        for ot in OBJECT_TYPES.values():
            if ENGINE_TYPE_MAP.get(ot.python_name) == var.type:
                obj_type_info = ot
                break
        if obj_type_info is None:
            raise EmitError(
                f"'{obj_name}' is not an engine object", lineno=call.lineno
            )

        method = obj_type_info.methods[method_name]
        args_strs = self._resolve_method_kwargs(call, method)
        args = ", ".join(args_strs)
        if args:
            self._line(f"{method.c_name}(&{obj_name}, {args});")
        else:
            self._line(f"{method.c_name}(&{obj_name});")

    def _emit_list_method_stmt(self, call: ast.Call, list_var: VariableInfo):
        """Emit list method call (append, remove)."""
        list_name = call.func.value.id
        method_name = call.func.attr

        if method_name == "append":
            arg = call.args[0]
            if (isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Name)
                    and arg.func.id in self.info.structs):
                # Inline struct init into array slot
                struct = self.info.structs[arg.func.id]
                provided = {}
                for kw in arg.keywords:
                    provided[kw.arg] = self._emit_expr(kw.value)
                for field in struct.fields:
                    if field.name in provided:
                        self._line(
                            f"{list_name}_items[{list_name}_count].{field.name} = "
                            f"{provided[field.name]};"
                        )
                    elif field.default is not None:
                        default_val = self._format_default(field.default, field.type)
                        self._line(
                            f"{list_name}_items[{list_name}_count].{field.name} = "
                            f"{default_val};"
                        )
                self._line(f"{list_name}_count++;")
            elif (isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and isinstance(arg.func.value, ast.Name)
                    and arg.func.value.id in OBJECT_TYPES
                    and arg.func.value.id in self.info.engine_imports):
                # Static method returning engine type into list slot:
                # e.g. eq_bars.append(Shape.grab(sheet, x, y, w, h))
                # -> amipython_shape_grab(&eq_bars_items[eq_bars_count], &sheet, x, y, w, h);
                class_name = arg.func.value.id
                method_name_s = arg.func.attr
                obj_type = OBJECT_TYPES[class_name]
                if method_name_s in obj_type.static_methods:
                    static = obj_type.static_methods[method_name_s]
                    args_strs = [self._emit_arg(a) for a in arg.args]
                    if method_name_s == "load" and class_name == "Shape" and args_strs:
                        embedded = self._embed_shape(
                            args_strs[0],
                            f"{list_name}_items[{list_name}_count]",
                        )
                        if embedded:
                            self._line(embedded)
                            self._line(f"{list_name}_count++;")
                            return
                        args_strs = [_rewrite_asset_path(s) for s in args_strs]
                    elif method_name_s == "load":
                        args_strs = [_rewrite_asset_path(s) for s in args_strs]
                    args = ", ".join(args_strs)
                    slot = f"&{list_name}_items[{list_name}_count]"
                    if args:
                        self._line(f"{static.c_name}({slot}, {args});")
                    else:
                        self._line(f"{static.c_name}({slot});")
                    self._line(f"{list_name}_count++;")
                else:
                    raise EmitError(
                        f"'{class_name}.{method_name_s}' is not a static method",
                        lineno=call.lineno,
                    )
            else:
                val = self._emit_expr(arg)
                self._line(f"{list_name}_items[{list_name}_count] = {val};")
                self._line(f"{list_name}_count++;")
            return

        if method_name == "remove":
            # Emit shift-down loop
            arg = call.args[0]
            val = self._emit_expr(arg)
            # We need a temp index var; use _remove_idx
            self._line("{")
            self.indent += 1
            self._line("LONG _ri;")
            self._line(f"for (_ri = 0; _ri < {list_name}_count; _ri++) {{")
            self.indent += 1
            self._line(f"if (&{list_name}_items[_ri] == {val}) {{")
            self.indent += 1
            self._line("LONG _rj;")
            self._line(f"for (_rj = _ri; _rj < {list_name}_count - 1; _rj++) {{")
            self.indent += 1
            self._line(f"{list_name}_items[_rj] = {list_name}_items[_rj + 1];")
            self.indent -= 1
            self._line("}")
            self._line(f"{list_name}_count--;")
            self._line("break;")
            self.indent -= 1
            self._line("}")
            self.indent -= 1
            self._line("}")
            self.indent -= 1
            self._line("}")
            return

        raise EmitError(f"unsupported list method '{method_name}'", lineno=call.lineno)

    def _emit_if(self, node: ast.If):
        cond = self._emit_expr(node.test)
        self._line(f"if ({cond}) {{")
        self.indent += 1
        for stmt in node.body:
            self._emit_stmt(stmt)
        self.indent -= 1

        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif
                elif_node = node.orelse[0]
                cond = self._emit_expr(elif_node.test)
                self._line(f"}} else if ({cond}) {{")
                self.indent += 1
                for stmt in elif_node.body:
                    self._emit_stmt(stmt)
                self.indent -= 1
                if elif_node.orelse:
                    self._emit_else(elif_node.orelse)
                else:
                    self._line("}")
            else:
                self._emit_else(node.orelse)
        else:
            self._line("}")

    def _emit_else(self, orelse: list[ast.stmt]):
        if len(orelse) == 1 and isinstance(orelse[0], ast.If):
            elif_node = orelse[0]
            cond = self._emit_expr(elif_node.test)
            self._line(f"}} else if ({cond}) {{")
            self.indent += 1
            for stmt in elif_node.body:
                self._emit_stmt(stmt)
            self.indent -= 1
            if elif_node.orelse:
                self._emit_else(elif_node.orelse)
            else:
                self._line("}")
        else:
            self._line("} else {")
            self.indent += 1
            for stmt in orelse:
                self._emit_stmt(stmt)
            self.indent -= 1
            self._line("}")

    def _emit_while(self, node: ast.While):
        cond = self._emit_expr(node.test)
        self._line(f"while ({cond}) {{")
        self.indent += 1
        for stmt in node.body:
            self._emit_stmt(stmt)
        self.indent -= 1
        self._line("}")

    def _emit_for(self, node: ast.For):
        """Emit for loops — range() or list iteration."""
        if not isinstance(node.target, ast.Name):
            raise EmitError("for loop target must be a name", lineno=node.lineno)
        var = node.target.id

        # List iteration: for b in balls
        if isinstance(node.iter, ast.Name):
            list_name = node.iter.id
            list_var = self._get_var_info(list_name)
            if list_var and list_var.type == AmipyType.LIST:
                idx = f"{var}_idx"
                use_ref = (list_var.list_element_type == AmipyType.STRUCT
                           or self._is_engine_object_type(list_var.list_element_type))
                if use_ref:
                    self._line(f"for ({idx} = 0; {idx} < {list_name}_count; {idx}++) {{")
                    self.indent += 1
                    self._line(f"{var} = &{list_name}_items[{idx}];")
                else:
                    self._line(f"for ({idx} = 0; {idx} < {list_name}_count; {idx}++) {{")
                    self.indent += 1
                    self._line(f"{var} = {list_name}_items[{idx}];")
                for stmt in node.body:
                    self._emit_stmt(stmt)
                self.indent -= 1
                self._line("}")
                return

        args = node.iter.args if isinstance(node.iter, ast.Call) else []

        if len(args) == 1:
            end = self._emit_expr(args[0])
            self._line(f"for ({var} = 0; {var} < {end}; {var}++) {{")
        elif len(args) == 2:
            start = self._emit_expr(args[0])
            end = self._emit_expr(args[1])
            self._line(f"for ({var} = {start}; {var} < {end}; {var}++) {{")
        elif len(args) == 3:
            start = self._emit_expr(args[0])
            end = self._emit_expr(args[1])
            step = self._emit_expr(args[2])
            # Need to handle negative steps
            self._line(
                f"for ({var} = {start}; "
                f"({step}) > 0 ? {var} < {end} : {var} > {end}; "
                f"{var} += {step}) {{"
            )
        else:
            raise EmitError("range() requires 1-3 arguments", lineno=node.lineno)

        self.indent += 1
        for stmt in node.body:
            self._emit_stmt(stmt)
        self.indent -= 1
        self._line("}")

    def _emit_return(self, node: ast.Return):
        if node.value is None:
            self._line("return;")
        else:
            val = self._emit_expr(node.value)
            self._line(f"return {val};")

    def _emit_expr(self, node: ast.expr) -> str:
        """Emit an expression and return the C code string."""
        if isinstance(node, ast.Constant):
            return self._emit_constant(node)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return self._emit_field_target(node)
        if isinstance(node, ast.BinOp):
            return self._emit_binop(node)
        if isinstance(node, ast.UnaryOp):
            return self._emit_unaryop(node)
        if isinstance(node, ast.BoolOp):
            return self._emit_boolop(node)
        if isinstance(node, ast.Compare):
            return self._emit_compare(node)
        if isinstance(node, ast.Call):
            return self._emit_call(node)
        if isinstance(node, ast.Subscript):
            return self._emit_subscript(node)
        raise EmitError(
            f"unsupported expression: {type(node).__name__}",
            lineno=getattr(node, "lineno", None),
        )

    def _emit_constant(self, node: ast.Constant) -> str:
        if isinstance(node.value, bool):
            return "TRUE" if node.value else "FALSE"
        if isinstance(node.value, int):
            return str(node.value)
        if isinstance(node.value, float):
            # Ensure float literal has a decimal point
            s = repr(node.value)
            if "." not in s and "e" not in s and "E" not in s:
                s += ".0"
            # Add f suffix for C float
            return s + "f"
        if isinstance(node.value, str):
            # Escape the string for C
            escaped = (
                node.value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'
        raise EmitError(
            f"unsupported constant type: {type(node.value).__name__}",
            lineno=node.lineno,
        )

    def _emit_binop(self, node: ast.BinOp) -> str:
        left = self._emit_expr(node.left)
        right = self._emit_expr(node.right)
        left_type = self._expr_type(node.left)
        right_type = self._expr_type(node.right)

        # Division always yields float
        if isinstance(node.op, ast.Div):
            return f"(float)({left}) / (float)({right})"

        # Floor division, modulo, power — use helper functions
        if isinstance(node.op, (ast.FloorDiv, ast.Pow, ast.Mod)):
            return self._emit_binop_call(
                node.op, left, right, left_type, right_type
            )

        op = self._binop_symbol(node.op)
        return f"({left} {op} {right})"

    def _emit_binop_call(
        self,
        op: ast.operator,
        left: str,
        right: str,
        left_type: AmipyType,
        right_type: AmipyType,
    ) -> str:
        is_float = left_type == AmipyType.FLOAT or right_type == AmipyType.FLOAT

        if isinstance(op, ast.FloorDiv):
            if is_float:
                return f"amipython_floordiv_f({left}, {right})"
            return f"amipython_floordiv({left}, {right})"

        if isinstance(op, ast.Mod):
            if is_float:
                return f"amipython_mod_f({left}, {right})"
            return f"amipython_mod({left}, {right})"

        if isinstance(op, ast.Pow):
            if is_float:
                return f"amipython_fpow({left}, {right})"
            return f"amipython_ipow({left}, {right})"

        raise EmitError(f"unsupported operator: {type(op).__name__}")

    def _binop_symbol(self, op: ast.operator) -> str:
        ops = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
        }
        cls = type(op)
        if cls in ops:
            return ops[cls]
        raise EmitError(f"unsupported operator: {cls.__name__}")

    def _emit_unaryop(self, node: ast.UnaryOp) -> str:
        operand = self._emit_expr(node.operand)
        if isinstance(node.op, ast.Not):
            return f"!({operand})"
        if isinstance(node.op, ast.USub):
            return f"(-{operand})"
        if isinstance(node.op, ast.UAdd):
            return f"(+{operand})"
        raise EmitError(f"unsupported unary op: {type(node.op).__name__}")

    def _emit_boolop(self, node: ast.BoolOp) -> str:
        op = "&&" if isinstance(node.op, ast.And) else "||"
        parts = [self._emit_expr(v) for v in node.values]
        return f"({f' {op} '.join(parts)})"

    def _emit_compare(self, node: ast.Compare) -> str:
        parts = []
        left = self._emit_expr(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self._emit_expr(comparator)
            cmp_op = self._cmpop_symbol(op)
            parts.append(f"({left} {cmp_op} {right})")
            left = right
        if len(parts) == 1:
            return parts[0]
        return "(" + " && ".join(parts) + ")"

    def _cmpop_symbol(self, op: ast.cmpop) -> str:
        ops = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        cls = type(op)
        if cls in ops:
            return ops[cls]
        raise EmitError(f"unsupported comparison: {cls.__name__}")

    def _emit_call(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == "print":
                # print is handled at statement level
                return ""
            if name == "int":
                arg = self._emit_expr(node.args[0])
                return f"(LONG)({arg})"
            if name == "float":
                arg = self._emit_expr(node.args[0])
                return f"(float)({arg})"
            if name == "abs":
                arg = self._emit_expr(node.args[0])
                arg_type = self._expr_type(node.args[0])
                if arg_type == AmipyType.FLOAT:
                    return f"(({arg}) < 0.0f ? -({arg}) : ({arg}))"
                return f"(({arg}) < 0 ? -({arg}) : ({arg}))"
            if name == "len":
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    return f"{arg.id}_count"
                raise EmitError("len() argument must be a variable", lineno=node.lineno)
            # Engine builtin as expression
            if name in BUILTINS and name in self.info.engine_imports:
                builtin = BUILTINS[name]
                args = ", ".join(self._emit_expr(a) for a in node.args)
                return f"{builtin.c_name}({args})"
            # User function call
            args = ", ".join(self._emit_expr(a) for a in node.args)
            return f"{name}({args})"
        if isinstance(node.func, ast.Attribute):
            return self._emit_method_call_expr(node)
        raise EmitError("unsupported call expression", lineno=node.lineno)

    def _emit_method_call_expr(self, call: ast.Call) -> str:
        """Emit method/module function call as expression."""
        attr = call.func
        if not isinstance(attr.value, ast.Name):
            raise EmitError("unsupported method call", lineno=call.lineno)

        obj_name = attr.value.id
        method_name = attr.attr

        # Static method: Shape.grab(...)
        if (obj_name in OBJECT_TYPES
                and obj_name in self.info.engine_imports
                and method_name in OBJECT_TYPES[obj_name].static_methods):
            static = OBJECT_TYPES[obj_name].static_methods[method_name]
            args_strs = [self._emit_arg(a) for a in call.args]
            if method_name == "load":
                args_strs = [_rewrite_asset_path(s) for s in args_strs]
            args = ", ".join(args_strs)
            return f"{static.c_name}({args})"

        if obj_name in self.info.engine_modules:
            mod = MODULE_TYPES[obj_name]
            func = mod.functions[method_name]
            args_strs = self._resolve_method_kwargs(call, func)
            args = ", ".join(args_strs)
            return f"{func.c_name}({args})"

        var = self._get_var_info(obj_name)
        if var is None:
            raise EmitError(f"unknown variable '{obj_name}'", lineno=call.lineno)

        obj_type_info = None
        for ot in OBJECT_TYPES.values():
            if ENGINE_TYPE_MAP.get(ot.python_name) == var.type:
                obj_type_info = ot
                break
        if obj_type_info is None:
            raise EmitError(
                f"'{obj_name}' is not an engine object", lineno=call.lineno
            )

        method = obj_type_info.methods[method_name]
        args_strs = self._resolve_method_kwargs(call, method)
        args = ", ".join(args_strs)
        if args:
            return f"{method.c_name}(&{obj_name}, {args})"
        return f"{method.c_name}(&{obj_name})"

    def _get_var_info(self, name: str) -> VariableInfo | None:
        # Check all local scopes then globals
        for locals_dict in self.info.locals.values():
            if name in locals_dict:
                return locals_dict[name]
        if name in self.info.globals:
            return self.info.globals[name]
        return None

    def _is_engine_object_type(self, t: AmipyType) -> bool:
        return t in (AmipyType.DISPLAY, AmipyType.BITMAP, AmipyType.SHAPE,
                     AmipyType.SPRITE, AmipyType.TILEMAP)

    def _emit_run(self, call: ast.Call):
        """Emit run(update, until=lambda: expr) as a game loop."""
        func_name = call.args[0].id
        until_expr = None
        for kw in call.keywords:
            if kw.arg == "until":
                # Extract expression from lambda body
                until_expr = self._emit_expr(kw.value.body)

        # Detect tilemap mode — use tilemap_process instead of vwait
        tilemap_var = None
        for name, var in self.info.globals.items():
            if var.type == AmipyType.TILEMAP:
                tilemap_var = name
                break

        self._line(f"while (!({until_expr})) {{")
        self.indent += 1
        if tilemap_var:
            self._line(f"amipython_tilemap_process(&{tilemap_var});")
        else:
            self._line("amipython_vwait(1);")
        self._line(f"{func_name}();")
        self.indent -= 1
        self._line("}")

    def _emit_arg(self, node: ast.expr) -> str:
        """Emit an argument, adding & for engine object references."""
        expr_str = self._emit_expr(node)
        t = self._expr_type(node)
        if self._is_engine_object_type(t):
            return f"&{expr_str}"
        return expr_str
