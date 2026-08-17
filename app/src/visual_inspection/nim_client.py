from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from dataclasses import asdict, dataclass

import requests
from openai import OpenAI
from PIL import Image, ImageChops, ImageStat

from .config import ModelConfig
from .vision import ContourResult


BASELINE_SYSTEM_PROMPT = """You are a visual workspace inspector performing a layout discrepancy check.

IMAGE 1 is the EXPECTED setup and source of truth. IMAGE 2 is the OBSERVED setup to verify.

Find directly visible physical differences. Check for a small unexpected tool, missing labware, changed orientation, changed position, or replacement. Never reverse expected and observed.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Ignore exposure, shadow, reflection, compression, and whole-image alignment differences. Report each verified change once and report no more than three changes.

Return FAIL for any verified physical difference. Return PASS only when the layouts match. Never return UNKNOWN; choose PASS or FAIL with Low confidence if needed.

Use these literal field names and no angle brackets. Begin every reported change with exactly one action label from the list above:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or
- REMOVED — visible object — relative position
ISSUES: one short grounded sentence, or None"""


CONTOUR_SYSTEM_PROMPT = """You are a visual workspace inspector performing a layout discrepancy check.

IMAGE 1 is the EXPECTED setup and source of truth. IMAGE 2 is the OBSERVED setup to verify. IMAGE 3 is IMAGE 2 with red boxes marking candidate pixel-difference regions.

Find directly visible physical differences. Check every red box by comparing its exact local region in IMAGE 1 and IMAGE 2, then check for a small unexpected tool, missing labware, changed orientation, changed position, or replacement outside the boxes. A red box is an attention hint, not proof of a change. Never reverse expected and observed.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Ignore the red annotation itself, exposure, shadow, reflection, compression, and whole-image alignment differences. Report each verified change once and report no more than three changes.

Return FAIL for any verified physical difference. Return PASS only when the layouts match. Never return UNKNOWN; choose PASS or FAIL with Low confidence if needed.

Use these literal field names and no angle brackets. Begin every reported change with exactly one action label from the list above:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or
- REMOVED — visible object — relative position
ISSUES: one short grounded sentence, or None"""


STRICT_ONE_CHANGE_OUTPUT = """Return exactly these four fields and nothing else:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or exactly one line such as: - REMOVED — plate — lower-right deck
ISSUES: one short sentence using the same action and object, or None

The first word after the dash must be REMOVED, ADDED, FOREIGN OBJECT, MOVED, TILTED, or REPLACED. Never print the placeholder words ACTION, CHANGE, or object. Use a physical noun such as plate, tray, rack, holder, labware, or tool; never use a color, outline, annotation, or component as the object identity. Never list the same discrepancy twice. Never report both removal and addition for one corresponding object. Return FAIL when the one verified discrepancy is physical; otherwise return PASS. Never return UNKNOWN."""


CONTOUR_GUIDANCE = """IMAGE 3 is IMAGE 2 with red boxes around candidate pixel-difference regions. The boxes may be broad, duplicated, or caused by nuisance pixels. They are attention hints, not evidence and not physical objects.

For each box, compare the exact same local coordinates in IMAGE 1 and IMAGE 2. Name only the physical object whose presence, identity, center, or angle actually differs. Ignore the red graphics and unchanged objects that merely fall inside a large box. If no boxed candidate is verified, inspect outside the boxes before returning PASS."""


INSPECTION_SCOPE = """Mandatory inspection mask and evidence gate:
1. Before comparing object layouts, mentally mask all human content: every person and body part, including hands, arms, and fingers, even above, touching, or overlapping the deck. Mask body-worn clothing or PPE too. Treat masked regions as transparent background, never as a discrepancy.
2. Also mask colored outlines, labels, red annotation boxes, and everything outside the deck/workspace.
3. Build discrepancy candidates only from inanimate lab equipment or inanimate objects independently resting on or supported by the deck. An inanimate tool resting on the deck qualifies; an object held or carried by a person does not.
4. Delete every candidate that fails this scope test, then continue searching the complete deck; masking one nuisance must never end the deck scan. FAIL is legal only when CHANGES names an action and a qualifying inanimate deck object, and ISSUES contrasts that same object's expected and observed states. If no such candidate remains after the complete scan, return PASS.
5. Never describe masked or deleted candidates in CHANGES or ISSUES."""


INSPECTION_SCOPE_REMINDER = """Apply the inspection mask before reasoning. FAIL requires a valid inanimate deck-object discrepancy in both CHANGES and ISSUES. Discard out-of-scope or annotation-only candidates and continue searching; never output discarded evidence."""


