"""Tests for edge cases in pydistill.

These tests cover scenarios that may occur in real-world codebases
but aren't covered by the basic test suite.
"""

import ast
from pathlib import Path
from textwrap import dedent

from pydistill.discovery import (
    ImportCollector,
    ModuleResolver,
    collect_imports_from_source,
    discover_modules,
)
from pydistill.extractor import ModuleExtractor
from pydistill.models import EntryPoint
from pydistill.rewriter import rewrite_imports


class TestStarImports:
    """Tests for 'from x import *' handling."""

    def test_collector_handles_star_import(self):
        """Star imports should be collected with '*' as the name."""
        source = "from myapp.models import *"
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == "myapp.models"
        assert collector.imports[0].names == ["*"]

    def test_rewriter_handles_star_import(self):
        """Star imports should have their module path rewritten."""
        source = "from myapp.models import *"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import *" in result

    def test_star_import_with_relative(self):
        """Relative star imports should be preserved."""
        source = "from .models import *"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from .models import *" in result


class TestTypeCheckingImports:
    """Tests for TYPE_CHECKING block imports."""

    def test_discovers_imports_inside_if_type_checking(self):
        """Imports inside TYPE_CHECKING blocks should be discovered."""
        source = dedent("""
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from myapp.models import HeavyModel
                from myapp.utils import Helper
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        modules = [imp.module for imp in collector.imports]
        assert "myapp.models" in modules
        assert "myapp.utils" in modules

    def test_rewrites_imports_inside_if_type_checking(self):
        """Imports inside TYPE_CHECKING should be rewritten."""
        source = dedent("""
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from myapp.models import Model
        """)
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import Model" in result

    def test_mixed_runtime_and_type_checking_imports(self):
        """Both runtime and TYPE_CHECKING imports should be handled."""
        source = dedent("""
            from typing import TYPE_CHECKING
            from myapp.base import Base

            if TYPE_CHECKING:
                from myapp.models import Model
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        modules = [imp.module for imp in collector.imports]
        assert "myapp.base" in modules
        assert "myapp.models" in modules


class TestCircularImports:
    """Tests for circular import handling."""

    def test_circular_import_discovery(self, tmp_path: Path):
        """Circular imports should be handled without infinite loops."""
        # Create two modules that import each other
        pkg = tmp_path / "circular_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        (pkg / "module_a.py").write_text(
            dedent("""
            from circular_pkg.module_b import B

            class A:
                pass
        """),
        )

        (pkg / "module_b.py").write_text(
            dedent("""
            from circular_pkg.module_a import A

            class B:
                pass
        """),
        )

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("circular_pkg.module_a:A")]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="circular_pkg",
            resolver=resolver,
        )

        # Both modules should be discovered
        assert "circular_pkg.module_a" in discovered
        assert "circular_pkg.module_b" in discovered

    def test_circular_import_extraction(self, tmp_path: Path):
        """Circular imports should extract correctly."""
        # Setup
        src = tmp_path / "src"
        pkg = src / "circular_pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")

        (pkg / "module_a.py").write_text(
            dedent("""
            from circular_pkg.module_b import B

            class A:
                b: "B"
        """),
        )

        (pkg / "module_b.py").write_text(
            dedent("""
            from circular_pkg.module_a import A

            class B:
                a: "A"
        """),
        )

        output_dir = tmp_path / "output"

        extractor = ModuleExtractor(
            base_package="circular_pkg",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[src],
            filesystem_only=True,
            quiet=True,
        )

        entry_points = [EntryPoint.parse("circular_pkg.module_a:A")]
        result = extractor.extract(entry_points)

        assert result.success
        assert len(result.modules_extracted) == 2

        # Verify imports were rewritten in both files
        module_a = (output_dir / "module_a.py").read_text()
        module_b = (output_dir / "module_b.py").read_text()
        assert "from extracted.module_b import B" in module_a
        assert "from extracted.module_a import A" in module_b


