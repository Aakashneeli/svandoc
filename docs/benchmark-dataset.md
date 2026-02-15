# Benchmark Dataset (T-046)

This repository includes a versioned synthetic benchmark dataset for extraction quality checks.

## Location

- Manifest: `datasets/benchmark/v1/manifest.json`
- Files: `datasets/benchmark/v1/samples/`

## Coverage

Each document type includes these variants:

1. `clean`
2. `noisy`
3. `rotated`
4. `multilayout`

Document types included:

1. `invoice`
2. `receipt`

Each sample includes both `PNG` and `PDF` versions.

## Regeneration

To regenerate samples and checksums:

```powershell
$env:PYTHONPATH='backend/src'
myvenv\Scripts\python.exe scripts/generate-benchmark-dataset.py
```

The script overwrites the `v1` sample files and updates `manifest.json`.

## Quality Evaluation

Ground-truth labels for the dataset live in:

- `datasets/benchmark/v1/ground_truth.json`

Run extraction quality evaluation (precision/recall/F1 by field and doc type):

```powershell
$env:QUALITY_EVAL_GROUND_TRUTH_PATH="datasets/benchmark/v1/ground_truth.json"
$env:QUALITY_EVAL_PREDICTIONS_PATH=".local-sandbox/quality-predictions.json"
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/quality-eval.ps1
```

Expected predictions input shape:

```json
{
  "version": "pred-v1",
  "samples": [
    {
      "sample_id": "invoice_clean_001",
      "doc_type": "invoice",
      "fields": {
        "vendor.name": "ACME Industrial Supply",
        "amounts.total": 1085.0
      }
    }
  ]
}
```
