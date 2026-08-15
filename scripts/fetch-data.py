#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Download, verify, and activate an approved data bundle."
    )
    parser.add_argument(
        "--profile", default=os.getenv("VISUAL_INSPECTION_DATA_PROFILE", "workshop")
    )
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
    parser.add_argument(
        "--source",
        choices=("auto", "github", "ngc", "sharepoint"),
        default=os.getenv("VISUAL_INSPECTION_DATA_SOURCE", "auto"),
    )
    parser.add_argument(
        "--github-repository",
        default=os.getenv("VISUAL_INSPECTION_DATA_GITHUB_REPOSITORY"),
        help="Private GitHub repository in owner/repository form.",
    )
    parser.add_argument(
        "--github-release",
        default=os.getenv("VISUAL_INSPECTION_DATA_GITHUB_RELEASE"),
    )
    parser.add_argument(
        "--github-asset",
        default=os.getenv("VISUAL_INSPECTION_DATA_GITHUB_ASSET"),
    )
    parser.add_argument(
        "--ngc-resource",
        default=os.getenv("VISUAL_INSPECTION_DATA_NGC_RESOURCE"),
        help="Private NGC resource in org/team/resource form.",
    )
    parser.add_argument(
        "--ngc-filename",
        default=os.getenv("VISUAL_INSPECTION_DATA_NGC_FILENAME"),
    )
    parser.add_argument("--url", default=os.getenv("VISUAL_INSPECTION_DATA_URL"))
    parser.add_argument("--sha256", default=os.getenv("VISUAL_INSPECTION_DATA_SHA256"))
    parser.add_argument("--version", default=os.getenv("VISUAL_INSPECTION_DATA_VERSION"))
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
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
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
        raise RuntimeError("Downloaded bundle has no artifact-manifest.json")

    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 3:
        raise RuntimeError("Data bundle manifest must use schema version 3")
    if manifest.get("profile") != profile_name:
        raise RuntimeError(
            f"Bundle profile is {manifest.get('profile')!r}, expected {profile_name!r}"
        )
    if manifest.get("version") != version:
        raise RuntimeError(
            f"Bundle version is {manifest.get('version')!r}, expected {version!r}"
        )

    missing = [path for path in profile["required_paths"] if not (dataset / path).exists()]
    if missing:
        raise RuntimeError(f"Bundle is missing required paths: {', '.join(missing)}")

    files = inventory(dataset)
    file_count = len(files)
    total_bytes = sum(item["bytes"] for item in files)
    if (
        file_count != manifest.get("file_count")
        or total_bytes != manifest.get("total_bytes")
        or files != manifest.get("files")
    ):
        raise RuntimeError(
            "Bundle checksums do not match its manifest: "
            f"found {file_count} files/{total_bytes} bytes"
        )
    return manifest


def activate(data_home: Path, target: Path) -> None:
    current = data_home / "current"
    if current.exists() and not current.is_symlink():
        raise RuntimeError(f"Refusing to replace non-symlink path: {current}")
    temporary_link = data_home / f".current.{os.getpid()}"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(target.relative_to(data_home), target_is_directory=True)
    temporary_link.replace(current)


def sharepoint_download_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"https", "file"}:
        raise ValueError("Data URL must use HTTPS")
    if parsed.scheme == "file":
        return url
    hostname = (parsed.hostname or "").lower()
    if hostname.endswith("sharepoint.com") or hostname == "1drv.ms":
        query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        query.setdefault("download", "1")
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
        )
    return url


def ngc_download_url(resource: str, version: str, filename: str) -> str:
    parts = resource.strip("/").split("/")
    if len(parts) != 3 or any(not part or part in {".", ".."} for part in parts):
        raise ValueError(
            "VISUAL_INSPECTION_DATA_NGC_RESOURCE must use org/team/resource form"
        )
    org, team, resource_name = (
        urllib.parse.quote(part, safe="") for part in parts
    )
    encoded_version = urllib.parse.quote(version, safe="")
    encoded_filename = urllib.parse.quote(filename, safe="")
    return (
        f"https://api.ngc.nvidia.com/v2/org/{org}/team/{team}/resources/"
        f"{resource_name}/versions/{encoded_version}/files/{encoded_filename}"
    )


