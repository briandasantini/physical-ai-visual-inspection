#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageDraw, ImageOps

from visual_inspection.config import MODELS
from visual_inspection.datasets import build_index
from visual_inspection.evaluation import calculate_metrics, score_semantics
from visual_inspection.nim_client import (
    BASELINE_SYSTEM_PROMPT,
    INSPECTION_SCOPE,
    INSPECTION_SCOPE_REMINDER,
    _image_content,
    parse_response,
)
from visual_inspection.vision import build_contour_diff


OUTPUT_RULES = """Return exactly this structure:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or at most three non-repeated lines beginning with REMOVED, ADDED, MOVED, TILTED, REPLACED, or FOREIGN OBJECT, followed by the visible object and relative position
ISSUES: one short grounded sentence, or None

Return FAIL for a verified physical difference and PASS only when the physical layouts match. Never return UNKNOWN. Ignore lighting, reflection, compression, and whole-image camera alignment differences."""


ONE_CHANGE_OUTPUT_RULES = """Return exactly these four fields and nothing else:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or exactly one line: - ACTION — generic object — relative location
ISSUES: one short sentence using the same action and object, or None

ACTION must be REMOVED, ADDED, FOREIGN OBJECT, MOVED, TILTED, or REPLACED. Never list the same discrepancy twice. Never report both removal and addition for one corresponding object. Return FAIL when the one verified discrepancy is physical; otherwise return PASS. Never return UNKNOWN."""


CONTOUR_GUIDANCE = """IMAGE 3 is IMAGE 2 with red boxes around candidate pixel-difference regions. The boxes may be broad, duplicated, or caused by nuisance pixels. They are attention hints, not evidence and not physical objects.

For each box, compare the exact same local coordinates in IMAGE 1 and IMAGE 2. Name only the physical object whose presence, identity, center, or angle actually differs. Ignore the red graphics and unchanged objects that merely fall inside a large box. If no boxed candidate is verified, inspect outside the boxes before returning PASS."""


DETAIL_GUIDANCE = """IMAGE 3 is an automatically generated DETAIL SHEET. Each numbered row repeats the exact same candidate region: EXPECTED IMAGE 1 is on the left and OBSERVED IMAGE 2 is on the right. The text labels and borders are annotations, not objects.

Compare left with right within each row. Use the full images to confirm context. Never compare IMAGE 2 with IMAGE 3 as if they were different workspace states: the right-hand detail is only a magnified copy of IMAGE 2. A detail row is an attention hint, not proof; ignore nuisance lighting and return PASS if no physical object differs."""


CROP_GUIDANCE = """After the full images, the user supplies numbered candidate crop pairs. Each EXPECTED CROP comes from IMAGE 1 and the immediately following OBSERVED CROP comes from the exact same coordinates in IMAGE 2. Compare only within each numbered pair. Crops are magnified attention hints, not additional workspace states and not proof of a physical change. Use the full images for context and ignore lighting nuisances."""


MODEL_MAX_TOKENS = {
    "reason2-2b": 192,
    "reason2-8b": 256,
    "cosmos3-nano": 256,
}


PROMPT_MAX_TOKENS = {
    "reason2-2b-cot-proof": 768,
    "reason2-8b-cot-proof": 1024,
    "nano-cot-domain": 768,
}


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
3. Small: inanimate tools resting on the deck, narrow gaps, object edges, and slight angle changes.

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

Find directly visible physical differences. Check for a small unexpected inanimate tool resting on the deck, missing labware, changed orientation, changed position, or replacement. Never reverse expected and observed.

Use these generic object names when visually supported: plate for a flat rectangular multiwell item, tray or holder for a supporting platform, rack for an organized set of wells or tubes, and tool for a small inanimate non-labware implement resting on the deck. If the subtype is unclear, use labware rather than inventing a color-based identity.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Report each change once.

{OUTPUT_RULES}""",
    "single-candidate": f"""Compare two physical workspace photographs.

IMAGE 1 is EXPECTED. IMAGE 2 is OBSERVED. If the images show the same physical layout, return PASS. Otherwise report exactly the single strongest local object-level discrepancy.

