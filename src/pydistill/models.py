"""Data models for pydistill."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EntryPoint:
    """Represents a model entry point like 'project_a.models:MyModel'."""

    module: str
    name: str

    @classmethod
    def parse(cls, spec: str) -> EntryPoint:
        """Parse 'module.path:ClassName' format."""
        if ":" not in spec:
            raise ValueError(
                f"Entry point must be in 'module:name' format, got: {spec}"
            )
        module, name = spec.rsplit(":", 1)
        return cls(module=module, name=name)

    def __str__(self) -> str:
        return f"{self.module}:{self.name}"


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: str  # The module being imported from
    names: list[str]  # Names being imported (empty for 'import X')
    is_from_import: bool  # True for 'from X import Y', False for 'import X'
    level: int = 0  # Relative import level (0 = absolute)


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    modules_discovered: set[str] = field(default_factory=set)
    modules_extracted: list[str] = field(default_factory=list)
    files_written: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.modules_extracted) > 0
