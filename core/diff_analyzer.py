"""
Git Diff Rule Generator - Automatically generate migration rules from git diffs.

Input: git diff between two versions
Output: migration_rules.json

Pipeline:
1. Parse AST before and after
2. Detect renamed APIs, removed args, moved modules, changed defaults
3. Generate structured rules
"""

import libcst as cst
from libcst.metadata import (
    MetadataWrapper,
    FullyQualifiedNameProvider,
    QualifiedNameProvider,
    ParentNodeProvider,
)
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import re


@dataclass
class APIDiff:
    kind: str
    name: str
    qualifiers: Tuple[str, ...] = field(default_factory=tuple)
    old_def: Optional[str] = None
    new_def: Optional[str] = None
    module: str = ""
    file_path: str = ""
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None


class ASTExtractor:
    """Extracts API definitions from source code AST."""

    def __init__(self, code: str):
        self.code = code
        self._tree = cst.parse_module(code)
        self._wrapper = MetadataWrapper(self._tree)
        self._imports: List[Dict[str, str]] = []
        self._functions: Dict[str, Dict] = {}
        self._classes: Dict[str, Dict] = {}
        self._imports_by_module: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}
        self._parse()

    def _parse(self):
        self._extract_imports()
        self._extract_definitions()

    def _extract_imports(self):
        for node in self._tree.body:
            if isinstance(node, cst.SimpleStatementLine):
                stmt = node.body[0] if node.body else None
                if isinstance(stmt, cst.ImportFrom):
                    module = ""
                    if stmt.module:
                        if isinstance(stmt.module, cst.Name):
                            module = stmt.module.value
                        elif isinstance(stmt.module, cst.Attribute):
                            module = self._dotted_name(stmt.module)
                    if isinstance(stmt.names, cst.ImportStar):
                        continue
                    for alias in stmt.names:
                        name = alias.name.value if isinstance(alias.name, cst.Name) else ""
                        asname = alias.asname.name.value if alias.asname else name
                        self._imports.append({"module": module, "name": name, "alias": asname})
                        if name != asname:
                            self._aliases[asname] = name
                        if module not in self._imports_by_module:
                            self._imports_by_module[module] = []
                        self._imports_by_module[module].append(name)
                elif isinstance(stmt, cst.Import):
                    for alias in stmt.names:
                        name = alias.name.value
                        asname = alias.asname.name.value if alias.asname else name
                        if name == asname:
                            self._imports.append({"module": name, "name": name, "alias": name})
                        else:
                            self._imports.append({"module": name, "name": name, "alias": asname})
                            if name not in self._imports_by_module:
                                self._imports_by_module[name] = []
                            self._imports_by_module[name].append(name)

    def _extract_definitions(self):
        for node in self._tree.body:
            if isinstance(node, cst.FunctionDef):
                self._process_function(node)
            elif isinstance(node, cst.ClassDef):
                self._process_class(node)

    def _process_function(self, node: cst.FunctionDef):
        try:
            provider_cache = self._wrapper.resolve_many(
                FullyQualifiedNameProvider, QualifiedNameProvider
            )
            fqname = provider_cache[FullyQualifiedNameProvider].get(node)
            qualname = fqname.qualname if fqname else (node.name.value,)
        except Exception:
            qualname = (node.name.value,)

        params = node.params
        param_info = []
        for p in params.params:
            name = p.name.value
            default_val = None
            if p.default:
                default_val = self._get_expr_text(p.default)
            param_info.append({"name": name, "default": default_val})

        self._functions[node.name.value] = {
            "qualifiers": qualname,
            "params": param_info,
            "decorators": [self._get_decorator_name(d) for d in node.decorators if d],
        }

    def _process_class(self, node: cst.ClassDef):
        try:
            provider_cache = self._wrapper.resolve_many(FullyQualifiedNameProvider)
            fqname = provider_cache[FullyQualifiedNameProvider].get(node)
            qualname = fqname.qualname if fqname else (node.name.value,)
        except Exception:
            qualname = (node.name.value,)

        methods = []
        for item in node.body.body:
            if isinstance(item, cst.FunctionDef):
                mname = item.name.value
                params = item.params
                param_info = []
                for p in params.params:
                    param_info.append({"name": p.name.value})
                methods.append({"name": mname, "params": param_info})

        self._classes[node.name.value] = {
            "qualifiers": qualname,
            "methods": methods,
        }

    def _dotted_name(self, node) -> str:
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            return f"{self._dotted_name(node.value)}.{node.attr.value}"
        return ""

    def _get_expr_text(self, expr) -> str:
        if hasattr(expr, "default") and expr.default:
            try:
                return cst.parse_expression(self._get_source_slice(expr)).code
            except Exception:
                return ""
        return ""

    def _get_source_slice(self, node) -> cst.BaseStatement:
        return node

    def _get_decorator_name(self, dec) -> str:
        if isinstance(dec.decorator, cst.Name):
            return dec.decorator.value
        if isinstance(dec.decorator, cst.Attribute):
            return self._dotted_name(dec.decorator)
        return ""

    def get_functions(self) -> Dict[str, Dict]:
        return self._functions

    def get_classes(self) -> Dict[str, Dict]:
        return self._classes

    def get_imports(self) -> List[Dict[str, str]]:
        return self._imports

    def get_imports_by_module(self) -> Dict[str, List[str]]:
        return self._imports_by_module