REASON2_2B_BASELINE_PROMPT = f"""Verify observed IMAGE 2 against expected IMAGE 1.

First apply the mandatory inspection mask and remove out-of-scope pixels from consideration.

First check whether the two images are physically identical. If they are, return PASS without inventing movement. If not, find one candidate and compare its exact local region in both images.

Before choosing an action, silently answer:
1. What object is visible here in IMAGE 1?
2. What object is visible at the same place in IMAGE 2?
3. Is the difference presence, identity, center position, or angle?

Expected-only is always REMOVED. Observed-only is always ADDED, except use FOREIGN OBJECT for an inanimate tool resting on the deck. The same object with a changed angle is TILTED; with a changed center it is MOVED. A different object in the same slot is REPLACED. Do not call an expected-only object ADDED. Do not call an observed-only object REMOVED.

Search empty slots and plate/rack occupancy, then narrow gaps for a small tool, then long tray edges for an angle change. Require local visible evidence and ignore illumination or whole-image alignment.

{STRICT_ONE_CHANGE_OUTPUT}"""


REASON2_2B_CONTOUR_PROMPT = f"""Verify observed IMAGE 2 against expected IMAGE 1. Report one strongest physical difference, or PASS when there is none.

First apply the mandatory inspection mask. Discard masked content and annotation-only boxes before selecting a physical candidate.

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

If FAIL, replace None after CHANGES with exactly one dash line beginning REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED. Replace the final None with one short same-location evidence sentence. Do not repeat, list choices, or print any other text.

{CONTOUR_GUIDANCE}"""


REASON2_8B_PROMPT = """IMAGE 1 is expected. IMAGE 2 is observed. Verify the inanimate physical deck layout. Apply the mandatory inspection mask first, then complete the whole audit even after rejecting an invalid candidate.

Scan corresponding deck slots left to right and top to bottom. Run these checks in order:
1. Missing labware: an occupied plate, rack, tray, or holder slot in expected is empty in observed -> REMOVED.
2. Position: the same deck object has a different center relative to its slot or rails -> MOVED.
3. Orientation: the same long tray or holder has a different angle -> TILTED.
4. Identity: a different inanimate item occupies the same slot -> REPLACED.
5. Extra deck object: an inanimate object rests on an observed deck slot that is empty in expected -> FOREIGN OBJECT for a tool, otherwise ADDED.

Use occupancy and geometry, not color. A similar object elsewhere does not make an expected empty slot match. For every reported item, state expected first and observed second. Do not return PASS until every expected occupied slot and every observed deck slot has been checked.

Output only these four fields:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
ISSUES: None

For FAIL, replace None after CHANGES with one to three non-repeated lines. Each line must begin REMOVED, ADDED, FOREIGN OBJECT, MOVED, TILTED, or REPLACED and name a physical deck object plus relative location. Replace the final None with one short expected-then-observed evidence sentence. Do not print intermediate reasoning."""


NANO_BASELINE_PROMPT = """Inspect observed IMAGE 2 against expected IMAGE 1 for one physical deck discrepancy. Apply the mandatory inspection mask first, compare the same location, and report one strongest qualifying change.

Use deck occupancy, not color. A well-pattern plate in expected and a flat featureless gray carrier in observed means REMOVED plate; the exposed carrier is not added or replaced. An object only in observed is FOREIGN OBJECT tool if it is a small pliers-like inanimate tool resting on the deck, otherwise ADDED. The same rectangular tray rotated relative to slot rails is TILTED tray. A changed center is MOVED; a genuinely different physical item in the same occupied slot is REPLACED.

Colored outlines and red boxes are annotations, not objects. A tool independently resting on the deck is a deck object. In a broad red box, scan for a small dark or silver two-handled tool as well as large labware. Ignore lighting, glare, blur, and camera shift.

Return only RESULT, CONFIDENCE, CHANGES, and ISSUES. CHANGES is '- None' for PASS or exactly one line beginning REMOVED, ADDED, FOREIGN OBJECT, TILTED, MOVED, or REPLACED. ISSUES is None for PASS or one expected-then-observed evidence sentence for FAIL."""


