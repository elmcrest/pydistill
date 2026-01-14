"""Tests for pydistill.models."""

import pytest
from pydistill.models import EntryPoint, ExtractionResult, ImportInfo


class TestEntryPoint:
    def test_parse_valid(self):
        ep = EntryPoint.parse("myapp.models:User")
        assert ep.module == "myapp.models"
        assert ep.name == "User"

    def test_parse_nested_module(self):
        ep = EntryPoint.parse("myapp.sub.models:MyModel")
        assert ep.module == "myapp.sub.models"
        assert ep.name == "MyModel"

    def test_parse_invalid_no_colon(self):
        with pytest.raises(ValueError, match="must be in 'module:name' format"):
            EntryPoint.parse("myapp.models.User")

    def test_str(self):
        ep = EntryPoint(module="myapp.models", name="User")
        assert str(ep) == "myapp.models:User"


class TestImportInfo:
    def test_from_import(self):
        info = ImportInfo(
            module="myapp.models",
            names=["User", "Order"],
            is_from_import=True,
            level=0,
        )
        assert info.module == "myapp.models"
        assert info.names == ["User", "Order"]
        assert info.is_from_import is True
        assert info.level == 0

    def test_relative_import(self):
        info = ImportInfo(
            module="models",
            names=["User"],
            is_from_import=True,
            level=1,
        )
        assert info.level == 1


class TestExtractionResult:
    def test_success_when_modules_extracted(self):
        result = ExtractionResult(
            modules_discovered={"a", "b"},
            modules_extracted=["a", "b"],
        )
        assert result.success is True

    def test_not_success_when_no_modules(self):
        result = ExtractionResult()
        assert result.success is False
