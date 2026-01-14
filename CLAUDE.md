# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyDistill extracts Python models and their transitive dependencies into standalone, self-contained packages. It automates extraction of Pydantic models (or any Python classes) from large projects by following import graphs and rewriting import paths.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_cli.py

# Run single test
uv run pytest tests/test_cli.py::TestCreateParser::test_entry_short_flag

# Run CLI
uv run pydistill --help

# Example extraction (using test_project)
uv run pydistill \
    -e project_a.appointments.models:Appointment \
    -b project_a \
    -p extracted \
    -o ./dist/extracted \
    -s ./test_project

# Extract from uninstallable project (filesystem-only mode)
uv run pydistill \
    -e some_package.models:Model \
    -b some_package \
    -p extracted \
    -o ./dist/extracted \
    -s /path/to/project \
    --filesystem-only

# Extract with formatting (uses ruff by default)
uv run pydistill \
    -e project_a.appointments.models:Appointment \
    -b project_a \
    -p extracted \
    -o ./dist/extracted \
    -s ./test_project \
    --format
```

## Architecture

The extraction pipeline follows this flow:

1. **Entry Point Parsing** (`models.py`) - Converts `"module.path:ClassName"` strings to `EntryPoint` objects
2. **Module Discovery** (`discovery.py`) - BFS traversal starting from entry points, collecting all imports within `base_package`
3. **Import Rewriting** (`rewriter.py`) - AST transformer that rewrites `base_package` imports to `output_package`
4. **Extraction** (`extractor.py`) - Orchestrates the workflow: reads sources, rewrites imports, writes output files
5. **Formatting** (optional) - Runs external formatter (e.g., `ruff format`) on extracted files

### Key Modules

- `cli.py` - Argument parsing, config loading, main entry point
- `config.py` - TOML config file support with auto-detection (walks up directory tree for `pydistill.toml`)
- `discovery.py` - `ImportCollector` (AST visitor), `ModuleResolver` (file path resolution), `discover_modules()` (BFS)
- `rewriter.py` - `ImportRewriter` (AST NodeTransformer) that preserves relative imports
- `extractor.py` - `ModuleExtractor` dataclass with dry-run mode, clean mode, `__init__.py` generation, optional formatting

### Design Decisions

- Zero external dependencies in production (uses only stdlib: `ast`, `importlib`, `tomllib`, `dataclasses`)
- AST-based import rewriting ensures safe transformation without regex pitfalls
- Extracts entire modules, not individual classes (if User and Admin share a module, both are extracted)
- Relative imports are preserved as-is since directory structure is maintained

## Test Project

`test_project/project_a/` contains a reference Pydantic project structure used by tests. It demonstrates nested dependencies: `Appointment` → `Vehicle` → `TimestampMixin`, `Status`, `Address`.