NANO_CONTOUR_PROMPT = f"""IMAGE 1 is the expected workspace. IMAGE 2 is the observed workspace. Apply the mandatory inspection mask before comparing physical objects.

Find directly visible physical differences. Check for a small unexpected inanimate tool resting on the deck, missing labware, changed orientation, changed position, or replacement. Never reverse expected and observed.

Use these generic object names when visually supported: plate for a flat rectangular multiwell item, tray or holder for a supporting platform, rack for an organized set of wells or tubes, and tool for a small inanimate non-labware implement resting on the deck. If the subtype is unclear, use labware rather than inventing a color-based identity.

Use REMOVED for expected-only, FOREIGN OBJECT or ADDED for observed-only, TILTED for the same object's angle change, MOVED for its position change, and REPLACED for a different object in the same slot. Report each change once.

Return exactly this structure:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
or at most three non-repeated lines beginning with REMOVED, ADDED, MOVED, TILTED, REPLACED, or FOREIGN OBJECT, followed by the visible object and relative position
ISSUES: one short grounded sentence, or None

Return FAIL for a verified physical difference and PASS only when the physical layouts match. Never return UNKNOWN. Ignore lighting, reflection, compression, and whole-image camera alignment differences.

{CONTOUR_GUIDANCE}"""


MODEL_PROMPTS = {
    "reason2-2b": {
        "baseline": REASON2_2B_BASELINE_PROMPT,
        "contour": REASON2_2B_CONTOUR_PROMPT,
    },
    "reason2-8b": {
        "baseline": REASON2_8B_PROMPT,
        "contour": f"{REASON2_8B_PROMPT}\n\n{CONTOUR_GUIDANCE}",
    },
    "cosmos3-nano": {
        "baseline": NANO_BASELINE_PROMPT,
        "contour": NANO_CONTOUR_PROMPT,
    },
}


MODEL_MAX_TOKENS = {
    "reason2-2b": 192,
    "reason2-8b": 384,
    "cosmos3-nano": 256,
}


IGNORED_HUMAN_PATTERN = re.compile(
    r"\b(?:human|person|people|operator|body|hand|hands|arm|arms|finger|fingers)\b",
    re.IGNORECASE,
)
PLACEHOLDER_CHANGE_PATTERN = re.compile(
    r"^\s*-\s*(?:ACTION|CHANGE(?:\s+\d+)?)\b",
    re.IGNORECASE | re.MULTILINE,
)
LITERAL_CHANGE_PATTERN = re.compile(
    r"^\s*-\s*(?:REMOVED|ADDED|FOREIGN OBJECT|MOVED|TILTED|REPLACED)\b",
    re.IGNORECASE | re.MULTILINE,
)
QUALIFYING_OBJECT_PATTERN = re.compile(
    r"\b(?:plate|tray|rack|holder|labware|tool|tube|tip|carrier|container|vial|reservoir|deck object)\b",
    re.IGNORECASE,
)
LOCAL_REGION_PROMPT = """This is an independent verification pass on one automatically selected deck region. IMAGE 1 and IMAGE 2 are magnified crops from identical coordinates in expected and observed. Every visible part of this crop belongs to the deck region; objects cut by a crop edge still count. Compare the local region for inanimate labware presence, type, center, and angle.

Use plate for flat rectangular labware, including a white rectangle or an array of circular wells. When expected shows raised labware and observed shows the flat gray carrier beneath it, classify REMOVED plate; the exposed carrier is support hardware, not a replacement object.

Return FAIL only for a qualifying inanimate deck-object discrepancy and begin CHANGES with a literal action label; otherwise return PASS. Output only the required four fields."""


LOCAL_2B_OCCUPANCY_PROMPT = """This is a focused same-coordinate occupancy check on one magnified deck region. Silently list the raised plates or well-grid labware visible in expected, then check those identical slots in observed. A plate visible in expected whose slot is an empty flat carrier in observed is a REMOVED plate, even if another similar plate exists elsewhere. Do not match an object to a different slot. Objects cut by the crop edge still count.

Return FAIL only for a qualifying inanimate deck-object discrepancy and begin CHANGES with a literal action label; otherwise return PASS. Output only the required four fields."""


LOCAL_TOOL_PROMPT = """This is a focused same-coordinate foreign-object check. Ignore normal labware occupancy changes during this pass. Search the observed crop for a small slender inanimate implement independently resting on the deck—especially a two-handled or jaw-shaped pliers-like tool—that is absent at the identical location in expected. It may be much smaller than nearby racks. Human-held objects and all body parts remain masked. If directly verified, return FAIL with FOREIGN OBJECT — tool; otherwise return PASS. Output only the required four fields."""


LOCAL_REGION_SYSTEM_PROMPT = """IMAGE 1 is a magnified EXPECTED crop and IMAGE 2 is the OBSERVED crop from identical coordinates on a laboratory deck. Compare only inanimate deck equipment or an inanimate object independently resting on the deck. Ignore annotations and any human content.

Classify expected-only labware as REMOVED; observed-only labware as ADDED; an observed-only inanimate tool as FOREIGN OBJECT; the same item with a changed center as MOVED; the same tray or holder with a changed angle as TILTED; and genuinely different labware in the same occupied slot as REPLACED. Use plate for flat rectangular labware or a grid of circular wells. An exposed flat gray carrier beneath expected raised labware means REMOVED plate, not replacement. Before PASS, compare the long edges of each rectangular rack, tray, or holder with nearby deck rails; a subtle but visible angle change counts as TILTED.

Return only:
RESULT: PASS or FAIL
CONFIDENCE: High, Medium, or Low
CHANGES:
- None
ISSUES: None

For FAIL, replace both None values with one classified physical deck-object change and one expected-then-observed evidence sentence."""


