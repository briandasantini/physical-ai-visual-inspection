#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Download and activate a versioned visual inspection NGC resource."
    )
    parser.add_argument("--profile", default=os.getenv("VISUAL_INSPECTION_DATA_PROFILE", "workshop"))
    parser.add_argument(
        "--profiles",
        type=Path,
        default=script_dir.parent / "data" / "profiles.json",
    )
    parser.add_argument(
        "--data-home",
        type=Path,
        default=Path(
            os.getenv(
                "VISUAL_INSPECTION_DATA_HOME",
                str(Path.home() / "workspace" / "visual-inspection-data"),
            )
        ),
    )
    parser.add_argument("--resource", default=os.getenv("VISUAL_INSPECTION_DATA_RESOURCE"))
    parser.add_argument("--version", default=os.getenv("VISUAL_INSPECTION_DATA_VERSION"))
    parser.add_argument("--ngc", default=os.getenv("NGC_CLI", "ngc"))
    return parser.parse_args()


def load_profile(path: Path, name: str) -> dict:
    profiles = json.loads(path.read_text())["profiles"]
    try:
        return profiles[name]
    except KeyError as error:
        choices = ", ".join(sorted(profiles))
        raise SystemExit(f"Unknown data profile {name!r}; choose one of: {choices}") from error


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
        and not path.name.startswith(".visual-inspection-")
        and path.name != ".artifact-manifest.json"
    ]


def validate_dataset(dataset: Path, profile_name: str, profile: dict, version: str) -> dict:
    manifest_path = dataset / ".artifact-manifest.json"
    if not manifest_path.is_file():
        manifest_path = dataset.parent / "artifact-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Downloaded resource has no artifact-manifest.json")

    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 2:
        raise RuntimeError("Resource manifest must use schema version 2")
    if manifest.get("profile") != profile_name:
        raise RuntimeError(
            f"Resource profile is {manifest.get('profile')!r}, expected {profile_name!r}"
        )
    if manifest.get("version") != version:
        raise RuntimeError(
            f"Resource version is {manifest.get('version')!r}, expected {version!r}"
        )

    missing = [path for path in profile["required_paths"] if not (dataset / path).exists()]
    if missing:
        raise RuntimeError(f"Resource is missing required paths: {', '.join(missing)}")

    files = inventory(dataset)
    file_count = len(files)
    total_bytes = sum(item["bytes"] for item in files)
    if (
        file_count != manifest.get("file_count")
        or total_bytes != manifest.get("total_bytes")
        or files != manifest.get("files")
    ):
        raise RuntimeError(
            "Resource checksums do not match its manifest: "
            f"found {file_count} files/{total_bytes} bytes"
        )
    return manifest


def find_artifact(download_root: Path) -> Path:
    manifests = list(download_root.rglob("artifact-manifest.json"))
    if len(manifests) != 1:
        raise RuntimeError(
            f"Expected one artifact-manifest.json, found {len(manifests)}"
        )
    artifact_root = manifests[0].parent
    if not (artifact_root / "dataset").is_dir():
        raise RuntimeError("Downloaded resource has no dataset directory")
    return artifact_root


def activate(data_home: Path, target: Path) -> None:
    current = data_home / "current"
    if current.exists() and not current.is_symlink():
        raise RuntimeError(f"Refusing to replace non-symlink path: {current}")
    temporary_link = data_home / f".current.{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(target.relative_to(data_home), target_is_directory=True)
    temporary_link.replace(current)


def main() -> None:
    args = parse_args()
    profile = load_profile(args.profiles, args.profile)
    resource = args.resource or profile.get("resource")
    version = args.version or profile.get("version")
    if not resource:
        raise SystemExit(
            "No NGC data resource configured. Set VISUAL_INSPECTION_DATA_RESOURCE to "
            "<org>[/<team>]/<resource>."
        )
    if not version:
        raise SystemExit("No data version configured. Set VISUAL_INSPECTION_DATA_VERSION.")

    data_home = args.data_home.expanduser().resolve()
    safe_version = version.replace("/", "-")
    target = data_home / "versions" / args.profile / safe_version
    if target.is_dir():
        validate_dataset(target, args.profile, profile, version)
        activate(data_home, target)
        print(f"Visual inspection data already verified: {target}")
        return

    data_home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=data_home) as temporary:
        download_root = Path(temporary)
        subprocess.run(
            [
                args.ngc,
                "registry",
                "resource",
                "download-version",
                f"{resource}:{version}",
                "--dest",
                str(download_root),
            ],
            check=True,
        )
        artifact_root = find_artifact(download_root)
        dataset = artifact_root / "dataset"
        manifest = validate_dataset(dataset, args.profile, profile, version)

        target.parent.mkdir(parents=True, exist_ok=True)
        pending_target = target.parent / f".{safe_version}.{os.getpid()}"
        shutil.move(str(dataset), pending_target)
        shutil.copy2(
            artifact_root / "artifact-manifest.json",
            pending_target / ".artifact-manifest.json",
        )
        (pending_target / ".visual-inspection-artifact.json").write_text(
            json.dumps(
                {
                    "resource": resource,
                    "profile": args.profile,
                    "version": version,
                    "file_count": manifest["file_count"],
                    "total_bytes": manifest["total_bytes"],
                },
                indent=2,
            )
            + "\n"
        )
        validate_dataset(pending_target, args.profile, profile, version)
        pending_target.replace(target)

    activate(data_home, target)
    print(f"Visual inspection data downloaded and activated: {target}")


if __name__ == "__main__":
    main()
