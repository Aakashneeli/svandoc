"""Image preprocessing helpers for OCR pipeline."""

from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import pvariance

from PIL import Image, ImageFilter, ImageOps

SUPPORTED_PREPROCESS_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/heic",
}


@dataclass(frozen=True)
class PreprocessResult:
    content: bytes
    applied_steps: tuple[str, ...]
    mime_type: str


def _rotation_score(image: Image.Image) -> float:
    bw = image.point(lambda pixel: 0 if pixel < 180 else 255, mode="1")
    width, height = bw.size
    row_counts: list[int] = []
    for y in range(height):
        black_count = 0
        for x in range(width):
            if bw.getpixel((x, y)) == 0:
                black_count += 1
        row_counts.append(black_count)
    return pvariance(row_counts) if row_counts else 0.0


def _estimate_best_skew_angle(image: Image.Image) -> float:
    base = image.convert("L")
    candidate_angles = [angle / 2 for angle in range(-10, 11)]
    best_angle = 0.0
    best_score = _rotation_score(base)

    for angle in candidate_angles:
        if angle == 0:
            continue
        rotated = base.rotate(angle, expand=True, fillcolor=255)
        score = _rotation_score(rotated)
        if score > best_score:
            best_score = score
            best_angle = angle
    return best_angle


def preprocess_image_content(content: bytes, mime_type: str) -> PreprocessResult:
    normalized_mime = (mime_type or "application/octet-stream").strip().lower()
    if normalized_mime not in SUPPORTED_PREPROCESS_MIME_TYPES:
        return PreprocessResult(content=content, applied_steps=tuple(), mime_type=normalized_mime)

    with Image.open(io.BytesIO(content)) as source_image:
        steps: list[str] = []

        image = ImageOps.exif_transpose(source_image)
        if image.size != source_image.size:
            steps.append("orientation")

        image = image.convert("L")
        image = ImageOps.autocontrast(image)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        steps.append("denoise")

        skew_angle = _estimate_best_skew_angle(image)
        if abs(skew_angle) >= 0.5:
            image = image.rotate(skew_angle, expand=True, fillcolor=255)
            steps.append("deskew")

        output = io.BytesIO()
        output_format = "PNG" if normalized_mime == "image/png" else "JPEG"
        image.save(output, format=output_format, quality=95)

    return PreprocessResult(
        content=output.getvalue(),
        applied_steps=tuple(steps),
        mime_type="image/png" if output_format == "PNG" else "image/jpeg",
    )