For the candidate, silently determine two facts: E = object visible at that location in EXPECTED; O = object visible at the same location in OBSERVED. Classify only from this table:
- E yes, O no: REMOVED.
- E no, O yes: FOREIGN OBJECT for an inanimate tool resting on the deck, otherwise ADDED.
- E yes, O yes, same object but angle changed: TILTED.
- E yes, O yes, same object but center changed: MOVED.
- E yes, O yes, different object type: REPLACED.

Never reverse IMAGE 1 and IMAGE 2. Do not compare unrelated objects from different locations. Ignore color, exposure, reflection, shadow, blur, compression, and global camera framing. Use generic nouns such as plate, tray, rack, labware, or tool rather than inventing a subtype.

{ONE_CHANGE_OUTPUT_RULES}""",
    "direction-gate": f"""Verify observed IMAGE 2 against expected IMAGE 1.

First check whether the two images are physically identical. If they are, return PASS without inventing movement. If not, find one candidate and compare its exact local region in both images.

Before choosing an action, silently answer:
1. What object is visible here in IMAGE 1?
2. What object is visible at the same place in IMAGE 2?
3. Is the difference presence, identity, center position, or angle?

Expected-only is always REMOVED. Observed-only is always ADDED, except use FOREIGN OBJECT for an inanimate tool resting on the deck. The same object with a changed angle is TILTED; with a changed center it is MOVED. A different object in the same slot is REPLACED. Do not call an expected-only object ADDED. Do not call an observed-only object REMOVED.

Search empty slots and plate/rack occupancy, then narrow gaps for a small tool, then long tray edges for an angle change. Require local visible evidence and ignore illumination or whole-image alignment.

{ONE_CHANGE_OUTPUT_RULES}""",
    "correspondence-map": f"""Audit whether IMAGE 2 matches expected IMAGE 1.

Silently pair each visible object in IMAGE 1 with the object at the corresponding location in IMAGE 2, using neighboring deck rails and unchanged labware as anchors. Then perform one scan for an object visible only in IMAGE 2. Keep only the strongest verified mismatch.

An unmatched expected object is REMOVED. An unmatched observed inanimate tool resting on the deck is FOREIGN OBJECT; other unmatched observed labware is ADDED. A matched object with a changed angle is TILTED, with a changed center is MOVED, and with a different identity is REPLACED. Do not turn one mismatch into multiple actions.

Check large labware occupancy, small inanimate tools resting on the deck in gaps, and tray-edge orientation. Reject glare, shadow, exposure, compression, color cast, and global camera offset.

{ONE_CHANGE_OUTPUT_RULES}""",
    "compact-sensitive": f"""IMAGE 1 = EXPECTED. IMAGE 2 = OBSERVED.

If the physical layouts are identical, PASS. Otherwise report one strongest physical difference only. Compare the same location in both images.

Presence rule: expected only -> REMOVED; observed only -> FOREIGN OBJECT for an inanimate tool resting on the deck or ADDED for labware. Same object: changed angle -> TILTED; changed center -> MOVED. Different object in the same slot -> REPLACED.

Check one missing plate or rack, one small unexpected tool in a gap, and one visibly angled tray before allowing PASS. Ignore lighting, shadows, glare, blur, and camera framing. Use a generic visible object name. Do not repeat or elaborate.

{ONE_CHANGE_OUTPUT_RULES}""",
    "reason2-2b-compact-proof": """Compare expected IMAGE 1 with observed IMAGE 2. Find at most one real physical discrepancy.

Decide object presence before comparing color. At the candidate's same location:
- object in IMAGE 1 and empty in IMAGE 2 = REMOVED
- empty in IMAGE 1 and object in IMAGE 2 = FOREIGN OBJECT for an inanimate tool resting on the deck, otherwise ADDED
- same object in both, but angle differs = TILTED
- same object in both, but center differs = MOVED
- different physical object in the same slot = REPLACED

Use only the generic nouns plate, tool, tray, rack, or labware. A flat rectangular well item is a plate. A pliers-like implement is a tool. A rectangular support or holder is a tray. Never use color as the object's identity. Ignore lighting and whole-image camera shift.

Reply with only these four fields. Do not copy instructions, add placeholders, enumerate alternatives, or repeat text.
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
ISSUES: None

