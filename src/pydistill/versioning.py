"""Content-hash-based auto-versioning for extracted packages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class VersionStrategy(Enum):
    AUTO_PATCH = "auto-patch"
    MANUAL = "manual"


@dataclass
class Manifest:
    content_hash: str
    version: str
    extracted_at: str
    entry_points: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)

    def save(self, path: Path) -> None:
        data = {
            "content_hash": self.content_hash,
            "version": self.version,
            "extracted_at": self.extracted_at,
            "entry_points": self.entry_points,
            "modules": self.modules,
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Manifest | None:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            content_hash=data["content_hash"],
            version=data["version"],
            extracted_at=data["extracted_at"],
            entry_points=data.get("entry_points", []),
            modules=data.get("modules", []),
        )


def compute_content_hash(sources: dict[str, str]) -> str:
    """SHA-256 over sorted (module_path, content) pairs."""
    hasher = hashlib.sha256()
    for key in sorted(sources):
        hasher.update(key.encode("utf-8"))
        hasher.update(sources[key].encode("utf-8"))
    return hasher.hexdigest()


def bump_patch(version: str) -> str:
    """1.0.0 -> 1.0.1. Simple split on '.', increment last part."""
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def resolve_version(
    manifest_path: Path,
    content_hash: str,
    base_version: str,
    strategy: VersionStrategy,
) -> str:
    """Determine version based on strategy and existing manifest."""
    if strategy == VersionStrategy.MANUAL:
        return base_version

    existing = Manifest.load(manifest_path)
    if existing is None:
        return base_version

    if existing.content_hash == content_hash:
        return existing.version

    return bump_patch(existing.version)


def create_manifest(
    content_hash: str,
    version: str,
    entry_points: list[str],
    modules: list[str],
) -> Manifest:
    return Manifest(
        content_hash=content_hash,
        version=version,
        extracted_at=datetime.now(timezone.utc).isoformat(),
        entry_points=entry_points,
        modules=modules,
    )
