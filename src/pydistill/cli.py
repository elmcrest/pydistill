"""Command-line interface for pydistill."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydistill import __version__
from pydistill.config import PyDistillConfig
from pydistill.extractor import ModuleExtractor
from pydistill.models import EntryPoint


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pydistill",
        description="Extract Python models and dependencies into standalone packages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from CLI arguments
  pydistill -e myapp.models:User -e myapp.models:Order \\
        -b myapp -p extracted -o ./dist/extracted

  # Use pydistill.toml configuration
  pydistill

  # Dry run to see what would be extracted
  pydistill --dry-run

Configuration file (pydistill.toml):
  [pydistill]
  entries = [
      "myapp.models:User",
      "myapp.models:Order",
  ]
  base_package = "myapp"
  output_package = "extracted"
  output_dir = "./dist/extracted"
  clean = true
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--entry",
        "-e",
        action="append",
        dest="entries",
        metavar="MODULE:NAME",
        help="Entry point in 'module.path:ClassName' format (can be repeated)",
    )

    parser.add_argument(
        "--base-package",
        "-b",
        metavar="PACKAGE",
        help="Base package name to extract from (e.g., 'myapp')",
    )

    parser.add_argument(
        "--output-package",
        "-p",
        metavar="PACKAGE",
        help="Output package name (e.g., 'extracted_models')",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        metavar="DIR",
        help="Output directory for extracted package",
    )

    parser.add_argument(
        "--source-root",
        "-s",
        action="append",
        dest="source_roots",
        type=Path,
        metavar="DIR",
        help="Additional source roots to search (can be repeated)",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        metavar="FILE",
        help="Path to pydistill.toml config file (default: auto-detect)",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be extracted without writing files",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove output directory before extraction",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output",
    )

    parser.add_argument(
        "--filesystem-only",
        "-f",
        action="store_true",
        help="Use only filesystem-based module resolution (skip importlib). "
        "Useful for extracting from projects that cannot be installed.",
    )

    parser.add_argument(
        "--format",
        action="store_true",
        help="Format extracted files using a code formatter (default: ruff format)",
    )

    parser.add_argument(
        "--formatter",
        metavar="CMD",
        help="Formatter command to use (default: 'ruff format'). Implies --format.",
    )

    return parser


def load_config(args: argparse.Namespace) -> PyDistillConfig:
    """Load and merge configuration from file and CLI arguments."""
    # Load config file
    if args.config:
        if not args.config.exists():
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        file_config = PyDistillConfig.load(args.config)
    else:
        file_config = PyDistillConfig.find_and_load()

    # --formatter implies --format
    format_enabled = args.format or args.formatter is not None

    # Start with file config or empty config
    if file_config:
        config = file_config.merge_with_args(
            entries=args.entries,
            base_package=args.base_package,
            output_package=args.output_package,
            output_dir=args.output_dir,
            source_roots=args.source_roots,
            clean=args.clean if args.clean else None,
            filesystem_only=args.filesystem_only if args.filesystem_only else None,
            format=format_enabled if format_enabled else None,
            formatter=args.formatter,
        )
    else:
        config = PyDistillConfig(
            entries=args.entries or [],
            base_package=args.base_package,
            output_package=args.output_package,
            output_dir=args.output_dir,
            source_roots=args.source_roots or [],
            clean=args.clean,
            filesystem_only=args.filesystem_only,
            format=format_enabled,
            formatter=args.formatter or "ruff format",
        )

    return config


def validate_config(config: PyDistillConfig) -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []

    if not config.entries:
        errors.append(
            "No entry points specified. Use --entry or configure in pydistill.toml",
        )

    if not config.base_package:
        errors.append(
            "No base package specified. Use --base-package or configure in pydistill.toml",
        )

    if not config.output_package:
        errors.append(
            "No output package specified. Use --output-package or configure in pydistill.toml",
        )

    if not config.output_dir:
        errors.append(
            "No output directory specified. Use --output-dir or configure in pydistill.toml",
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Load configuration
    config = load_config(args)

    # Validate
    errors = validate_config(config)
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    # Parse entry points
    try:
        entry_points = [EntryPoint.parse(e) for e in config.entries]
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create extractor and run
    extractor = ModuleExtractor(
        base_package=config.base_package,  # type: ignore[arg-type]
        output_package=config.output_package,  # type: ignore[arg-type]
        output_dir=config.output_dir,  # type: ignore[arg-type]
        source_roots=config.source_roots,
        dry_run=args.dry_run,
        clean=config.clean,
        quiet=args.quiet,
        filesystem_only=config.filesystem_only,
        format=config.format,
        formatter=config.formatter,
    )

    result = extractor.extract(entry_points)

    if not result.success and not args.dry_run:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