For a failure, replace the two None values with one action/object/location line and one evidence sentence. The evidence sentence must say what is present at the same location in IMAGE 1 and IMAGE 2.""",
    "reason2-2b-worked-proof": """Verify observed IMAGE 2 against expected IMAGE 1. Report one strongest physical difference, or PASS when there is none.

Use these classification examples as rules:
- expected plate, observed empty -> REMOVED plate
- expected empty, observed pliers or another inanimate implement resting on the deck -> FOREIGN OBJECT tool
- same tray in both, observed tray has a different angle -> TILTED tray
- same object with a different center -> MOVED
- different object in the same occupied slot -> REPLACED

Compare the exact same location; never reverse the images. Search occupied labware slots, narrow gaps for a small tool, and long tray edges. Ignore glare, shadow, exposure, blur, compression, color variation, and global camera alignment.

Return only four fields in this form:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
ISSUES: None

If FAIL, replace None after CHANGES with exactly one dash line beginning REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED. Replace the final None with one short same-location evidence sentence. Do not repeat, list choices, or print any other text.""",
    "reason2-8b-sensitive-proof": """Perform a high-sensitivity physical layout audit of observed IMAGE 2 against expected IMAGE 1.

Before returning PASS, inspect every corresponding region at three scales: occupied labware slots; individual plates, racks, and trays; then narrow gaps for a small pliers-like inanimate tool resting on the deck and long tray edges for a slight angle change. A small but clearly visible object or angle change is a real discrepancy. Ignore illumination, reflections, compression, and global camera offset.

For the single strongest candidate, establish the same-location state in this order: what physical object is present in expected IMAGE 1, what is present in observed IMAGE 2, then whether the difference is presence, angle, center, or identity. Apply exactly:
- expected-only: REMOVED
- observed-only inanimate implement resting on the deck: FOREIGN OBJECT tool
- other observed-only object: ADDED
- same object, different angle: TILTED
- same object, different center: MOVED
- different object in the same slot: REPLACED

Use stable generic nouns: plate for flat rectangular well labware, tool for pliers or another inanimate implement resting on the deck, tray for a rectangular support or holder, rack, or labware. Do not identify an object by color. Never reverse expected and observed.

Return exactly RESULT, CONFIDENCE, CHANGES, and ISSUES. Under CHANGES write either one line '- None' or one dash line starting with the action, then object and relative location. ISSUES must be None for PASS; for FAIL it must contrast the same location in IMAGE 1 and IMAGE 2. Report one change only and no other prose.""",
    "reason2-8b-two-stage": """IMAGE 1 is expected. IMAGE 2 is observed. Audit physical object layout in two mandatory stages.

Stage 1, detection: compare corresponding large objects, then inspect for a small unexpected inanimate tool resting on the deck, then compare the orientation of each long rectangular tray or holder. Do not allow the small size or subtle angle of a clearly visible change to make it PASS.

Stage 2, direction: at the strongest changed location, describe the expected state first and observed state second. Expected object then observed empty means REMOVED. Expected empty then observed tool means FOREIGN OBJECT tool. Expected and observed same tray with changed angle means TILTED tray. A changed center means MOVED; a different item in one slot means REPLACED. Ignore color, lighting, shadow, glare, and global framing.

Output only:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
ISSUES: None

