from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .config import MODELS
from .datasets import InspectionPair, build_index
from .evaluation import calculate_metrics
from .nim_client import health_status, inspect_workspace
from .vision import build_contour_diff


COLLECTIONS = {
    "all": None,
    "round1": "Round 1",
    "evaluation": "Workshop evaluation",
}
MODES = {
    "baseline": ("Baseline",),
    "contour": ("Contour-assisted",),
    "both": ("Baseline", "Contour-assisted"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vision-inspect",
        description="Run the visual inspection workshop from the terminal.",
    )
    parser.add_argument(
        "--data-root",
        default=os.getenv("VISUAL_INSPECTION_DATA_ROOT", "/data"),
        help="Organized inspection data root (default: VISUAL_INSPECTION_DATA_ROOT or /data).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show model and dataset readiness.")

    pairs = subparsers.add_parser("pairs", help="List labeled image pairs.")
    pairs.add_argument("--collection", choices=COLLECTIONS, default="all")
    pairs.add_argument("--category", default="All")
    pairs.add_argument("--limit", type=positive_int, default=50)

    inspect = subparsers.add_parser(
        "inspect",
        help="Run one pair and compare model reasoning.",
    )
    source = inspect.add_mutually_exclusive_group(required=True)
    source.add_argument("--pair", help="Pair ID from `vision-inspect pairs`.")
    source.add_argument("--reference", type=Path, help="Reference image path.")
    inspect.add_argument("--live", type=Path, help="Live image path with --reference.")
    inspect.add_argument("--expected", choices=("PASS", "FAIL"))
    add_inference_arguments(inspect, multiple_models=True, default_mode="both")

    round_one = subparsers.add_parser(
        "round1",
        help="Run the five curated examples in workshop order.",
    )
    add_inference_arguments(round_one, multiple_models=True, default_mode="baseline")
    round_one.add_argument("--limit", type=positive_int, default=5)

    batch = subparsers.add_parser(
        "batch",
        help="Evaluate a fixed sample from the larger labeled set.",
    )
    batch.add_argument("--category", default="All")
    batch.add_argument("--count", type=positive_int, default=10)
    add_inference_arguments(batch, multiple_models=False, default_mode="baseline")

    return parser


def positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def add_inference_arguments(
    parser: argparse.ArgumentParser,
    *,
    multiple_models: bool,
    default_mode: str,
) -> None:
    if multiple_models:
        parser.add_argument(
            "--models",
            nargs="+",
            choices=sorted(MODELS),
            default=["reason2-8b"],
        )
    else:
        parser.add_argument(
            "--model",
            choices=sorted(MODELS),
            default="reason2-8b",
        )
    parser.add_argument("--mode", choices=MODES, default=default_mode)
    parser.add_argument("--output", type=Path, help="Write complete JSON evidence.")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print complete raw model responses.",
    )


def selected_pairs(
    data_root: str,
    *,
    collection: str = "all",
    category: str = "All",
    limit: int | None = None,
) -> list[InspectionPair]:
    collection_label = COLLECTIONS[collection]
    pairs = [
        pair
        for pair in build_index(data_root)
        if (collection_label is None or pair.collection == collection_label)
        and (category == "All" or pair.category == category)
    ]
    return pairs[:limit] if limit is not None else pairs


def find_pair(data_root: str, pair_id: str) -> InspectionPair:
    pair = next((item for item in build_index(data_root) if item.pair_id == pair_id), None)
    if pair is None:
        raise SystemExit(f"Unknown pair ID: {pair_id}")
    return pair


def load_images(pair: InspectionPair) -> tuple[Image.Image, Image.Image]:
    with Image.open(pair.reference) as image:
        reference = image.convert("RGB")
    with Image.open(pair.live) as image:
        live = image.convert("RGB")
    return reference, live


def require_models(model_keys: list[str]) -> None:
    unavailable = []
    for key in model_keys:
        ready, detail = health_status(MODELS[key])
        if not ready:
            unavailable.append(f"{MODELS[key].label}: {detail}")
    if unavailable:
        raise SystemExit("Selected models are not ready:\n- " + "\n- ".join(unavailable))


def run_pair(
    pair: InspectionPair,
    model_keys: list[str],
    mode_key: str,
) -> dict:
    require_models(model_keys)
    reference, live = load_images(pair)
    contour = build_contour_diff(reference, live)
    runs = []
    for mode in MODES[mode_key]:
        selected_contour = contour if mode == "Contour-assisted" else None
        with ThreadPoolExecutor(max_workers=len(model_keys)) as executor:
            results = list(
                executor.map(
                    lambda key: inspect_workspace(
                        reference,
                        live,
                        selected_contour,
                        MODELS[key],
                    ),
                    model_keys,
                )
            )
        runs.extend(result.to_dict() for result in results)
    return {
        "pair": pair.to_dict(),
        "contour": {
            "regions": len(contour.regions),
            "changed_pixel_ratio": round(contour.changed_pixel_ratio, 6),
        },
        "results": runs,
    }


