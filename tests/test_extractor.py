"""Tests for pydistill.extractor."""

import sys
from io import StringIO
from pathlib import Path

from pydistill.extractor import ModuleExtractor
from pydistill.models import EntryPoint


class TestModuleExtractor:
    def test_extract_creates_package(
        self, test_project_path: Path, output_dir: Path, add_test_project_to_path
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)

        assert result.success
        assert len(result.modules_extracted) == 3
        assert output_dir.exists()
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "appointments" / "models.py").exists()
        assert (output_dir / "common" / "types.py").exists()
        assert (output_dir / "vehicles" / "models.py").exists()

    def test_extract_rewrites_imports(
        self, test_project_path: Path, output_dir: Path, add_test_project_to_path
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        extractor.extract(entry_points)

        # Check that imports were rewritten
        models_content = (output_dir / "appointments" / "models.py").read_text()
        assert "from extracted.common.types import" in models_content
        assert "from extracted.vehicles.models import" in models_content
        assert "from project_a" not in models_content

    def test_dry_run_does_not_write(
        self, test_project_path: Path, output_dir: Path, add_test_project_to_path
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            dry_run=True,
            quiet=True,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)

        # Modules should be discovered but not extracted
        assert len(result.modules_discovered) == 3
        assert len(result.modules_extracted) == 0
        assert not output_dir.exists()

    def test_clean_removes_existing(
        self, test_project_path: Path, output_dir: Path, add_test_project_to_path
    ):
        # Create some existing content
        output_dir.mkdir(parents=True)
        old_file = output_dir / "old_file.py"
        old_file.write_text("# old content")

        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            clean=True,
            quiet=True,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        extractor.extract(entry_points)

        # Old file should be gone
        assert not old_file.exists()
        # New files should exist
        assert (output_dir / "appointments" / "models.py").exists()

    def test_extracted_package_is_importable(
        self, test_project_path: Path, output_dir: Path, add_test_project_to_path
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        extractor.extract(entry_points)

        # Add output dir parent to sys.path and try importing
        sys.path.insert(0, str(output_dir.parent))
        try:
            from extracted.appointments.models import Appointment
            from extracted.common.types import Status

            assert hasattr(Appointment, "model_fields")
            assert hasattr(Status, "ACTIVE")
        finally:
            sys.path.remove(str(output_dir.parent))