For FAIL, replace the two None values with exactly one classified change and one sentence contrasting the same location in expected then observed. Never list more than one change or any intermediate reasoning.""",
    "reason2-2b-cot-proof": """You are a precise visual workspace inspection assistant. Follow the user's expected-versus-observed directions and put the structured verdict only inside the answer block.""",
    "reason2-8b-cot-proof": """You are a high-sensitivity visual workspace inspection assistant. Follow the user's expected-versus-observed directions and put the structured verdict only inside the answer block.""",
    "nano-domain-direct": """Inspect observed IMAGE 2 against expected IMAGE 1 for one physical deck discrepancy. Compare the same location and report one strongest change.

Use deck occupancy, not color. A well-pattern plate in expected and a flat featureless gray carrier in observed means REMOVED plate; the exposed carrier is not added or replaced. An object only in observed is FOREIGN OBJECT tool if it is a small pliers-like inanimate tool resting on the deck, otherwise ADDED. The same rectangular tray rotated relative to slot rails is TILTED tray. A changed center is MOVED; a genuinely different physical item in the same occupied slot is REPLACED.

Colored outlines and red boxes are annotations, not objects. A tool independently resting on the deck is a deck object. In a broad red box, scan for a small dark or silver two-handled tool as well as large labware. Ignore lighting, glare, blur, and camera shift.

Return only RESULT, CONFIDENCE, CHANGES, and ISSUES. CHANGES is '- None' for PASS or exactly one line beginning REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED. ISSUES is None for PASS or one expected-then-observed evidence sentence for FAIL.""",
    "nano-occupancy-direct": """IMAGE 1 is expected; IMAGE 2 is observed. Check one candidate region at a time and keep only the strongest physical mismatch.

Ask: is a raised grid/well-pattern labware item present at this exact slot in expected, and what occupies the same slot in observed? Expected labware followed by bare flat metal/plastic carrier is REMOVED plate. Bare expected slot followed by a small pliers-like implement on the deck is FOREIGN OBJECT tool. If the same tray remains but its long edge changes angle relative to the parallel deck rails, use TILTED tray. Use MOVED only for a changed center and REPLACED only when two different raised objects occupy the same slot. Never classify exposed deck, colored outlines, or red annotations as objects.

Before PASS, scan inside broad candidate boxes for a small dark/silver inanimate tool resting on the deck and compare each rectangular tray edge with nearby rails. Ignore illumination, glare, blur, and global alignment.

Output exactly four fields: RESULT, CONFIDENCE, CHANGES, ISSUES. Report one change. Use the generic noun plate, tool, tray, rack, or labware. No extra prose.""",
    "nano-cot-domain": """You are a careful Tecan deck inspection assistant. Follow the user's direction and put only the structured verdict in the answer block.""",
}