class TestImportsInsideFunctions:
    """Tests for imports inside function/method bodies."""

    def test_discovers_imports_inside_function(self):
        """Imports inside functions should be discovered."""
        source = dedent("""
            def get_model():
                from myapp.models import LazyModel
                return LazyModel
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == "myapp.models"

    def test_discovers_imports_inside_method(self):
        """Imports inside class methods should be discovered."""
        source = dedent("""
            class Factory:
                def create(self):
                    from myapp.models import Model
                    return Model()
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == "myapp.models"

    def test_discovers_imports_inside_nested_function(self):
        """Imports inside nested functions should be discovered."""
        source = dedent("""
            def outer():
                def inner():
                    from myapp.models import Model
                    return Model
                return inner
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == "myapp.models"

    def test_rewrites_imports_inside_function(self):
        """Imports inside functions should be rewritten."""
        source = dedent("""
            def get_model():
                from myapp.models import Model
                return Model
        """)
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import Model" in result


class TestStringAnnotations:
    """Tests for string annotations (PEP 563)."""

    def test_future_annotations_import_preserved(self):
        """The __future__ import should be preserved."""
        source = dedent("""
            from __future__ import annotations
            from myapp.models import Model
        """)
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from __future__ import annotations" in result
        assert "from extracted.models import Model" in result

    def test_string_annotations_not_traced_as_imports(self):
        """String annotations should not be traced as imports."""
        source = dedent("""
            from __future__ import annotations

            class User:
                # Note: NotImported is a string, not an actual import
                related: "NotImported"
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        # Only __future__ import, nothing from myapp
        assert len(collector.imports) == 0


class TestNamespacePackages:
    """Tests for PEP 420 namespace packages (no __init__.py)."""

    def test_resolver_finds_namespace_package_module(self, tmp_path: Path):
        """Modules in namespace packages should be resolved."""
        # Create namespace package (no __init__.py)
        ns_pkg = tmp_path / "namespace_pkg" / "subpkg"
        ns_pkg.mkdir(parents=True)
        # Note: no __init__.py files

        (ns_pkg / "models.py").write_text("class Model: pass")

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        path = resolver.resolve("namespace_pkg.subpkg.models")

        assert path is not None
        assert path.name == "models.py"

    def test_namespace_package_discovery(self, tmp_path: Path):
        """Discovery should work with namespace packages."""
        # Create namespace package structure
        pkg = tmp_path / "nspkg" / "sub"
        pkg.mkdir(parents=True)
        # No __init__.py - this is a namespace package

        (pkg / "models.py").write_text(
            dedent("""
            from nspkg.sub.utils import helper

            class Model:
                pass
        """),
        )

        (pkg / "utils.py").write_text(
            dedent("""
            def helper():
                pass
        """),
        )

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("nspkg.sub.models:Model")]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="nspkg",
            resolver=resolver,
        )

        assert "nspkg.sub.models" in discovered
        assert "nspkg.sub.utils" in discovered


class TestInitPyWithCode:
    """Tests for __init__.py files that contain actual code."""

    def test_init_with_imports_discovered(self, tmp_path: Path):
        """Imports in __init__.py should be discovered."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()

        # __init__.py with re-exports
        (pkg / "__init__.py").write_text(
            dedent("""
            from mypkg.models import Model
            from mypkg.utils import helper

            __all__ = ["Model", "helper"]
        """),
        )

        (pkg / "models.py").write_text("class Model: pass")
        (pkg / "utils.py").write_text("def helper(): pass")

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("mypkg:Model")]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="mypkg",
            resolver=resolver,
        )

        # The __init__.py (mypkg) and its imports should be discovered
        assert "mypkg" in discovered
        assert "mypkg.models" in discovered
        assert "mypkg.utils" in discovered

    def test_init_code_extracted_correctly(self, tmp_path: Path):
        """__init__.py code should be extracted and rewritten."""
        src = tmp_path / "src"
        pkg = src / "mypkg"
        pkg.mkdir(parents=True)

        (pkg / "__init__.py").write_text(
            dedent("""
            from mypkg.models import Model

            __all__ = ["Model"]
        """),
        )

        (pkg / "models.py").write_text("class Model: pass")

        output_dir = tmp_path / "output"

        extractor = ModuleExtractor(
            base_package="mypkg",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[src],
            filesystem_only=True,
            quiet=True,
        )

        entry_points = [EntryPoint.parse("mypkg:Model")]
        result = extractor.extract(entry_points)

        assert result.success

        # The root __init__.py should contain the rewritten imports
        init_content = (output_dir / "__init__.py").read_text()
        assert "from extracted.models import Model" in init_content


class TestConditionalImports:
    """Tests for imports inside conditional blocks."""

    def test_discovers_imports_in_try_except(self):
        """Imports inside try/except should be discovered."""
        source = dedent("""
            try:
                from myapp.fast import FastImpl
            except ImportError:
                from myapp.slow import SlowImpl
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        modules = [imp.module for imp in collector.imports]
        assert "myapp.fast" in modules
        assert "myapp.slow" in modules

    def test_discovers_imports_in_if_else(self):
        """Imports inside if/else should be discovered."""
        source = dedent("""
            import sys
            if sys.version_info >= (3, 11):
                from myapp.new_impl import Feature
            else:
                from myapp.compat import Feature
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        modules = [imp.module for imp in collector.imports]
        assert "myapp.new_impl" in modules
        assert "myapp.compat" in modules


class TestEncodingHandling:
    """Tests for file encoding handling."""

    def test_utf8_source_file(self, tmp_path: Path):
        """UTF-8 encoded files with special characters should work."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        # Source with UTF-8 characters
        (pkg / "models.py").write_text(
            dedent("""
                # Ümläut and émojis: 🎉
                class Modèle:
                    '''Döcstring with spëcial chäräcters'''
                    name: str = "défault"
            """),
            encoding="utf-8",
        )

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("mypkg.models:Modèle")]

        # Should not raise
        discovered = discover_modules(
            entry_points=entry_points,
            base_package="mypkg",
            resolver=resolver,
        )

        assert "mypkg.models" in discovered

    def test_non_utf8_file_warns(self, tmp_path: Path):
        """Non-UTF-8 files should produce warnings, not crash."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        # Write with Latin-1 encoding (incompatible bytes for UTF-8)
        (pkg / "models.py").write_bytes(
            b"# Latin-1: caf\xe9\nclass Model: pass",
        )

        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("mypkg.models:Model")]

        warnings = []
        discover_modules(
            entry_points=entry_points,
            base_package="mypkg",
            resolver=resolver,
            on_warning=lambda msg: warnings.append(msg),
        )

        # Should have warned about the file, not crashed
        assert len(warnings) > 0
        assert any("Could not read" in w for w in warnings)


class TestEntryPointValidation:
    """Tests for entry point handling edge cases."""

    def test_duplicate_entry_points(self, tmp_path: Path):
        """Duplicate entry points should not cause issues."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "models.py").write_text("class Model: pass")

        resolver = ModuleResolver([tmp_path], filesystem_only=True)

        # Same module specified twice via different class names
        entry_points = [
            EntryPoint.parse("mypkg.models:Model"),
            EntryPoint.parse("mypkg.models:AnotherClass"),
        ]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="mypkg",
            resolver=resolver,
        )

        # Module should only appear once
        assert discovered == {"mypkg.models"}

    def test_nonexistent_module_warns(self, tmp_path: Path):
        """Non-existent modules should produce warnings."""
        resolver = ModuleResolver([tmp_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("nonexistent.module:Class")]

        warnings = []
        discovered = discover_modules(
            entry_points=entry_points,
            base_package="nonexistent",
            resolver=resolver,
            on_warning=lambda msg: warnings.append(msg),
        )

        assert len(discovered) == 0
        assert any("Could not resolve" in w for w in warnings)


class TestRelativeImportEdgeCases:
    """Tests for edge cases in relative import handling."""

    def test_deep_relative_import(self):
        """Multi-level relative imports should be resolved."""
        source = "from ...models import Model"
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].level == 3

    def test_relative_import_from_dot_only(self):
        """'from . import X' should be handled."""
        source = "from . import submodule"
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == ""
        assert collector.imports[0].names == ["submodule"]
        assert collector.imports[0].level == 1


