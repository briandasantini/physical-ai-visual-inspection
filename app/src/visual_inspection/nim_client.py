from __future__ import annotations

import base64
import io
import os
import re
import time
from dataclasses import asdict, dataclass

import requests
from openai import OpenAI
from PIL import Image

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


def parse_response(
    raw: str,
    *,
    model: ModelConfig,
    latency_seconds: float,
    contour: ContourResult | None,
    analysis_mode: str = "Contour-assisted",
    preprocessing_seconds: float = 0.0,
) -> InspectionResult:
    verdict = _extract(
        r"^RESULT:\s*<?\s*(PASS|FAIL)\s*>?",
        raw,
        "UNKNOWN",
    ).upper()
    if verdict == "UNKNOWN":
        verdict = _extract(r"^\s*(PASS|FAIL)\s*$", raw, "UNKNOWN").upper()
    confidence = _extract(
        r"^CONFIDENCE:\s*<?\s*(High|Medium|Low)\s*>?",
        raw,
        "Unknown",
    ).title()
    issues = _extract(r"^ISSUES:\s*(.+)$", raw, "See raw response")
    changes = _extract(
        r"^CHANGES:\s*([\s\S]*?)(?=^ISSUES:)",
        raw,
        "See raw response",
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
        raw_response=raw,
    )


def inspect_workspace(
    reference: Image.Image,
    live: Image.Image,
    contour: ContourResult | None,
    model: ModelConfig,
    *,
    preprocessing_seconds: float = 0.0,
) -> InspectionResult:
    client = OpenAI(
        base_url=model.base_url,
        api_key=os.getenv("NIM_API_KEY", "not-needed"),
        timeout=180.0,
    )
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
            "text": "Inspect the pair and commit to the required PASS or FAIL result.",
        }
    )
    analysis_mode = "Contour-assisted" if contour is not None else "Baseline"

    started_at = time.perf_counter()
    response = client.chat.completions.create(
        model=model.model_id,
        messages=[
            {
                "role": "system",
                "content": (
                    CONTOUR_SYSTEM_PROMPT
                    if contour is not None
                    else BASELINE_SYSTEM_PROMPT
                ),
            },
            {"role": "user", "content": content},
        ],
        max_tokens=384,
        temperature=0.0,
    )
    latency_seconds = time.perf_counter() - started_at
    message = response.choices[0].message
    raw = message.content or getattr(message, "reasoning_content", "") or ""
    return parse_response(
        raw,
        model=model,
        latency_seconds=latency_seconds,
        contour=contour,
        analysis_mode=analysis_mode,
        preprocessing_seconds=preprocessing_seconds,
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
