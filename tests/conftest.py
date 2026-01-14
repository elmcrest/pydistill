"""Pytest fixtures for pydistill tests."""

import sys
from pathlib import Path

import pytest


@pytest.fixture
def test_project_path() -> Path:
    """Path to the test_project fixture."""
    return Path(__file__).parent.parent / "test_project"


@pytest.fixture
def project_a_path(test_project_path: Path) -> Path:
    """Path to project_a within test_project."""
    return test_project_path / "project_a"


@pytest.fixture
def add_test_project_to_path(test_project_path: Path):
    """Add test_project to sys.path for import resolution."""
    path_str = str(test_project_path)
    sys.path.insert(0, path_str)
    yield
    sys.path.remove(path_str)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Temporary output directory for extraction."""
    return tmp_path / "extracted"