class TestMultipleImportStyles:
    """Tests for various import statement styles."""

    def test_multiple_names_in_from_import(self):
        """Multiple names in one import should all be captured."""
        source = "from myapp.models import User, Order, Product"
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].names == ["User", "Order", "Product"]

    def test_multiple_modules_in_import(self):
        """Multiple modules in one import should all be captured."""
        source = "import myapp.models, myapp.utils, myapp.views"
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 3

    def test_multiline_import(self):
        """Multi-line imports should be handled."""
        source = dedent("""
            from myapp.models import (
                User,
                Order,
                Product,
            )
        """)
        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert set(collector.imports[0].names) == {"User", "Order", "Product"}

    def test_import_with_multiple_aliases(self):
        """Multiple aliases in imports should be preserved."""
        source = "from myapp.models import User as U, Order as O"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import User as U, Order as O" in result


class TestSyntaxErrorHandling:
    """Tests for handling invalid Python syntax."""

    def test_collect_imports_returns_empty_on_syntax_error(self):
        """Syntax errors should return empty list, not raise."""
        source = "from myapp.models import ("  # Invalid: unclosed paren
        resolver = ModuleResolver([])

        imports = collect_imports_from_source(
            source=source,
            module_name="test",
            base_package="myapp",
            resolver=resolver,
        )

        assert imports == []

    def test_rewrite_returns_original_on_syntax_error(self):
        """Syntax errors should return original source."""
        source = "from myapp.models import ("  # Invalid
        result = rewrite_imports(source, "myapp", "extracted")
        assert result == source


class TestCommentsNotPreserved:
    """Tests documenting that comments are lost (known limitation)."""

    def test_comments_are_stripped(self):
        """Verify that comments are stripped during rewriting."""
        source = dedent("""
            # This is a module comment
            from myapp.models import Model  # inline comment

            class Foo:
                '''Docstring is preserved'''
                # Method comment
                def bar(self):
                    pass
        """)
        result = rewrite_imports(source, "myapp", "extracted")

        # Docstrings ARE preserved (they're part of AST)
        assert "Docstring is preserved" in result

        # Comments are NOT preserved (they're stripped by ast.parse)
        assert "module comment" not in result
        assert "inline comment" not in result
        assert "Method comment" not in result
