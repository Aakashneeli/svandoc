import unittest

from svandoc_backend.chandra_ocr import ChandraOCRAdapter
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
            latency_ms=18,
        )


class ChandraOCRAdapterTests(unittest.TestCase):
    def test_extract_handles_hard_sample_payload(self) -> None:
        hard_sample_payload = (
            '{"raw_text":"MULTI COLUMN INVOICE","structured_payload":{"line_items":[{"description":"Part A","qty":2,"amount":88.4}],'
            '"tax_breakdown":{"state_tax":5.25,"city_tax":1.14}},'
            '"confidence_map":{"line_items":[{"description":0.89,"qty":0.94,"amount":0.86}],"tax_breakdown":{"state_tax":0.88,"city_tax":0.87}}}'
        )
        adapter = ChandraOCRAdapter(client=_StubVLLMClient(hard_sample_payload), model_name="chandra")

        result = adapter.extract(
            document_content=b"complex-layout-sample",
            mime_type="image/png",
            filename="hard-sample.png",
            doc_type_hint="invoice",
        )

        self.assertEqual(result.model, "chandra")
        self.assertIn("line_items", result.structured_payload)
        self.assertFalse(result.review_required)


if __name__ == "__main__":
    unittest.main()
