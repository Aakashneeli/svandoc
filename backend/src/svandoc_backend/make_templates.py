"""Make.com integration template helpers."""

from __future__ import annotations

from typing import Any


def build_make_templates(*, api_base_url: str) -> list[dict[str, Any]]:
    base = api_base_url.rstrip("/")
    return [
        {
            "id": "upload_to_status_polling",
            "name": "Upload Documents and Poll Job Status",
            "description": "Uploads one or more files to svanDoc, then polls for completion status.",
            "modules": [
                {
                    "type": "http",
                    "name": "Upload Documents",
                    "method": "POST",
                    "url": f"{base}/api/documents/upload",
                    "headers": {"x-user-role": "editor"},
                    "body_type": "multipart/form-data",
                },
                {
                    "type": "iterator",
                    "name": "Iterate Job IDs",
                    "source_path": "data.job_ids[]",
                },
                {
                    "type": "http",
                    "name": "Get Job Status",
                    "method": "GET",
                    "url": f"{base}/api/jobs/{{{{job_id}}}}",
                    "headers": {"x-user-role": "viewer"},
                },
            ],
            "expected_outcome": "Completed jobs produce document IDs for downstream review/export.",
        },
        {
            "id": "completed_job_to_export",
            "name": "Completed Job to Export Artifact",
            "description": "Consumes a completed job event and exports document output in desired format.",
            "modules": [
                {
                    "type": "webhook",
                    "name": "Receive job.completed",
                    "event_type": "job.completed",
                },
                {
                    "type": "http",
                    "name": "Fetch Extraction",
                    "method": "GET",
                    "url": f"{base}/api/documents/{{{{document_id}}}}/extraction",
                    "headers": {"x-user-role": "viewer"},
                },
                {
                    "type": "http",
                    "name": "Create Export",
                    "method": "POST",
                    "url": f"{base}/api/documents/{{{{document_id}}}}/export",
                    "headers": {"x-user-role": "editor"},
                    "json_body": {"format": "json"},
                },
            ],
            "expected_outcome": "Export artifact URI is generated for automation handoff.",
        },
    ]
