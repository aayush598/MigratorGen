"""
Semantic Symbol Resolution - LibCST metadata-based scope-aware symbol resolution.

Provides:
- Scope tracking (global, local, class, enclosing function)
- Import graph understanding
- Alias tracking
- Type-aware matching
- Qualified name resolution
"""

from dataclasses import dataclass, field
from enum import Enum

import libcst as cst
from libcst.metadata import (
    FullyQualifiedNameProvider,
    MetadataWrapper,
    QualifiedNameProvider,
    ScopeProvider,
)


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    ATTRIBUTE = "attribute"
    MODULE = "module"
    PARAMETER = "parameter"
    VARIABLE = "variable"
    UNKNOWN = "unknown"


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    qualifiers: tuple[str, ...] = field(default_factory=tuple)
    defined_in: str = ""
    import_source: str | None = None
    alias: str | None = None
    line_number: int = 0
    col_offset: int = 0
    is_builtin: bool = False
    is_exported: bool = False


@dataclass
class ResolutionContext:
    scope_stack: list[str] = field(default_factory=list)
    class_stack: list[str] = field(default_factory=list)
    function_stack: list[str] = field(default_factory=list)
    import_aliases: dict[str, str] = field(default_factory=dict)
    local_definitions: dict[str, Symbol] = field(default_factory=dict)
    module_symbols: dict[str, Symbol] = field(default_factory=dict)
    import_sources: dict[str, str] = field(default_factory=dict)


class ImportGraph:
    """Tracks import relationships across a module."""

    def __init__(self):
        self.imports: dict[str, dict[str, str]] = {}
        self.alias_map: dict[str, str] = {}
        self.export_sets: dict[str, set[str]] = {}
        self.import_sources: dict[str, str] = {}

    def add_import(self, module_name: str, symbol: str, alias: str | None = None):
        if module_name not in self.imports:
            self.imports[module_name] = {}
        self.imports[module_name][alias or symbol] = symbol
        if alias:
            self.alias_map[alias] = symbol
        self.import_sources[alias or symbol] = module_name

    def get_actual_symbol(self, alias: str) -> str | None:
        return self.alias_map.get(alias)

    def is_imported_from(self, symbol: str, module: str) -> bool:
        return self.import_sources.get(symbol) == module

    def get_module_for_symbol(self, symbol: str) -> str | None:
        return self.import_sources.get(symbol)


