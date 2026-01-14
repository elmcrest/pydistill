"""Tests for pydistill.discovery."""

from pathlib import Path

from pydistill.discovery import (
    ImportCollector,
    ModuleResolver,
    collect_imports_from_source,
    discover_modules,
    resolve_relative_import,
)
from pydistill.models import EntryPoint


class TestResolveRelativeImport:
    def test_absolute_import(self):
        result = resolve_relative_import("myapp.views", "myapp.models", level=0)
        assert result == "myapp.models"

    def test_relative_level_1(self):
        result = resolve_relative_import("myapp.views", "models", level=1)
        assert result == "myapp.models"

    def test_relative_level_2(self):
        result = resolve_relative_import("myapp.sub.views", "models", level=2)
        assert result == "myapp.models"

    def test_relative_empty_module(self):
        result = resolve_relative_import("myapp.sub.views", "", level=1)
        assert result == "myapp.sub"


class TestImportCollector:
    def test_collects_absolute_import(self):
        source = "from myapp.models import User"
        import ast

        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].module == "myapp.models"
        assert collector.imports[0].names == ["User"]

    def test_ignores_third_party(self):
        source = "from pydantic import BaseModel"
        import ast

        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 0

    def test_collects_relative_import(self):
        source = "from .models import User"
        import ast

        tree = ast.parse(source)
        collector = ImportCollector("myapp")
        collector.visit(tree)

        assert len(collector.imports) == 1
        assert collector.imports[0].level == 1


class TestCollectImportsFromSource:
    def test_collects_imports(self, test_project_path: Path, add_test_project_to_path):
        source = """
from project_a.common.types import Status
from project_a.vehicles.models import Vehicle
from pydantic import BaseModel
"""
        resolver = ModuleResolver([test_project_path])
        imports = collect_imports_from_source(
            source=source,
            module_name="project_a.appointments.models",
            base_package="project_a",
            resolver=resolver,
        )

        assert "project_a.common.types" in imports
        assert "project_a.vehicles.models" in imports
        # pydantic should not be included
        assert not any("pydantic" in imp for imp in imports)


class TestModuleResolver:
    def test_filesystem_only_skips_importlib(self, test_project_path: Path):
        """Test that filesystem_only=True resolves modules without importlib."""
        # Note: we intentionally do NOT use add_test_project_to_path fixture
        resolver = ModuleResolver([test_project_path], filesystem_only=True)

        # Should find the module via filesystem search
        path = resolver.resolve("project_a.appointments.models")
        assert path is not None
        assert path.exists()
        assert "appointments" in str(path)
        assert path.name == "models.py"

    def test_filesystem_only_resolves_package(self, test_project_path: Path):
        """Test that filesystem_only can resolve packages (__init__.py)."""
        resolver = ModuleResolver([test_project_path], filesystem_only=True)

        path = resolver.resolve("project_a.common")
        assert path is not None
        assert path.exists()
        assert path.name == "__init__.py"


class TestDiscoverModules:
    def test_discovers_transitive_deps(
        self, test_project_path: Path, add_test_project_to_path
    ):
        resolver = ModuleResolver([test_project_path])
        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="project_a",
            resolver=resolver,
        )

        assert "project_a.appointments.models" in discovered
        assert "project_a.common.types" in discovered
        assert "project_a.vehicles.models" in discovered

    def test_discovers_with_filesystem_only(self, test_project_path: Path):
        """Test discovery using filesystem-only resolution."""
        # Note: we intentionally do NOT use add_test_project_to_path fixture
        resolver = ModuleResolver([test_project_path], filesystem_only=True)
        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]

        discovered = discover_modules(
            entry_points=entry_points,
            base_package="project_a",
            resolver=resolver,
        )

        assert "project_a.appointments.models" in discovered
        assert "project_a.common.types" in discovered
        assert "project_a.vehicles.models" in discovered
