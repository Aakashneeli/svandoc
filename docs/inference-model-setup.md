# Inference Model Provisioning (Hugging Face + Dual vLLM)

Last updated: 2026-02-15

This runbook provisions the canonical OCR models used by svanDoc:

1. Primary: `FL33TW00D-HF/dots.ocr`
2. Fallback: `datalab-to/chandra`

svanDoc expects dual endpoints:

1. Primary endpoint: `VLLM_BASE_URL` (default `http://localhost:11434/v1`)
2. Fallback endpoint: `VLLM_FALLBACK_BASE_URL` (default `http://localhost:11435/v1`)

## 1) Prerequisites

1. Python environment with `vllm` installed for inference serving.
2. NVIDIA GPU and CUDA-compatible drivers.
3. Hugging Face account (and access approval if either model is gated).

## 2) Recommended Cache Paths (Windows)

Set cache paths to repo-local or dedicated disk paths to avoid permission and space issues:

```powershell
$env:HF_HOME="D:\ml-cache\hf-home"
$env:HUGGINGFACE_HUB_CACHE="D:\ml-cache\hf-hub"
$env:TRANSFORMERS_CACHE="D:\ml-cache\transformers"
```

## 3) Hugging Face Authentication

```powershell
huggingface-cli login
```

Verify model pages are reachable from this machine:

1. `https://huggingface.co/FL33TW00D-HF/dots.ocr`
2. `https://huggingface.co/datalab-to/chandra`

## 4) Start Primary vLLM Server (`dots.ocr`)

Run in terminal window A:

```powershell
python -m vllm.entrypoints.openai.api_server `
  --model FL33TW00D-HF/dots.ocr `
  --served-model-name FL33TW00D-HF/dots.ocr `
  --host 0.0.0.0 `
  --port 11434
```

## 5) Start Fallback vLLM Server (`chandra`)

Run in terminal window B:

```powershell
python -m vllm.entrypoints.openai.api_server `
  --model datalab-to/chandra `
  --served-model-name datalab-to/chandra `
  --host 0.0.0.0 `
  --port 11435
```

## 6) `.env` Contract

Use these values in `.env`:

```powershell
VLLM_BASE_URL=http://localhost:11434/v1
VLLM_FALLBACK_BASE_URL=http://localhost:11435/v1
OCR_DEFAULT_MODEL=FL33TW00D-HF/dots.ocr
OCR_FALLBACK_MODEL=datalab-to/chandra
```

## 7) GPU and VRAM Guidance

1. Run one model per process/GPU when possible; avoid sharing a low-memory GPU between both servers.
2. Full-precision checkpoints may require high VRAM and can OOM on smaller cards.
3. If OOM occurs:
   - stop one server and validate one model at a time,
   - reduce context length/throughput settings in vLLM,
   - or use an explicitly documented quantized variant for local dev only.
4. Keep canonical upstream IDs as defaults; treat quantized/community repos as non-default overrides.

## 8) Troubleshooting

1. `401/403` on model pull:
   - re-run `huggingface-cli login`,
   - confirm account access to model repo.
2. `CUDA out of memory`:
   - run a single model server first,
   - reduce vLLM memory pressure,
   - switch to lower-footprint model variant for local smoke testing.
3. Connection failures from backend:
   - verify both ports (`11434`, `11435`) are listening,
   - verify `.env` URLs include `/v1`,
   - verify model names in `.env` match served model names exactly.
4. Slow startup:
   - first launch downloads model weights; subsequent launches reuse cache paths.

## 9) Smoke Validation

Run the repo smoke validator after both servers are up:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File backend/scripts/inference-smoke.ps1
```

Expected:

1. Exit code `0`
2. Evidence file written at `.local-sandbox/inference-smoke.json` (or `INFERENCE_SMOKE_OUTPUT_PATH`)
3. `overall_success=true` with one successful completion check per model endpoint
