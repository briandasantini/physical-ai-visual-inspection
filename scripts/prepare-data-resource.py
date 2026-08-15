#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


IGNORED_NAMES = {".DS_Store"}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Stage approved visual inspection data as an NGC resource upload."
    )
    parser.add_argument("profile", choices=("workshop", "full"))
    parser.add_argument("data_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version")
    parser.add_argument(
        "--profiles",
        type=Path,
        default=script_dir.parent / "data" / "profiles.json",
    )
    return parser.parse_args()


def should_ignore(path: Path) -> bool:
    return path.name in IGNORED_NAMES or path.name.startswith("._")


def link_tree(source: Path, destination: Path) -> None:
    if source.is_symlink():
        raise RuntimeError(f"Refusing to package symlink: {source}")
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        for child in sorted(source.iterdir()):
            if not should_ignore(child):
                link_tree(child, destination / child.name)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> list[dict]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def main() -> None:
    args = parse_args()
    profiles = json.loads(args.profiles.read_text())["profiles"]
    profile = profiles[args.profile]
    version = args.version or profile["version"]
    data_root = args.data_root.expanduser().resolve()
    output = args.output.expanduser().resolve()

    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty or absent: {output}")

    dataset = output / "dataset"
    for relative in profile["include_paths"]:
        source = data_root / relative
        if not source.exists():
            raise SystemExit(f"Required source path is missing: {source}")
        link_tree(source, dataset / relative)

    files = inventory(dataset)
    manifest = {
        "schema_version": 2,
        "profile": args.profile,
        "version": version,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "include_paths": profile["include_paths"],
        "files": files,
    }
    (output / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(
        f"Prepared {args.profile} resource: {manifest['file_count']} files, "
        f"{manifest['total_bytes']} bytes"
    )
    print(output)


if __name__ == "__main__":
    main()
