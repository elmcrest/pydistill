"""Tests for pydistill.rewriter."""

from pydistill.rewriter import rewrite_imports


class TestImportRewriter:
    def test_rewrites_from_import(self):
        source = "from myapp.models import User"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import User" in result

    def test_rewrites_import(self):
        source = "import myapp.models"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "import extracted.models" in result

    def test_preserves_third_party(self):
        source = "from pydantic import BaseModel"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from pydantic import BaseModel" in result

    def test_preserves_relative_imports(self):
        source = "from .models import User"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from .models import User" in result

    def test_handles_alias(self):
        source = "from myapp.models import User as U"
        result = rewrite_imports(source, "myapp", "extracted")
        assert "from extracted.models import User as U" in result

    def test_complex_source(self):
        source = """
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from myapp.common.types import Status
from myapp.vehicles.models import Vehicle

class Appointment(BaseModel):
    id: int
    status: Status
"""
        result = rewrite_imports(source, "myapp", "extracted")

        # Should rewrite myapp imports
        assert "from extracted.common.types import Status" in result
        assert "from extracted.vehicles.models import Vehicle" in result

        # Should preserve third-party
        assert "from datetime import datetime" in result
        assert "from pydantic import BaseModel" in result