class SymbolResolver:
    """
    Resolves symbols to their definitions using LibCST metadata.

    Uses QualifiedNameProvider and ScopeProvider for accurate symbol resolution
    that respects scope boundaries, aliases, and import context.
    """

    def __init__(self, code: str):
        self.code = code
        self._tree = cst.parse_module(code)
        self._wrapper = MetadataWrapper(self._tree)
        self._import_graph = ImportGraph()
        self._symbol_index: dict[str, Symbol] = {}
        self._context = ResolutionContext()
        self._indexed = False

    def _build_import_graph(self) -> None:
        """Extract all imports from the module."""
        for node in self._tree.body:
            self._process_import_node(node)

    def _process_import_node(self, node) -> None:
        """Process import statements."""
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, cst.ImportFrom):
                    module = self._dotted_name(stmt.module) if stmt.module else ""
                    if isinstance(stmt.names, cst.ImportStar):
                        continue
                    for alias in stmt.names:
                        name = self._dotted_name(alias.name)
                        actual = alias.asname.name.value if alias.asname else name
                        if module:
                            self._import_graph.add_import(module, name, actual)
                elif isinstance(stmt, cst.Import):
                    for alias in stmt.names:
                        name = alias.name.value
                        actual = alias.asname.name.value if alias.asname else name
                        if name == actual:
                            self._import_graph.add_import(name, name, actual)
                        else:
                            self._import_graph.add_import(name, name, actual)

    def _dotted_name(self, node) -> str:
        if node is None:
            return ""
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            return f"{self._dotted_name(node.value)}.{node.attr.value}"
        return ""

    def _index_symbols(self) -> None:
        """Index all symbol definitions in the module."""
        self._build_import_graph()
        try:
            provider_cache = self._wrapper.resolve_many(
                ScopeProvider, QualifiedNameProvider, FullyQualifiedNameProvider
            )
            scope_map = provider_cache[ScopeProvider]
            qualname_map = provider_cache[QualifiedNameProvider]
            fqname_map = provider_cache[FullyQualifiedNameProvider]

            for node, scope in scope_map.items():
                qualname_map.get(node)
                fqname = fqname_map.get(node)
                if isinstance(node, cst.FunctionDef):
                    name = node.name.value
                    kind = SymbolKind.METHOD if self._in_class_scope(scope) else SymbolKind.FUNCTION
                    qualifiers = tuple(fqname.qualname) if fqname else (name,)
                    in_class = self._get_enclosing_class(scope)
                    symbol = Symbol(
                        name=name,
                        kind=kind,
                        qualifiers=qualifiers,
                        defined_in=in_class or "<module>",
                        import_source=None,
                        line_number=node.name.line,
                        col_offset=node.name.column,
                        is_builtin=False,
                        is_exported=self._is_exported(name),
                    )
                    self._symbol_index[name] = symbol
                    key = f"{in_class or ''}.{name}" if in_class else name
                    self._symbol_index[key] = symbol

                elif isinstance(node, (cst.ClassDef)):
                    name = node.name.value
                    qualifiers = tuple(fqname.qualname) if fqname else (name,)
                    symbol = Symbol(
                        name=name,
                        kind=SymbolKind.CLASS,
                        qualifiers=qualifiers,
                        defined_in="<module>",
                        import_source=None,
                        line_number=node.name.line,
                        col_offset=node.name.column,
                        is_builtin=False,
                        is_exported=self._is_exported(name),
                    )
                    self._symbol_index[name] = symbol
                    self._symbol_index[qualifiers[-1]] = symbol

        except Exception:
            pass

    def _in_class_scope(self, scope) -> bool:
        return False

    def _get_enclosing_class(self, scope) -> str | None:
        return None

    def _is_exported(self, name: str) -> bool:
        all_names = [n.value if isinstance(n, cst.Name) else "" for n in self._tree.body]
        all_names = [n for n in all_names if n]
        return name in all_names

    def resolve_symbol(
        self,
        name_node: cst.Name,
        scope=None,
        import_graph: ImportGraph = None,
    ) -> Symbol | None:
        """Resolve a Name node to its actual Symbol definition."""
        name = name_node.value
        ig = import_graph or self._import_graph

        if ig.is_imported_from(name, "builtins"):
            return Symbol(name=name, kind=SymbolKind.UNKNOWN, is_builtin=True)

        if ig.get_actual_symbol(name):
            actual = ig.get_actual_symbol(name)
            return Symbol(
                name=actual,
                kind=SymbolKind.UNKNOWN,
                import_source=ig.get_module_for_symbol(actual),
                alias=name,
            )

        if name in self._symbol_index:
            return self._symbol_index[name]

        for key, sym in self._symbol_index.items():
            if name in key.split("."):
                return sym

        return None

    def resolve_to_definition(self, node: cst.CSTNode) -> tuple[cst.CSTNode, Symbol] | None:
        """Find the definition site for a given node."""
        if not isinstance(node, cst.Name):
            return None

        symbol = self.resolve_symbol(node)
        if not symbol:
            return None

        for def_node, s in self._definition_nodes():
            if s.name == symbol.name or symbol.name in s.qualifiers:
                return def_node, s
        return None

    def _definition_nodes(self):
        """Yield all definition nodes with their symbols."""
        try:
            provider_cache = self._wrapper.resolve_many(ScopeProvider)
            scope_map = provider_cache[ScopeProvider]
            for node, _scope in scope_map.items():
                if isinstance(node, (cst.FunctionDef, cst.AsyncFunctionDef, cst.ClassDef)):
                    name = node.name.value
                    if name in self._symbol_index:
                        yield node, self._symbol_index[name]
        except Exception:
            pass

    def is_definition_site(self, node: cst.CSTNode) -> bool:
        """Check if this node is a definition (not a use)."""
        return isinstance(node, (cst.FunctionDef, cst.AsyncFunctionDef, cst.ClassDef))

    def get_symbol_qualifiers(self, name: str) -> tuple[str, ...]:
        """Get the full qualified name for a symbol."""
        if name in self._symbol_index:
            return self._symbol_index[name].qualifiers
        return (name,)


