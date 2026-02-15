# Cloud Storage Connectors

Last updated: 2026-02-15

svanDoc supports direct export artifact delivery to:
1. Google Drive (`format=gdrive`)
2. OneDrive (`format=onedrive`)
3. Dropbox (`format=dropbox`)

## API Request

`POST /api/documents/{id}/export`

```json
{
  "format": "gdrive",
  "cloud_access_token": "oauth-access-token",
  "cloud_folder": "optional-target-folder",
  "cloud_filename": "optional-file-name.json"
}
```

Supported `format` values for cloud delivery:
1. `gdrive`
2. `onedrive`
3. `dropbox`

Required:
1. `cloud_access_token`

Optional:
1. `cloud_folder`
2. `cloud_filename`

## Delivery Status Tracking

`export_artifacts` now tracks:
1. `format`
2. `storage_uri`
3. `delivery_status` (`pending`, `completed`, `failed`)

Failure behavior:
1. Connector failure returns `502 EXPORT_DELIVERY_FAILED`.
2. Failed attempts are persisted in `export_artifacts` with `delivery_status=failed`.

## Audit Endpoint

`GET /api/documents/{id}/audit` export entries include:
1. `format`
2. `storage_uri`
3. `delivery_status`
4. `created_by`
5. `created_at`