USER_PROMPTS = {
    "reason2-2b-cot-proof": """IMAGE 1 is EXPECTED and IMAGE 2 is OBSERVED. Decide if their physical object layouts match. Check occupied labware slots, small inanimate tools resting on the deck in gaps, and tray angles. Ignore lighting, shadows, reflections, blur, color variation, and global camera shift.

At the strongest candidate, compare the same location. Expected object and observed empty means REMOVED. Expected empty and observed pliers-like implement means FOREIGN OBJECT tool. Other observed-only means ADDED. The same tray at a different angle means TILTED tray. A changed center means MOVED. A different object in one slot means REPLACED. Use generic nouns plate, tool, tray, rack, or labware; do not identify by color. Report one change only.

Answer the question in the following format:
<think>
In at most 100 words, verify the strongest same-location candidate and its direction. Do not repeat.
</think>
<answer>
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None, or one line beginning with REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED
ISSUES: None, or one short expected-then-observed evidence sentence
</answer>""",
    "reason2-8b-cot-proof": """IMAGE 1 is EXPECTED and IMAGE 2 is OBSERVED. Determine whether the physical layouts match. Before PASS, compare occupied slots, individual plates/racks/trays, narrow gaps for a small pliers-like tool, and long tray edges for a subtle angle change. Small but visible differences count. Ignore illumination, reflection, blur, compression, color variation, and global camera offset.

For the strongest candidate, inspect the exact same location and classify only after stating expected state then observed state. Expected-only means REMOVED. Observed-only pliers or another inanimate implement resting on the deck means FOREIGN OBJECT tool; other observed-only means ADDED. Same tray with changed angle means TILTED tray. Changed center means MOVED. Different item in the same slot means REPLACED. Use generic nouns plate, tool, tray, rack, or labware. Report exactly one change.

Answer the question in the following format:
<think>
In at most 160 words, scan all three scales, then verify one same-location candidate and its direction. Do not speculate or repeat.
</think>
<answer>
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None, or one line beginning with REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED
ISSUES: None, or one short expected-then-observed evidence sentence
</answer>""",
    "nano-cot-domain": """IMAGE 1 is expected and IMAGE 2 is observed. Find one strongest physical deck discrepancy. A raised well-pattern plate in expected followed by bare flat carrier in observed is REMOVED plate. A small pliers-like inanimate implement independently resting on the deck only in observed is FOREIGN OBJECT tool. The same tray rotated relative to deck rails is TILTED tray. Exposed carriers, colored outlines, and red boxes are not objects. Ignore lighting, glare, blur, and camera shift. Before PASS, check occupied slots, broad candidate regions for a small tool, and tray edges.

Answer the question using the following format:
<think>
In under 100 words, compare one exact location in expected then observed and classify its occupancy or angle.
</think>
<answer>
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES: - None, or one line starting REMOVED, FOREIGN OBJECT, ADDED, TILTED, MOVED, or REPLACED
ISSUES: None, or one expected-then-observed evidence sentence
</answer>""",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=os.getenv("VISUAL_INSPECTION_DATA_ROOT", "/data"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=tuple(MODELS),
        default=["reason2-2b", "reason2-8b"],
    )
    parser.add_argument("--prompts", nargs="+", choices=tuple(PROMPTS), default=list(PROMPTS))
    parser.add_argument(
        "--mode",
        choices=("baseline", "contour", "detail", "crops"),
        default="baseline",
    )
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    return parser.parse_args()


def inspect_with_prompt(
    reference: Image.Image,
    live: Image.Image,
    model_key: str,
    prompt: str,
    max_tokens: int,
    contour=None,
    benchmark_mode: str = "baseline",
    user_prompt: str | None = None,
    crop_pairs=(),
):
    model = MODELS[model_key]
    client = OpenAI(base_url=model.base_url, api_key="not-needed", timeout=180.0)
    prompt = f"{prompt}\n\n{INSPECTION_SCOPE}"
    content = [
        {"type": "text", "text": "IMAGE 1 — EXPECTED:"},
        _image_content(reference),
        {"type": "text", "text": "IMAGE 2 — OBSERVED:"},
        _image_content(live),
    ]
    if benchmark_mode == "crops":
        for index, (expected_crop, observed_crop) in enumerate(crop_pairs, start=1):
            content.extend(
                [
                    {"type": "text", "text": f"REGION {index} — EXPECTED CROP:"},
                    _image_content(expected_crop),
                    {"type": "text", "text": f"REGION {index} — OBSERVED CROP:"},
                    _image_content(observed_crop),
                ]
            )
        guidance = CROP_GUIDANCE
        if user_prompt is None:
            prompt = f"{prompt}\n\n{guidance}"
        else:
            user_prompt = f"{user_prompt}\n\n{guidance}"
    elif contour is not None:
        content.extend(
            [
                {"type": "text", "text": "IMAGE 3 — CONTOUR VIEW:"},
                _image_content(contour.image),
            ]
        )
        guidance = DETAIL_GUIDANCE if benchmark_mode == "detail" else CONTOUR_GUIDANCE
        if user_prompt is None:
            prompt = f"{prompt}\n\n{guidance}"
        else:
            user_prompt = f"{user_prompt}\n\n{guidance}"
    content.append(
        {
            "type": "text",
            "text": (
                f"{INSPECTION_SCOPE_REMINDER}\n\n"
                f"{user_prompt or 'Inspect the pair and commit to the required PASS or FAIL result.'}"
            ),
        }
    )
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
        contour=contour,
        analysis_mode=(
            f"{benchmark_mode.title()} prompt benchmark"
        ),
    )