def print_pair_evidence(evidence: dict, *, raw: bool) -> None:
    pair = evidence["pair"]
    print(
        f"\n{pair['pair_id']} | {pair['scene']} | expected {pair['expected']} "
        f"| {pair['category']}"
    )
    print("-" * 96)
    for result in evidence["results"]:
        correct = "YES" if result["verdict"] == pair["expected"] else "NO"
        print(
            f"{result['model']} | {result['analysis_mode']} | "
            f"{result['verdict']} {result['confidence']} | correct {correct} | "
            f"{result['latency_seconds']:.3f}s"
        )
        print(f"  Changes: {result['changes']}")
        print(f"  Issues:  {result['issues']}")
        if raw:
            print("  Raw:")
            for line in result["raw_response"].splitlines():
                print(f"    {line}")


def write_evidence(path: Path | None, payload: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nEvidence written to {path}")


def command_status(data_root: str) -> int:
    pairs = build_index(data_root)
    print(f"Dataset: {len(pairs)} pairs at {data_root}")
    print(f"  Round 1: {sum(pair.collection == 'Round 1' for pair in pairs)}")
    print(
        "  Evaluation: "
        f"{sum(pair.collection == 'Workshop evaluation' for pair in pairs)}"
    )
    for key, model in MODELS.items():
        ready, detail = health_status(model)
        label = "READY" if ready else "OFF" if model.optional else "WAIT"
        suffix = "" if ready or model.optional else f" ({detail})"
        print(f"{label:5} {key:14} {model.label}{suffix}")
    return 0


def command_pairs(args: argparse.Namespace) -> int:
    pairs = selected_pairs(
        args.data_root,
        collection=args.collection,
        category=args.category,
        limit=args.limit,
    )
    if not pairs:
        print("No pairs matched.")
        return 1
    for pair in pairs:
        print(
            f"{pair.pair_id:20} {pair.expected:4} {pair.category:16} "
            f"{pair.collection:20} {pair.scene}"
        )
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    if args.pair:
        pair = find_pair(args.data_root, args.pair)
    else:
        if args.live is None:
            raise SystemExit("--live is required with --reference")
        pair = InspectionPair(
            pair_id="custom",
            collection="Custom",
            category="Other",
            expected=args.expected or "UNKNOWN",
            scene="Custom image pair",
            error_type="Custom",
            reference=str(args.reference),
            live=str(args.live),
        )
    if args.expected:
        pair = InspectionPair(**{**pair.to_dict(), "expected": args.expected})
    evidence = run_pair(pair, args.models, args.mode)
    print_pair_evidence(evidence, raw=args.raw)
    write_evidence(args.output, evidence)
    return 0


def command_round_one(args: argparse.Namespace) -> int:
    pairs = selected_pairs(
        args.data_root,
        collection="round1",
        limit=min(args.limit, 5),
    )
    if len(pairs) < min(args.limit, 5):
        raise SystemExit("The Round 1 collection is missing or incomplete.")
    evidence = [run_pair(pair, args.models, args.mode) for pair in pairs]
    for item in evidence:
        print_pair_evidence(item, raw=args.raw)
    payload = {"exercise": "Round 1", "runs": evidence}
    write_evidence(args.output, payload)
    return 0


def command_batch(args: argparse.Namespace) -> int:
    pairs = selected_pairs(
        args.data_root,
        collection="evaluation",
        category=args.category,
        limit=args.count,
    )
    if not pairs:
        raise SystemExit("No larger-set pairs matched the requested category.")
    runs = [run_pair(pair, [args.model], args.mode) for pair in pairs]
    records = [
        {
            **run["pair"],
            **result,
        }
        for run in runs
        for result in run["results"]
    ]
    metrics_by_mode = {}
    for mode in MODES[args.mode]:
        mode_records = [record for record in records if record["analysis_mode"] == mode]
        metrics_by_mode[mode] = calculate_metrics(mode_records)
    for item in runs:
        print_pair_evidence(item, raw=args.raw)
    print("\nSummary")
    print("-" * 72)
    for mode, metrics in metrics_by_mode.items():
        print(
            f"{mode:18} pairs {metrics['pairs']:3} | accuracy {metrics['accuracy']:.0%} "
            f"| precision {metrics['precision']:.0%} | recall {metrics['recall']:.0%} "
            f"| F1 {metrics['f1']:.0%}"
        )
    payload = {
        "exercise": "Larger set",
        "category": args.category,
        "model": args.model,
        "metrics": metrics_by_mode,
        "runs": runs,
    }
    write_evidence(args.output, payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return command_status(args.data_root)
    if args.command == "pairs":
        return command_pairs(args)
    if args.command == "inspect":
        return command_inspect(args)
    if args.command == "round1":
        return command_round_one(args)
    if args.command == "batch":
        return command_batch(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
