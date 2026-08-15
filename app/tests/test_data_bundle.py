import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREPARE = load_script("prepare_data_bundle", "prepare-data-bundle.py")
FETCH = load_script("fetch_data", "fetch-data.py")
ORGANIZE = load_script(
    "organize_private_deliveries", "organize-private-deliveries.py"
)


class DataBundleTests(unittest.TestCase):
    def test_prepares_fetches_and_reuses_verified_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "private-data"
            round_one = data_root / "derived" / "round1"
            round_one.mkdir(parents=True)
            (round_one / "index.json").write_text('{"pairs": []}\n')
            (round_one / "image.png").write_bytes(b"image-data")

            profile = {
                "version": "test-version",
                "include_paths": ["derived/round1"],
                "required_paths": ["derived/round1"],
            }
            bundle = root / "workshop.tar"
            metadata = PREPARE.prepare_bundle(
                "workshop", profile, data_root, bundle, "test-version"
            )

            data_home = root / "cache"
            target = FETCH.fetch_profile(
                "workshop",
                profile,
                data_home,
                bundle.as_uri(),
                metadata["bundle_sha256"],
                "test-version",
            )
            self.assertEqual((target / "derived/round1/image.png").read_bytes(), b"image-data")
            self.assertEqual((data_home / "current").resolve(), target)

            reused = FETCH.fetch_profile(
                "workshop",
                profile,
                data_home,
                "https://expired.invalid/bundle.tar",
                metadata["bundle_sha256"],
                "test-version",
            )
            self.assertEqual(reused, target)

    def test_rejects_unsafe_tar_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "unsafe.tar"
            with tarfile.open(bundle, "w") as archive:
                info = tarfile.TarInfo("../outside")
                payload = b"unsafe"
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

            with self.assertRaisesRegex(RuntimeError, "Unsafe path"):
                FETCH.safe_extract(bundle, root / "output")

    def test_adds_sharepoint_download_hint_without_losing_query(self):
        url = "https://example.sharepoint.com/:u:/s/site/token?e=abc"

        normalized = FETCH.sharepoint_download_url(url)

        self.assertIn("e=abc", normalized)
        self.assertIn("download=1", normalized)

    def test_builds_private_ngc_resource_download_url(self):
        url = FETCH.ngc_download_url(
            "example-org/workshop-team/visual-inspection-data",
            "2026.08.15",
            "workshop bundle.tar",
        )

        self.assertEqual(
            url,
            "https://api.ngc.nvidia.com/v2/org/example-org/team/workshop-team/"
            "resources/visual-inspection-data/versions/2026.08.15/files/"
            "workshop%20bundle.tar",
        )

    def test_rejects_ngc_resource_without_team(self):
        with self.assertRaisesRegex(ValueError, "org/team/resource"):
            FETCH.ngc_download_url("example-org/resource", "1", "bundle.tar")

    def test_resolves_private_github_release_asset(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {"assets": [{"id": 123, "name": "workshop.tar"}]}
        ).encode()

        with mock.patch.object(
            FETCH.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            url = FETCH.github_release_asset_url(
                "example/data", "workshop-1", "workshop.tar", "test-token"
            )

        self.assertEqual(
            url,
            "https://api.github.com/repos/example/data/releases/assets/123",
        )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_rejects_invalid_github_repository(self):
        with self.assertRaisesRegex(ValueError, "owner/repository"):
            FETCH.github_release_asset_url(
                "example", "workshop-1", "workshop.tar", "test-token"
            )

    def test_private_ngc_download_uses_bearer_token(self):
        payload = b"private bundle"
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = [payload, b""]

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            FETCH.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            FETCH.download_bundle(
                "https://api.ngc.nvidia.com/resource.tar",
                Path(directory) / "bundle.tar",
                hashlib.sha256(payload).hexdigest(),
                source="NGC",
                bearer_token="test-token",
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_organizes_received_file_with_integrity_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "received.zip"
            source.write_bytes(b"archive")
            private_manifest = root / "deliveries.json"
            private_manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "deliveries": [
                            {
                                "source": str(source),
                                "destination": "received/originals/source.zip",
                                "record_received_file": True,
                                "integrity": "validated",
                            }
                        ],
                    }
                )
            )

            result = ORGANIZE.organize(private_manifest, root / "organized")

            self.assertEqual(result["file_count"], 1)
            self.assertEqual(result["files"][0]["integrity"], "validated")


if __name__ == "__main__":
    unittest.main()
