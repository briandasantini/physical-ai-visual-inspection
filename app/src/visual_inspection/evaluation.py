from __future__ import annotations


def calculate_metrics(records: list[dict]) -> dict:
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
    return {
        "pairs": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def metrics_row(label: str, metrics: dict) -> list[str | int]:
    return [
        label,
        metrics["pairs"],
        f"{metrics['accuracy']:.0%}",
        f"{metrics['precision']:.0%}",
        f"{metrics['recall']:.0%}",
        f"{metrics['f1']:.0%}",
    ]