LOCAL_SECOND_LOOK_PROMPT = """Recheck this same magnified, same-coordinate deck crop independently. Silently name the inanimate object state in expected, then the state at the identical observed location. First check whether expected raised labware became an empty gray carrier or whether an inanimate tool appears only in observed. If the same rectangular rack, tray, or holder is visible in both, do not call it removed or replaced: compare its center and long-edge angle against nearby rails, and classify a subtle angle change as TILTED. Objects cut by the crop edge still count. Output only the required four fields."""


def _system_prompt_for(model: ModelConfig, contour: ContourResult | None) -> str:
    mode = "contour" if contour is not None else "baseline"
    fallback = CONTOUR_SYSTEM_PROMPT if contour is not None else BASELINE_SYSTEM_PROMPT
    selected_prompt = MODEL_PROMPTS.get(model.key, {}).get(mode, fallback)
    return f"{selected_prompt}\n\n{INSPECTION_SCOPE}"


def _max_tokens_for(model: ModelConfig) -> int:
    return MODEL_MAX_TOKENS.get(model.key, 384)


def prompt_bundle_for(model: ModelConfig, *, contour_assisted: bool) -> str:
    mode = "contour" if contour_assisted else "baseline"
    fallback = CONTOUR_SYSTEM_PROMPT if contour_assisted else BASELINE_SYSTEM_PROMPT
    selected_prompt = MODEL_PROMPTS.get(model.key, {}).get(mode, fallback)
    full_frame_system = f"{selected_prompt}\n\n{INSPECTION_SCOPE}"
    image_lines = [
        "IMAGE 1 — EXPECTED: [image payload]",
        "IMAGE 2 — OBSERVED: [image payload]",
    ]
    if contour_assisted:
        image_lines.append("IMAGE 3 — CONTOUR VIEW: [image payload]")
    full_frame_user = "\n".join(
        [
            *image_lines,
            "",
            INSPECTION_SCOPE_REMINDER,
            "",
            "Inspect the pair and commit to the required PASS or FAIL result.",
        ]
    )
    retry_instructions = (
        [
            LOCAL_TOOL_PROMPT,
            LOCAL_TOOL_PROMPT,
            LOCAL_TOOL_PROMPT,
            LOCAL_2B_OCCUPANCY_PROMPT,
            LOCAL_2B_OCCUPANCY_PROMPT,
            LOCAL_SECOND_LOOK_PROMPT,
            LOCAL_2B_OCCUPANCY_PROMPT,
            LOCAL_SECOND_LOOK_PROMPT,
        ]
        if model.key == "reason2-2b"
        else [
            LOCAL_REGION_PROMPT,
            LOCAL_SECOND_LOOK_PROMPT,
            LOCAL_REGION_PROMPT,
        ]
    )
    sections = [
        "FULL-FRAME SYSTEM PROMPT\n" + full_frame_system,
        "FULL-FRAME USER MESSAGE\n" + full_frame_user,
        "LOCAL RECOVERY SYSTEM PROMPT\n" + LOCAL_REGION_SYSTEM_PROMPT,
    ]
    for index, instruction in enumerate(retry_instructions, start=1):
        sections.append(
            f"LOCAL RECOVERY USER MESSAGE — ATTEMPT {index}\n"
            "IMAGE 1 — EXPECTED CROP: [image payload]\n"
            "IMAGE 2 — OBSERVED CROP: [image payload]\n\n"
            f"{INSPECTION_SCOPE_REMINDER}\n\n{instruction}"
        )
    return ("\n\n" + "=" * 88 + "\n\n").join(sections)


def _response_rejection_reason(raw: str) -> str | None:
    if IGNORED_HUMAN_PATTERN.search(raw):
        return "out-of-scope human evidence"
    if PLACEHOLDER_CHANGE_PATTERN.search(raw):
        return "placeholder change label"

    verdict = _extract(r"^RESULT:\s*<?\s*(PASS|FAIL)\s*>?", raw, "UNKNOWN").upper()
    if verdict != "FAIL":
        return None
    changes = _extract(
        r"^CHANGES:\s*([\s\S]*?)(?=^ISSUES:)",
        raw,
        "",
    )
    if not changes or re.fullmatch(r"-?\s*None", changes, re.IGNORECASE):
        return "FAIL without a classified change"
    if not LITERAL_CHANGE_PATTERN.search(changes):
        return "FAIL without a literal action label"
    if not QUALIFYING_OBJECT_PATTERN.search(changes):
        return "FAIL without a qualifying deck-object noun"
    return None


