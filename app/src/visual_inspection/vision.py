from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ChangeRegion:
    x: int
    y: int
    width: int
    height: int
    area: float


@dataclass(frozen=True)
class ContourResult:
    image: Image.Image
    regions: tuple[ChangeRegion, ...]
    changed_pixel_ratio: float


def _to_rgb_array(image: Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"))

    array = np.asarray(image)
    if array.ndim == 2:
        return cv2.cvtColor(array, cv2.COLOR_GRAY2RGB)
    if array.ndim != 3:
        raise ValueError("Expected a grayscale or RGB image")
    if array.shape[2] == 4:
        return cv2.cvtColor(array, cv2.COLOR_RGBA2RGB)
    return array[:, :, :3].astype(np.uint8, copy=False)


def build_contour_diff(
    reference: Image.Image | np.ndarray,
    live: Image.Image | np.ndarray,
    *,
    threshold: int = 25,
    min_area: int = 3000,
    method: str = "color",
) -> ContourResult:
    reference_rgb = _to_rgb_array(reference)
    live_rgb = _to_rgb_array(live)

    if reference_rgb.shape != live_rgb.shape:
        live_rgb = cv2.resize(
            live_rgb,
            (reference_rgb.shape[1], reference_rgb.shape[0]),
            interpolation=cv2.INTER_AREA,
        )

    reference_bgr = cv2.cvtColor(reference_rgb, cv2.COLOR_RGB2BGR)
    live_bgr = cv2.cvtColor(live_rgb, cv2.COLOR_RGB2BGR)
    if method == "color":
        difference = cv2.absdiff(reference_bgr, live_bgr)
        difference_gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
    elif method == "channel-max":
        difference = cv2.absdiff(reference_bgr, live_bgr)
        difference_gray = np.max(difference, axis=2).astype(np.uint8)
    elif method == "edges":
        reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
        live_gray = cv2.cvtColor(live_bgr, cv2.COLOR_BGR2GRAY)
        reference_edges = cv2.Canny(reference_gray, 50, 150)
        live_edges = cv2.Canny(live_gray, 50, 150)
        difference_gray = cv2.absdiff(reference_edges, live_edges)
    else:
        raise ValueError(f"Unsupported contour method: {method}")
    _, thresholded = cv2.threshold(
        difference_gray,
        threshold,
        255,
        cv2.THRESH_BINARY,
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    cleaned = cv2.morphologyEx(thresholded, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.dilate(cleaned, kernel, iterations=3)
    contours, _ = cv2.findContours(
        cleaned,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    significant = [
        contour for contour in contours if cv2.contourArea(contour) > min_area
    ]
    significant.sort(key=cv2.contourArea, reverse=True)

    annotated = live_bgr.copy()
    regions: list[ChangeRegion] = []
    for index, contour in enumerate(significant, start=1):
        x, y, width, height = cv2.boundingRect(contour)
        regions.append(
            ChangeRegion(
                x=x,
                y=y,
                width=width,
                height=height,
                area=float(cv2.contourArea(contour)),
            )
        )
        cv2.rectangle(
            annotated,
            (x, y),
            (x + width, y + height),
            (0, 0, 255),
            4,
        )
        cv2.putText(
            annotated,
            f"CHANGE {index}",
            (x, max(32, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3,
        )

    changed_pixel_ratio = float(np.count_nonzero(cleaned)) / float(cleaned.size)
    annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
    return ContourResult(
        image=Image.fromarray(annotated_rgb),
        regions=tuple(regions),
        changed_pixel_ratio=changed_pixel_ratio,
    )
