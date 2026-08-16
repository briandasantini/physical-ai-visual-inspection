from __future__ import annotations

import math
import re
import statistics


ACTION_SYNONYMS = {
    "ADDED": ("added", "extra", "unexpected", "foreign", "new object", "additional"),
    "REMOVED": ("removed", "missing", "absent", "gone", "no longer present"),
    "MOVED": ("moved", "shifted", "displaced", "misaligned", "offset", "position"),
    "TILTED": ("tilted", "rotated", "angled", "orientation", "not seated"),
    "REPLACED": ("replaced", "swapped", "exchanged", "different object", "wrong type"),
}

ITEM_SYNONYMS = {
    "tip box": ("diti", "tip box", "tip rack", "pipette tip", "tips"),
    "plate": ("plate", "microplate", "well plate", "assay plate"),
    "tube runner": ("tube runner", "tube rack", "tube", "runner", "vial"),
    "trough": ("trough", "reservoir", "liquid container"),
    "tray": ("tray", "holder", "rack"),
    "box": ("box", "container", "cartridge"),
    "tool": ("tool", "pliers", "foreign object"),
    "wash station": ("wash", "wash station"),
    "grid": ("grid", "segment", "section"),
    "waste": ("waste", "bin", "discard"),
    "labware": ("labware", "plate", "rack", "tray", "holder", "container"),
}

ROUND_ONE_SEMANTICS = {
    "r1_cd006": ("REMOVED", "plate"),
    "r1_cd016": ("REMOVED", "plate"),
    "r1_pliers": ("ADDED", "tool"),
    "r1_tilt": ("TILTED", "tray"),
}


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def expected_semantics(record: dict) -> tuple[str | None, str | None]:
    pair_id = str(record.get("pair_id", ""))
    if pair_id in ROUND_ONE_SEMANTICS:
        return ROUND_ONE_SEMANTICS[pair_id]

    source = f"{record.get('category', '')} {record.get('error_type', '')}".lower()
    if "tilt" in source or "rotate" in source:
        action = "TILTED"
    elif "replace" in source or "swap" in source or "exchange" in source:
        action = "REPLACED"
    elif "remove" in source or "missing" in source:
        action = "REMOVED"
    elif "shift" in source or "displace" in source or "move" in source:
        action = "MOVED"
    elif "add" in source:
        action = "ADDED"
    else:
        action = None

    normalized = re.sub(r"[^a-z0-9]+", " ", source)
    if "diti" in normalized or "tip" in normalized:
        item = "tip box"
    elif "trough" in normalized or "reservoir" in normalized:
        item = "trough"
    elif "tube" in normalized:
        item = "tube runner"
    elif "plate" in normalized:
        item = "plate"
    elif "wash" in normalized:
        item = "wash station"
    elif "waste" in normalized:
        item = "waste"
    elif "box" in normalized:
        item = "box"
    elif "grid" in normalized:
        item = "grid"
    elif "labware" in normalized:
        item = "labware"
    else:
        item = None
    return action, item


def score_semantics(record: dict) -> dict:
    expected_action, expected_item = expected_semantics(record)
    text = f"{record.get('changes', '')} {record.get('issues', '')}".lower()
    eligible = record.get("expected") == "FAIL" and record.get("verdict") == "FAIL"
    action_correct = (
        _contains_any(text, ACTION_SYNONYMS[expected_action])
        if eligible and expected_action
        else None
    )
    item_correct = (
        _contains_any(text, ITEM_SYNONYMS[expected_item])
        if eligible and expected_item
        else None
    )
    return {
        "expected_action": expected_action,
        "expected_item": expected_item,
        "action_correct": action_correct,
        "item_correct": item_correct,
    }


def add_semantic_scores(records: list[dict]) -> list[dict]:
    return [{**record, **score_semantics(record)} for record in records]


def _average(records: list[dict], key: str) -> float:
    values = [float(record[key]) for record in records if record.get(key) is not None]
    return round(statistics.fmean(values), 3) if values else 0.0


def _p95(records: list[dict], key: str) -> float:
    values = sorted(float(record[key]) for record in records if record.get(key) is not None)
    if not values:
        return 0.0
    return round(values[max(0, math.ceil(len(values) * 0.95) - 1)], 3)


def calculate_metrics(records: list[dict]) -> dict:
    records = add_semantic_scores(records)
    total = len(records)
    correct = sum(record.get("expected") == record.get("verdict") for record in records)
    true_positive = sum(
        record.get("expected") == "FAIL" and record.get("verdict") == "FAIL"
        for record in records
    )
    false_positive = sum(
        record.get("expected") == "PASS" and record.get("verdict") == "FAIL"
        for record in records
    )
    false_negative = sum(
        record.get("expected") == "FAIL" and record.get("verdict") != "FAIL"
        for record in records
    )
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    action_scores = [record["action_correct"] for record in records if record["action_correct"] is not None]
    item_scores = [record["item_correct"] for record in records if record["item_correct"] is not None]
    return {
        "pairs": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "action_total": len(action_scores),
        "action_accuracy": round(sum(action_scores) / len(action_scores), 4) if action_scores else 0.0,
        "item_total": len(item_scores),
        "item_accuracy": round(sum(item_scores) / len(item_scores), 4) if item_scores else 0.0,
        "avg_nim_seconds": _average(records, "latency_seconds"),
        "avg_preprocessing_seconds": _average(records, "preprocessing_seconds"),
        "avg_total_seconds": _average(records, "total_seconds"),
        "p95_total_seconds": _p95(records, "total_seconds"),
    }


def metrics_row(label: str, metrics: dict) -> list[str | int]:
    return [
        label,
        metrics["pairs"],
        f"{metrics['accuracy']:.0%}",
        f"{metrics['precision']:.0%}",
        f"{metrics['recall']:.0%}",
        f"{metrics['f1']:.0%}",
        f"{metrics['action_accuracy']:.0%} ({metrics['action_total']})",
        f"{metrics['item_accuracy']:.0%} ({metrics['item_total']})",
        f"{metrics['avg_nim_seconds']:.2f}s",
        f"{metrics['avg_preprocessing_seconds']:.2f}s",
        f"{metrics['avg_total_seconds']:.2f}s",
    ]
