"""Import discovery and module resolution."""

from __future__ import annotations

import ast
import importlib.util
import sys
from collections import deque
from pathlib import Path
from typing import Callable, Optional

from pydistill.models import EntryPoint, ImportInfo


class ImportCollector(ast.NodeVisitor):
    """AST visitor that collects all import statements from a module."""

    def __init__(self, base_package: str):
        self.base_package = base_package
        self.imports: list[ImportInfo] = []

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        for alias in node.names:
            if alias.name.startswith(self.base_package):
                self.imports.append(
                    ImportInfo(
                        module=alias.name,
                        names=[],
                        is_from_import=False,
                    ),
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        if node.module is None:
            # Relative import with no module (from . import X)
            module = ""
        else:
            module = node.module

        # For relative imports, we'll resolve them later
        # For absolute imports, check if they're in our base package
        if node.level > 0 or module.startswith(self.base_package):
            names = [alias.name for alias in node.names]
            self.imports.append(
                ImportInfo(
                    module=module,
                    names=names,
                    is_from_import=True,
                    level=node.level,
                ),
            )
        self.generic_visit(node)


class ModuleResolver:
    """Resolves module names to file paths."""

    def __init__(
        self,
        source_roots: list[Path] | None = None,
        filesystem_only: bool = False,
    ):
        self.source_roots = source_roots or [Path.cwd()] + [
            Path(p) for p in sys.path if p
        ]
        self.filesystem_only = filesystem_only
        self._cache: dict[str, Path] = {}

    def resolve(self, module_name: str) -> Optional[Path]:
        """Resolve a module name to its source file path."""
        if module_name in self._cache:
            return self._cache[module_name]

        # Try using importlib (unless filesystem_only is set)
        if not self.filesystem_only:
            try:
                spec = importlib.util.find_spec(module_name)
                if spec and spec.origin and spec.origin != "built-in":
                    path = Path(spec.origin)
                    if path.exists() and path.suffix == ".py":
                        self._cache[module_name] = path
                        return path
            except (ModuleNotFoundError, ValueError, AttributeError):
                pass

        # Fallback: search source roots (or primary method when filesystem_only)
        module_parts = module_name.split(".")
        for root in self.source_roots:
            # Try as a module file
            module_path = root / "/".join(module_parts[:-1]) / f"{module_parts[-1]}.py"
            if module_path.exists():
                self._cache[module_name] = module_path
                return module_path

            # Try as a package __init__.py
            package_path = root / "/".join(module_parts) / "__init__.py"
            if package_path.exists():
                self._cache[module_name] = package_path
                return package_path

        return None


def resolve_relative_import(current_module: str, import_module: str, level: int) -> str:
    """Resolve a relative import to an absolute module path."""
    if level == 0:
        return import_module

    parts = current_module.split(".")
    parent_parts = parts[:-level] if level <= len(parts) else []

    if import_module:
        return ".".join(parent_parts + [import_module])
    return ".".join(parent_parts)


def collect_imports_from_source(
    source: str,
    module_name: str,
    base_package: str,
    resolver: ModuleResolver,
) -> list[str]:
    """Parse source code and return all local module imports."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    collector = ImportCollector(base_package)
    collector.visit(tree)

    resolved_modules = []
    for imp in collector.imports:
        if imp.level > 0:
            resolved = resolve_relative_import(module_name, imp.module, imp.level)
        else:
            resolved = imp.module

        if resolved.startswith(base_package):
            resolved_modules.append(resolved)

            # For 'from X import Y', Y might be a submodule
            if imp.is_from_import:
                for name in imp.names:
                    submodule = f"{resolved}.{name}"
                    if resolver.resolve(submodule):
                        resolved_modules.append(submodule)

    return resolved_modules


def discover_modules(
    entry_points: list[EntryPoint],
    base_package: str,
    resolver: ModuleResolver,
    on_discover: Callable[[str, Path], None] | None = None,
    on_warning: Callable[[str], None] | None = None,
) -> set[str]:
    """BFS through imports starting from entry points."""
    queue = deque(ep.module for ep in entry_points)
    discovered: set[str] = set()

    while queue:
        module_name = queue.popleft()

        if module_name in discovered:
            continue

        source_path = resolver.resolve(module_name)
        if not source_path:
            if on_warning:
                on_warning(f"Could not resolve module: {module_name}")
            continue

        discovered.add(module_name)
        if on_discover:
            on_discover(module_name, source_path)

        # Find all imports in this module
        try:
            source = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            if on_warning:
                on_warning(f"Could not read {source_path}: {e}")
            continue

        imports = collect_imports_from_source(
            source, module_name, base_package, resolver
        )
        for imp in imports:
            if imp not in discovered:
                queue.append(imp)

    return discovered
