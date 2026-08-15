from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from .config import MODELS
from .nim_client import health_status, inspect_workspace
from .vision import build_contour_diff


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one visual inspection NIM smoke test")
    parser.add_argument("reference", type=Path)
    parser.add_argument("live", type=Path)
    parser.add_argument(
        "--model",
        choices=sorted(MODELS),
        default="reason2-8b",
    )
    args = parser.parse_args()

    model = MODELS[args.model]
    ready, detail = health_status(model)
    if not ready:
        raise SystemExit(f"{model.label} is not ready: {detail}")

    with Image.open(args.reference) as reference_image:
        reference = reference_image.convert("RGB")
    with Image.open(args.live) as live_image:
        live = live_image.convert("RGB")

    contour = build_contour_diff(reference, live)
    result = inspect_workspace(reference, live, contour, model)
    print(json.dumps(result.to_dict(), indent=2))
    if result.verdict == "UNKNOWN":
        raise SystemExit("NIM response did not contain a structured verdict")


if __name__ == "__main__":
    main()