class GitDiffAnalyzer:
    """
    Analyzes git diff between two versions and generates migration rules.

    Compares ASTs before and after to detect:
    - Renamed functions/classes
    - Added/removed arguments
    - Changed default values
    - Moved modules
    - Changed decorators
    - Removed functions/classes
    """

    def __init__(self, old_code: str, new_code: str, module_prefix: str = ""):
        self.old_code = old_code
        self.new_code = new_code
        self.module_prefix = module_prefix
        self.old_ast = ASTExtractor(old_code)
        self.new_ast = ASTExtractor(new_code)
        self.rules: List[Dict[str, Any]] = []
        self._rule_counter = 1
        self._potential_rename_pairs: List[Tuple[str, str]] = []

    def analyze(self) -> List[Dict[str, Any]]:
        """Main analysis entry point."""
        self._detect_renames()
        self._detect_signature_changes()
        self._detect_import_changes()
        self._detect_decorator_changes()
        self._detect_removals()
        return self.rules

    def _make_rule_id(self, change_type: str) -> str:
        rid = f"AUTO-{self._rule_counter:03d}"
        self._rule_counter += 1
        return rid

    def _detect_renames(self):
        """Detect renamed functions and classes."""
        old_funcs = set(self.old_ast.get_functions().keys())
        new_funcs = set(self.new_ast.get_functions().keys())

        removed_funcs = old_funcs - new_funcs
        added_funcs = new_funcs - old_funcs

        potential_renames = []
        for removed in removed_funcs:
            old_info = self.old_ast.get_functions()[removed]
            for added in added_funcs:
                new_info = self.new_ast.get_functions()[added]
                if self._similar_signatures(
                    old_info.get("params", []), new_info.get("params", [])
                ):
                    potential_renames.append((removed, added, old_info, new_info))

        for old_name, new_name, old_info, new_info in potential_renames:
            if len(old_name) <= 3 or len(new_name) <= 3:
                continue
            old_qual = old_info.get("qualifiers", ())
            new_qual = new_info.get("qualifiers", ())
            self._potential_rename_pairs.append((old_name, new_name))
            self.rules.append({
                "id": self._make_rule_id("rename_function"),
                "change_type": "rename_function",
                "version_introduced": "X.Y.Z",
                "description": f"Renamed function {old_name} to {new_name}",
                "old_name": old_name,
                "new_name": new_name,
                "tags": ["auto-generated", "rename"],
            })

        old_classes = set(self.old_ast.get_classes().keys())
        new_classes = set(self.new_ast.get_classes().keys())

        removed_classes = old_classes - new_classes
        added_classes = new_classes - old_classes

        for removed in removed_classes:
            old_info = self.old_ast.get_classes()[removed]
            for added in added_classes:
                new_info = self.new_ast.get_classes()[added]
                if len(old_info.get("methods", [])) == len(new_info.get("methods", [])):
                    self._potential_rename_pairs.append((removed, added))
                    self.rules.append({
                        "id": self._make_rule_id("rename_class"),
                        "change_type": "rename_class",
                        "version_introduced": "X.Y.Z",
                        "description": f"Renamed class {removed} to {added}",
                        "old_name": removed,
                        "new_name": added,
                        "tags": ["auto-generated", "rename"],
                    })

    def _detect_signature_changes(self):
        """Detect added, removed, or reordered function arguments."""
        old_funcs = self.old_ast.get_functions()
        new_funcs = self.new_ast.get_functions()

        common = set(old_funcs.keys()) & set(new_funcs.keys())

        for fname in common:
            old_params = {p["name"]: p for p in old_funcs[fname].get("params", [])}
            new_params = {p["name"]: p for p in new_funcs[fname].get("params", [])}

            old_names = set(old_params.keys())
            new_names = set(new_params.keys())

            added_args = new_names - old_names
            removed_args = old_names - new_names
            changed_defaults = []

            for pname in old_names & new_names:
                old_def = old_params[pname].get("default")
                new_def = new_params[pname].get("default")
                if old_def != new_def:
                    changed_defaults.append((pname, old_def, new_def))

            for arg in added_args:
                new_def = new_params[arg].get("default", "None")
                self.rules.append({
                    "id": self._make_rule_id("add_argument"),
                    "change_type": "add_argument",
                    "version_introduced": "X.Y.Z",
                    "description": f"Added argument '{arg}' to {fname}()",
                    "function_name": fname,
                    "argument_name": arg,
                    "default_value": new_def,
                    "tags": ["auto-generated", "signature-change"],
                })

            for arg in removed_args:
                self.rules.append({
                    "id": self._make_rule_id("remove_argument"),
                    "change_type": "remove_argument",
                    "version_introduced": "X.Y.Z",
                    "description": f"Removed argument '{arg}' from {fname}()",
                    "function_name": fname,
                    "argument_name": arg,
                    "tags": ["auto-generated", "signature-change"],
                })

            for pname, old_def, new_def in changed_defaults:
                if old_def and new_def:
                    self.rules.append({
                        "id": self._make_rule_id("change_argument_default"),
                        "change_type": "change_argument_default",
                        "version_introduced": "X.Y.Z",
                        "description": f"Changed default for '{pname}' in {fname}() from {old_def} to {new_def}",
                        "argument_name": pname,
                        "default_value": new_def,
                        "function_name": fname,
                        "tags": ["auto-generated", "signature-change"],
                    })

            if old_names != new_names:
                reordered = self._detect_reordered_params(
                    list(old_params.keys()), list(new_params.keys())
                )
                if reordered:
                    self.rules.append({
                        "id": self._make_rule_id("reorder_arguments"),
                        "change_type": "reorder_arguments",
                        "version_introduced": "X.Y.Z",
                        "description": f"Reordered parameters of {fname}()",
                        "function_name": fname,
                        "new_order": reordered,
                        "tags": ["auto-generated", "signature-change"],
                    })

    def _detect_reordered_params(
        self, old_names: List[str], new_names: List[str]
    ) -> Optional[List[str]]:
        common = list(set(old_names) & set(new_names))
        if len(common) < 2:
            return None

        old_indices = {n: i for i, n in enumerate(old_names)}
        new_indices = {n: i for i, n in enumerate(new_names)}

        common_old = [n for n in old_names if n in common]
        common_new = [n for n in new_names if n in common]

        reorder_count = sum(
            1 for i in range(len(common_old) - 1)
            if old_indices.get(common_old[i], 0) > old_indices.get(common_old[i + 1], 0)
        )

        if reorder_count > 0:
            return common_new

        return None

    def _detect_import_changes(self):
        """Detect changed import paths."""
        old_imp = self.old_ast.get_imports_by_module()
        new_imp = self.new_ast.get_imports_by_module()

        old_modules = set(old_imp.keys())
        new_modules = set(new_imp.keys())

        moved_symbols = []
        for sym_set in old_modules & new_modules:
            pass

        for sym in self.old_ast.get_imports():
            old_mod = sym["module"]
            sym_name = sym["name"]
            for sym2 in self.new_ast.get_imports():
                if sym2["name"] == sym_name and sym2["module"] != old_mod:
                    moved_symbols.append((sym_name, old_mod, sym2["module"]))

        for sym_name, old_mod, new_mod in moved_symbols:
            if old_mod and new_mod:
                self.rules.append({
                    "id": self._make_rule_id("move_to_module"),
                    "change_type": "move_to_module",
                    "version_introduced": "X.Y.Z",
                    "description": f"Moved {sym_name} from {old_mod} to {new_mod}",
                    "old_name": sym_name,
                    "source_module": old_mod,
                    "target_module": new_mod,
                    "tags": ["auto-generated", "import-change"],
                })

    def _detect_decorator_changes(self):
        """Detect added or removed decorators."""
        old_funcs = self.old_ast.get_functions()
        new_funcs = self.new_ast.get_functions()

        common = set(old_funcs.keys()) & set(new_funcs.keys())

        for fname in common:
            old_decs = set(old_funcs[fname].get("decorators", []))
            new_decs = set(new_funcs[fname].get("decorators", []))

            added_decs = new_decs - old_decs
            removed_decs = old_decs - new_decs

            for dec in added_decs:
                self.rules.append({
                    "id": self._make_rule_id("add_decorator"),
                    "change_type": "add_decorator",
                    "version_introduced": "X.Y.Z",
                    "description": f"Added @{dec} to {fname}()",
                    "function_name": fname,
                    "decorator_name": dec,
                    "tags": ["auto-generated", "decorator-change"],
                })

            for dec in removed_decs:
                self.rules.append({
                    "id": self._make_rule_id("remove_decorator"),
                    "change_type": "remove_decorator",
                    "version_introduced": "X.Y.Z",
                    "description": f"Removed @{dec} from {fname}()",
                    "function_name": fname,
                    "decorator_name": dec,
                    "tags": ["auto-generated", "decorator-change"],
                })

    def _detect_removals(self):
        """Detect removed functions and classes."""
        old_funcs = set(self.old_ast.get_functions().keys())
        new_funcs = set(self.new_ast.get_functions().keys())
        removed_funcs = old_funcs - new_funcs

        renamed_old = {pair[0] for pair in self._potential_rename_pairs}
        for removed in removed_funcs - renamed_old:
            self.rules.append({
                "id": self._make_rule_id("remove_function"),
                "change_type": "remove_function",
                "version_introduced": "X.Y.Z",
                "description": f"Removed function {removed}()",
                "old_name": removed,
                "safety": "risky",
                "reversible": False,
                "tags": ["auto-generated", "removal"],
            })

        old_classes = set(self.old_ast.get_classes().keys())
        new_classes = set(self.new_ast.get_classes().keys())

        renamed_class_old = {pair[0] for pair in self._potential_rename_pairs}
        for removed in old_classes - new_classes - renamed_class_old:
            self.rules.append({
                "id": self._make_rule_id("remove_class"),
                "change_type": "remove_class",
                "version_introduced": "X.Y.Z",
                "description": f"Removed class {removed}",
                "old_name": removed,
                "safety": "risky",
                "reversible": False,
                "tags": ["auto-generated", "removal"],
            })

    def _similar_signatures(
        self, old_params: List[Dict], new_params: List[Dict]
    ) -> bool:
        if abs(len(old_params) - len(new_params)) > 2:
            return False

        old_names = {p["name"] for p in old_params}
        new_names = {p["name"] for p in new_params}
        common = old_names & new_names

        if len(common) == 0:
            return len(old_params) == len(new_params)

        overlap_ratio = len(common) / max(len(old_names), len(new_names))
        return overlap_ratio >= 0.5


