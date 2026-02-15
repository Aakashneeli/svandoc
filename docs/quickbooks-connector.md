# QuickBooks Online Connector

This document covers task `T-067`.

svanDoc supports direct QuickBooks Online sync through export endpoint format `quickbooks`.

## Endpoint

`POST /api/documents/{document_id}/export`

Request body:

```json
{
  "format": "quickbooks",
  "quickbooks_access_token": "<oauth-access-token>",
  "quickbooks_realm_id": "<company-realm-id>"
}
```

## Mapping Rules

Canonical extraction payload is mapped to QuickBooks `Purchase` payload:

1. Vendor mapping:
   Invoice `vendor.name` or receipt `merchant.name` -> `VendorRef.name`.
2. Amount mapping:
   `amounts.total` -> `TotalAmt`.
3. Tax mapping:
   `amounts.tax` -> `TxnTaxDetail.TotalTax`.
4. Reference mapping:
   Invoice `invoice.invoice_number` or receipt `receipt.receipt_number` -> `DocNumber`.
5. Source trace:
   `metadata.document_id` -> `PrivateNote`.

## Delivery and Tracking

1. Success persists `export_artifacts` row with `format=quickbooks` and `storage_uri=quickbooks://<realm>/<purchase_id>`.
2. Connector failures persist `delivery_status=failed` and return `502 EXPORT_DELIVERY_FAILED`.
3. `export.created` webhook is emitted for both successful and failed QuickBooks export attempts.

## Configuration

`.env`:

1. `QUICKBOOKS_API_BASE_URL` (optional, defaults to Intuit production API).
