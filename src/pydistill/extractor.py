"""Main module extraction logic."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from pydistill.discovery import ModuleResolver, discover_modules
from pydistill.models import EntryPoint, ExtractionResult
from pydistill.rewriter import rewrite_imports


@dataclass
class ModuleExtractor:
    """Main class for extracting modules and their dependencies."""

    base_package: str
    output_package: str
    output_dir: Path
    source_roots: list[Path] = field(default_factory=list)
    dry_run: bool = False
    clean: bool = False
    quiet: bool = False
    filesystem_only: bool = False
    format: bool = False
    formatter: str = "ruff format"
    output: TextIO = field(default_factory=lambda: sys.stdout)

    # Internal state
    _resolver: ModuleResolver | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._resolver is None:
            roots = self.source_roots if self.source_roots else None
            self._resolver = ModuleResolver(roots, filesystem_only=self.filesystem_only)

    @property
    def resolver(self) -> ModuleResolver:
        assert self._resolver is not None
        return self._resolver

    def _log(self, message: str) -> None:
        if not self.quiet:
            print(message, file=self.output)

    def _warn(self, message: str) -> None:
        print(f"Warning: {message}", file=sys.stderr)

    def _format_file(self, file_path: Path) -> bool:
        """Format a single file using the configured formatter. Returns True on success."""
        try:
            cmd = [*shlex.split(self.formatter), str(file_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError) as e:
            self._warn(f"Failed to format {file_path}: {e}")
            return False

    def get_relative_path(self, module_name: str) -> Path:
        """Get the relative path for a module within the output package."""
        if module_name.startswith(self.base_package):
            relative_module = module_name[len(self.base_package) :]
            if relative_module.startswith("."):
                relative_module = relative_module[1:]
        else:
            relative_module = module_name

        if not relative_module:
            return Path("__init__.py")

        parts = relative_module.split(".")

        source_path = self.resolver.resolve(module_name)
        if source_path and source_path.name == "__init__.py":
            return Path(*parts) / "__init__.py"
        if len(parts) > 1:
            return Path(*parts[:-1]) / f"{parts[-1]}.py"
        return Path(f"{parts[0]}.py")

    def extract(self, entry_points: list[EntryPoint]) -> ExtractionResult:
        """Extract all modules and write to output directory."""
        result = ExtractionResult()

        self._log(f"\nDiscovering modules from {len(entry_points)} entry point(s)...")

        def on_discover(module: str, path: Path) -> None:
            self._log(f"  Discovered: {module} -> {path}")

        def on_warning(msg: str) -> None:
            self._warn(msg)
            result.warnings.append(msg)

        modules = discover_modules(
            entry_points=entry_points,
            base_package=self.base_package,
            resolver=self.resolver,
            on_discover=on_discover,
            on_warning=on_warning,
        )
        result.modules_discovered = modules

        if not modules:
            self._warn("No modules discovered!")
            return result

        self._log(f"\nFound {len(modules)} module(s) to extract")

        if self.dry_run:
            self._log("\n[DRY RUN] Would extract the following modules:")
            for module_name in sorted(modules):
                relative_path = self.get_relative_path(module_name)
                output_path = self.output_dir / relative_path
                self._log(f"  {module_name} -> {output_path}")
            return result

        # Clean output directory if requested
        if self.clean and self.output_dir.exists():
            self._log(f"\nCleaning output directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Collect all directories that need __init__.py
        init_dirs: set[Path] = set()

        # Copy and rewrite each module
        self._log("\nExtracting modules:")
        for module_name in sorted(modules):
            source_path = self.resolver.resolve(module_name)
            if not source_path:
                continue

            relative_path = self.get_relative_path(module_name)
            output_path = self.output_dir / relative_path

            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Track directories needing __init__.py
            rel_parent = relative_path.parent
            while rel_parent != Path():
                init_dirs.add(rel_parent)
                rel_parent = rel_parent.parent

            # Read, rewrite, and write source
            try:
                source = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                self._warn(f"Could not read {source_path}: {e}")
                continue

            rewritten = rewrite_imports(source, self.base_package, self.output_package)

            output_path.write_text(rewritten, encoding="utf-8")
            result.modules_extracted.append(module_name)
            result.files_written.append(output_path)
            self._log(f"  {module_name} -> {output_path}")

        # Create root __init__.py
        root_init = self.output_dir / "__init__.py"
        if not root_init.exists():
            root_init.write_text(
                f'"""Auto-generated {self.output_package} package."""\n'
            )
            result.files_written.append(root_init)

        # Create missing __init__.py files
        for init_dir in sorted(init_dirs):
            init_path = self.output_dir / init_dir / "__init__.py"
            if not init_path.exists():
                init_path.parent.mkdir(parents=True, exist_ok=True)
                init_path.write_text('"""Auto-generated subpackage."""\n')
                result.files_written.append(init_path)
                self._log(f"  Created: {init_path}")

        # Format files if requested
        if self.format:
            self._log(f"\nFormatting with: {self.formatter}")
            format_failures = 0
            for file_path in result.files_written:
                if file_path.suffix == ".py":
                    if not self._format_file(file_path):
                        format_failures += 1
            if format_failures > 0:
                self._warn(f"Failed to format {format_failures} file(s)")

        self._log(f"\nExtraction complete! Output written to: {self.output_dir}")

        return result
