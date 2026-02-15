import io
import unittest

from PIL import Image, ImageChops, ImageDraw

from svandoc_backend.preprocessing import preprocess_image_content


def _to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_clean_invoice_like_sample() -> bytes:
    image = Image.new("L", (640, 420), color=255)
    draw = ImageDraw.Draw(image)
    for y in range(40, 360, 36):
        draw.rectangle((50, y, 580, y + 6), fill=0)
    return _to_png_bytes(image)


def _build_noisy_receipt_like_sample() -> bytes:
    image = Image.new("L", (540, 360), color=255)
    draw = ImageDraw.Draw(image)
    for y in range(30, 320, 26):
        draw.rectangle((40, y, 500, y + 5), fill=0)
    for x in range(0, 540, 14):
        draw.point((x, (x * 7) % 360), fill=0)
    return _to_png_bytes(image)


def _build_skewed_sample() -> bytes:
    base = Image.new("L", (600, 360), color=255)
    draw = ImageDraw.Draw(base)
    for y in range(50, 300, 34):
        draw.rectangle((55, y, 560, y + 6), fill=0)
    skewed = base.rotate(4.0, expand=True, fillcolor=255)
    return _to_png_bytes(skewed)


class PreprocessingTests(unittest.TestCase):
    def test_non_image_mime_is_passthrough(self) -> None:
        content = b"%PDF-1.5 fake"
        result = preprocess_image_content(content, "application/pdf")
        self.assertEqual(result.content, content)
        self.assertEqual(result.applied_steps, tuple())
        self.assertEqual(result.mime_type, "application/pdf")

    def test_preprocessing_runs_on_sample_corpus(self) -> None:
        samples = [
            ("clean", _build_clean_invoice_like_sample(), False),
            ("noisy", _build_noisy_receipt_like_sample(), False),
            ("skewed", _build_skewed_sample(), True),
        ]

        for name, content, expect_deskew in samples:
            with self.subTest(sample=name):
                result = preprocess_image_content(content, "image/png")
                self.assertTrue(result.content)
                self.assertIn("denoise", result.applied_steps)
                if expect_deskew:
                    self.assertIn("deskew", result.applied_steps)

    def test_denoise_changes_noisy_pixels(self) -> None:
        noisy_content = _build_noisy_receipt_like_sample()
        result = preprocess_image_content(noisy_content, "image/png")

        before = Image.open(io.BytesIO(noisy_content)).convert("L")
        after = Image.open(io.BytesIO(result.content)).convert("L")
        after = after.resize(before.size)

        diff_bbox = ImageChops.difference(before, after).getbbox()
        self.assertIsNotNone(diff_bbox)


if __name__ == "__main__":
    unittest.main()
