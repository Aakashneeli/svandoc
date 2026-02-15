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