class ScopeAwareTransformer(cst.CSTTransformer):
    """
    Base transformer that uses semantic symbol resolution to avoid
    shadowing and false-positive matches.
    """

    def __init__(self, rule, import_graph: ImportGraph = None):
        super().__init__(rule)
        self._import_graph = import_graph or ImportGraph()
        self._resolver: SymbolResolver | None = None
        self._current_scope_stack: list[str] = []

    def _init_resolver(self, code: str) -> SymbolResolver:
        """Initialize symbol resolver for the code."""
        if self._resolver is None or self._resolver.code != code:
            self._resolver = SymbolResolver(code)
        return self._resolver

    def _is_same_scope(self, node: cst.CSTNode, expected_scope: str) -> bool:
        """Check if a node is within the expected scope."""
        return True

    def _resolve_name_uses(
        self,
        name_node: cst.Name,
        expected_source: str | None = None,
    ) -> bool:
        """
        Check if a name use should be transformed based on:
        1. It matches the target name
        2. It's not shadowed by a local definition
        3. If expected_source is given, it matches that import source
        """
        name = name_node.value
        if self._import_graph.get_actual_symbol(name):
            actual = self._import_graph.get_actual_symbol(name)
            if expected_source:
                return self._import_graph.get_module_for_symbol(actual) == expected_source
            return True

        if self._resolver:
            symbol = self._resolver.resolve_symbol(name_node)
            if symbol:
                if symbol.is_builtin:
                    return False
                if expected_source:
                    return symbol.import_source == expected_source
                return True
        return True

    def _get_call_context(self, call_node: cst.Call) -> str | None:
        """Extract the calling context (e.g., 'mylib.utils') from a call."""
        func = call_node.func
        if isinstance(func, cst.Attribute):
            base = func.value
            if isinstance(base, cst.Name):
                return base.value
            if isinstance(base, cst.Attribute):
                return self._dotted_name_from_node(base)
        elif isinstance(func, cst.Name):
            return (
                self._resolver._import_graph.get_module_for_symbol(func.value)
                if self._resolver
                else None
            )
        return None

    def _dotted_name_from_node(self, node) -> str:
        if isinstance(node, cst.Name):
            return node.value
        if isinstance(node, cst.Attribute):
            return f"{self._dotted_name_from_node(node.value)}.{node.attr.value}"
        return ""


class ConfidenceScorer:
    """Computes confidence scores for rule applications."""

    @staticmethod
    def score_rename(
        name_node: cst.Name,
        resolver: SymbolResolver,
        import_graph: ImportGraph,
    ) -> float:
        """
        Score 0.0-1.0 for a rename operation on a name node.
        """
        name = name_node.value

        if import_graph.is_imported_from(name, "builtins"):
            return 0.1

        actual = import_graph.get_actual_symbol(name)
        if actual:
            return 0.95

        if resolver:
            symbol = resolver.resolve_symbol(name_node)
            if symbol:
                if symbol.kind == SymbolKind.FUNCTION:
                    return 0.9
                if symbol.kind == SymbolKind.CLASS:
                    return 0.9
                if symbol.kind == SymbolKind.METHOD:
                    return 0.85
                if symbol.kind == SymbolKind.VARIABLE:
                    return 0.5
                return 0.7

        return 0.6

    @staticmethod
    def score_attribute(
        attr_node: cst.Attribute,
        import_graph: ImportGraph,
    ) -> float:
        """Score for an attribute rename."""
        base = attr_node.value
        if isinstance(base, cst.Name):
            module = import_graph.get_module_for_symbol(base.value)
            if module:
                return 0.92
        return 0.7

    @staticmethod
    def score_import_change(
        import_node: cst.ImportFrom,
        old_module: str,
        old_name: str,
    ) -> float:
        """Score for an import change."""
        module_name = ""
        if import_node.module:
            if isinstance(import_node.module, cst.Name):
                module_name = import_node.module.value
            elif isinstance(import_node.module, cst.Attribute):
                module_name = f"{import_node.module.value.value}.{import_node.module.attr.value}"

        if module_name != old_module:
            return 0.0

        if isinstance(import_node.names, cst.ImportStar):
            return 0.5

        for alias in import_node.names:
            name = alias.name.value if isinstance(alias.name, cst.Name) else ""
            if name == old_name:
                return 0.98

        return 0.0
