#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


IGNORED_NAMES = {".DS_Store"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize private source deliveries from an untracked manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def link_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def link_entry(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise RuntimeError(f"Refusing to organize symlink: {source}")
    if source.is_file():
        link_file(source, destination)
        return
    if not source.is_dir():
        raise FileNotFoundError(source)
    for child in sorted(source.rglob("*")):
        if child.name in IGNORED_NAMES or child.name.startswith("._"):
            continue
        if child.is_symlink():
            raise RuntimeError(f"Refusing to organize symlink: {child}")
        if child.is_file():
            link_file(child, destination / child.relative_to(source))


def organize(manifest_path: Path, output: Path) -> dict:
    payload = json.loads(manifest_path.expanduser().read_text())
    if payload.get("schema_version") != 1:
        raise ValueError("Private delivery manifest must use schema version 1")
    output = output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output must be empty or absent: {output}")
    output.mkdir(parents=True, exist_ok=True)
    output_root = output.resolve()

    records = []
    for entry in payload["deliveries"]:
        source = Path(entry["source"]).expanduser().resolve()
        destination = (output / entry["destination"]).resolve()
        destination.relative_to(output_root)
        if not source.exists():
            raise FileNotFoundError(source)
        link_entry(source, destination)

        if entry.get("record_received_file", False):
            if not destination.is_file():
                raise ValueError("record_received_file requires a file destination")
            records.append(
                {
                    "path": destination.relative_to(output_root).as_posix(),
                    "bytes": destination.stat().st_size,
                    "sha256": sha256(destination),
                    "integrity": entry.get("integrity", "unverified"),
                    "notes": entry.get("notes", ""),
                }
            )

    received_manifest = {
        "schema_version": 1,
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "files": records,
    }
    manifest_output = output / "manifests" / "received-files.json"
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(json.dumps(received_manifest, indent=2) + "\n")
    return received_manifest


def main() -> None:
    args = parse_args()
    manifest = organize(args.manifest, args.output)
    print(
        f"Organized {manifest['file_count']} original received files "
        f"({manifest['total_bytes']} bytes)"
    )
    print(args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
