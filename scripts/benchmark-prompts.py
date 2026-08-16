#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from openai import OpenAI
from PIL import Image

from visual_inspection.config import MODELS
from visual_inspection.datasets import build_index
from visual_inspection.evaluation import calculate_metrics, score_semantics
from visual_inspection.nim_client import (
    BASELINE_SYSTEM_PROMPT,
    _image_content,
    parse_response,
)


OUTPUT_RULES = """Return exactly this structure:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or at most three non-repeated lines beginning with REMOVED, ADDED, MOVED, TILTED, REPLACED, or FOREIGN OBJECT, followed by the visible object and relative position
ISSUES: one short grounded sentence, or None

Return FAIL for a verified physical difference and PASS only when the physical layouts match. Never return UNKNOWN. Ignore lighting, reflection, compression, and whole-image camera alignment differences."""


PROMPTS = {
    "inventory": BASELINE_SYSTEM_PROMPT,
    "concise-correspondence": f"""You compare two workspace images for physical setup differences.

IMAGE 1 is EXPECTED. IMAGE 2 is OBSERVED.

Compare corresponding locations directly. First decide whether the same physical objects occupy the same locations with the same orientation. Then check IMAGE 2 for an extra object. Report only differences supported by a visible mismatch between corresponding local regions. Do not infer a change from blur, glare, shadow, exposure, or a small camera shift.

Use REMOVED when an expected object is absent, ADDED or FOREIGN OBJECT when an extra object appears, MOVED when the same object changes position, TILTED when its orientation changes, and REPLACED when the object type changes.

{OUTPUT_RULES}""",
    "binary-then-localize": f"""Act as a conservative visual verification system.

IMAGE 1 is the expected setup and IMAGE 2 is the observed setup. Perform two passes:
1. Binary pass: determine whether there is at least one physical object-level difference.
2. Localization pass: if different, identify the single clearest changed object, action, and relative location. If there are multiple verified changes, list them separately.

Require direct visual evidence in both images before naming an action or object. A difference in pixels alone is not a physical difference. Check for missing objects, extra tools, displacement, orientation changes, and substitution.

{OUTPUT_RULES}""",
    "spatial-grid": f"""Verify the observed workspace against the expected workspace.

IMAGE 1 is EXPECTED. IMAGE 2 is OBSERVED. Mentally divide both images into a 3 by 3 grid. Compare each matching grid cell for object occupancy, object identity, position, and orientation. Use stable neighboring objects as anchors so that camera framing does not count as movement. After checking all cells, scan IMAGE 2 once for a small unexpected tool or object.

Report only a local physical discrepancy that remains after accounting for illumination, reflection, compression, and global alignment.

{OUTPUT_RULES}""",
    "evidence-ledger": f"""You are auditing whether an observed physical workspace matches an expected one.

IMAGE 1 is EXPECTED. IMAGE 2 is OBSERVED. Build an internal evidence ledger with one row per distinct expected object: relative location, visible feature, present in IMAGE 2, same position, and same orientation. Then add a final row for objects visible only in IMAGE 2. Do not print the ledger.

A failed check must be tied to a visible object and corresponding location. Prefer Low confidence over inventing an object identity, but still commit to PASS or FAIL.

{OUTPUT_RULES}""",
    "ordered-taxonomy": f"""Compare an expected physical workspace with an observed workspace.

IMAGE 1 is EXPECTED and IMAGE 2 is OBSERVED. Never reverse them. Run these checks in order:
1. Extra: visible in IMAGE 2 but not IMAGE 1. Use FOREIGN OBJECT for a tool and ADDED for labware.
2. Missing: visible in IMAGE 1 but absent from the matching location in IMAGE 2. Use REMOVED.
3. Orientation: the same object is present in both but its angle relative to neighboring rails or objects changed. Use TILTED.
4. Position: the same object is present in both but its center moved relative to neighboring objects. Use MOVED.
5. Identity: a different object occupies the same location. Use REPLACED.

Inspect small tools as well as plates, racks, trays, and holders. Report only the strongest directly visible differences and do not repeat a claim.

{OUTPUT_RULES}""",
    "anchor-taxonomy": f"""Perform a physical layout verification.

IMAGE 1 is EXPECTED. IMAGE 2 is OBSERVED. For each candidate difference, use two unchanged neighboring objects or deck features as anchors. A claim is valid only if the local object-to-anchor relationship differs between the images.

Check observed-only tools first, expected objects that disappeared second, orientation of racks and trays third, then displacement and replacement. Use FOREIGN OBJECT or ADDED for observed-only objects, REMOVED for expected-only objects, TILTED for an angle change of the same object, MOVED for a position change, and REPLACED for a different object in the same location.

Report no more than three distinct changes. Never repeat or restate a change.

{OUTPUT_RULES}""",
    "minimal-taxonomy": f"""IMAGE 1 is the expected workspace. IMAGE 2 is the observed workspace.

Find directly visible physical differences. Check for a small unexpected tool, missing labware, changed orientation, changed position, or a replacement. Never reverse expected and observed.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Report each change once.

{OUTPUT_RULES}""",
    "zone-taxonomy": f"""Verify IMAGE 2 against IMAGE 1. IMAGE 1 is EXPECTED and IMAGE 2 is OBSERVED.

Compare matching top-left, top-center, top-right, middle-left, middle-center, middle-right, bottom-left, bottom-center, and bottom-right regions. Within each region check object presence, identity, center position, and orientation. Finish with a separate scan for a small observed-only tool.

Classify direction carefully: expected-only is REMOVED; observed-only is ADDED or FOREIGN OBJECT; same object with a changed center is MOVED; same object with a changed angle is TILTED; different object in the same place is REPLACED. Keep only the three strongest non-repeated discrepancies.

{OUTPUT_RULES}""",
    "multiscale-taxonomy": f"""Compare IMAGE 2 against expected IMAGE 1 for physical setup discrepancies.

Inspect at three visual scales before deciding:
1. Large: overall occupied slots and large labware.
2. Medium: individual plates, racks, trays, and holders.
3. Small: hand tools, narrow gaps, object edges, and slight angle changes.

At every scale compare the same local position in both images. Expected-only means REMOVED. Observed-only means FOREIGN OBJECT for a tool or ADDED for labware. The same object with a changed angle is TILTED, with a changed center is MOVED, and a different object in the same slot is REPLACED. Do not convert lighting or camera alignment into a change.

Do not return PASS until all three scales have been checked. Report each verified change once, with no more than three changes.

{OUTPUT_RULES}""",
    "pass-gate": f"""IMAGE 1 is the expected physical workspace and IMAGE 2 is the observed workspace.

Generate candidate discrepancies by checking observed-only objects, expected-only objects, orientation, position, and identity. For each candidate, compare its exact local region in both images and reject it if the evidence is only lighting, reflection, blur, compression, or global camera shift.

PASS is allowed only after the full image has been scanned for a small foreign tool and every visible tray or rack has been checked for presence and orientation. Use REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED according to the direction of the verified difference. Report each change once.

{OUTPUT_RULES}""",
    "contrastive-proof": f"""Verify whether observed IMAGE 2 physically matches expected IMAGE 1.

For each possible change, first state internally the strongest evidence that it is real and then the strongest reason it might be a visual nuisance. Keep the candidate only when the local object evidence is stronger than the nuisance explanation. Search for missing labware, an added small tool, a shifted object, a tilted tray or rack, and replacement.

Never reverse image direction: expected-only is REMOVED, observed-only is ADDED or FOREIGN OBJECT, same object with angle change is TILTED, same object with center change is MOVED, and different identity in the same location is REPLACED. Do not print the internal proof and do not repeat a finding.

{OUTPUT_RULES}""",
    "minimal-ontology": f"""IMAGE 1 is the expected workspace. IMAGE 2 is the observed workspace.

Find directly visible physical differences. Check for a small unexpected hand tool, missing labware, changed orientation, changed position, or replacement. Never reverse expected and observed.

Use these generic object names when visually supported: plate for a flat rectangular multiwell item, tray or holder for a supporting platform, rack for an organized set of wells or tubes, and hand tool for a small non-labware implement. If the subtype is unclear, use labware rather than inventing a color-based identity.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Report each change once.

{OUTPUT_RULES}""",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=os.getenv("VISUAL_INSPECTION_DATA_ROOT", "/data"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=("reason2-2b", "reason2-8b"),
        default=["reason2-2b", "reason2-8b"],
    )
    parser.add_argument("--prompts", nargs="+", choices=tuple(PROMPTS), default=list(PROMPTS))
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--repeats", type=int, default=1)
    return parser.parse_args()


def inspect_with_prompt(
    reference: Image.Image,
    live: Image.Image,
    model_key: str,
    prompt: str,
    max_tokens: int,
):
    model = MODELS[model_key]
    client = OpenAI(base_url=model.base_url, api_key="not-needed", timeout=180.0)
    content = [
        {"type": "text", "text": "IMAGE 1 — EXPECTED:"},
        _image_content(reference),
        {"type": "text", "text": "IMAGE 2 — OBSERVED:"},
        _image_content(live),
        {
            "type": "text",
            "text": "Inspect the pair and commit to the required PASS or FAIL result.",
        },
    ]
    started_at = time.perf_counter()
    response = client.chat.completions.create(
        model=model.model_id,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=max_tokens,
        temperature=0.0,
    )
    latency = time.perf_counter() - started_at
    message = response.choices[0].message
    raw = message.content or getattr(message, "reasoning_content", "") or ""
    return parse_response(
        raw,
        model=model,
        latency_seconds=latency,
        contour=None,
        analysis_mode="Prompt benchmark",
    )


def main() -> int:
    args = parse_args()
    pairs = [pair for pair in build_index(args.data_root) if pair.collection == "Round 1"][:5]
    if len(pairs) != 5:
        raise SystemExit(f"Expected five Round 1 pairs, found {len(pairs)}")

    records = []
    summaries = []
    for prompt_name in args.prompts:
        for model_key in args.models:
            model_records = []
            for repeat in range(1, args.repeats + 1):
                for pair in pairs:
                    result = inspect_with_prompt(
                        Image.open(pair.reference).convert("RGB"),
                        Image.open(pair.live).convert("RGB"),
                        model_key,
                        PROMPTS[prompt_name],
                        args.max_tokens,
                    ).to_dict()
                    record = {
                        "prompt": prompt_name,
                        "model_key": model_key,
                        "repeat": repeat,
                        **pair.to_dict(),
                        **result,
                    }
                    record.update(score_semantics(record))
                    records.append(record)
                    model_records.append(record)
            metrics = calculate_metrics(model_records)
            summary = {"prompt": prompt_name, "model_key": model_key, **metrics}
            summaries.append(summary)
            print(
                f"{prompt_name:24} {model_key:11} "
                f"verdict={metrics['correct']}/{metrics['pairs']} "
                f"action={metrics['action_accuracy']:.0%}/{metrics['action_total']} "
                f"item={metrics['item_accuracy']:.0%}/{metrics['item_total']} "
                f"avg={metrics['avg_total_seconds']:.2f}s",
                flush=True,
            )

    payload = {
        "prompts": {name: PROMPTS[name] for name in args.prompts},
        "summaries": summaries,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
