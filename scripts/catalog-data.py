#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def summarize(collection: Path) -> dict:
    files = [path for path in collection.rglob("*") if path.is_file()]
    extensions = Counter(path.suffix.lower() or "[no extension]" for path in files)
    return {
        "path": str(collection),
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "extensions": dict(sorted(extensions.items())),
    }


def build_catalog(data_root: Path) -> dict:
    collections = []
    for category in ("raw", "derived", "archives"):
        category_path = data_root / category
        if not category_path.exists():
            continue
        children = sorted(path for path in category_path.iterdir() if not path.name.startswith("."))
        if category == "archives":
            collections.append(summarize(category_path))
            continue
        collections.extend(summarize(child) for child in children if child.is_dir())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "collections": collections,
        "totals": {
            "files": sum(item["files"] for item in collections),
            "bytes": sum(item["bytes"] for item in collections),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Catalog the organized visual inspection data tree")
    parser.add_argument("data_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    catalog = build_catalog(args.data_root.resolve())
    serialized = json.dumps(catalog, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
