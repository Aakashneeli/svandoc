from __future__ import annotations

import os
from uuid import uuid4
from pathlib import Path

from svandoc_sdk import SvanDocClient


def main() -> int:
    api_base_url = os.getenv("SVANDOC_API_BASE_URL", "http://localhost:8000").strip()
    api_key = os.getenv("SVANDOC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SVANDOC_API_KEY is required.")

    client = SvanDocClient(api_base_url=api_base_url, api_key=api_key)
    sandbox_dir = Path(".local-sandbox")
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    sample_path = sandbox_dir / f"sdk-sample-{uuid4().hex}.pdf"
    sample_path.write_bytes(b"%PDF-1.7 sample quickstart")
    try:
        upload_data = client.upload_document(file_path=sample_path)
    finally:
        sample_path.unlink(missing_ok=True)

    document_id = upload_data["document_ids"][0]
    job_id = upload_data["job_ids"][0]
    job = client.get_job(job_id)
    extraction = client.get_extraction(document_id)
    export = client.export_document(document_id, export_format="json")

    print("upload.document_id", document_id)
    print("job.status", job.get("status"))
    print("extraction.doc_type", extraction.get("doc_type"))
    print("export.storage_uri", export.get("storage_uri"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