def github_release_asset_url(
    repository: str, release: str, asset_name: str, token: str
) -> str:
    parts = repository.strip("/").split("/")
    if len(parts) != 2 or any(not part or part in {".", ".."} for part in parts):
        raise ValueError(
            "VISUAL_INSPECTION_DATA_GITHUB_REPOSITORY must use owner/repository form"
        )
    owner, repository_name = (
        urllib.parse.quote(part, safe="") for part in parts
    )
    encoded_release = urllib.parse.quote(release, safe="")
    metadata_url = (
        f"https://api.github.com/repos/{owner}/{repository_name}/releases/tags/"
        f"{encoded_release}"
    )
    request = urllib.request.Request(
        metadata_url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "physical-ai-visual-inspection/1",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            release_metadata = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "GitHub release lookup failed. Confirm the repository, release, and token."
        ) from error

    for asset in release_metadata.get("assets", []):
        if asset.get("name") == asset_name and isinstance(asset.get("id"), int):
            return (
                f"https://api.github.com/repos/{owner}/{repository_name}/releases/"
                f"assets/{asset['id']}"
            )
    raise RuntimeError(f"GitHub release has no asset named {asset_name!r}")


def download_bundle(
    url: str,
    destination: Path,
    expected_sha256: str,
    *,
    source: str = "SharePoint",
    bearer_token: str | None = None,
    request_headers: dict[str, str] | None = None,
) -> None:
    headers = {"User-Agent": "physical-ai-visual-inspection/1"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if request_headers:
        headers.update(request_headers)
    request = urllib.request.Request(
        sharepoint_download_url(url),
        headers=headers,
    )
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=120) as response, destination.open(
            "wb"
        ) as output:
            for chunk in iter(lambda: response.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
                output.write(chunk)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            f"{source} download failed. Confirm the resource and credentials are valid."
        ) from error
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"Bundle SHA-256 mismatch: downloaded {actual}, expected {expected_sha256}"
        )


def safe_extract(bundle_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with tarfile.open(bundle_path, "r") as bundle:
        for member in bundle:
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination_root)
            except ValueError as error:
                raise RuntimeError(f"Unsafe path in data bundle: {member.name}") from error
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RuntimeError(f"Unsupported entry in data bundle: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = bundle.extractfile(member)
            if payload is None:
                raise RuntimeError(f"Could not read data bundle entry: {member.name}")
            with payload, target.open("wb") as output:
                shutil.copyfileobj(payload, output, length=8 * 1024 * 1024)
            target.chmod(member.mode & 0o666)


def fetch_profile(
    profile_name: str,
    profile: dict,
    data_home: Path,
    url: str,
    expected_sha256: str,
    version: str,
    *,
    source: str = "sharepoint",
    bearer_token: str | None = None,
    request_headers: dict[str, str] | None = None,
) -> Path:
    if len(expected_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_sha256.lower()
    ):
        raise ValueError("VISUAL_INSPECTION_DATA_SHA256 must be a 64-character SHA-256")
    expected_sha256 = expected_sha256.lower()
    data_home = data_home.expanduser().resolve()
    safe_version = version.replace("/", "-")
    target = data_home / "versions" / profile_name / safe_version
    if target.is_dir():
        validate_dataset(target, profile_name, profile, version)
        activate(data_home, target)
        print(f"Visual inspection data already verified: {target}")
        return target

    data_home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=data_home) as temporary:
        download_root = Path(temporary)
        bundle_path = download_root / "data-bundle.tar"
        extracted = download_root / "extracted"
        extracted.mkdir()
        source_label = {
            "github": "GitHub",
            "ngc": "NGC",
            "sharepoint": "SharePoint",
        }.get(source, "approved source")
        print(f"Downloading approved {source_label} data bundle...")
        download_bundle(
            url,
            bundle_path,
            expected_sha256,
            source=source_label,
            bearer_token=bearer_token,
            request_headers=request_headers,
        )
        try:
            safe_extract(bundle_path, extracted)
        except tarfile.TarError as error:
            raise RuntimeError(
                f"The {source_label} download did not return a valid data bundle."
            ) from error

        dataset = extracted / "dataset"
        manifest_path = extracted / "artifact-manifest.json"
        if not dataset.is_dir() or not manifest_path.is_file():
            raise RuntimeError("Downloaded bundle has an invalid directory layout")
        manifest = validate_dataset(dataset, profile_name, profile, version)

        target.parent.mkdir(parents=True, exist_ok=True)
        pending_target = target.parent / f".{safe_version}.{os.getpid()}"
        shutil.move(str(dataset), pending_target)
        shutil.copy2(manifest_path, pending_target / ".artifact-manifest.json")
        (pending_target / ".visual-inspection-artifact.json").write_text(
            json.dumps(
                {
                    "source": source,
                    "profile": profile_name,
                    "version": version,
                    "bundle_sha256": expected_sha256,
                    "file_count": manifest["file_count"],
                    "total_bytes": manifest["total_bytes"],
                },
                indent=2,
            )
            + "\n"
        )
        validate_dataset(pending_target, profile_name, profile, version)
        pending_target.replace(target)

    activate(data_home, target)
    print(f"Visual inspection data downloaded and activated: {target}")
    return target


