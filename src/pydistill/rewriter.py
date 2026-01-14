"""AST-based import rewriting."""

from __future__ import annotations

import ast


class ImportRewriter(ast.NodeTransformer):
    """AST transformer that rewrites imports from base_package to output_package."""

    def __init__(self, base_package: str, output_package: str):
        self.base_package = base_package
        self.output_package = output_package

    def _rewrite_module(self, module: str) -> str:
        """Rewrite a module path from base to output package."""
        if module.startswith(self.base_package):
            return self.output_package + module[len(self.base_package) :]
        return module

    def visit_Import(self, node: ast.Import) -> ast.Import:
        """Rewrite 'import X' statements."""
        new_names = []
        for alias in node.names:
            new_name = self._rewrite_module(alias.name)
            new_alias = ast.alias(
                name=new_name,
                asname=alias.asname,
            )
            new_names.append(new_alias)
        node.names = new_names
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """Rewrite 'from X import Y' statements."""
        if node.level > 0:
            # Keep relative imports as-is (they're relative to the new package)
            return node

        if node.module and node.module.startswith(self.base_package):
            node.module = self._rewrite_module(node.module)

        return node


def rewrite_imports(source: str, base_package: str, output_package: str) -> str:
    """Rewrite all imports in source code from base_package to output_package."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    rewriter = ImportRewriter(base_package, output_package)
    new_tree = rewriter.visit(tree)
    ast.fix_missing_locations(new_tree)

    return ast.unparse(new_tree)