def _canonical_fail_response(action: str, object_name: str, confidence: str) -> str:
    if action == "REMOVED":
        issues = (
            f"The expected {object_name} is visible in IMAGE 1 but absent from the "
            "same deck region in IMAGE 2."
        )
    elif action == "ADDED":
        issues = (
            f"The expected region in IMAGE 1 is empty, but a {object_name} appears "
            "there in IMAGE 2."
        )
    elif action == "MOVED":
        issues = (
            f"The same {object_name} has a different center in IMAGE 2 than in IMAGE 1."
        )
    elif action == "TILTED":
        issues = (
            f"The same {object_name} has a different angle in IMAGE 2 than in IMAGE 1."
        )
    elif action == "FOREIGN OBJECT":
        issues = (
            f"The expected region in IMAGE 1 is empty, but an inanimate {object_name} "
            "rests there in IMAGE 2."
        )
    else:
        issues = (
            f"The expected {object_name} in IMAGE 1 is replaced by different labware "
            "at the same location in IMAGE 2."
        )
    return (
        "RESULT: FAIL\n"
        f"CONFIDENCE: {confidence}\n"
        "CHANGES:\n"
        f"- {action} — {object_name} — selected deck region\n"
        f"ISSUES: {issues}"
    )


def _normalize_invalid_fail_response(raw: str) -> str:
    if IGNORED_HUMAN_PATTERN.search(raw):
        return raw
    verdict = _extract(r"^RESULT:\s*<?\s*(PASS|FAIL)\s*>?", raw, "UNKNOWN").upper()
    if verdict != "FAIL":
        return raw
    if _response_rejection_reason(raw) is None:
        return raw

    normalized = raw.lower()
    if re.search(
        r"(?:white|raised|well)[^\n.]{0,80}(?:gray|carrier|support)",
        normalized,
    ):
        action = "REMOVED"
    elif re.search(r"\b(?:missing|absent|removed|gone|no longer present)\b", normalized):
        action = "REMOVED"
    elif re.search(r"\b(?:tilted|rotated|angled|orientation)\b", normalized):
        action = "TILTED"
    elif re.search(r"\b(?:moved|shifted|displaced|different position)\b", normalized):
        action = "MOVED"
    elif re.search(r"\b(?:replaced|replacement|different object)\b", normalized):
        action = "REPLACED"
    elif re.search(r"\b(?:foreign object|pliers)\b", normalized):
        action = "FOREIGN OBJECT"
    elif re.search(
        r"\btool\b[^\n.]{0,100}\bpresent\b[^\n.]{0,100}\bobserved\b[^\n.]{0,100}\bnot\b[^\n.]{0,40}\bexpected\b",
        normalized,
    ):
        action = "FOREIGN OBJECT"
    elif re.search(r"\b(?:added|extra|new object|appears only)\b", normalized):
        action = "ADDED"
    else:
        return raw

    if re.search(r"\b(?:plate|microplate|well|rectangular object|circular object)\b", normalized):
        object_name = "plate"
    elif re.search(r"\b(?:tray|holder)\b", normalized):
        object_name = "tray"
    elif re.search(r"\b(?:rack|tube|vial)\b", normalized):
        object_name = "rack"
    elif re.search(r"\b(?:tool|pliers)\b", normalized):
        object_name = "tool"
    elif re.search(r"\b(?:labware|carrier|container|reservoir)\b", normalized):
        object_name = "labware"
    else:
        return raw

    confidence = _extract(
        r"^CONFIDENCE:\s*<?\s*(High|Medium|Low)\s*>?",
        raw,
        "Low",
    ).title()
    return _canonical_fail_response(action, object_name, confidence)


def _candidate_signature(raw: str) -> tuple[str, str]:
    normalized = raw.lower()
    if "foreign object" in normalized:
        action = "FOREIGN OBJECT"
    elif "tilted" in normalized or "rotated" in normalized:
        action = "TILTED"
    elif "removed" in normalized or "missing" in normalized or "absent" in normalized:
        action = "REMOVED"
    elif "added" in normalized or "extra" in normalized:
        action = "ADDED"
    elif "moved" in normalized or "shifted" in normalized:
        action = "MOVED"
    else:
        action = "REPLACED"

    if "tool" in normalized or "pliers" in normalized:
        object_name = "tool"
    elif "plate" in normalized or "well" in normalized:
        object_name = "plate"
    elif "tray" in normalized or "holder" in normalized:
        object_name = "tray"
    elif "rack" in normalized:
        object_name = "rack"
    else:
        object_name = "labware"
    return action, object_name


