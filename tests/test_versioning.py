"""Tests for pydistill.versioning."""

from pathlib import Path

from pydistill.versioning import (
    Manifest,
    VersionStrategy,
    bump_patch,
    compute_content_hash,
    resolve_version,
)


class TestComputeContentHash:
    def test_deterministic(self):
        sources = {"a.py": "print('hello')", "b.py": "x = 1"}
        assert compute_content_hash(sources) == compute_content_hash(sources)

    def test_differs_on_content(self):
        sources_a = {"a.py": "print('hello')"}
        sources_b = {"a.py": "print('world')"}
        assert compute_content_hash(sources_a) != compute_content_hash(sources_b)

    def test_order_independent(self):
        sources_a = {"b.py": "x = 1", "a.py": "y = 2"}
        sources_b = {"a.py": "y = 2", "b.py": "x = 1"}
        assert compute_content_hash(sources_a) == compute_content_hash(sources_b)


class TestBumpPatch:
    def test_simple(self):
        assert bump_patch("1.0.0") == "1.0.1"

    def test_carries(self):
        assert bump_patch("1.0.9") == "1.0.10"


class TestManifest:
    def test_save_load_roundtrip(self, tmp_path: Path):
        manifest = Manifest(
            content_hash="abc123",
            version="1.0.0",
            extracted_at="2026-01-01T00:00:00+00:00",
            entry_points=["myapp.models:User"],
            modules=["myapp.models", "myapp.utils"],
        )
        path = tmp_path / ".pydistill-manifest.json"
        manifest.save(path)

        loaded = Manifest.load(path)
        assert loaded is not None
        assert loaded.content_hash == "abc123"
        assert loaded.version == "1.0.0"
        assert loaded.extracted_at == "2026-01-01T00:00:00+00:00"
        assert loaded.entry_points == ["myapp.models:User"]
        assert loaded.modules == ["myapp.models", "myapp.utils"]

    def test_load_missing_file(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        assert Manifest.load(path) is None


class TestResolveVersion:
    def test_first_extraction(self, tmp_path: Path):
        manifest_path = tmp_path / ".pydistill-manifest.json"
        version = resolve_version(
            manifest_path, "hash123", "1.0.0", VersionStrategy.AUTO_PATCH
        )
        assert version == "1.0.0"

    def test_unchanged_content(self, tmp_path: Path):
        manifest_path = tmp_path / ".pydistill-manifest.json"
        Manifest(
            content_hash="hash123",
            version="1.0.3",
            extracted_at="2026-01-01T00:00:00+00:00",
        ).save(manifest_path)

        version = resolve_version(
            manifest_path, "hash123", "1.0.0", VersionStrategy.AUTO_PATCH
        )
        assert version == "1.0.3"

    def test_changed_content(self, tmp_path: Path):
        manifest_path = tmp_path / ".pydistill-manifest.json"
        Manifest(
            content_hash="old_hash",
            version="1.0.3",
            extracted_at="2026-01-01T00:00:00+00:00",
        ).save(manifest_path)

        version = resolve_version(
            manifest_path, "new_hash", "1.0.0", VersionStrategy.AUTO_PATCH
        )
        assert version == "1.0.4"

    def test_manual_strategy(self, tmp_path: Path):
        manifest_path = tmp_path / ".pydistill-manifest.json"
        Manifest(
            content_hash="old_hash",
            version="1.0.3",
            extracted_at="2026-01-01T00:00:00+00:00",
        ).save(manifest_path)

        version = resolve_version(
            manifest_path, "new_hash", "5.0.0", VersionStrategy.MANUAL
        )
        assert version == "5.0.0"
