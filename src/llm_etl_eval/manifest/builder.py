"""Pure builders for run manifests.

A manifest captures everything needed to reproduce a pipeline run:
git state, config/schema/inputs hashes, simulator settings, and a
sortable run id. It is written next to the evaluation report so each
run is auditable and comparable.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""

    return _sha256_bytes(path.read_bytes())


def _count_jsonl_records(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def file_descriptor(path: Path | None) -> dict[str, Any] | None:
    """Build a file descriptor (path, hash, size, optional record count).

    Returns None if `path` is None. Returns a stub with `exists=False`
    when the path is set but the file is missing — callers should treat
    that as a misconfigured run rather than failing hard.
    """

    if path is None:
        return None
    if not path.exists():
        return {"path": str(path), "exists": False}

    descriptor: dict[str, Any] = {
        "path": str(path),
        "exists": True,
        "sha256": file_hash(path),
        "size_bytes": path.stat().st_size,
    }
    if path.suffix.lower() == ".jsonl":
        descriptor["records"] = _count_jsonl_records(path)
    return descriptor


def _run_git(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def git_info(cwd: Path | None = None) -> dict[str, Any]:
    """Return git sha/branch/dirty for the given working tree.

    All fields are None when git is unavailable or the directory is
    not a repo, so the manifest is still valid in non-git contexts.
    """

    cwd = cwd or Path.cwd()
    sha = _run_git(["rev-parse", "HEAD"], cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    status = _run_git(["status", "--porcelain"], cwd)
    return {
        "sha": sha,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
    }


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class ManifestInputs:
    """Inputs for `build_manifest`. All paths are optional so the same
    builder works for partial pipeline stages (e.g., simulator-only)."""

    config_path: Path | None = None
    schema_path: Path | None = None
    inputs_path: Path | None = None
    outputs_path: Path | None = None
    gold_path: Path | None = None
    prompts_path: Path | None = None
    seed: int | None = None
    error_rate: float | None = None
    run_id: str | None = None
    label: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def build_manifest(args: ManifestInputs, *, cwd: Path | None = None) -> dict[str, Any]:
    """Build a manifest dict from the given inputs."""

    cwd = cwd or Path.cwd()
    return {
        "run_id": args.run_id or _default_run_id(),
        "label": args.label,
        "created_at": _utc_now_iso(),
        "git": git_info(cwd=cwd),
        "config": file_descriptor(args.config_path),
        "schema": file_descriptor(args.schema_path),
        "inputs": file_descriptor(args.inputs_path),
        "outputs": file_descriptor(args.outputs_path),
        "gold": file_descriptor(args.gold_path),
        "prompts": file_descriptor(args.prompts_path),
        "simulator": {
            "seed": args.seed,
            "error_rate": args.error_rate,
        },
        "extra": dict(args.extra),
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write a manifest JSON file with stable key order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