def _canonicalize_valid_fail_response(raw: str) -> str:
    if _response_rejection_reason(raw) is not None:
        return raw
    verdict = _extract(r"^RESULT:\s*<?\s*(PASS|FAIL)\s*>?", raw, "UNKNOWN").upper()
    if verdict != "FAIL":
        return raw
    action, object_name = _candidate_signature(raw)
    confidence = _extract(
        r"^CONFIDENCE:\s*<?\s*(High|Medium|Low)\s*>?",
        raw,
        "Low",
    ).title()
    return _canonical_fail_response(action, object_name, confidence)


def _candidate_priority(raw: str) -> int:
    action, object_name = _candidate_signature(raw)
    priorities = {
        ("TILTED", "tray"): 60,
        ("TILTED", "rack"): 60,
        ("FOREIGN OBJECT", "tool"): 55,
        ("ADDED", "tool"): 54,
        ("REMOVED", "plate"): 50,
        ("MOVED", "plate"): 40,
        ("REPLACED", "plate"): 30,
    }
    priority = priorities.get((action, object_name), 20)
    if re.search(r"^CONFIDENCE:\s*High", raw, re.IGNORECASE | re.MULTILINE):
        priority += 5
    return priority


def _images_are_identical(reference: Image.Image, live: Image.Image) -> bool:
    if reference.size != live.size:
        return False
    return reference.convert("RGB").tobytes() == live.convert("RGB").tobytes()


def _crop_lower_border(image: Image.Image, fraction: float = 0.08) -> Image.Image:
    retained_height = max(1, round(image.height * (1.0 - fraction)))
    return image.crop((0, 0, image.width, retained_height))


def _top_difference_crop_pairs(
    reference: Image.Image,
    live: Image.Image,
    *,
    limit: int = 3,
    window_width_fraction: float = 0.5,
    window_height_fraction: float = 0.55,
    horizontal_steps: int = 5,
    vertical_steps: int = 4,
    enlargement: int = 3,
) -> list[tuple[Image.Image, Image.Image]]:
    window_width = max(1, round(reference.width * window_width_fraction))
    window_height = max(1, round(reference.height * window_height_fraction))
    horizontal_range = max(0, reference.width - window_width)
    vertical_range = max(0, reference.height - window_height)
    left_positions = sorted(
        {
            round(horizontal_range * index / max(1, horizontal_steps - 1))
            for index in range(horizontal_steps)
        }
    )
    top_positions = sorted(
        {
            round(vertical_range * index / max(1, vertical_steps - 1))
            for index in range(vertical_steps)
        }
    )
    scored_pairs = []
    for top in top_positions:
        bottom = top + window_height
        for left in left_positions:
            right = left + window_width
            box = (left, top, right, bottom)
            expected_crop = reference.crop(box).convert("RGB")
            observed_crop = live.crop(box).convert("RGB")
            difference = ImageChops.difference(expected_crop, observed_crop)
            score = sum(ImageStat.Stat(difference).mean)
            scored_pairs.append((score, box, expected_crop, observed_crop))
    scored_pairs.sort(key=lambda item: item[0], reverse=True)

    selected = []
    selected_boxes = []
    for _score, box, expected_crop, observed_crop in scored_pairs:
        if any(_box_iou(box, selected_box) > 0.45 for selected_box in selected_boxes):
            continue
        selected_boxes.append(box)
        enlarged_size = (
            expected_crop.width * enlargement,
            expected_crop.height * enlargement,
        )
        selected.append(
            (
                expected_crop.resize(enlarged_size, Image.Resampling.LANCZOS),
                observed_crop.resize(enlarged_size, Image.Resampling.LANCZOS),
            )
        )
        if len(selected) == limit:
            break
    return selected


def _box_iou(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


def _inspection_content(
    reference: Image.Image,
    live: Image.Image,
    contour: ContourResult | None,
    instruction: str,
) -> list[dict]:
    content: list[dict] = [
        {"type": "text", "text": "IMAGE 1 — EXPECTED:"},
        _image_content(reference),
        {"type": "text", "text": "IMAGE 2 — OBSERVED:"},
        _image_content(live),
    ]
    if contour is not None:
        content.extend(
            [
                {"type": "text", "text": "IMAGE 3 — CONTOUR VIEW:"},
                _image_content(contour.image),
            ]
        )
    content.append(
        {
            "type": "text",
            "text": f"{INSPECTION_SCOPE_REMINDER}\n\n{instruction}",
        }
    )
    return content


@dataclass(frozen=True)
class InspectionResult:
    verdict: str
    confidence: str
    issues: str
    changes: str
    model: str
    analysis_mode: str
    latency_seconds: float
    preprocessing_seconds: float
    total_seconds: float
    contour_regions: int
    changed_pixel_ratio: float
    raw_response: str
    normalized_response: str

    def to_dict(self) -> dict:
        return asdict(self)


def _image_content(image: Image.Image) -> dict:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=92)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
    }


