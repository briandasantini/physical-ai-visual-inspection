from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class InspectionPair:
    pair_id: str
    collection: str
    category: str
    expected: str
    scene: str
    error_type: str
    reference: str
    live: str

    def to_row(self) -> list[str]:
        return [
            self.pair_id,
            self.collection,
            self.category,
            self.expected,
            self.scene,
            self.error_type,
        ]

    def to_dict(self) -> dict:
        return asdict(self)


def broad_category(label: str) -> str:
    normalized = label.lower()
    if any(token in normalized for token in ("removed", "missing", "remove")):
        return "Remove"
    if any(token in normalized for token in ("added", "add", "with ")):
        return "Add"
    if any(
        token in normalized
        for token in ("replaced", "replace", "exchange", "swap", "color")
    ):
        return "Replace/Swap"
    if any(
        token in normalized
        for token in ("shifted", "shift", "moved", "move", "displace")
    ):
        return "Shift/Displace"
    if "illumin" in normalized:
        return "Illumination"
    return "Other"


def _pair_id(collection: str, reference: Path, live: Path) -> str:
    return f"{collection}:{reference.stem}:{live.stem}"


def discover_workshop_pairs(root: Path) -> list[InspectionPair]:
    pairs: list[InspectionPair] = []
    if not root.exists():
        return pairs
    for reference in sorted(root.glob("*_A_reference_ok.png")):
        live = reference.with_name(
            reference.name.replace("_A_reference_ok.png", "_B_test_error.png")
        )
        if live.exists():
            pairs.append(
                InspectionPair(
                    pair_id=_pair_id("workshop", reference, live),
                    collection="Workshop pairs",
                    category="Curated",
                    expected="FAIL",
                    scene=reference.stem.split("_A_")[0],
                    error_type="Curated error",
                    reference=str(reference),
                    live=str(live),
                )
            )
    return pairs


def discover_manifest_pairs(root: Path, default_collection: str) -> list[InspectionPair]:
    manifest = root / "index.json"
    if not manifest.exists():
        return []
    try:
        payload = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    entries = payload.get("pairs", []) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return []

    resolved_root = root.resolve()
    pairs: list[InspectionPair] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            reference = (root / entry["reference"]).resolve()
            live = (root / entry["live"]).resolve()
            reference.relative_to(resolved_root)
            live.relative_to(resolved_root)
        except (KeyError, OSError, ValueError):
            continue
        if not reference.exists() or not live.exists():
            continue
        expected = str(entry.get("expected", "FAIL")).upper()
        pairs.append(
            InspectionPair(
                pair_id=str(entry.get("pair_id", _pair_id("manifest", reference, live))),
                collection=str(entry.get("collection", default_collection)),
                category=str(entry.get("category", "Other")),
                expected=expected,
                scene=str(entry.get("scene", reference.parent.name)),
                error_type=str(entry.get("error_type", entry.get("category", "Other"))),
                reference=str(reference),
                live=str(live),
            )
        )
    return pairs


