#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def result_records(payload: dict) -> list[dict]:
    for value in payload.values():
        if isinstance(value, dict) and isinstance(value.get("results"), list):
            return value["results"]
    raise ValueError("The results JSON does not contain a model results list")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize a labeled evaluation set recorded in a results JSON file."
    )
    parser.add_argument("results_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records = result_records(json.loads(args.results_json.read_text()))
    if not records:
        raise SystemExit("The results JSON contains no evaluation pairs.")

    staging = args.output.with_name(f".{args.output.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    entries = []
    for index, record in enumerate(records, start=1):
        reference_source = Path(record["ref"])
        live_source = Path(record["live"])
        if not reference_source.is_file() or not live_source.is_file():
            raise FileNotFoundError(
                f"Missing source image for result {index}: {reference_source} or {live_source}"
            )
        pair_dir = staging / "pairs" / f"{index:04d}"
        pair_dir.mkdir(parents=True)
        reference_name = f"reference{reference_source.suffix.lower()}"
        live_name = f"live{live_source.suffix.lower()}"
        shutil.copy2(reference_source, pair_dir / reference_name)
        shutil.copy2(live_source, pair_dir / live_name)
        entries.append(
            {
                "pair_id": f"evaluation-{index:04d}",
                "collection": "Workshop evaluation",
                "category": record.get("category", "Other"),
                "expected": str(record.get("label", "FAIL")).upper(),
                "scene": record.get("scene", reference_source.parent.name),
                "error_type": record.get("error_type", record.get("category", "Other")),
                "reference": f"pairs/{index:04d}/{reference_name}",
                "live": f"pairs/{index:04d}/{live_name}",
            }
        )

    (staging / "index.json").write_text(
        json.dumps({"schema_version": 1, "pairs": entries}, indent=2) + "\n"
    )
    if args.output.exists():
        shutil.rmtree(args.output)
    staging.replace(args.output)
    print(f"Prepared the exact {len(entries)}-pair evaluation set at {args.output}")


if __name__ == "__main__":
    main()