def main() -> None:
    args = parse_args()
    profile = load_profile(args.profiles, args.profile)
    version = args.version or profile.get("version")
    expected_sha256 = args.sha256 or profile.get("bundle_sha256")
    if not version:
        raise SystemExit("No data version configured. Set VISUAL_INSPECTION_DATA_VERSION.")
    if not expected_sha256:
        raise SystemExit(
            "No bundle checksum configured. Set VISUAL_INSPECTION_DATA_SHA256."
        )

    source = args.source
    if source == "auto":
        if args.github_repository or profile.get("github_repository"):
            source = "github"
        elif args.ngc_resource:
            source = "ngc"
        else:
            source = "sharepoint"

    bearer_token = None
    request_headers = None
    if source == "github":
        repository = args.github_repository or profile.get("github_repository")
        release = args.github_release or profile.get("github_release")
        asset_name = args.github_asset or profile.get("github_asset")
        token = os.getenv("VISUAL_INSPECTION_DATA_GITHUB_TOKEN")
        if not repository:
            raise SystemExit(
                "No GitHub repository configured. Set "
                "VISUAL_INSPECTION_DATA_GITHUB_REPOSITORY."
            )
        if not release or not asset_name:
            raise SystemExit("No GitHub release or asset configured for this profile.")
        if not token:
            raise SystemExit(
                "VISUAL_INSPECTION_DATA_GITHUB_TOKEN is required to download private data."
            )
        url = github_release_asset_url(repository, release, asset_name, token)
        request_headers = {
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
        }
    elif source == "ngc":
        if not args.ngc_resource:
            raise SystemExit(
                "No NGC resource configured. Set VISUAL_INSPECTION_DATA_NGC_RESOURCE."
            )
        filename = args.ngc_filename or profile.get("ngc_filename")
        if not filename:
            raise SystemExit(
                "No NGC filename configured. Set VISUAL_INSPECTION_DATA_NGC_FILENAME."
            )
        bearer_token = os.getenv("NGC_API_KEY")
        if not bearer_token:
            raise SystemExit("NGC_API_KEY is required to download private NGC data.")
        url = ngc_download_url(args.ngc_resource, version, filename)
    else:
        url = args.url
        if not url:
            raise SystemExit(
                "No SharePoint data link configured. Set VISUAL_INSPECTION_DATA_URL to "
                "an approved download link."
            )

    fetch_profile(
        args.profile,
        profile,
        args.data_home,
        url,
        expected_sha256,
        version,
        source=source,
        bearer_token=bearer_token,
        request_headers=request_headers,
    )


if __name__ == "__main__":
    main()
