import unittest

from svandoc_backend.dots_ocr import DotsOCRAdapter
from svandoc_backend.vllm_client import VLLMCompletionResult


class _StubVLLMClient:
    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, *, model: str, prompt: str, max_tokens: int = 2048, temperature: float = 0.0, extra_payload=None):  # type: ignore[no-untyped-def]
        _ = (prompt, max_tokens, temperature, extra_payload)
        return VLLMCompletionResult(
            model=model,
            text=self._text,
            response_payload={"choices": [{"message": {"content": self._text}}]},
            attempts=1,
            latency_ms=10,
        )


class DotsOCRAdapterTests(unittest.TestCase):
    def test_extract_parses_structured_json_and_review_required(self) -> None:
        payload = (
            '{"raw_text":"ACME INVOICE","structured_payload":{"vendor_name":"ACME","total":123.45},'
            '"confidence_map":{"vendor_name":0.98,"total":0.81}}'
        )
        adapter = DotsOCRAdapter(client=_StubVLLMClient(payload), model_name="dots.ocr")

        result = adapter.extract(
            document_content=b"fake-image-bytes",
            mime_type="image/png",
            filename="invoice.png",
            doc_type_hint="invoice",
        )

        self.assertEqual(result.raw_text, "ACME INVOICE")
        self.assertEqual(result.structured_payload["vendor_name"], "ACME")
        self.assertTrue(result.review_required)

    def test_extract_handles_non_json_response(self) -> None:
        adapter = DotsOCRAdapter(client=_StubVLLMClient("plain text output"), model_name="dots.ocr")

        result = adapter.extract(
            document_content=b"fake-image-bytes",
            mime_type="image/png",
            filename="receipt.png",
            doc_type_hint="receipt",
        )

        self.assertEqual(result.raw_text, "plain text output")
        self.assertEqual(result.structured_payload, {})
        self.assertEqual(result.confidence_map, {})
        self.assertTrue(result.review_required)


if __name__ == "__main__":
    unittest.main()
