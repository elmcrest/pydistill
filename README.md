# pydistill
[![codecov](https://codecov.io/gh/elmcrest/pydistill/graph/badge.svg?token=hWfKsrCkxK)](https://codecov.io/gh/elmcrest/pydistill)

Extract Python models and their transitive dependencies into standalone, self-contained packages.

## Why?

You have a large Python project and want to share some Pydantic models (or any Python classes) with another service without:
- Publishing your entire codebase
- Manually copying files and fixing imports
- Maintaining a separate package by hand

PyDistill automates this: point it at your entry points, and it extracts exactly what's needed into an importable package.

## Installation

```bash
# With uv
uv add pydistill

# With pip
pip install pydistill
```

## Quick Start

```bash
# Extract a model and its dependencies
pydistill \
    --entry myapp.models:User \
    --entry myapp.models:Order \
    --base-package myapp \
    --output-package extracted_models \
    --output-dir ./dist/extracted_models
```

This will:
1. Discover all local imports transitively from `User` and `Order`
2. Copy the relevant source files to `./dist/extracted_models/`
3. Rewrite imports (`myapp.*` → `extracted_models.*`)
4. Generate `__init__.py` files so the package is importable

## Configuration

### CLI Options

```
pydistill [OPTIONS]

Options:
  -e, --entry MODULE:NAME     Entry point (can be repeated)
  -b, --base-package PACKAGE  Base package to extract from
  -p, --output-package PACKAGE Output package name
  -o, --output-dir DIR        Output directory
  -s, --source-root DIR       Additional source roots (can be repeated)
  -c, --config FILE           Path to config file
  -n, --dry-run               Show what would be extracted
  --clean                     Remove output directory first
  -q, --quiet                 Suppress output
  -f, --filesystem-only       Skip importlib, use only filesystem resolution
  --format                    Format extracted files (default: ruff format)
  --formatter CMD             Custom formatter command (implies --format)
  --version                   Show version
  -h, --help                  Show help
```

### Configuration File

Create a `pydistill.toml` in your project root:

```toml
[pydistill]
entries = [
    "myapp.users.models:User",
    "myapp.orders.models:Order",
]
base_package = "myapp"
output_package = "extracted_models"
output_dir = "./dist/extracted_models"
clean = true
# filesystem_only = true  # Enable for uninstallable projects
# format = true           # Format extracted files
# formatter = "ruff format"  # Custom formatter command
```

Then just run:

```bash
pydistill
```

PyDistill automatically searches for `pydistill.toml` in the current directory and parent directories.

CLI arguments override config file values.

## Example

Given this project structure:

```
myapp/
├── __init__.py
├── common/
│   ├── __init__.py
│   └── types.py          # Status enum, Address model
├── users/
│   ├── __init__.py
│   └── models.py         # User model (imports common.types)
└── orders/
    ├── __init__.py
    └── models.py         # Order model (imports users.models, common.types)
```

Running:

```bash
pydistill -e myapp.orders.models:Order -b myapp -p extracted -o ./dist/extracted
```

Produces:

```
dist/extracted/
├── __init__.py
├── common/
│   ├── __init__.py
│   └── types.py          # Status, Address (imports rewritten)
├── users/
│   ├── __init__.py
│   └── models.py         # User (imports rewritten)
└── orders/
    ├── __init__.py
    └── models.py         # Order (imports rewritten)
```

All imports like `from myapp.common.types import Status` become `from extracted.common.types import Status`.

## Extracting from Uninstallable Projects

Need to extract models from a project that can't be installed in your current environment (e.g., has Windows-only dependencies on macOS)? Use `--filesystem-only`:

```bash
pydistill \
    -e their_app.models:SomeModel \
    -b their_app \
    -p extracted \
    -o ./dist/extracted \
    -s /path/to/their/project \
    --filesystem-only
```

This skips Python's `importlib` and resolves modules purely via filesystem search in the specified source roots.

## Formatting Extracted Code

The AST-based import rewriting can produce code that's not perfectly formatted. Use `--format` to automatically format extracted files:

```bash
# Use ruff (default)
pydistill -e myapp:Model -b myapp -p out -o ./dist --format

# Use black instead
pydistill ... --format --formatter black

# Custom ruff config
pydistill ... --format --formatter "ruff format --line-length 120"
```

Formatting failures are non-fatal—extraction will succeed even if the formatter is unavailable.

## How It Works

1. **Parse entry points** - Resolve `module:ClassName` to source files
2. **Discover imports** - Use Python's `ast` module to find all `import` and `from ... import` statements
3. **BFS traversal** - Follow imports transitively within the base package (ignores third-party like `pydantic`, `datetime`, etc.)
4. **Rewrite imports** - Use `ast.NodeTransformer` to rewrite module paths
5. **Generate package** - Copy files preserving structure, create `__init__.py` files

## Use Cases

- **Microservices**: Share domain models between services without a monorepo
- **API clients**: Generate a lightweight client package with just the request/response models
- **CI/CD**: Automatically generate model packages when source changes
- **Cross-platform extraction**: Extract from projects with platform-specific dependencies using `--filesystem-only`

## Limitations

- Only follows imports within `--base-package` (by design)
- Extracts entire modules, not individual classes (a module containing `User` and `Admin` will include both)
- Relative imports are preserved as-is (they work in the output package since structure is maintained)
- **Comments are not preserved**: The AST-based rewriting uses `ast.parse()` and `ast.unparse()`, which strips comments from source files. This is acceptable for artifact/tarball use cases but means the extracted code loses inline documentation. Use `--format` to ensure consistent formatting of the output.
- **Dynamic imports are not traced**: Imports using `importlib.import_module()` or `__import__()` cannot be statically analyzed
- **Star imports (`from x import *`)**: The module path is rewritten correctly, but transitive dependencies imported via `__all__` re-exports may not be discovered

## Development

```bash
# Clone and install
git clone https://github.com/yourorg/pydistill
cd pydistill
uv sync

# Run tests
uv run pytest

# Run pydistill locally
uv run pydistill --help
```

## License

MIT
