"""Tests for pydistill.extractor."""

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from pydistill.extractor import ModuleExtractor
from pydistill.models import EntryPoint
from pydistill.versioning import VersionStrategy


def _python_for_install_test() -> str | None:
    """Find a Python executable with pip and setuptools available."""
    candidates = [
        sys.executable,
        getattr(sys, "_base_executable", None),
        shutil.which("python3"),
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result = subprocess.run(
            [candidate, "-c", "import pip, setuptools"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return None


INSTALL_TEST_PYTHON = _python_for_install_test()


class TestModuleExtractor:
    def test_extract_creates_package(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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
        assert (output_dir / "extracted" / "__init__.py").exists()
        assert (output_dir / "extracted" / "appointments" / "models.py").exists()
        assert (output_dir / "extracted" / "common" / "types.py").exists()
        assert (output_dir / "extracted" / "vehicles" / "models.py").exists()
        assert (output_dir / "pyproject.toml").exists()

    def test_extract_writes_pyproject_by_default(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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
        pyproject_path = output_dir / "pyproject.toml"

        assert result.success
        assert pyproject_path.exists()

        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        assert data["build-system"]["requires"] == ["setuptools>=68"]
        assert data["build-system"]["build-backend"] == "setuptools.build_meta"
        assert data["project"]["name"] == "extracted"
        assert data["project"]["version"] == "1.0.0"
        assert data["project"]["requires-python"] == ">=3.11"
        assert data["project"]["dependencies"] == []
        assert data["tool"]["setuptools"]["packages"] == [
            "extracted",
            "extracted.appointments",
            "extracted.common",
            "extracted.vehicles",
        ]
        assert "package-dir" not in data["tool"]["setuptools"]

    def test_extract_writes_custom_dist_metadata(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
            dist_name="appointments-contracts",
            dist_version="2.4.1",
            version_strategy=VersionStrategy.MANUAL,
            dependencies=["pydantic>=2.0", "email-validator>=2.0"],
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)
        pyproject_path = output_dir / "pyproject.toml"

        assert result.success
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        assert data["project"]["name"] == "appointments-contracts"
        assert data["project"]["version"] == "2.4.1"
        assert data["project"]["dependencies"] == [
            "pydantic>=2.0",
            "email-validator>=2.0",
        ]

    def test_extract_rewrites_imports(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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
        models_content = (
            output_dir / "extracted" / "appointments" / "models.py"
        ).read_text()
        assert "from extracted.common.types import" in models_content
        assert "from extracted.vehicles.models import" in models_content
        assert "from project_a" not in models_content

    def test_dry_run_does_not_write(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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
        assert (output_dir / "extracted" / "appointments" / "models.py").exists()

    def test_extracted_package_is_importable(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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

        # Add output dir to sys.path and try importing
        sys.path.insert(0, str(output_dir))
        try:
            from extracted.appointments.models import Appointment  # type: ignore[import-not-found]
            from extracted.common.types import Status  # type: ignore[import-not-found]

            assert hasattr(Appointment, "model_fields")
            assert hasattr(Status, "ACTIVE")
        finally:
            sys.path.remove(str(output_dir))

    @pytest.mark.skipif(
        shutil.which("ruff") is None,
        reason="ruff not installed",
    )
    def test_format_with_ruff(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        """Test that --format runs ruff on extracted files."""
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
            format=True,
            formatter="ruff format",
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)

        assert result.success
        # Verify files exist and are valid Python
        models_content = (
            output_dir / "extracted" / "appointments" / "models.py"
        ).read_text()
        assert "from extracted.common.types import" in models_content

    def test_format_with_unavailable_formatter(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        """Test that extraction succeeds even if formatter is not available."""
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
            format=True,
            formatter="nonexistent_formatter_xyz",
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)

        # Should still succeed - formatting failure is non-fatal
        assert result.success
        assert (output_dir / "extracted" / "appointments" / "models.py").exists()

    def test_format_disabled_by_default(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        """Test that formatting is disabled by default."""
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )

        assert extractor.format is False

    def test_extract_writes_manifest(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
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

        manifest_path = output_dir / ".pydistill-manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["version"] == "1.0.0"
        assert "content_hash" in data
        assert len(data["content_hash"]) == 64  # SHA-256 hex
        assert result.version == "1.0.0"
        assert result.content_hash == data["content_hash"]

    def test_extract_auto_bumps_version_on_change(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]

        # First extraction
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )
        result1 = extractor.extract(entry_points)
        assert result1.version == "1.0.0"

        # Modify a source file in the output to simulate changed content hash
        # We tamper with the manifest's content_hash to simulate a change
        manifest_path = output_dir / ".pydistill-manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["content_hash"] = "different_hash"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")

        # Second extraction (content hash won't match manifest)
        extractor2 = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )
        result2 = extractor2.extract(entry_points)
        assert result2.version == "1.0.1"

    def test_extract_keeps_version_on_same_content(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]

        # First extraction
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )
        result1 = extractor.extract(entry_points)
        assert result1.version == "1.0.0"

        # Second extraction, same content
        extractor2 = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
        )
        result2 = extractor2.extract(entry_points)
        assert result2.version == "1.0.0"

    def test_extract_manual_strategy_uses_exact(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        extractor = ModuleExtractor(
            base_package="project_a",
            output_package="extracted",
            output_dir=output_dir,
            source_roots=[test_project_path],
            quiet=True,
            dist_version="5.0.0",
            version_strategy=VersionStrategy.MANUAL,
        )

        entry_points = [EntryPoint.parse("project_a.appointments.models:Appointment")]
        result = extractor.extract(entry_points)
        assert result.version == "5.0.0"

        data = tomllib.loads(
            (output_dir / "pyproject.toml").read_text(encoding="utf-8")
        )
        assert data["project"]["version"] == "5.0.0"
