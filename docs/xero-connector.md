# Xero Connector

This document covers task `T-068`.

svanDoc supports direct Xero sync through export endpoint format `xero`.

## Endpoint

`POST /api/documents/{document_id}/export`

Request body:

```json
{
  "format": "xero",
  "xero_access_token": "<oauth-access-token>",
  "xero_tenant_id": "<xero-tenant-id>"
}
```

## Mapping

svanDoc maps canonical extraction fields to Xero bill payload (`Invoices`, type `ACCPAY`):

1. Vendor/merchant name -> `Contact.Name`
2. Invoice/receipt reference -> `Reference`
3. Amount total -> line totals and document totals
4. Tax amount -> `TotalTax`

## Idempotent Retry Behavior

1. Connector computes deterministic idempotency key from `document_id + payload`.
2. Same key is sent on each retry via `Idempotency-Key` header.
3. Retry policy covers transient failures (`429`, `5xx`) with exponential backoff.

## Reconciliation Logs

Each sync attempt is persisted in `xero_sync_logs` with:

1. `artifact_id`
2. `document_id`
3. `idempotency_key`
4. `attempt_number`
5. `sync_status` (`retrying`, `synced`, `failed`)
6. `external_reference` (Xero invoice id when synced)
7. `error_message`

## Configuration

`.env`:

1. `XERO_API_BASE_URL` (optional, defaults to Xero production API).
