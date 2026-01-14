"""Tests for pydistill.cli."""

from pathlib import Path

from pydistill.cli import create_parser, main, validate_config
from pydistill.config import PyDistillConfig


class TestCreateParser:
    def test_parser_creation(self):
        parser = create_parser()
        assert parser is not None

    def test_parse_entries(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp.models:User",
                "-e",
                "myapp.models:Order",
                "-b",
                "myapp",
                "-p",
                "extracted",
                "-o",
                "./dist",
            ],
        )
        assert args.entries == ["myapp.models:User", "myapp.models:Order"]
        assert args.base_package == "myapp"
        assert args.output_package == "extracted"
        assert args.output_dir == Path("./dist")

    def test_parse_dry_run(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--dry-run",
            ],
        )
        assert args.dry_run is True

    def test_parse_clean(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--clean",
            ],
        )
        assert args.clean is True

    def test_parse_filesystem_only(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--filesystem-only",
            ],
        )
        assert args.filesystem_only is True

    def test_parse_filesystem_only_short_flag(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "-f",
            ],
        )
        assert args.filesystem_only is True

    def test_parse_format(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--format",
            ],
        )
        assert args.format is True

    def test_parse_formatter(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--formatter",
                "black",
            ],
        )
        assert args.formatter == "black"

    def test_parse_formatter_with_options(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "-e",
                "myapp:User",
                "-b",
                "myapp",
                "-p",
                "out",
                "-o",
                "./dist",
                "--formatter",
                "ruff format --line-length 120",
            ],
        )
        assert args.formatter == "ruff format --line-length 120"


class TestValidateConfig:
    def test_valid_config(self):
        config = PyDistillConfig(
            entries=["myapp:User"],
            base_package="myapp",
            output_package="extracted",
            output_dir=Path("./dist"),
        )
        errors = validate_config(config)
        assert len(errors) == 0

    def test_missing_entries(self):
        config = PyDistillConfig(
            entries=[],
            base_package="myapp",
            output_package="extracted",
            output_dir=Path("./dist"),
        )
        errors = validate_config(config)
        assert any("entry points" in e.lower() for e in errors)

    def test_missing_base_package(self):
        config = PyDistillConfig(
            entries=["myapp:User"],
            base_package=None,
            output_package="extracted",
            output_dir=Path("./dist"),
        )
        errors = validate_config(config)
        assert any("base package" in e.lower() for e in errors)


class TestMain:
    def test_main_with_valid_args(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        result = main(
            [
                "-e",
                "project_a.appointments.models:Appointment",
                "-b",
                "project_a",
                "-p",
                "extracted",
                "-o",
                str(output_dir),
                "-s",
                str(test_project_path),
                "--quiet",
            ],
        )
        assert result == 0
        assert output_dir.exists()

    def test_main_dry_run(
        self,
        test_project_path: Path,
        output_dir: Path,
        add_test_project_to_path,
    ):
        result = main(
            [
                "-e",
                "project_a.appointments.models:Appointment",
                "-b",
                "project_a",
                "-p",
                "extracted",
                "-o",
                str(output_dir),
                "-s",
                str(test_project_path),
                "--dry-run",
                "--quiet",
            ],
        )
        assert result == 0
        assert not output_dir.exists()

    def test_main_missing_required_args(self):
        result = main([])
        assert result == 1

    def test_main_invalid_entry_point(self, tmp_path: Path):
        result = main(
            [
                "-e",
                "invalid_format_no_colon",
                "-b",
                "myapp",
                "-p",
                "extracted",
                "-o",
                str(tmp_path / "out"),
            ],
        )
        assert result == 1

    def test_main_filesystem_only(self, test_project_path: Path, output_dir: Path):
        """Test extraction using --filesystem-only without adding to sys.path."""
        # Note: we intentionally do NOT use add_test_project_to_path fixture
        # to verify that --filesystem-only works without importlib
        result = main(
            [
                "-e",
                "project_a.appointments.models:Appointment",
                "-b",
                "project_a",
                "-p",
                "extracted",
                "-o",
                str(output_dir),
                "-s",
                str(test_project_path),
                "--filesystem-only",
                "--quiet",
            ],
        )
        assert result == 0
        assert output_dir.exists()
        assert (output_dir / "appointments" / "models.py").exists()
        assert (output_dir / "common" / "types.py").exists()
        assert (output_dir / "vehicles" / "models.py").exists()