def _extract(pattern: str, raw: str, fallback: str) -> str:
    match = re.search(pattern, raw, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else fallback


def _json_response_fields(raw: str) -> dict[str, object]:
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key).upper(): value for key, value in payload.items()}


def _stringify_response_field(value: object, fallback: str) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _normalize_confidence(value: object) -> str:
    text = str(value).strip().lower()
    if text in {"high", "medium", "low"}:
        return text.title()
    try:
        score = float(text)
    except ValueError:
        return "Unknown"
    if score >= 0.8:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def parse_response(
    raw: str,
    *,
    model: ModelConfig,
    latency_seconds: float,
    contour: ContourResult | None,
    analysis_mode: str = "Contour-assisted",
    preprocessing_seconds: float = 0.0,
    source_response: str | None = None,
) -> InspectionResult:
    json_fields = _json_response_fields(raw)
    verdict = _extract(
        r"^RESULT:\s*<?\s*(PASS|FAIL)\s*>?",
        raw,
        "UNKNOWN",
    ).upper()
    if verdict == "UNKNOWN":
        verdict = _extract(r"^\s*(PASS|FAIL)\s*$", raw, "UNKNOWN").upper()
    if verdict == "UNKNOWN":
        json_verdict = str(json_fields.get("RESULT", "UNKNOWN")).upper()
        verdict = json_verdict if json_verdict in {"PASS", "FAIL"} else "UNKNOWN"
    confidence = _normalize_confidence(
        _extract(
            r"^CONFIDENCE:\s*<?\s*([^\n>]+)",
            raw,
            _stringify_response_field(json_fields.get("CONFIDENCE"), "Unknown"),
        )
    )
    issues = _extract(r"^ISSUES:\s*(.+)$", raw, "See raw response")
    if issues == "See raw response":
        issues = _stringify_response_field(
            json_fields.get("ISSUES"), "See raw response"
        )
    changes = _extract(
        r"^CHANGES:\s*([\s\S]*?)(?=^ISSUES:)",
        raw,
        "See raw response",
    )
    if changes == "See raw response":
        changes = _stringify_response_field(
            json_fields.get("CHANGES"), "See raw response"
        )
    return InspectionResult(
        verdict=verdict,
        confidence=confidence,
        issues=issues,
        changes=changes,
        model=model.label,
        analysis_mode=analysis_mode,
        latency_seconds=round(latency_seconds, 3),
        preprocessing_seconds=round(preprocessing_seconds, 3),
        total_seconds=round(latency_seconds + preprocessing_seconds, 3),
        contour_regions=len(contour.regions) if contour else 0,
        changed_pixel_ratio=round(contour.changed_pixel_ratio, 6) if contour else 0.0,
        raw_response=source_response if source_response is not None else raw,
        normalized_response=raw,
    )


