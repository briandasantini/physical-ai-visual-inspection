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


BASELINE_SYSTEM_PROMPT = """You are a visual workspace inspector performing an expected-versus-observed setup discrepancy check.

You receive:
- IMAGE 1 — EXPECTED: the correct workspace setup and source of truth
- IMAGE 2 — OBSERVED: the current workspace state

Compare IMAGE 1 and IMAGE 2 directly. Classify a confirmed physical change as REMOVED, ADDED, MOVED, REPLACED, TILTED, or FOREIGN OBJECT. Ignore lighting and shadow changes.

Return FAIL if any real physical change is confirmed. Return PASS only when the observed workspace matches the expected workspace. If uncertain about a possible safety-relevant change, return FAIL with Low confidence.

Respond exactly in this format:
RESULT: <PASS or FAIL>
CONFIDENCE: <High, Medium, or Low>
CHANGES:
- <change type>: <object and location>, or None
ISSUES: <one plain-English sentence, or None>"""


CONTOUR_SYSTEM_PROMPT = """You are a visual workspace inspector performing an expected-versus-observed setup discrepancy check.

You receive:
- IMAGE 1 — EXPECTED: the correct workspace setup and source of truth
- IMAGE 2 — OBSERVED: the current workspace state
- IMAGE 3 — CONTOUR VIEW: IMAGE 2 with red boxes around candidate changes

For every red box, compare the same location in IMAGE 1 and IMAGE 2. Classify a confirmed physical change as REMOVED, ADDED, MOVED, REPLACED, TILTED, or FOREIGN OBJECT. Red boxes are attention hints, not proof; ignore lighting and shadow changes. Then scan the rest of the workspace for changes the contour view missed.

Return FAIL if any real physical change is confirmed. Return PASS only when the observed workspace matches the expected workspace. If uncertain about a possible safety-relevant change, return FAIL with Low confidence.

Respond exactly in this format:
RESULT: <PASS or FAIL>
CONFIDENCE: <High, Medium, or Low>
CHANGES:
- <change type>: <object and location>, or None
ISSUES: <one plain-English sentence, or None>"""


@dataclass(frozen=True)
class InspectionResult:
    verdict: str
    confidence: str
    issues: str
    changes: str
    model: str
    analysis_mode: str
    latency_seconds: float
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
) -> InspectionResult:
    verdict = _extract(r"^RESULT:\s*(PASS|FAIL)\b", raw, "UNKNOWN").upper()
    confidence = _extract(
        r"^CONFIDENCE:\s*(High|Medium|Low)\b",
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
        contour_regions=len(contour.regions) if contour else 0,
        changed_pixel_ratio=round(contour.changed_pixel_ratio, 6) if contour else 0.0,
        raw_response=raw,
    )


def inspect_workspace(
    reference: Image.Image,
    live: Image.Image,
    contour: ContourResult | None,
    model: ModelConfig,
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
        max_tokens=768,
        temperature=0.1,
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
