# Email Intake Runbook

Last updated: 2026-02-16

## Overview

svanDoc supports email-based intake via:

- `POST /api/documents/email-intake`

The endpoint accepts a forwarded RFC822 message (`.eml`), validates the workspace address, extracts attachments, applies upload safeguards, and creates queued processing jobs.

## Workspace-specific ingestion address

Ingestion address formula:

`<team_id>@<EMAIL_INGESTION_DOMAIN>`

Example:

- `team_a@ingest.svandoc.local`

If the inbound `To` address does not match the caller workspace (`x-team-id`), intake is rejected.

## Safeguards

1. Sender domain allow-list (optional):
- `EMAIL_ALLOWED_SENDER_DOMAINS=trusted.example,partner.example`
2. Attachment count limit:
- `EMAIL_MAX_ATTACHMENTS=10`
3. Existing upload validations:
- file type
- file size
- page-count limits
4. Duplicate detection:
- duplicate in same email
- already existing document checksum

## Request example

`multipart/form-data`:
- `message`: `forwarded.eml` (content type `message/rfc822`)

Headers:
- `x-team-id`: workspace/team identifier
- `x-user-id`: actor identifier (optional, defaults to `local-user`)

## Response

Success payload includes:
- `document_ids`
- `job_ids`
- `to_address`
- `subject`