class ChangelogToRulesConverter:
    """
    Converts changelog markdown text into migration rules using pattern matching.
    """

    PATTERNS = [
        (
            r"renamed\s+(\w+)\s*\(\)\s+to\s+(\w+)\s*\(\)",
            lambda m: {
                "change_type": "rename_function",
                "old_name": m.group(1),
                "new_name": m.group(2),
            },
        ),
        (
            r"renamed\s+(\w+)\s+to\s+(\w+)",
            lambda m: {
                "change_type": "rename_function",
                "old_name": m.group(1),
                "new_name": m.group(2),
            },
        ),
        (
            r"moved\s+(\w+)\s+from\s+([\w.]+)\s+to\s+([\w.]+)",
            lambda m: {
                "change_type": "move_to_module",
                "old_name": m.group(1),
                "source_module": m.group(2),
                "target_module": m.group(3),
            },
        ),
        (
            r"moved\s+([\w.]+)\s+to\s+([\w.]+)",
            lambda m: {
                "change_type": "move_to_module",
                "source_module": m.group(1),
                "target_module": m.group(2),
            },
        ),
        (
            r"added\s+(?:argument\s+)?['\"]?(\w+)['\"]?\s+(?:to\s+)?(\w+)\s*\(\)",
            lambda m: {
                "change_type": "add_argument",
                "argument_name": m.group(1),
                "function_name": m.group(2),
            },
        ),
        (
            r"removed\s+(?:argument\s+)?['\"]?(\w+)['\"]?\s+from\s+(\w+)\s*\(\)",
            lambda m: {
                "change_type": "remove_argument",
                "argument_name": m.group(1),
                "function_name": m.group(2),
            },
        ),
        (
            r"changed\s+default\s+(?:of\s+)?(\w+)\s+in\s+(\w+)\s*\(\)",
            lambda m: {
                "change_type": "change_argument_default",
                "argument_name": m.group(1),
                "function_name": m.group(2),
            },
        ),
        (
            r"added\s+@(\w+)\s+to\s+(\w+)",
            lambda m: {
                "change_type": "add_decorator",
                "decorator_name": m.group(1),
                "function_name": m.group(2),
            },
        ),
        (
            r"removed\s+@(\w+)\s+from\s+(\w+)",
            lambda m: {
                "change_type": "remove_decorator",
                "decorator_name": m.group(1),
                "function_name": m.group(2),
            },
        ),
    ]

    def __init__(self, changelog_text: str, version: str = "X.Y.Z"):
        self.changelog_text = changelog_text
        self.version = version
        self.rules: List[Dict] = []
        self._rule_counter = 1

    def convert(self) -> List[Dict]:
        """Convert changelog text to rules."""
        lines = self.changelog_text.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("- "):
                line = line.lstrip("- ").strip()

            if not line:
                continue

            for pattern, builder in self.PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    rule_data = builder(match)
                    rule_data["id"] = f"CHANGELOG-{self._rule_counter:03d}"
                    rule_data["version_introduced"] = self.version
                    rule_data["description"] = line
                    rule_data["tags"] = ["auto-generated", "changelog"]
                    self._rule_counter += 1
                    self.rules.append(rule_data)
                    break

        return self.rules


def generate_from_git_diff(old_code: str, new_code: str, module: str = "") -> List[Dict]:
    """Main entry point: generate migration rules from git diff code."""
    analyzer = GitDiffAnalyzer(old_code, new_code, module)
    return analyzer.analyze()


def generate_from_changelog(text: str, version: str = "X.Y.Z") -> List[Dict]:
    """Main entry point: convert changelog text to migration rules."""
    converter = ChangelogToRulesConverter(text, version)
    return converter.convert()


def export_rules(rules: List[Dict], library: str, output: Path = None) -> str:
    """Export rules as JSON."""
    data = {
        "library": library,
        "schema_version": "1.0",
        "versions": [
            {
                "version": "X.Y.Z",
                "release_date": "",
                "notes": "Auto-generated from diff analysis",
                "rules": rules,
            }
        ],
    }
    json_str = json.dumps(data, indent=2)
    if output:
        output.write_text(json_str, encoding="utf-8")
    return json_str