def build_detail_sheet(reference: Image.Image, live: Image.Image, contour):
    rows = []
    for index, region in enumerate(contour.regions[:3], start=1):
        padding = 14
        left = max(0, region.x - padding)
        top = max(0, region.y - padding)
        right = min(reference.width, region.x + region.width + padding)
        bottom = min(reference.height, region.y + region.height + padding)
        rows.append(
            (
                index,
                reference.crop((left, top, right, bottom)),
                live.crop((left, top, right, bottom)),
            )
        )
    if not rows:
        return contour

    panel_width = 480
    panel_height = 360
    label_height = 36
    row_height = label_height + panel_height + 12
    sheet = Image.new("RGB", (panel_width * 2 + 36, row_height * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for row_index, (region_index, expected_crop, observed_crop) in enumerate(rows):
        y = row_index * row_height
        draw.text((8, y + 10), f"REGION {region_index} EXPECTED", fill="black")
        draw.text((panel_width + 28, y + 10), f"REGION {region_index} OBSERVED", fill="black")
        for column, crop in enumerate((expected_crop, observed_crop)):
            fitted = ImageOps.contain(
                crop.convert("RGB"),
                (panel_width, panel_height),
                method=Image.Resampling.LANCZOS,
            )
            panel = Image.new("RGB", (panel_width, panel_height), "#eeeeee")
            panel.paste(
                fitted,
                ((panel_width - fitted.width) // 2, (panel_height - fitted.height) // 2),
            )
            x = 8 + column * (panel_width + 20)
            sheet.paste(panel, (x, y + label_height))
            draw.rectangle(
                (x, y + label_height, x + panel_width - 1, y + label_height + panel_height - 1),
                outline="black",
                width=2,
            )
    return type(contour)(
        image=sheet,
        regions=contour.regions,
        changed_pixel_ratio=contour.changed_pixel_ratio,
    )


def build_crop_pairs(reference: Image.Image, live: Image.Image, contour):
    pairs = []
    for region in contour.regions[:1]:
        padding = 14
        box = (
            max(0, region.x - padding),
            max(0, region.y - padding),
            min(reference.width, region.x + region.width + padding),
            min(reference.height, region.y + region.height + padding),
        )
        crop_pair = []
        for image in (reference, live):
            crop = image.crop(box).convert("RGB")
            scale = min(6.0, 720.0 / max(crop.width, crop.height))
            crop_pair.append(
                crop.resize(
                    (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            )
        pairs.append(tuple(crop_pair))
    return tuple(pairs)


def main() -> int:
    args = parse_args()
    pairs = [pair for pair in build_index(args.data_root) if pair.collection == "Round 1"][:5]
    if len(pairs) != 5:
        raise SystemExit(f"Expected five Round 1 pairs, found {len(pairs)}")

    records = []
    summaries = []
    prepared_pairs = []
    for pair in pairs:
        reference = Image.open(pair.reference).convert("RGB")
        live = Image.open(pair.live).convert("RGB")
        contour = (
            build_contour_diff(reference, live, threshold=25, min_area=3000, method="color")
            if args.mode in ("contour", "detail", "crops")
            else None
        )
        crop_pairs = (
            build_crop_pairs(reference, live, contour)
            if args.mode == "crops" and contour is not None
            else ()
        )
        if args.mode == "detail" and contour is not None:
            contour = build_detail_sheet(reference, live, contour)
        prepared_pairs.append((pair, reference, live, contour, crop_pairs))
    for prompt_name in args.prompts:
        for model_key in args.models:
            model_records = []
            for repeat in range(1, args.repeats + 1):
                for pair, reference, live, contour, crop_pairs in prepared_pairs:
                    result = inspect_with_prompt(
                        reference,
                        live,
                        model_key,
                        PROMPTS[prompt_name],
                        args.max_tokens
                        or PROMPT_MAX_TOKENS.get(
                            prompt_name, MODEL_MAX_TOKENS[model_key]
                        ),
                        contour,
                        args.mode,
                        USER_PROMPTS.get(prompt_name),
                        crop_pairs,
                    ).to_dict()
                    record = {
                        "prompt": prompt_name,
                        "model_key": model_key,
                        "benchmark_mode": args.mode,
                        "repeat": repeat,
                        **pair.to_dict(),
                        **result,
                    }
                    record.update(score_semantics(record))
                    records.append(record)
                    model_records.append(record)
            metrics = calculate_metrics(model_records)
            summary = {
                "prompt": prompt_name,
                "model_key": model_key,
                "benchmark_mode": args.mode,
                **metrics,
            }
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
        "user_prompts": {
            name: USER_PROMPTS[name] for name in args.prompts if name in USER_PROMPTS
        },
        "contour_guidance": (
            DETAIL_GUIDANCE
            if args.mode == "detail"
            else CROP_GUIDANCE
            if args.mode == "crops"
            else CONTOUR_GUIDANCE
            if args.mode == "contour"
            else None
        ),
        "benchmark_mode": args.mode,
        "summaries": summaries,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
