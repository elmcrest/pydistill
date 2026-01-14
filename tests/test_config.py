"""Tests for pydistill.config."""

from pathlib import Path

from pydistill.config import PyDistillConfig


class TestPyDistillConfig:
    def test_from_dict(self):
        data = {
            "pydistill": {
                "entries": ["myapp.models:User"],
                "base_package": "myapp",
                "output_package": "extracted",
                "output_dir": "./dist",
                "clean": True,
            },
        }
        config = PyDistillConfig.from_dict(data)

        assert config.entries == ["myapp.models:User"]
        assert config.base_package == "myapp"
        assert config.output_package == "extracted"
        assert config.output_dir == Path("./dist")
        assert config.clean is True

    def test_from_dict_without_pydistill_key(self):
        data = {
            "entries": ["myapp.models:User"],
            "base_package": "myapp",
            "output_package": "extracted",
            "output_dir": "./dist",
        }
        config = PyDistillConfig.from_dict(data)

        assert config.entries == ["myapp.models:User"]
        assert config.base_package == "myapp"

    def test_merge_with_args_cli_takes_precedence(self):
        config = PyDistillConfig(
            entries=["myapp.models:User"],
            base_package="myapp",
            output_package="extracted",
            output_dir=Path("./dist"),
            clean=False,
        )

        merged = config.merge_with_args(
            entries=["other.models:Order"],
            base_package=None,  # Should keep original
            output_package="cli_extracted",
            output_dir=None,  # Should keep original
            clean=True,
        )

        assert merged.entries == ["other.models:Order"]
        assert merged.base_package == "myapp"  # Kept from file
        assert merged.output_package == "cli_extracted"
        assert merged.output_dir == Path("./dist")  # Kept from file
        assert merged.clean is True

    def test_load_from_file(self, tmp_path: Path):
        config_file = tmp_path / "pydistill.toml"
        config_file.write_text("""
[pydistill]
entries = ["myapp.models:User", "myapp.models:Order"]
base_package = "myapp"
output_package = "extracted"
output_dir = "./dist/extracted"
clean = true
""")

        config = PyDistillConfig.load(config_file)

        assert config.entries == ["myapp.models:User", "myapp.models:Order"]
        assert config.base_package == "myapp"
        assert config.output_package == "extracted"
        assert config.output_dir == Path("./dist/extracted")
        assert config.clean is True