def _discover_json_scene(folder: Path) -> list[InspectionPair] | None:
    json_files = [
        path for path in folder.glob("*.json") if "ErrorConfidence" not in path.name
    ]
    if not json_files:
        return None
    try:
        data = json.loads(json_files[0].read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if "ValidationScenarios" not in data:
        return []

    image_dir = folder / "Images"
    scene = data.get("SceneName", folder.name)
    pairs: list[InspectionPair] = []
    for scenario in data["ValidationScenarios"]:
        for validation_scene in scenario.get("ValidationScenes", []):
            for detail in validation_scene.get("SceneDetails", []):
                reference = image_dir / detail["ReferenceImagePath"]
                live = image_dir / detail["ActualImagePath"]
                if not reference.exists() or not live.exists():
                    continue
                expected = "PASS" if detail.get("ExpectedPassResult", False) else "FAIL"
                error_type = (
                    detail["ActualImagePath"].split("_B_")[-1].removesuffix(".png")
                    if "_B_" in detail["ActualImagePath"]
                    else scene
                )
                pairs.append(
                    InspectionPair(
                        pair_id=_pair_id("core", reference, live),
                        collection="Core dataset",
                        category=broad_category(error_type) if expected == "FAIL" else "PASS",
                        expected=expected,
                        scene=scene,
                        error_type=error_type,
                        reference=str(reference),
                        live=str(live),
                    )
                )
    return pairs


def _discover_flat_scene(folder: Path) -> list[InspectionPair]:
    if not re.match(r"Scene \d+", folder.name):
        return []

    references: dict[tuple[str, str], Path] = {}
    live_images: dict[tuple[str, str], list[tuple[Path, str]]] = {}
    for image in sorted(folder.rglob("*.png")):
        if "_G_" in image.name:
            key = (image.parent.name, image.name.split("_G_")[0])
            references[key] = image
        elif "_B_" in image.name:
            prefix, error_part = image.name.split("_B_", maxsplit=1)
            error_type = re.sub(
                r"[-\s]+\d+$",
                "",
                error_part.removesuffix(".png"),
            ).strip()
            live_images.setdefault((image.parent.name, prefix), []).append(
                (image, error_type)
            )

    pairs: list[InspectionPair] = []
    for (camera, timestamp), candidates in live_images.items():
        camera_references = {
            key: path for key, path in references.items() if key[0] == camera
        }
        if not camera_references:
            camera_references = references
        reference_key = min(
            camera_references,
            key=lambda key: abs(len(key[1]) - len(timestamp)),
            default=None,
        )
        if reference_key is None:
            continue
        reference = camera_references[reference_key]
        for live, error_type in candidates:
            pairs.append(
                InspectionPair(
                    pair_id=_pair_id("core", reference, live),
                    collection="Core dataset",
                    category=broad_category(error_type),
                    expected="FAIL",
                    scene=folder.name,
                    error_type=error_type,
                    reference=str(reference),
                    live=str(live),
                )
            )

    for reference in references.values():
        pairs.append(
            InspectionPair(
                pair_id=_pair_id("core", reference, reference),
                collection="Core dataset",
                category=(
                    "Illumination" if "illumin" in folder.name.lower() else "PASS"
                ),
                expected="PASS",
                scene=folder.name,
                error_type="Identical",
                reference=str(reference),
                live=str(reference),
            )
        )
    return pairs


def discover_core_pairs(root: Path) -> list[InspectionPair]:
    if not root.exists():
        return []
    pairs: list[InspectionPair] = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        json_pairs = _discover_json_scene(folder)
        pairs.extend(
            _discover_flat_scene(folder) if json_pairs is None else json_pairs
        )
    return pairs


@lru_cache(maxsize=4)
def build_index(data_root: str) -> tuple[InspectionPair, ...]:
    root = Path(data_root)
    pairs = discover_manifest_pairs(root / "derived" / "round1", "Round 1")
    pairs.extend(
        discover_manifest_pairs(
            root / "derived" / "workshop-evaluation",
            "Workshop evaluation",
        )
    )
    workshop_root = root / "derived" / "workshop-pairs"
    if not workshop_root.exists():
        workshop_root = root / "examples"
    pairs.extend(discover_workshop_pairs(workshop_root))
    pairs.extend(discover_core_pairs(root / "raw" / "core"))
    unique = {pair.pair_id: pair for pair in pairs}
    return tuple(unique.values())


def filter_pairs(
    pairs: tuple[InspectionPair, ...],
    *,
    category: str = "All",
    query: str = "",
    limit: int = 200,
) -> list[InspectionPair]:
    normalized_query = query.strip().lower()
    filtered = []
    for pair in pairs:
        if category != "All" and pair.category != category:
            continue
        searchable = f"{pair.scene} {pair.error_type} {pair.collection}".lower()
        if normalized_query and normalized_query not in searchable:
            continue
        filtered.append(pair)
        if len(filtered) >= limit:
            break
    return filtered
