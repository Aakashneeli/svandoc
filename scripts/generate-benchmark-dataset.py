"""Generate synthetic benchmark samples for invoice/receipt extraction quality checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path("datasets/benchmark/v1")
SAMPLES_DIR = ROOT / "samples"
MANIFEST_PATH = ROOT / "manifest.json"


def _base_canvas() -> Image.Image:
    return Image.new("RGB", (1240, 1754), "white")


def _draw_invoice(draw: ImageDraw.ImageDraw) -> None:
    draw.text((80, 70), "INVOICE", fill="black")
    draw.text((80, 130), "Vendor: ACME Industrial Supply", fill="black")
    draw.text((80, 165), "Invoice #: INV-1007", fill="black")
    draw.text((80, 200), "Issue Date: 2026-02-15", fill="black")
    draw.text((80, 235), "Due Date: 2026-03-01", fill="black")
    draw.text((80, 305), "Description", fill="black")
    draw.text((560, 305), "Qty", fill="black")
    draw.text((700, 305), "Unit", fill="black")
    draw.text((910, 305), "Total", fill="black")
    draw.line((80, 335, 1110, 335), fill="black", width=2)
    draw.text((80, 365), "Consulting Services", fill="black")
    draw.text((560, 365), "4", fill="black")
    draw.text((700, 365), "250.00", fill="black")
    draw.text((910, 365), "1000.00", fill="black")
    draw.text((80, 420), "Subtotal: 1000.00", fill="black")
    draw.text((80, 455), "Tax: 85.00", fill="black")
    draw.text((80, 490), "Total: 1085.00 USD", fill="black")


def _draw_receipt(draw: ImageDraw.ImageDraw) -> None:
    draw.text((80, 70), "RECEIPT", fill="black")
    draw.text((80, 120), "Merchant: Corner Market", fill="black")
    draw.text((80, 155), "Receipt #: RCPT-3321", fill="black")
    draw.text((80, 190), "Date: 2026-02-15 18:40", fill="black")
    draw.text((80, 250), "Item", fill="black")
    draw.text((760, 250), "Price", fill="black")
    draw.line((80, 280, 980, 280), fill="black", width=2)
    draw.text((80, 320), "Whole Grain Bread", fill="black")
    draw.text((760, 320), "4.50", fill="black")
    draw.text((80, 355), "Milk 2%", fill="black")
    draw.text((760, 355), "3.20", fill="black")
    draw.text((80, 390), "Fruit Basket", fill="black")
    draw.text((760, 390), "8.30", fill="black")
    draw.text((80, 450), "Subtotal: 16.00", fill="black")
    draw.text((80, 485), "Tax: 1.44", fill="black")
    draw.text((80, 520), "Total: 17.44 USD", fill="black")
    draw.text((80, 555), "Payment: Card", fill="black")


def _add_noise(image: Image.Image) -> Image.Image:
    pixels = image.load()
    width, height = image.size
    for y in range(0, height, 25):
        for x in range((y * 7) % 17, width, 37):
            if (x + y) % 3 == 0:
                pixels[x, y] = (210, 210, 210)
    return image.filter(ImageFilter.GaussianBlur(radius=0.6))


def _add_multilayout(image: Image.Image, doc_type: str) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 620, 1170, 1450), outline="black", width=2)
    draw.line((620, 620, 620, 1450), fill="black", width=2)
    left_title = "Billing Notes" if doc_type == "invoice" else "Store Notes"
    right_title = "Payment Summary" if doc_type == "invoice" else "Card Summary"
    draw.text((90, 650), left_title, fill="black")
    draw.text((650, 650), right_title, fill="black")
    for idx in range(0, 8):
        draw.text((90, 700 + (idx * 55)), f"- Line block A{idx + 1}", fill="black")
        draw.text((650, 700 + (idx * 55)), f"- Line block B{idx + 1}", fill="black")
    return image


def _save_sample(image: Image.Image, sample_name: str) -> dict[str, Any]:
    png_path = SAMPLES_DIR / f"{sample_name}.png"
    pdf_path = SAMPLES_DIR / f"{sample_name}.pdf"
    image.save(png_path, "PNG")
    image.save(pdf_path, "PDF", resolution=150.0)

    png_bytes = png_path.read_bytes()
    pdf_bytes = pdf_path.read_bytes()
    return {
        "id": sample_name,
        "png_path": str(png_path.as_posix()),
        "pdf_path": str(pdf_path.as_posix()),
        "png_sha256": hashlib.sha256(png_bytes).hexdigest(),
        "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
    }


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []

    for doc_type in ("invoice", "receipt"):
        for variant in ("clean", "noisy", "rotated", "multilayout"):
            image = _base_canvas()
            draw = ImageDraw.Draw(image)
            if doc_type == "invoice":
                _draw_invoice(draw)
            else:
                _draw_receipt(draw)

            if variant == "noisy":
                image = _add_noise(image)
            if variant == "rotated":
                image = image.rotate(7.5, expand=True, fillcolor="white")
            if variant == "multilayout":
                image = _add_multilayout(image, doc_type)

            sample_name = f"{doc_type}_{variant}_001"
            sample_info = _save_sample(image, sample_name)
            sample_info["doc_type"] = doc_type
            sample_info["variant"] = variant
            items.append(sample_info)

    manifest = {
        "dataset": "svandoc-benchmark",
        "version": "v1",
        "description": "Synthetic invoice/receipt benchmark set for extraction regression checks.",
        "required_variants": ["clean", "noisy", "rotated", "multilayout"],
        "samples": items,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
