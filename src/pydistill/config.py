"""Configuration file support for pydistill.toml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib


@dataclass
class PyDistillConfig:
    """Configuration loaded from pydistill.toml."""

    entries: list[str] = field(default_factory=list)
    base_package: str | None = None
    output_package: str | None = None
    output_dir: Path | None = None
    source_roots: list[Path] = field(default_factory=list)
    clean: bool = False
    filesystem_only: bool = False
    format: bool = False
    formatter: str = "ruff format"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PyDistillConfig:
        """Create config from a dictionary (parsed TOML)."""
        pydistill_data = data.get("pydistill", data)

        source_roots = [Path(p) for p in pydistill_data.get("source_roots", [])]
        output_dir = pydistill_data.get("output_dir")

        return cls(
            entries=pydistill_data.get("entries", []),
            base_package=pydistill_data.get("base_package"),
            output_package=pydistill_data.get("output_package"),
            output_dir=Path(output_dir) if output_dir else None,
            source_roots=source_roots,
            clean=pydistill_data.get("clean", False),
            filesystem_only=pydistill_data.get("filesystem_only", False),
            format=pydistill_data.get("format", False),
            formatter=pydistill_data.get("formatter", "ruff format"),
        )

    @classmethod
    def load(cls, path: Path) -> PyDistillConfig:
        """Load configuration from a TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.from_dict(data)

    @classmethod
    def find_and_load(cls, start_dir: Path | None = None) -> PyDistillConfig | None:
        """Find pydistill.toml by walking up from start_dir, then load it."""
        if start_dir is None:
            start_dir = Path.cwd()

        current = start_dir.resolve()
        while current != current.parent:
            config_path = current / "pydistill.toml"
            if config_path.exists():
                return cls.load(config_path)
            current = current.parent

        # Check root
        config_path = current / "pydistill.toml"
        if config_path.exists():
            return cls.load(config_path)

        return None

    def merge_with_args(
        self,
        entries: list[str] | None = None,
        base_package: str | None = None,
        output_package: str | None = None,
        output_dir: Path | None = None,
        source_roots: list[Path] | None = None,
        clean: bool | None = None,
        filesystem_only: bool | None = None,
        format: bool | None = None,
        formatter: str | None = None,
    ) -> PyDistillConfig:
        """Merge CLI arguments with config file (CLI takes precedence)."""
        return PyDistillConfig(
            entries=entries if entries else self.entries,
            base_package=base_package if base_package else self.base_package,
            output_package=output_package if output_package else self.output_package,
            output_dir=output_dir if output_dir else self.output_dir,
            source_roots=source_roots if source_roots else self.source_roots,
            clean=clean if clean is not None else self.clean,
            filesystem_only=filesystem_only
            if filesystem_only is not None
            else self.filesystem_only,
            format=format if format is not None else self.format,
            formatter=formatter if formatter else self.formatter,
        )
