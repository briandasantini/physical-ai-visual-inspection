#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import tarfile
from pathlib import Path


IGNORED_NAMES = {".DS_Store"}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Create a verified visual-inspection data bundle for SharePoint."
    )
    parser.add_argument("profile")
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_files(data_root: Path, include_paths: list[str]) -> list[tuple[str, Path]]:
    selected: dict[str, Path] = {}
    for relative in include_paths:
        source = data_root / relative
        if not source.exists():
            raise FileNotFoundError(f"Required source path is missing: {source}")
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for candidate in candidates:
            if should_ignore(candidate):
                continue
            if candidate.is_symlink():
                raise RuntimeError(f"Refusing to package symlink: {candidate}")
            if not candidate.is_file():
                continue
            destination = candidate.relative_to(data_root).as_posix()
            selected[destination] = candidate
    return sorted(selected.items())


def inventory(files: list[tuple[str, Path]]) -> list[dict]:
    return [
        {
            "path": destination,
            "bytes": source.stat().st_size,
            "sha256": sha256(source),
        }
        for destination, source in files
    ]


def tar_info(name: str, size: int, mode: int = 0o644) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def prepare_bundle(
    profile_name: str,
    profile: dict,
    data_root: Path,
    output: Path,
    version: str,
) -> dict:
    data_root = data_root.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    files = selected_files(data_root, profile["include_paths"])
    file_inventory = inventory(files)
    manifest = {
        "schema_version": 3,
        "profile": profile_name,
        "version": version,
        "file_count": len(file_inventory),
        "total_bytes": sum(item["bytes"] for item in file_inventory),
        "include_paths": profile["include_paths"],
        "files": file_inventory,
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()

    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.with_name(f".{output.name}.{os.getpid()}.pending")
    with tarfile.open(pending, "w", format=tarfile.PAX_FORMAT) as bundle:
        bundle.addfile(
            tar_info("artifact-manifest.json", len(manifest_bytes)),
            io.BytesIO(manifest_bytes),
        )
        for destination, source in files:
            mode = stat.S_IMODE(source.stat().st_mode) & 0o666
            with source.open("rb") as payload:
                bundle.addfile(
                    tar_info(f"dataset/{destination}", source.stat().st_size, mode),
                    payload,
                )
    pending.replace(output)

    metadata = {
        "schema_version": 1,
        "profile": profile_name,
        "version": version,
        "bundle": output.name,
        "bundle_bytes": output.stat().st_size,
        "bundle_sha256": sha256(output),
        "file_count": manifest["file_count"],
        "dataset_bytes": manifest["total_bytes"],
    }
    output.with_suffix(output.suffix + ".json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    return metadata


def main() -> None:
    args = parse_args()
    profiles = json.loads(args.profiles.read_text())["profiles"]
    if args.profile not in profiles:
        choices = ", ".join(sorted(profiles))
        raise SystemExit(f"Unknown profile {args.profile!r}; choose one of: {choices}")
    profile = profiles[args.profile]
    version = args.version or profile["version"]
    metadata = prepare_bundle(
        args.profile,
        profile,
        args.data_root,
        args.output,
        version,
    )
    print(
        f"Prepared {metadata['profile']} bundle: {metadata['file_count']} files, "
        f"{metadata['dataset_bytes']} dataset bytes"
    )
    print(f"Bundle SHA-256: {metadata['bundle_sha256']}")
    print(args.output.expanduser().resolve())


if __name__ == "__main__":
    main()