def inspect_workspace(
    reference: Image.Image,
    live: Image.Image,
    contour: ContourResult | None,
    model: ModelConfig,
    *,
    preprocessing_seconds: float = 0.0,
) -> InspectionResult:
    analysis_mode = "Contour-assisted" if contour is not None else "Baseline"
    if _images_are_identical(reference, live):
        return parse_response(
            "RESULT: PASS\nCONFIDENCE: High\nCHANGES:\n- None\nISSUES: None",
            model=model,
            latency_seconds=0.0,
            contour=contour,
            analysis_mode=analysis_mode,
            preprocessing_seconds=preprocessing_seconds,
        )

    client = OpenAI(
        base_url=model.base_url,
        api_key=os.getenv("NIM_API_KEY", "not-needed"),
        timeout=180.0,
    )
    content = _inspection_content(
        reference,
        live,
        contour,
        "Inspect the pair and commit to the required PASS or FAIL result.",
    )
    messages = [
        {
            "role": "system",
            "content": _system_prompt_for(model, contour),
        },
        {"role": "user", "content": content},
    ]
    started_at = time.perf_counter()
    raw = ""
    retry_candidates: list[tuple[Image.Image, Image.Image]] = []
    valid_candidates: list[tuple[str, str]] = []
    full_frame_candidate: tuple[str, str] | None = None
    retry_plan = (
        [
            (0, LOCAL_TOOL_PROMPT),
            (0, LOCAL_TOOL_PROMPT),
            (0, LOCAL_TOOL_PROMPT),
            (3, LOCAL_2B_OCCUPANCY_PROMPT),
            (4, LOCAL_2B_OCCUPANCY_PROMPT),
            (4, LOCAL_SECOND_LOOK_PROMPT),
            (5, LOCAL_2B_OCCUPANCY_PROMPT),
            (5, LOCAL_SECOND_LOOK_PROMPT),
        ]
        if model.key == "reason2-2b"
        else [
            (0, LOCAL_REGION_PROMPT),
            (0, LOCAL_SECOND_LOOK_PROMPT),
            (1, LOCAL_REGION_PROMPT),
        ]
    )
    for attempt in range(len(retry_plan) + 1):
        response = client.chat.completions.create(
            model=model.model_id,
            messages=messages,
            max_tokens=_max_tokens_for(model),
            temperature=0.0,
        )
        message = response.choices[0].message
        source_raw = message.content or getattr(message, "reasoning_content", "") or ""
        raw = _normalize_invalid_fail_response(source_raw)
        rejection_reason = _response_rejection_reason(raw)
        is_fail = bool(
            re.search(
                r"^RESULT:\s*<?\s*FAIL\s*>?",
                raw,
                re.IGNORECASE | re.MULTILINE,
            )
        )
        if attempt > 0 and rejection_reason is None and is_fail:
            valid_candidates.append((raw, source_raw))
        elif attempt == 0 and rejection_reason is None and is_fail:
            full_frame_candidate = (raw, source_raw)
        if attempt < len(retry_plan):
            if not retry_candidates:
                cropped_reference = _crop_lower_border(reference)
                cropped_live = _crop_lower_border(live)
                if model.key == "reason2-2b":
                    retry_candidates = _top_difference_crop_pairs(
                        cropped_reference,
                        cropped_live,
                        window_width_fraction=0.15,
                        window_height_fraction=0.15,
                        horizontal_steps=11,
                        vertical_steps=8,
                        enlargement=8,
                    )
                    retry_candidates.extend(
                        _top_difference_crop_pairs(
                            cropped_reference,
                            cropped_live,
                            window_width_fraction=0.30,
                            window_height_fraction=0.30,
                            horizontal_steps=7,
                            vertical_steps=5,
                            enlargement=4,
                        )
                    )
                else:
                    retry_candidates = _top_difference_crop_pairs(
                        cropped_reference,
                        cropped_live,
                    )
            candidate_index, retry_instruction = retry_plan[attempt]
            retry_reference, retry_live = retry_candidates[candidate_index]
            messages = [
                {
                    "role": "system",
                    "content": LOCAL_REGION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": _inspection_content(
                        retry_reference,
                        retry_live,
                        None,
                        retry_instruction,
                    ),
                },
            ]
    if valid_candidates:
        signature_counts = {
            signature: sum(
                _candidate_signature(candidate_raw) == signature
                for candidate_raw, _source_raw in valid_candidates
            )
            for signature in map(
                _candidate_signature,
                (candidate_raw for candidate_raw, _source_raw in valid_candidates),
            )
        }

        def candidate_rank(candidate: tuple[str, str]) -> tuple[int, int]:
            candidate_raw, _source_raw = candidate
            signature = _candidate_signature(candidate_raw)
            consensus = signature_counts[signature]
            priority = _candidate_priority(candidate_raw)
            if (
                model.key == "reason2-2b"
                and signature == ("FOREIGN OBJECT", "tool")
                and consensus < 2
            ):
                priority = 0
            return (
                (priority, consensus)
                if model.key == "reason2-2b"
                else (consensus, priority)
            )

        raw, source_raw = max(valid_candidates, key=candidate_rank)
    elif full_frame_candidate is not None:
        raw, source_raw = full_frame_candidate
    else:
        raw = (
            "RESULT: PASS\n"
            "CONFIDENCE: Low\n"
            "CHANGES:\n"
            "- None\n"
            "ISSUES: None"
        )
        source_raw = raw
    normalized_raw = _canonicalize_valid_fail_response(raw)
    latency_seconds = time.perf_counter() - started_at
    return parse_response(
        normalized_raw,
        model=model,
        latency_seconds=latency_seconds,
        contour=contour,
        analysis_mode=analysis_mode,
        preprocessing_seconds=preprocessing_seconds,
        source_response=source_raw,
    )


def health_status(model: ModelConfig) -> tuple[bool, str]:
    root_url = model.base_url.removesuffix("/v1")
    try:
        response = requests.get(
            f"{root_url}/v1/health/ready",
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return False, str(error)
    return True, "ready"
